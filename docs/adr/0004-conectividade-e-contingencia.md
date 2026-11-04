# ADR 0004 — Conectividade online, contingência em papel e reconciliação

- Tarefa: SIGAB-006
- Requisitos relacionados: RNF-01; RNF-02 (texto no documento inicial de requisitos, não versionado neste repositório)
- Status: aceito por Arquitetura/Produto, 2026-10-19. As metas de RPO/RTO valem para o MVP e serão reavaliadas na validação com a organização-piloto.

## Contexto

O segmento inicial opera hoje em papel ([decisão 0001](../decisoes/0001-segmento-inicial.md)). A base técnica é um monólito Django com PostgreSQL e templates server-side ([ADR 0001](0001-stack-e-frontend.md)), cuja garantia central é uma única saída por item, obtida por transação, bloqueio de linha e chave de idempotência única ([ADR 0003](0003-eventos-idempotencia.md)). Essa garantia só existe enquanto todas as escritas passam pelo mesmo banco.

Foram consideradas três opções:

| Opção | Descrição | Avaliação |
|---|---|---|
| **Online centralizado** | navegador → servidor único → PostgreSQL | preserva a exclusão mútua no banco; depende de rede |
| Local por unidade | servidor instalado na rede da reserva | continua online do ponto de vista do navegador; transfere backup, atualização e segurança física ao Município; pode ser reavaliado por contrato sem mudar o modelo |
| Híbrido / offline-first | cliente grava localmente e sincroniza | exige resolução de conflitos, autenticação offline e dados de acervo bélico armazenados no dispositivo; duas reservas desconectadas podem aceitar a mesma saída |

## Decisão

1. **O MVP é exclusivamente online.** O PostgreSQL de produção é a única fonte de verdade do estado atual e do histórico registrado no sistema.
2. **Limites offline: nenhuma escrita sem servidor.** Não há PWA, service worker, fila local, cache de dados operacionais no navegador nem sincronização. Sem conexão, o SIGAB fica indisponível para leitura e escrita; não se exibe estado possivelmente desatualizado como se fosse atual.
3. **Contingência em papel.** Durante indisponibilidade, a reserva volta ao controle em papel já conhecido pelos armeiros, seguindo o procedimento abaixo. Durante a contingência, o registro em papel é a fonte de verdade dos fatos ocorridos naquele período.
4. **Reconciliação obrigatória e rastreável.** Os fatos em papel são lançados depois no sistema como registros de contingência, sem apresentar o instante do lançamento como instante da entrega. Implementado pela SIGAB-046 (ver Consequências).
5. **Metas de continuidade do MVP:**
   - **RPO ≤ 15 minutos** para dados confirmados no sistema. O `pg_dump` diário não atende sozinho; a produção precisa de arquivamento contínuo de WAL/PITR (ou serviço gerenciado equivalente) mais o dump lógico periódico. Fatos ocorridos durante a contingência não contam no RPO porque estão preservados no papel.
   - **RTO ≤ 4 horas** para restabelecer o serviço, em qualquer horário de operação da reserva. A operação da reserva não para nesse intervalo, porque prossegue em papel.
   - As metas serão verificadas pela SIGAB-042 (backup e teste de restauração).

## Prevenção de dupla entrega

- **No sistema:** mantém-se o ADR 0003, com transação, `select_for_update`, atualização condicional e chave de idempotência única por organização. Item em posse não sai de novo.
- **Contingência por reserva inteira:** a contingência é declarada para o local de guarda como um todo. Enquanto ela durar, nenhum operador daquele local registra no sistema, mesmo que o seu terminal volte a funcionar. É proibido misturar papel e sistema na mesma reserva ao mesmo tempo.
- **Um único livro por reserva:** usa-se uma única sequência de folhas numeradas, sem folhas paralelas em balcões diferentes.
- **Presença física:** em contingência, somente sai o item fisicamente presente na reserva e conferido pelo identificador (série/patrimônio).
- **Operação em curso no momento da queda:** se a confirmação foi enviada e não houve resposta, o resultado é incerto. O armeiro registra a operação no papel marcada como "resultado incerto". Ao retornar, consulta o histórico do item antes de lançar qualquer coisa. Reenviar o mesmo formulário reaproveita a chave de idempotência oculta e não duplica a operação.
- **Na reconciliação:** o lançamento passa pelas mesmas regras de estado. Conflito (por exemplo, o papel registra saída de um item que o sistema mostra em posse) não é forçado; é tratado como divergência e investigado.

## Procedimento de contingência

1. **Declaração:** o armeiro de serviço constata a indisponibilidade (falha de acesso confirmada em outro dispositivo ou rede, ou aviso do suporte) e registra no livro: início (data/hora local), reserva, operador e motivo. Comunica o administrador da organização.
2. **Operação:** cada saída ou devolução vira uma linha numerada com data/hora, identificador do item, destinatário (nome e matrícula, nunca CPF), modalidade, condição na devolução quando houver, operador e assinatura do destinatário. A linha não é rasurada; erro se corrige com nova linha que referencia a anterior.
3. **Encerramento:** com o sistema restabelecido, o armeiro registra o fim no livro. Nenhuma nova operação é lançada no sistema antes da reconciliação daquela reserva.
4. **Reconciliação:** lançam-se as linhas em ordem cronológica, com o número da folha/linha como referência. Lançamento e conferência são feitos por pessoas distintas quando houver dois operadores. As folhas originais são guardadas conforme a tabela de temporalidade municipal (SIGAB-039).
5. **Divergências:** ficam registradas e são resolvidas por evento compensatório, nunca por edição de movimento confirmado.

## Consequências

- **Lançamento de contingência (SIGAB-046, implementado em 2026-11-03):** saída e devolução aceitam o objeto `contingency` com instante do fato e folha/linha; `Movement.origin = contingency`, `declared_occurred_at` separado de `confirmed_at`, auditoria `item.checkout.contingency`/`item.return.contingency`, mesmas regras de estado, permissão, tenant e idempotência. Fato no futuro é inválido; fato igual ou anterior ao último registro em vigor do item, conflito de estado ou folha/linha já lançada na mesma reserva são recusados como divergência (409, auditoria `result = divergence`), nunca forçados. A declaração/encerramento da contingência por reserva e a conferência por segunda pessoa continuam procedimento em papel, sem controle no sistema. Contexto anterior: o modelo gravava `confirmed_at` no instante do registro e não tem origem "contingência", instante declarado do fato nem referência ao documento em papel. Até existir esse lançamento, uma queda gera uma de duas coisas: lançamentos com horário incorreto ou fatos ausentes do histórico. A tarefa SIGAB-046 ("Registrar movimentação de contingência") cobre esse lançamento, com o instante do fato separado do instante do registro, a referência à folha e um evento de auditoria específico. Ela deve ser concluída antes do uso com acervo real; até lá, o sistema serve a piloto e demonstração.
- Uma folha de situação atual para consulta durante a queda seria útil, mas é relatório/exportação e está fora do escopo; fica registrada como extensão futura.
- Qualquer proposta de operação offline ou híbrida exige novo ADR que substitua este, com modelo de conflito, autenticação offline e proteção de dados no dispositivo.
- A implantação local por unidade continua possível sem mudança de modelo, desde que atenda as mesmas metas de RPO/RTO.
- Ficam pendentes de validação com a organização: horários e duração das quedas toleradas, aceitação das metas, modelo do livro de contingência e exigências municipais sobre o documento em papel.
