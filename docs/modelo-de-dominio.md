# Modelo de domínio

```text
Organization ─┬─ Unit ─ StorageLocation
              ├─ Person ─ Membership
              ├─ Account ─ Grant ─ Role(permissions)
              └─ EquipmentType ─ Item ─ Movement ─ MovementEvent
                                      └──────────── AuditEvent
```

`Person` é isolada por organização. Essa decisão reduz risco de correlação e vazamento entre clientes; eventual unificação futura exigirá serviço de identidade separado e consentimento/finalidade explícitos. Conta e pessoa têm ciclos independentes.

O estado do item separa condição física, disponibilidade, situação administrativa, unidade/local e responsável atual. A máquina de estados validada está na [decisão 0004](decisoes/0004-ciclo-de-vida-do-item-individual.md). Movimentações são a operação confirmada; eventos são fatos cronológicos e imutáveis nos fluxos normais. A [posse operacional](glossario.md#posse-operacional) atual é uma projeção transacional no item, verificável pelo histórico. Ela não deve ser confundida com custódia, que designa o dever de guarda.

Unicidade adotada provisoriamente: código de unidade/local, matrícula, nome do tipo, número de série e patrimônio são únicos dentro da organização quando preenchidos. O UUID interno nunca depende desses identificadores.

