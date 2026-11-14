# Política de dados pessoais

- Tarefa: SIGAB-039
- Revisão: 2026-11-02, conferida com `backend/sigab/models.py`
- Requisito: RNF-04 do [DOC-0011 v0.1](fontes/DOC-0011-analise-de-requisitos-v0.1.md)
- Base: OBR-11 e OBR-12 da [nota regulatória 0001](notas-regulatorias/0001-guardas-municipais.md), [matriz de papéis 0002](decisoes/0002-papeis-e-escopos.md), [modelo de ameaças](modelo-de-ameacas.md), [observabilidade](observabilidade.md)
- Estado: **proposta técnica**. Bases legais e prazos dependem do Jurídico do Município, do Encarregado e da tabela de temporalidade municipal (OBR-11), que ainda não foram obtidos

## 1. Papéis no tratamento

| Papel LGPD | Quem | Responsabilidade aqui |
|---|---|---|
| Controlador | o Município (organização cliente) | finalidade, base legal, retenção, atendimento ao titular, Encarregado |
| Operador | fornecedor do SIGAB, quando trata dados em nome do Município (conforme contrato) | segurança, minimização técnica, registro das operações, apoio a incidentes; não usa os dados para finalidade própria |
| Encarregado | indicado pelo Município | canal com titulares e ANPD |

Cada organização é um controlador distinto; dados de uma nunca são acessíveis a outra (RF-01, RNF-05).

## 2. Finalidade e base legal comuns

Finalidade única: controlar a guarda, a entrega e a devolução de material bélico institucional e responsabilizar quem o detém, como sistema auxiliar do controle patrimonial e do SINARM (nota regulatória, itens 1 e 3). Base legal proposta: execução de competência legal e políticas públicas pelo poder público (LGPD, art. 7º, III, e art. 23) e cumprimento de obrigação legal (art. 7º, II) quanto ao controle de armas. **A confirmar pelo Jurídico.**

Nenhum dado é usado para perfilamento, propaganda ou finalidade alheia ao controle do acervo.

## 3. Matriz de dados

Retenção “histórica” significa: enquanto existir o registro patrimonial do item ou movimentação que referencie a pessoa, e depois conforme a tabela de temporalidade municipal. **Nada é eliminado automaticamente** até a tabela existir (OBR-11). Desativar pessoa, vínculo ou conta não apaga dados.

| Dado | Onde | Finalidade | Quem acessa | Retenção | Descarte | Responsável |
|---|---|---|---|---|---|---|
| nome, nome funcional | `Person` | identificar quem recebe e devolve | `identity.manage`; nome de exibição para `person.view_minimal`, `movement.checkout` e quem lê histórico do item | histórica | anonimização após a tabela, preservando o fato patrimonial | Município |
| CPF | `Person.cpf` | desambiguar pessoas homônimas (RN-01) | gravação por `identity.manage`; **nunca** exibido completo; API mostra só os 2 últimos dígitos | enquanto houver vínculo ativo ou movimentação a desambiguar; opcional | apagar o campo quando deixar de ser necessário, após a tabela | Município |
| telefone | `Person.phone` | contato funcional | `identity.manage` | enquanto ativo | apagar ao desligamento, salvo exigência da tabela | Município |
| matrícula, posto, unidade | `Membership` | vínculo funcional e escopo | `identity.manage`; matrícula também para `person.view_minimal` | histórica | conforme tabela | Município |
| usuário, e-mail, hash de senha | `Account` | autenticação | `identity.manage` vê usuário e e-mail; o hash não é exposto | enquanto a conta existir; revogação torna a senha inutilizável | conta revogada mantida para a trilha | Município (gestão), fornecedor (segurança) |
| último acesso | `Account.last_login` | segurança da conta | `identity.manage` | enquanto a conta existir | junto com a conta | Município |
| usuário digitado em falha de login | `AuthenticationFailure.username_digest` | limitar tentativas | ninguém pela interface | 1 dia | apagado automaticamente | fornecedor |
| endereço IP | `AuthenticationFailure.ip_address` | limitar tentativas | ninguém pela interface | 1 dia | apagado automaticamente | fornecedor |
| ator, ação, instante, motivo | `AuditEvent`, `MovementEvent`, `Movement` | prova de quem fez o quê (RF-60, RF-62) | `audit.view` na organização; histórico do item para `item.view` | histórica, imutável (ADR 0006) | só por rotina arquivística formal, nunca por exclusão comum | Município |
| conta e organização no log técnico | saída do processo | diagnóstico | operação do fornecedor | a definir na implantação (sugestão: 90 dias) | rotação do coletor | fornecedor |

Dados **não** tratados: biometria, diagnóstico, laudo, decisão judicial, endereço, documentos anexos. Introduzir qualquer um deles exige revisão desta política e do modelo de ameaças antes do código.

**Biometria facial: implementada, aguardando aprovação jurídica para produção.** O [ADR 0008](adr/0008-biometria-facial.md) define o tratamento. O código existe (SIGAB-085/086) e o modelo de ameaças foi revisto (seção 3.6). Nenhuma instalação deve entrar em produção com biometria antes de três passos: aprovação do Jurídico e do encarregado do cliente, RIPD e aviso ao titular.

| Dado | Onde | Finalidade | Acesso | Retenção | Descarte | Responsável |
|---|---|---|---|---|---|---|
| modelo biométrico facial (vetor, sem imagem), criptografado com chave fora do banco | `BiometricTemplate` | confirmar a identidade de quem retira ou devolve; obrigatório nas duas operações (decisão de 13/11/2026) | cadastro e exclusão por `biometric.manage`; uso só pelo motor local de verificação 1:1; nunca exibido nem exportado | enquanto houver vínculo ativo | exclusão definitiva ao encerrar o último vínculo ou a pedido; auditoria sem o dado | cliente (controlador) |
| resultado de verificação facial (aprovada ou recusada, sem pontuação), operador, operação e instante | `FaceVerification` | provar a identificação de quem retira ou devolve | operador que verificou; trilha `audit.view` | histórica, como a movimentação | não apagada; não contém dado biométrico | cliente (controlador) |
| termo sem biometria (pessoa, matrícula, materiais, motivo, decisão) | `IdentityException` e termo em papel arquivado na reserva | alternativa quando a biometria não for possível | quem registrou e `movement.exception.approve` | histórica | conforme tabela de temporalidade | cliente (controlador) |

## 4. Regras de acesso e exibição

- Telas operacionais mostram nome de exibição e matrícula; CPF e telefone ficam só na ficha da pessoa, para `identity.manage`.
- Busca e listas operacionais nunca retornam CPF nem telefone.
- Log técnico registra só UUIDs; CPF e segredos são mascarados por `redact()`.
- Auditoria de alteração de dado pessoal registra o **nome** do campo, não o valor (ADR 0006).

## 5. Direitos do titular

| Pedido | Como atender hoje |
|---|---|
| confirmação e acesso | o Município consulta a ficha da pessoa e o histórico de posse (`/api/v1/items/?holder=`, feed por pessoa) |
| correção | edição cadastral auditada (`PATCH /people/<id>/`) |
| eliminação | limitada pela finalidade pública e pela tabela arquivística; fatos confirmados não são apagados (LGPD, art. 16, I, e OBR-11) |
| portabilidade e exportação | depende da tarefa de exportação (ameaça V-01) |

## 6. Exportação

Não existe exportação. Quando existir: permissão própria (`audit.export` para trilha; permissão a definir para acervo), filtro por organização e escopo, sem CPF por padrão, auditoria de cada exportação com filtros usados.

## 7. Pendências

- Base legal, prazos e destinação validados pelo Jurídico e pelo Encarregado do Município.
- Tabela de temporalidade municipal e rotina auditável de eliminação ou anonimização.
- Retenção do log técnico, definida com a implantação.
- Contrato controlador–operador com o Município.
- Biometria facial: aprovação do [ADR 0008](adr/0008-biometria-facial.md), base legal (proposta: art. 11, II, "g"), RIPD e aviso ao titular antes de qualquer ativação.
