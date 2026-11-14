# Pesquisa 0002 — Verificação facial no balcão

- Tarefa: SIGAB-084 (prova de conceito técnica), insumo da SIGAB-083
- Data: 13/11/2026
- Situação: **comparação documental concluída; a medição prática ainda não foi feita.** Nenhum código entrou no produto. Nenhuma imagem foi coletada ou processada.

## 1. Pergunta

Qual tecnologia permite confirmar, no balcão da reserva, que quem retira ou devolve material é a pessoa selecionada? Ela precisa funcionar com webcam comum, com rede instável (ADR 0004), em produto revendido por instalação (ADR 0007) e dentro da LGPD?

## 2. O que esta pesquisa entrega e o que falta

O critério de aceite pede taxas de falsa aceitação e de falsa rejeição, além do tempo por verificação, **medidos** com imagens sintéticas ou de voluntários com consentimento registrado. Essa medição exige câmera de balcão, voluntários e termo de consentimento. Não pode ser feita só no repositório.

Esta pesquisa entrega:

- a comparação documental das opções;
- um protocolo de medição pronto (seção 6);
- uma recomendação provisória.

As colunas de medição ficam **a medir**, sem números inventados.

## 3. Opções avaliadas

| Critério | A. Local aberto: OpenCV YuNet + SFace e antifraude passivo aberto | B. Local comercial: SDK embarcado com prova de vida certificada | C. Nuvem global: AWS Rekognition (CompareFaces + Face Liveness) | D. Nuvem nacional: Serpro Datavalid (biometria facial) |
|---|---|---|---|---|
| Modo | 1:1 contra modelo cadastrado na instalação | 1:1 contra modelo cadastrado | 1:1 entre a foto do balcão e uma referência enviada | 1:1 contra a base oficial (CNH) |
| Licença para revenda | Código e pesos do OpenCV Zoo sob Apache 2.0 ([SFace](https://huggingface.co/opencv/face_recognition_sface), [model card](https://github.com/opencv/opencv_zoo/blob/main/models/face_recognition_sface/README.md)). Evitar os pesos do InsightFace: código MIT, mas modelos pré-treinados exigem licença comercial à parte ([fonte](https://libraries.io/pypi/insightface)) | Licença comercial por instalação ou dispositivo, negociada com o fornecedor | Uso por API, contrato da instalação com a AWS | Contrato com o Serpro, cobrança por validação ([Serpro 2024](https://serpro.gov.br/menu/noticias/noticias-2024/nova-versao-do-datavalid)) |
| Prova de vida | Fraca. Modelos passivos abertos (ex.: Silent-Face, Apache 2.0) dependem de câmera e cena e não têm certificação ISO/IEC 30107-3 ([fonte](https://clarifai.com/minivision-ai/silent-face-anti-spoofing/models/silent-face-anti-spoofing)) | Forte quando o fornecedor tem certificação ISO/IEC 30107-3 (iBeta), o que deve ser exigido em contrato | Forte: [Face Liveness](https://docs.aws.amazon.com/rekognition/latest/dg/face-liveness.html), com interação guiada no navegador | Passiva, segundo o Serpro (mesma fonte acima) |
| Sem internet | **Sim**: processamento no servidor da instalação | **Sim** | **Não** | **Não** |
| Onde o dado é processado | Servidor do cliente | Servidor do cliente | Região AWS escolhida; há transferência a operador externo | Serpro; a referência é a base do governo |
| Retenção pelo fornecedor | Nenhuma | Nenhuma, se o SDK não tiver telemetria (exigir em contrato) | Conforme os termos da AWS; o SIGAB não precisa manter coleção na AWS se usar CompareFaces com referência enviada | Conforme o contrato com o Serpro |
| Custo por organização | Sem licença; custo de CPU no servidor | Licença por instalação ou dispositivo, sob consulta | Por chamada; preço regional sob consulta ([preços](https://aws.amazon.com/rekognition/pricing/)) | Por validação. Reportagem antiga cita R$ 1,68 na faixa inicial, valor não confirmado ([Tecnoblog](https://tecnoblog.net/noticias/mpdft-acusa-serpro-usar-dados-cnh-sem-autorizacao/)) |
| Falsa aceitação / falsa rejeição | a medir. O model card do SFace informa 0,994 em avaliação interna, sem protocolo de verificação equivalente ao LFW | a medir; pedir os relatórios NIST FRTE do fornecedor | a medir | a medir |
| Tempo no balcão | a medir; esperado abaixo de 1 s em CPU de servidor | a medir | a medir; depende da latência de rede | a medir; depende da latência de rede |
| Cadastro da referência | Coleta no SIGAB (SIGAB-085) | Coleta no SIGAB | Coleta no SIGAB | **Dispensa coleta**, mas exige CPF e CNH e liga o SIGAB a uma base externa |
| Risco jurídico ou de reputação | Menor exposição: dado fica na instalação | Igual à opção A, mais o contrato com o fornecedor | Transferência internacional e acesso de terceiro a dado sensível | Questionamento público já registrado sobre o Datavalid (mesma reportagem); CPF passaria a ser obrigatório, contra a política atual |

Ficou de fora o **Azure Face**: verificação e prova de vida dependem de aprovação discricionária da Microsoft por caso de uso ([Limited Access](https://learn.microsoft.com/legal/cognitive-services/computer-vision/limited-access-identity)), o que não se presta a um produto revendido por instalação.

## 4. Leitura dos critérios do SIGAB

1. **Queda de rede (ADR 0004).** Hoje o sistema inteiro fica indisponível sem rede, e a reserva passa ao papel. Com C ou D, porém, haveria um segundo ponto de falha: o SIGAB funcionando e a verificação fora do ar. Isso obrigaria a usar a alternativa sem biometria em toda instabilidade do provedor. As opções A e B só falham junto com o próprio servidor.
2. **Revenda (ADR 0007).** A opção A não tem custo de licença. B depende de negociação. C e D criam contrato e custo variável por cliente.
3. **LGPD.** Com A e B, o modelo biométrico não sai da instalação do cliente, que é o controlador. Com C e D, entra um operador externo de dado sensível, o que pede cláusulas específicas e, no caso C, avaliação de transferência internacional.
4. **Prova de vida.** É o ponto fraco da opção A. Com webcam comum e antifraude aberto, uma foto impressa ou exibida em tela pode passar. O operador de balcão está presente e vê a pessoa, o que reduz o risco, mas não o elimina.

## 5. Recomendação provisória para a SIGAB-083

- **Arquitetura:** processamento **local**, no servidor da instalação, com verificação **1:1** contra a pessoa selecionada pelo operador. Nada de identificação 1:N.
- **Motor:** começar a medição pela opção A (YuNet + SFace, Apache 2.0) com a interface de motor isolada, para permitir trocar por um SDK comercial certificado (opção B) se a medição de prova de vida for insuficiente.
- **Prova de vida:** exigir uma das duas saídas abaixo antes de habilitar a verificação facial como obrigatória:
  - um SDK com certificação ISO/IEC 30107-3;
  - a conferência visual explícita pelo operador, registrada como parte do método.
- **Nuvem:** C e D ficam descartadas para o MVP. Podem ser reavaliadas por instalação, se um cliente exigir validação contra base oficial.

## 6. Protocolo de medição (pendente de execução)

1. Termo de consentimento específico para o teste, com finalidade, prazo e descarte. Apenas voluntários adultos. Nenhum dado de cliente.
2. Equipamento: webcam 1080p de balcão, iluminação da reserva e servidor equivalente ao de produção.
3. Amostra mínima: 30 voluntários × 5 capturas, em dois dias diferentes.
4. Métricas:
   - falsa rejeição (pares genuínos) e falsa aceitação (pares impostores) em três limiares;
   - tempo da captura até o resultado, por percentil 50 e 95;
   - taxa de ataque aceita com foto impressa e com tela de celular.
5. Meta proposta para habilitar o uso:
   - falsa aceitação ≤ 0,1 % no limiar escolhido;
   - falsa rejeição ≤ 3 %;
   - percentil 95 do tempo ≤ 2 s;
   - nenhum ataque de foto aceito sem a conferência visual do operador.
6. Descarte: imagens e modelos apagados ao final, com registro do descarte. O relatório guarda só números agregados.
7. Resultado registrado nesta pesquisa, como seção 7.

## 7. Resultados da medição

A preencher quando o protocolo da seção 6 for executado.
