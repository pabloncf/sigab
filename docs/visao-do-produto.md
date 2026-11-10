# Visão do produto

O SIGAB pretende dar rastreabilidade a acervos de organizações que hoje operam sem sistema adequado. O [segmento inicial escolhido](decisoes/0001-segmento-inicial.md) é o de Guardas Municipais brasileiras com acervo de armamentos e equipamentos operacionais, sem limitar a expansão futura para outros segmentos. O documento inicial de requisitos foi produzido após validação com o usuário-alvo desse segmento. O primeiro incremento reduz deliberadamente o problema a itens individuais e preserva operador, destinatário, estado atual e fatos históricos.

O produto é single-tenant: cada cliente tem instalação e banco próprios, uma organização e suas unidades internas. O sucesso técnico da base inclui impedir uma segunda organização, autorizar no servidor por papel/unidade e garantir uma única saída concorrente por item. Ver [ADR 0007](adr/0007-single-tenant.md). Não constitui alegação de conformidade regulatória ou LGPD. Os termos operacionais aprovados estão no [glossário v0.2](glossario.md).

