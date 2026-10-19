# Nota regulatória 0001 — Guardas Municipais com acervo de armamentos e equipamentos

- Tarefa: SIGAB-005
- Dependência: [SIGAB-001 — segmento inicial](../decisoes/0001-segmento-inicial.md)
- Versão: 0.1.0
- Data-base da verificação: 2026-10-19
- Responsáveis pela pesquisa: Produto
- Validação necessária: Jurídico do Município, Comando da Guarda, Controle Patrimonial, Arquivo Público/CPAD, Encarregado de Dados e, nos temas federais, unidade competente da Polícia Federal ou do Exército
- Estado: pesquisa técnica preliminar concluída; validação jurídica e aderência local pendentes

> **Aviso:** esta nota organiza fontes oficiais e impactos prováveis no produto. Não é parecer jurídico, não certifica conformidade e não substitui a análise dos atos do Município, do TAD/ACT efetivamente celebrado, das determinações da Polícia Federal, da tabela de temporalidade local nem das características concretas do acervo.

## 1. Escopo e conclusão executiva

O recorte é o definido pela SIGAB-001: Guardas Municipais brasileiras que mantêm acervo institucional e entregam temporária ou continuadamente armas e outros equipamentos individualizados a seus integrantes. Como o Município e a unidade da Federação ainda não foram definidos, esta nota fecha a linha de base federal e transforma a legislação local em requisito de implantação.

Conclusões para o produto:

1. O **SINARM é o cadastro oficial de armas e portes** deste segmento. O SIGAB deve ser tratado como sistema operacional auxiliar da Guarda e não como substituto do SINARM, do processo administrativo oficial ou do sistema patrimonial municipal.
2. Não foi encontrada, nas fontes oficiais verificadas, obrigação de integração automática do SIGAB com SINARM, Sinesp, sistema patrimonial ou Anatel. A IN DG/PF nº 310/2025 prevê módulo próprio no SINARM “a ser desenvolvido oportunamente” e, enquanto ausente, formulário da PF. Portanto, o primeiro incremento pode operar sem API oficial, desde que não impeça o cumprimento manual e gere evidência exportável.
3. O produto precisa manter identificação inequívoca do item, responsável atual, localização, entrega, devolução, operador, autorização e histórico imutável. Para armas, deve ainda referenciar o cadastro SINARM/CRAF e impedir entrega quando houver suspensão, cancelamento, restrição ou falta de habilitação vigente.
4. Laudos psicológicos, certidões criminais e motivos médicos ou judiciais são dados de risco elevado. O MVP deve guardar apenas estado, validade, referência e localização do processo oficial, sem copiar o conteúdo desses documentos, salvo decisão formal do controlador com controles próprios.
5. Não existe, nas normas federais examinadas, prazo único de retenção para cautelas e movimentações de Guarda Municipal. A eliminação deve seguir a tabela de temporalidade municipal e autorização arquivística. Até essa validação, o SIGAB não deve eliminar automaticamente histórico confirmado nem documentos probatórios.

## 2. Matriz de obrigações aplicáveis

Todos os itens abaixo foram verificados em 2026-10-19. “Impacto” distingue obrigação normativa de decisão prudencial do produto.

### OBR-01 — Registro patrimonial e agente responsável

- **Aplicabilidade:** todos os bens permanentes individualizados do acervo municipal, armados ou não.
- **Fonte oficial:** [Lei nº 4.320/1964, arts. 94 a 96](https://www.planalto.gov.br/ccivil_03/leis/l4320compilado.htm).
- **Obrigação:** manter registro analítico que caracterize cada bem permanente e identifique o agente responsável por sua guarda e administração; o inventário analítico da unidade subsidia o levantamento geral.
- **Responsável primário:** Controle Patrimonial do Município; a Guarda responde pelos eventos sob sua custódia.
- **Impacto no SIGAB:** número patrimonial, características individualizantes, unidade/local e custodiante atual são campos obrigatórios quando aplicáveis. Saída, transferência interna, devolução e baixa devem produzir trilha exportável. O SIGAB não substitui a contabilidade patrimonial; deve admitir referência ou reconciliação com ela.
- **Retenção/evidência:** conforme tabela de temporalidade e regras patrimoniais municipais; sem descarte automático enquanto não houver regra local aprovada.
- **Verificação:** 2026-10-19.

### OBR-02 — Cadastro oficial de armas no SINARM

- **Aplicabilidade:** armas institucionais das Guardas Municipais e armas particulares de seus integrantes, quando abrangidas pelo regime funcional.
- **Fontes oficiais:** [Decreto nº 11.615/2023, arts. 3º, 4º e 7º](https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2023/decreto/d11615.htm) e [Lei nº 10.826/2003, arts. 1º e 2º](https://www.planalto.gov.br/ccivil_03/leis/2003/l10.826compilado.htm).
- **Obrigação:** armas institucionais das Guardas Municipais integram o SINARM; eventos capazes de alterar o cadastro, como transferência, extravio, furto, roubo, recuperação e apreensão, pertencem ao fluxo oficial.
- **Responsável primário:** Polícia Federal pelo SINARM; Município/Comando da Guarda pela correção e tempestividade das informações que lhe caibam.
- **Impacto no SIGAB:** armazenar identificador SINARM, número de série, marca/modelo/calibre, propriedade institucional, situação do cadastro e referência ao processo oficial. Mudança operacional no SIGAB não pode ser apresentada como atualização do SINARM.
- **Retenção/evidência:** preservar o histórico e os comprovantes conforme a tabela municipal e enquanto necessários à prova da regularidade do acervo.
- **Verificação:** 2026-10-19.

### OBR-03 — Autorização, registro, CRAF e transporte

- **Aplicabilidade:** aquisição, transferência, posse e transporte de arma de fogo.
- **Fontes oficiais:** [Decreto nº 11.615/2023, arts. 15, 17, 21 a 25 e 56](https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2023/decreto/d11615.htm), [serviço oficial da PF para Guardas Municipais](https://www.gov.br/pf/pt-br/assuntos/armas/aquisicao/guardas-municipais) e [Portaria Conjunta COLOG/C Ex e DPA/PF nº 1/2024](https://www.gov.br/pf/pt-br/assuntos/armas/portaria-conjunta-colog_c-ex-e-dpa_pf-no-1-de-29-de-novembro-de-2024-dou.pdf).
- **Obrigação:** aquisição e transferência dependem de autorização prévia e registro; o transporte fora da hipótese de porte exige o documento cabível. Armas particulares e institucionais não brasonadas devem ser conduzidas com o CRAF, ressalvada a hipótese judicial prevista no decreto.
- **Responsável primário:** Município/Comando na aquisição institucional; Polícia Federal e, quando se tratar de uso restrito/PCE, Exército nos atos de sua competência.
- **Impacto no SIGAB:** controlar tipo e número do documento, órgão emissor, validade quando houver e vínculo com o item; alertar pendências. Não gerar CRAF, porte ou guia própria com aparência de documento oficial.
- **Retenção/evidência:** processo administrativo e documentos conforme tabela municipal; metadados e histórico do item permanecem enquanto houver obrigação probatória.
- **Verificação:** 2026-10-19.

### OBR-04 — TAD/ACT, controles institucionais e norma municipal de uso

- **Aplicabilidade:** Guarda que pretende ou mantém porte funcional condicionado concedido pela PF.
- **Fontes oficiais:** [IN DG/PF nº 310/2025, arts. 2º a 6º e Anexos I a III](https://www.gov.br/pf/pt-br/assuntos/armas/normativos/IN310_2025DGPFPORTEFUNCIONALGUARDASMUNICIPAISTERMODEADESAOECOMPROMISSAO.pdf), [Decreto nº 11.615/2023, arts. 57 a 60](https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2023/decreto/d11615.htm) e [Lei nº 13.022/2014, arts. 13, 14 e 16](https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2014/lei/l13022.htm).
- **Obrigação:** manter TAD ou ACT vigente, corregedoria própria e independente, ouvidoria autônoma, código de conduta, coordenador pedagógico, local seguro, metodologia de controle do uso em serviço e regramento municipal de utilização das armas. O TAD deve ser publicado no DOU no prazo previsto no instrumento; a perda de sua vigência cancela os portes nele amparados.
- **Responsável primário:** Prefeito/Município, Comando da Guarda, Corregedoria e Ouvidoria; PF celebra e fiscaliza o instrumento.
- **Impacto no SIGAB:** parametrizar vigência do TAD/ACT e bloquear entrega de arma quando o instrumento estiver vencido, rescindido ou suspenso. Registrar somente referência, vigência e documento oficial; o produto não decide se os requisitos institucionais estão satisfeitos.
- **Retenção/evidência:** TAD, aditivos, publicação, leis e portarias são documentos do processo administrativo e seguem a tabela municipal; sua vigência deve permanecer historicamente consultável.
- **Verificação:** 2026-10-19.

### OBR-05 — Dossiê individual do porte funcional

- **Aplicabilidade:** cada guarda indicado para porte funcional condicionado.
- **Fonte oficial:** [IN DG/PF nº 310/2025, arts. 7º a 10](https://www.gov.br/pf/pt-br/assuntos/armas/normativos/IN310_2025DGPFPORTEFUNCIONALGUARDASMUNICIPAISTERMODEADESAOECOMPROMISSAO.pdf).
- **Obrigação:** requerimento individual com foto e arquivamento físico ou digital, pela Guarda, de certidões, declarações, certificado de formação e laudos de aptidão psicológica e capacidade técnica; o dirigente atesta o cumprimento e a PF pode requisitar a amostra documental. A carteira funcional deve conter a informação do porte nos termos do ato.
- **Responsável primário:** Comando/dirigente da Guarda; RH/formação e corregedoria alimentam evidências dentro de suas competências.
- **Impacto no SIGAB:** para decisão de entrega, manter apenas `apto/inapto/suspenso`, validade, tipo de habilitação, referência ao processo e autoridade que atestou. O repositório integral desses documentos deve ficar fora do módulo operacional até haver política específica, criptografia, perfis segregados e avaliação de impacto.
- **Retenção/evidência:** a IN exige arquivamento, mas não fixa prazo final. Aplicar tabela municipal; sem regra aprovada, não eliminar automaticamente. Laudos usados no pedido devem ter no máximo um ano na data relevante, o que é validade de uso, não prazo de descarte.
- **Verificação:** 2026-10-19.

### OBR-06 — Formação, avaliações e EQP anual

- **Aplicabilidade:** integrantes com porte funcional.
- **Fontes oficiais:** [Decreto nº 11.615/2023, arts. 58 e 59](https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2023/decreto/d11615.htm), [IN DG/PF nº 310/2025, art. 13 e obrigações do TAD](https://www.gov.br/pf/pt-br/assuntos/armas/normativos/IN310_2025DGPFPORTEFUNCIONALGUARDASMUNICIPAISTERMODEADESAOECOMPROMISSAO.pdf) e [Portaria CGCSP/DIREX/PF nº 9/2022 e anexos da PF](https://www.gov.br/pf/pt-br/assuntos/armas/normativos/anexos-da-in-no-180-dg-pf).
- **Obrigação:** formação conforme currículo aprovado, cargas mínimas por tipo de arma e EQP anual de no mínimo 80 horas, com 65% de conteúdo prático. Reprovação ou não realização pode cancelar o porte. O TAD exige o envio do resultado até, no máximo, o segundo mês do ano subsequente.
- **Responsável primário:** Coordenação pedagógica e Comando da Guarda; PF fiscaliza.
- **Impacto no SIGAB:** habilitação deve ser por pessoa, tipo de arma, situação, data, exercício e validade; entrega incompatível deve ser bloqueada. Alertas não substituem a comunicação oficial.
- **Retenção/evidência:** certificados, listas, notas, justificativas e ofícios segundo a tabela municipal; manter o estado histórico que fundamentou cada entrega.
- **Verificação:** 2026-10-19.

### OBR-07 — Suspensão, cancelamento, impedimento e recolhimento

- **Aplicabilidade:** qualquer condição médica, judicial, disciplinar, funcional ou administrativa que restrinja porte ou acesso.
- **Fontes oficiais:** [Lei nº 13.022/2014, art. 16, parágrafo único](https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2014/lei/l13022.htm) e [IN DG/PF nº 310/2025, arts. 11, 12 e obrigações do TAD](https://www.gov.br/pf/pt-br/assuntos/armas/normativos/IN310_2025DGPFPORTEFUNCIONALGUARDASMUNICIPAISTERMODEADESAOECOMPROMISSAO.pdf).
- **Obrigação:** suspender o acesso quando houver impedimento, recolher imediatamente carteira e arma institucional e comunicar à PF os eventos previstos. O modelo de TAD fixa até 48 horas para eventos funcionais que impliquem cancelamento/revogação, suspensão e perda/extravio da carteira; impedimento total também exige cautelar guarda de armas particulares e comunicação imediata.
- **Responsável primário:** Comando e Corregedoria; RH deve disparar eventos funcionais; Prefeito resolve divergência prevista na IN.
- **Impacto no SIGAB:** bloqueio transacional imediato por estado de elegibilidade; fila de recolhimento com prazo, escalonamento e prova de ciência; motivo operacional em categoria mínima, sem expor diagnóstico ou inteiro teor judicial a armeiros.
- **Retenção/evidência:** preservar decisão, comunicações e eventos de recolhimento conforme processo e tabela municipal; não apagar o fato histórico após levantamento da restrição.
- **Verificação:** 2026-10-19.

### OBR-08 — Armazenamento seguro e controle do uso em serviço

- **Aplicabilidade:** acervo institucional de armas e munições.
- **Fontes oficiais:** [IN DG/PF nº 310/2025, arts. 3º, 5º e Anexo III](https://www.gov.br/pf/pt-br/assuntos/armas/normativos/IN310_2025DGPFPORTEFUNCIONALGUARDASMUNICIPAISTERMODEADESAOECOMPROMISSAO.pdf) e [Lei nº 10.826/2003, arts. 12 a 16](https://www.planalto.gov.br/ccivil_03/leis/2003/l10.826compilado.htm).
- **Obrigação:** o Município informa o local seguro e a metodologia de controle do uso; a PF pode inspecionar armazenamento, controles e registros e requisitar documentos, fotos ou filmagens.
- **Responsável primário:** Comando da Guarda e responsável pela reserva/armeiro; Segurança institucional pelas salvaguardas físicas.
- **Impacto no SIGAB:** cada saída e retorno deve vincular item, destinatário, operador, data/hora, local, modalidade, autorização e estado; alterações posteriores devem ser eventos corretivos, nunca sobrescrita silenciosa. Gerar relatório de fiscalização e conciliação física.
- **Retenção/evidência:** tabela municipal e necessidade probatória. A lei federal examinada não fixa prazo único para a cautela operacional.
- **Verificação:** 2026-10-19.

### OBR-09 — Extravio, furto, roubo e recuperação

- **Aplicabilidade:** arma, munição, acessório ou documento sob responsabilidade do Município ou do portador.
- **Fontes oficiais:** [Decreto nº 11.615/2023, arts. 3º, 4º, 7º e 50](https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2023/decreto/d11615.htm) e [IN DG/PF nº 310/2025, art. 12 e modelo de TAD](https://www.gov.br/pf/pt-br/assuntos/armas/normativos/IN310_2025DGPFPORTEFUNCIONALGUARDASMUNICIPAISTERMODEADESAOECOMPROMISSAO.pdf).
- **Obrigação:** registrar a ocorrência no canal competente e atualizar/comunicar a PF conforme a natureza do evento; o titular de porte comunica imediatamente extravio, furto ou roubo da arma à unidade policial mais próxima e à PF. O TAD disciplina também a perda/extravio da carteira funcional em até 48 horas.
- **Responsável primário:** portador e Comando da Guarda; Corregedoria acompanha; PF atualiza o SINARM.
- **Impacto no SIGAB:** fluxo de incidente com indisponibilidade imediata do item, relógio de prazo, número do boletim/processo, comunicações, recuperação e reconciliação. Não inferir que o registro interno cumpre a comunicação externa.
- **Retenção/evidência:** ocorrência, ofícios e trilha do item conforme tabela municipal e enquanto houver investigação, tomada de contas, processo ou retenção legal.
- **Verificação:** 2026-10-19.

### OBR-10 — Munição e rastreabilidade de lote

- **Aplicabilidade:** condicional; necessária quando o escopo incluir estoque, entrega, consumo, recarga ou devolução de munição. Está fora do primeiro incremento pela SIGAB-008.
- **Fontes oficiais:** [Lei nº 10.826/2003, art. 23, §§ 1º, 2º e 4º](https://www.planalto.gov.br/ccivil_03/leis/2003/l10.826compilado.htm) e [Decreto nº 11.615/2023, arts. 3º, 4º, 7º, 12, 13 e 17](https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2023/decreto/d11615.htm).
- **Obrigação:** compras destinadas aos órgãos do art. 6º observam identificação de lote e adquirente; aquisição, cadastro e comunicação seguem o regime do produto e do calibre. Recarga própria depende de autorização e regras específicas.
- **Responsável primário:** Município/Comando, Compras e responsável pela reserva; PF e Exército nos atos de sua competência.
- **Impacto no SIGAB:** não representar munição como item individual do modelo atual. Antes de implementar, modelar lote, calibre, fabricante, validade, entrada, saldo, saída, consumo, devolução e ajustes com autorização; integração ou exportação será definida no processo oficial concreto.
- **Retenção/evidência:** depende do processo de aquisição, tabela municipal e normas específicas aplicáveis. Não há decisão de retenção nesta versão.
- **Verificação:** 2026-10-19.

### OBR-11 — Gestão arquivística, retenção e eliminação

- **Aplicabilidade:** todos os registros e documentos públicos produzidos ou recebidos pelo Município, em qualquer suporte.
- **Fontes oficiais:** [Lei nº 8.159/1991, arts. 1º a 10 e 17 a 21](https://www.planalto.gov.br/ccivil_03/leis/l8159.htm), [Resolução CONARQ nº 40/2014, alterada pela nº 44/2020](https://www.gov.br/arquivonacional/pt-br/servicos/gestao-de-documentos/legislacao) e [orientação do CONARQ para arquivos municipais](https://www.gov.br/conarq/pt-br/assuntos/campanha-arquivos-municipais-publicos/o-arquivo-publico-municipal).
- **Obrigação:** gerir, avaliar e proteger documentos; eliminar somente segundo tabela aprovada, avaliação da CPAD e autorização da instituição arquivística competente, com o procedimento formal aplicável. Documento permanente não pode ser eliminado.
- **Responsável primário:** Arquivo Público/órgão arquivístico municipal e CPAD; cada unidade produtora classifica corretamente; TI executa a destinação autorizada.
- **Impacto no SIGAB:** classificação arquivística, data de corte, retenção, destinação, bloqueio por litígio/investigação e exportação preservando contexto e autenticidade. Exclusão comum de eventos confirmados fica proibida; descarte futuro exige rotina administrativa auditável, não ação direta do operador.
- **Retenção/evidência:** prazo e destinação vêm da tabela municipal. Até obtê-la, retenção conservadora sem eliminação automática.
- **Verificação:** 2026-10-19.

### OBR-12 — Dados pessoais, segurança, transparência e acesso

- **Aplicabilidade:** pessoas, contas, vínculos, portes, restrições, avaliações e eventos que identifiquem guardas ou operadores.
- **Fontes oficiais:** [LGPD — Lei nº 13.709/2018, arts. 11, 15, 16, 23, 37 e 46 a 48](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm), [Guia da ANPD para o Poder Público](https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia_orientativo_tratamento_de_dados_pessoais_pelo_poder_publico) e [LAI — Lei nº 12.527/2011, arts. 23 e 31](https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12527.htm).
- **Obrigação:** tratar dados para finalidade pública e competência legal, dar transparência ao tratamento, indicar encarregado, registrar operações e adotar segurança desde a concepção. Dados sensíveis exigem hipótese legal e necessidade demonstradas. Acesso público não equivale a exposição de dados pessoais nem de informação cuja divulgação comprometa segurança.
- **Responsável primário:** Município como controlador, Encarregado, Segurança da Informação e gestores da Guarda; fornecedor do SIGAB será operador quando tratar dados em nome do Município, conforme o contrato concreto.
- **Impacto no SIGAB:** minimização, perfis por função e organização, logs de acesso, criptografia em trânsito e repouso conforme arquitetura aprovada, resposta a incidentes, exportação/correção e política de privacidade. Ocultar CPF de telas operacionais e não registrar diagnóstico, conteúdo de laudo ou inteiro teor de decisão quando um estado de elegibilidade bastar.
- **Retenção/evidência:** término e conservação seguem finalidade, obrigação legal e tabela arquivística; LGPD não autoriza destruir documento público à margem do regime arquivístico.
- **Verificação:** 2026-10-19.

### OBR-13 — Sinesp e fornecimento institucional de dados

- **Aplicabilidade:** o Município integra o Susp por órgão designado; o conjunto de dados efetivamente exigido depende da governança e dos padrões do Sinesp.
- **Fontes oficiais:** [Lei nº 13.675/2018, arts. 9º e 35 a 37](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13675.htm) e [orientações oficiais de acesso ao Sinesp para Guardas Municipais](https://www.gov.br/mj/pt-br/assuntos/sua-seguranca/seguranca-publica/sinesp-1/perguntas/perguntas-frequentes).
- **Obrigação:** entes e órgãos designados fornecem e atualizam dados padronizados do Sinesp. O Decreto nº 11.615/2023 já determina a articulação do SINARM com o Sinesp.
- **Responsável primário:** órgão municipal designado e gestor/cadastrador do Sinesp; não necessariamente o armeiro nem o SIGAB.
- **Impacto no SIGAB:** nenhuma integração direta é requisito do MVP sem leiaute, credenciais, instrumento e atribuição formal. Preservar exportação estruturada e rastreabilidade para futura integração. Não duplicar no SIGAB consultas do Infoseg ou outros módulos sem autorização específica.
- **Retenção/evidência:** conforme conjunto de dados, instrumento de adesão e tabela municipal; registrar remessas, confirmações e erros se a integração for implementada.
- **Verificação:** 2026-10-19.

### OBR-14 — Rádios e outros PCE, quando presentes

- **Aplicabilidade:** condicional à composição concreta do acervo e às características técnicas do equipamento.
- **Fontes oficiais:** [Anatel — espectro, homologação, outorga e licenciamento](https://www.gov.br/anatel/pt-br/regulado/espectro), [Lei nº 13.022/2014, art. 17](https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2014/lei/l13022.htm), [Decreto nº 10.030/2019 — Regulamento de PCE](https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2019/decreto/d10030.htm) e [Portaria nº 118-COLOG/2019 — lista de PCE](https://www.gov.br/siscomex/pt-br/arquivos-e-imagens/2019/10/Portaria-no-118-COLOG-de-4-Out-2019-Lista-de-PCE.pdf).
- **Obrigação:** produtos de telecomunicações devem ser homologados; o uso de radiofrequência e estações pode exigir outorga, cadastro e licença conforme o serviço. Proteções balísticas, agentes lacrimogêneos e outros itens podem ser PCE conforme classificação vigente e exigir documentação do Exército.
- **Responsável primário:** Telecomunicações/TI e Patrimônio para rádios; Compras, Comando e fiscalização de PCE para os demais itens.
- **Impacto no SIGAB:** campos opcionais por regime: homologação Anatel, estação/licença, validade, certificado/registro de PCE e órgão emissor. Não tornar esses campos universais até classificar cada tipo de equipamento.
- **Retenção/evidência:** processo de aquisição, licença e tabela municipal. Validar a norma complementar vigente no momento da compra e em cada implantação.
- **Verificação:** 2026-10-19.

## 3. Sistemas oficiais e posição do SIGAB

| Sistema/processo | Função oficial | Relação com o SIGAB v0.1 |
|---|---|---|
| SINARM / Polícia Federal | Cadastro de armas, portes e ocorrências; tramitação prevista na IN nº 310/2025 | Fonte oficial. SIGAB guarda referência e produz evidência; sem sincronização automática presumida. |
| Processo administrativo municipal e PF | TAD/ACT, ofícios, publicações, requerimentos, comunicações e fiscalização | Fonte documental. SIGAB referencia o número do processo e seus estados. |
| Sistema patrimonial municipal | Registro contábil/patrimonial e inventário | Fonte patrimonial. Conciliação ou integração depende do Município. |
| Sinesp | Integração nacional de dados de segurança pública | Obrigação institucional do ente/órgão designado; não é sistema de cautela do SIGAB. |
| SisFPC/serviços do Exército | Autorizações e fiscalização de PCE | Condicional ao tipo de produto e ao ato praticado. |
| Mosaico/BDTA e processos Anatel | Radiofrequência, estações e licenças | Condicional ao sistema de radiocomunicação usado. |
| Arquivo/CPAD municipal | Classificação, temporalidade, destinação e autorização de eliminação | Define retenção. Sem integração técnica obrigatória, mas suas regras devem ser parametrizadas. |

## 4. Requisitos derivados para o produto

### P0 — antes de uso real com armamento

- Classificar o item por regime: bem comum, arma SINARM, munição, PCE, rádio ou combinação aplicável.
- Tornar obrigatórios, conforme o tipo, patrimônio, número de série, identificador SINARM/CRAF, órgão emissor, vigência e situação.
- Manter eventos imutáveis de entrega, devolução, recolhimento, incidente, correção e conciliação, sempre com ator, data/hora, item, pessoa, unidade e justificativa.
- Separar `condição física`, `disponibilidade`, `localização`, `custodiante` e `situação regulatória`.
- Implementar elegibilidade por pessoa e tipo de arma, com bloqueio por suspensão, cancelamento, restrição, TAD/ACT inativo, falta de habilitação ou EQP pendente.
- Criar prazos e alertas para 48 horas, comunicações imediatas, validade documental, EQP e renovação, sem declarar que o alerta realiza o protocolo oficial.
- Registrar referências a ofício, boletim, processo, CRAF, porte e publicação; anexos sensíveis ficam fora do MVP.
- Oferecer exportação legível e estruturada, conciliação física e relatório de fiscalização com cadeia de auditoria.
- Aplicar segregação: armeiro vê apenas o necessário à entrega; Comando/Corregedoria tratam restrição; RH/formação tratam habilitação; auditor lê sem alterar.
- Proibir exclusão ou edição destrutiva do histórico confirmado; correção é novo evento relacionado ao anterior.

### P1 — após identificar o primeiro Município

- Importação/reconciliação do cadastro patrimonial e do inventário SINARM autorizado.
- Parametrização da tabela de temporalidade, classificação arquivística, legal hold e destinação.
- Integrações oficiais apenas após instrumento, leiaute, credenciais, ambiente de teste, responsável e regra de reconciliação documentados.
- Gestão documental sensível somente após RIPD/avaliação equivalente, matriz de acesso e decisão do controlador.

## 5. Evidências obrigatórias antes da implantação

O responsável de implantação deve obter e versionar:

1. lei de criação da Guarda e código de conduta;
2. leis/atos da corregedoria e ouvidoria e nomeações vigentes;
3. TAD ou ACT vigente, aditivos, publicação e gestor designado;
4. norma municipal de uso de armas, inclusive fora de serviço e em aglomerações;
5. descrição aprovada do local seguro e da metodologia de controle;
6. relação oficial do acervo e dos CRAF/SINARM, com autorização de acesso;
7. regra de formação, avaliações e EQP, responsáveis e calendário;
8. processo municipal para restrição, recolhimento, incidente e comunicações;
9. sistema patrimonial fonte de verdade e responsável pela conciliação;
10. tabela de temporalidade, CPAD e autoridade arquivística competente;
11. controlador, encarregado, operador contratado, política de acesso e resposta a incidentes;
12. órgão municipal designado no Sinesp e obrigações de dados vigentes;
13. para rádios/PCE, atos, certificados, licenças e classificação técnica de cada tipo.

Sem os itens 3 a 8, a funcionalidade de entrega de armas não deve ser habilitada em produção.

## 6. Pendências jurídicas e de produto

- Identificar o primeiro Município/UF e revisar lei local, regulamentos, TAD/ACT e determinações da SR/PF competente.
- Confirmar com PF se o módulo próprio do SINARM previsto no art. 16 da IN nº 310/2025 já está disponível e quais formulários/canais estão vigentes na implantação.
- Obter a tabela de temporalidade aplicável; não converter validade documental em prazo de retenção.
- Validar se o Município exige termo de cautela, assinatura eletrônica, dupla autorização, inventário periódico ou campos adicionais.
- Classificar o acervo real de munições, proteções balísticas, agentes químicos, dispositivos menos letais e rádios antes de modelar regras.
- Definir por contrato os papéis LGPD, hospedagem, suboperadores, retorno/eliminação ao término, auditoria e resposta a incidentes.

## 7. Histórico de versões

| Versão | Data | Alteração |
|---|---|---|
| 0.1.0 | 2026-10-19 | Linha de base federal, sistemas oficiais, retenção, integrações e impactos iniciais no produto. |
