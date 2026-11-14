const quantityFormat = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 });
const dateTimeFormat = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });

/** Quantidade decimal da API ("1200.000") no formato local ("1.200"). */
export function formatQuantity(value: string | number) {
  return quantityFormat.format(Number(value));
}

export function formatDateTime(value: string) {
  return dateTimeFormat.format(new Date(value));
}

interface ScopeSource {
  organization: { name: string };
  item_scope?: { all_units: boolean; units: Array<{ code: string; name: string }> };
}

/** Nomeia as unidades consultadas, no lugar de um vago "no seu escopo". */
export function scopeLabel(session: ScopeSource): string {
  const scope = session.item_scope;
  if (!scope) return "nas unidades permitidas à sua conta";
  if (scope.all_units) return `em todas as unidades de ${session.organization.name}`;
  if (scope.units.length === 0) return "em nenhuma unidade (sua conta não tem acesso ao acervo)";
  const names = scope.units.map((unit) => `${unit.code} · ${unit.name}`);
  if (names.length === 1) return `na unidade ${names[0]}`;
  if (names.length <= 3) return `nas unidades ${names.slice(0, -1).join(", ")} e ${names[names.length - 1]}`;
  return `em ${names.length} unidades (${scope.units.map((unit) => unit.code).join(", ")})`;
}
