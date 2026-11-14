# ADR 0008 — Biometria facial na retirada e na devolução

- Tarefa: SIGAB-083. Insumo técnico: [pesquisa 0002](../pesquisas/0002-verificacao-facial-no-balcao.md) (SIGAB-084).
- Requisitos relacionados: RF-05 (substituído na obrigatoriedade), RF-20 a RF-22, RF-26, RF-60, RN-06, RN-07, RNF-01, RNF-04, RNF-06.
- Status: **decisões de produto tomadas e desenho implementado (SIGAB-085/086, 13/11/2026); aprovação de Segurança e Jurídico pendente para produção.** A obrigatoriedade (seção 1) e o termo com aprovação do administrador (seção 8) são decisões do responsável pelo produto, de 13/11/2026. Quem registrou a operação não aprova o próprio termo, por segregação de funções. Antes da produção, o cliente precisa de RIPD, aviso ao titular e a medição da SIGAB-084. Precisam aprovar, com registro de nome e data abaixo: o responsável pelo produto, a Segurança e o Jurídico (no cliente, o encarregado de dados). Até a aprovação, nada desta decisão está vigente, e as tarefas SIGAB-085 e SIGAB-086 não começam.

## Contexto

Na revisão de 12/11/2026, o responsável pelo produto informou que o cliente definiu a biometria **facial** como forma de identificar quem retira e quem devolve material. Em 13/11/2026, definiu que essa validação é **obrigatória** na retirada e na devolução. Isso substitui o RF-05 do DOC-0011, que previa biometria opcional com alternativa sem biometria para toda operação.

Biometria é dado pessoal sensível (LGPD, art. 5º, II, e art. 11). A [política de dados pessoais](../politica-de-dados-pessoais.md) hoje declara que o SIGAB não trata biometria e exige revisão da política e do modelo de ameaças antes de qualquer código.

Restrições que a decisão precisa respeitar:

- o sistema é exclusivamente online e cai para papel quando o servidor está indisponível (ADR 0004);
- cada cliente tem instalação própria e o produto é revendido por instalação (ADR 0007);
- a devolução nunca pode ser impedida (RN-07);
- uma restrição ativa sempre impede a saída (RN-06).

## Decisão proposta

### 1. Obrigatoriedade

**A validação por biometria facial é obrigatória na retirada e na devolução** (decisão do responsável pelo produto, 13/11/2026).

- O sistema só confirma uma retirada ou uma devolução com verificação facial **aprovada** da pessoa selecionada.
- Não há modo opcional nem configuração para desligar a exigência por instalação.
- Quando a biometria não for possível, a única alternativa é o termo assinado pelo servidor e aprovado pelo administrador do acervo (seção 8).
- A pessoa precisa ter biometria cadastrada (SIGAB-085) antes da primeira retirada.
- A verificação não substitui a permissão do operador.
- A verificação não afrouxa restrições: pessoa com restrição ativa não retira material, mesmo com verificação aprovada (RN-06).
- Com o servidor indisponível, o sistema inteiro fica fora do ar e vale a contingência em papel do ADR 0004 (seção 8).

### 2. Modo de reconhecimento

Apenas **verificação 1:1**: o operador seleciona a pessoa, e o sistema compara a captura com o modelo dessa pessoa. A identificação 1:N (descobrir quem é a pessoa pela face) não será implementada.

### 3. Prova de vida

Detecção passiva na captura, somada à **conferência visual obrigatória do operador**, que fica registrada como parte do método. Como a validação é obrigatória, a entrada em produção depende da medição da SIGAB-084. Se a meta contra ataques com foto não for atingida, será preciso usar um motor com certificação ISO/IEC 30107-3.

### 4. Equipamento e captura

Webcam comum do balcão. A captura acontece no navegador e é enviada por HTTPS ao servidor da própria instalação. Nada fica no navegador: sem cache, sem armazenamento local e sem imagem em `sessionStorage`. A prévia mostra uma moldura oval para enquadrar o rosto, e só a área dessa moldura (com uma margem para o detector) é enviada; fundo e pessoas ao lado ficam fora da imagem. A mesma moldura vale para cadastro e verificação.

### 5. Processamento

**Local**, no servidor da instalação, por um motor isolado atrás de uma interface própria, que permite trocá-lo. A recomendação inicial é OpenCV YuNet + SFace (Apache 2.0); um SDK comercial certificado é a alternativa.

Nenhum serviço externo de nuvem. Com isso:

- a decisão fica compatível com o ADR 0004: não surge um ponto de falha além do próprio servidor;
- fica compatível com a revenda (ADR 0007): não há custo variável por chamada;
- o dado não sai do controlador.

### 6. O que é armazenado

- **Somente o modelo biométrico** (vetor numérico), nunca a imagem. A imagem é processada em memória e descartada na mesma requisição.
- O modelo é criptografado na aplicação com uma chave separada do banco, fornecida pelo ambiente da instalação. Junto dele ficam a versão do motor e a data do cadastro.
- Cada modelo fica vinculado a uma pessoa e à organização.
- Retenção: enquanto a pessoa tiver vínculo ativo. Ao encerrar o último vínculo, o modelo é apagado.
- Exclusão a pedido do titular ou do gestor autorizado: o modelo é apagado de forma definitiva, não por desativação lógica. A auditoria registra a exclusão sem o dado.
- Backups seguem a rotação definida na SIGAB-042. O RIPD deve registrar o prazo de expiração dos modelos nos backups.

### 7. Base legal e governança

- Proposta de base legal: **LGPD, art. 11, II, "g"**: garantia da prevenção à fraude e da segurança do titular nos processos de identificação e autenticação de cadastro em sistemas eletrônicos.
- O Jurídico de cada cliente confirma a base legal, ou a substitui por outra hipótese do art. 11 aplicável ao poder público, antes da ativação.
- O cliente é o controlador e nomeia o responsável (encarregado). O fornecedor é operador.
- **Antes de entrar em produção**, o cliente precisa ter um RIPD (relatório de impacto, LGPD art. 38) aprovado. O aviso ao titular deve informar a finalidade, a retenção e que a validação é obrigatória para retirar e devolver material.
- O cadastro, o recadastro e a exclusão exigem uma permissão explícita nova (`biometric.manage`), negada por padrão.

### 8. Quando a biometria não for possível: termo assinado e aprovação do administrador

Decisão do responsável pelo produto, 13/11/2026. Vale para a retirada e para a devolução.

Quando não for possível validar por biometria (verificação recusada depois de novas tentativas, câmera indisponível ou pessoa ainda sem cadastro):

1. **O operador gera um termo** da operação no sistema. O termo contém:
   - código único do termo;
   - tipo da operação (retirada ou devolução);
   - nome e matrícula do servidor público (nunca CPF completo);
   - materiais, com número de série ou patrimônio, quantidades e condição na devolução;
   - unidade, data e hora, operador;
   - motivo pelo qual a biometria não foi possível.
2. **O servidor público assina o termo** impresso, à mão. O operador registra no sistema que o termo assinado foi recolhido.
3. **Somente o administrador do acervo aprova.** A aprovação exige a permissão explícita `movement.exception.approve`, concedida só ao papel de administrador do acervo, sem herança implícita de outros papéis. O administrador confere o termo assinado e aprova ou recusa, informando o motivo da recusa.
4. **Só a aprovação confirma a operação.** Até lá:
   - a retirada não acontece: o material não sai da reserva;
   - na devolução, o material fica guardado na reserva, mas a posse continua com o servidor no sistema e aparece como "devolução aguardando aprovação".
   - Na aprovação, o sistema revalida tudo na mesma transação: disponibilidade, posse, restrição ativa (RN-06) e escopo do aprovador. Se algo mudou, a aprovação falha e nada é confirmado.
   - A recusa encerra o pedido sem movimentação.
   - Cada termo é aprovado ou recusado uma única vez, com chave de idempotência e bloqueio; aprovações concorrentes aceitam exatamente uma.
5. **Registro:** o termo, o pedido, a aprovação ou recusa, o aprovador e os instantes ficam na trilha de auditoria. O termo assinado em papel é arquivado pela reserva. A digitalização e anexo do termo e a assinatura eletrônica ficam fora deste incremento, como anexos e assinatura definitiva no escopo do produto.

**Contingência:** quando o servidor ou a rede estiverem indisponíveis, o sistema inteiro fica fora do ar e a reserva passa ao papel (ADR 0004). O lançamento posterior registra o método `paper_contingency`.

### 9. Registro na movimentação e na auditoria

- A movimentação e a auditoria registram apenas:
  - o método (`facial`, `signed_term` ou `paper_contingency`);
  - o resultado (`approved`; `not_attempted` só no lançamento de contingência e nos registros anteriores à adoção);
  - no método `signed_term`: código do termo, motivo da falha da biometria, aprovador e instante da aprovação;
  - a versão do motor.
- Imagem, modelo e pontuação bruta de similaridade nunca vão para log, evento, auditoria, mensagem de erro ou comprovante.
- Uma verificação aprovada gera um comprovante de uso único e curta validade (10 minutos por padrão, `SIGAB_FACE_VERIFICATION_TTL_SECONDS`). Ele fica vinculado a organização, pessoa, operador e tipo de operação, e é consumido na mesma transação da movimentação. Assim, a idempotência e a atomicidade existentes continuam valendo, e a verificação de uma pessoa não pode ser usada para outra pessoa ou outra organização.

## Consequências

- **Antes do código da SIGAB-085:** atualizar a política de dados pessoais (seção 3) e o modelo de ameaças. Ameaças a cobrir: vazamento do modelo, ataque com foto, reaproveitamento de verificação e acesso indevido ao cadastro.
- **Novas migrações:** modelo biométrico, configuração da instalação e campos de método e resultado na movimentação e no atendimento. As movimentações já confirmadas não são alteradas; registros anteriores à adoção ficam como `not_attempted`.
- **Tarefas:**
  - a SIGAB-071 registra o destino da biometria: decidida como facial, local, 1:1 e obrigatória na retirada e na devolução;
  - a SIGAB-085 implementa o cadastro;
  - a SIGAB-086 implementa a verificação;
  - a medição da SIGAB-084 (protocolo da seção 6 da pesquisa) é pré-requisito para entrar em produção.
- **Implantação:** antes de ativar, todas as pessoas que retiram ou devolvem material devem ter biometria cadastrada. Quem não tiver cadastro passa pelo termo com aprovação do administrador, o que sobrecarrega o administrador nos primeiros dias.
- **Nova permissão** `movement.exception.approve`, a incluir na matriz de permissões e no papel de administrador do acervo.
- **Dependência da câmera:** com a validação obrigatória, câmera e motor de verificação passam a ser pré-requisito da operação do balcão. A instalação precisa de câmera reserva.
- **Reversibilidade:** voltar a uma alternativa sem biometria exige nova decisão de produto e alteração de código. Já apagar os modelos de todas as pessoas é irreversível por definição e deve ser a ação padrão ao desativar a biometria de forma permanente.

## Alternativas consideradas

- **Biometria opcional por instalação, com alternativa por documento conferido pelo próprio operador** (proposta inicial deste ADR e RF-05): substituída pela decisão de 13/11/2026. A biometria é obrigatória, e a única alternativa é o termo assinado pelo servidor e aprovado pelo administrador do acervo.
- **Serviço em nuvem (AWS Rekognition, Azure Face, Serpro Datavalid):** descartado para o MVP. Cria dependência de rede além do servidor, operador externo de dado sensível e custo por chamada. No caso do Azure, o acesso depende de aprovação discricionária. Ver pesquisa 0002.
- **Identificação 1:N:** descartada. Aumenta risco e impacto sem necessidade no balcão, porque o operador já sabe quem atende.
- **Guardar a imagem para conferência posterior:** descartado. Multiplica o dado sensível retido sem ganho para a prova do fato, que já está na movimentação e no método registrado.

## Aprovação

| Papel | Nome | Data | Decisão |
|---|---|---|---|
| Responsável pelo produto | | | |
| Segurança | | | |
| Jurídico / encarregado do cliente | | | |

## Revisão de 13/11/2026: entrada e saída pela matrícula

- O balcão começa pela identificação: no Início, "Entrada e saída" pede a matrícula (busca exata, `GET /counter/identify/`), o operador escolhe saída (retirada) ou entrada (devolução) e o painel faz o reconhecimento facial 1:1 antes da escolha dos materiais.
- Como os materiais são escolhidos depois da verificação, a validade passou de 2 para 10 minutos (configurável). Continua de uso único e vinculada a pessoa, operador, operação e organização, consumida na transação da movimentação; depois de qualquer tentativa de confirmação o navegador descarta o identificador.
- Sem biometria cadastrada ou possível, o painel leva à operação já com a pessoa selecionada, e a confirmação segue pelo termo da seção 8.
- O cadastro de pessoa passou a aceitar o primeiro vínculo e a captura facial no mesmo passo; a face só é gravada depois que pessoa e vínculo existem.
- Depois da identidade confirmada, o operador pode cancelar a operação: a verificação é invalidada no servidor (auditoria `face.verification.cancelled`) e não autoriza mais nenhuma movimentação. Verificação já usada não é cancelada.
- Só o rosto de quem retira ou devolve (o servidor) é verificado; o operador não faz reconhecimento facial, apenas a conferência visual.
- O operador também tem biometria cadastrada, mas ela só serve para as retiradas e devoluções dele próprio, que são sempre registradas por **outro operador**. O sistema recusa (`409`) a operação, a verificação facial e o termo em que a pessoa atendida é a da conta do operador, inclusive no lançamento de contingência; a identificação pela matrícula avisa antes.
