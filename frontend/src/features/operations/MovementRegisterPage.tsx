import { Pager, useUrlQuery } from "../../components/Query";
import { useLatestRequest } from "../../hooks/useLatestRequest";
import { FormEvent, useEffect, useState } from "react";
import { apiPage, apiRequest, describeError } from "../../api/client";
import type { RegisterOptions, RegisterRow } from "../../api/types";
import { ErrorState, LoadingState } from "../../components/Feedback";
import { formatDateTime, formatQuantity } from "../../components/format";

const PAGE_SIZE = 50;
const FILTERS = ["person", "operator", "equipment_type", "type", "kind", "from", "to"] as const;
type Filters = Record<(typeof FILTERS)[number], string>;
const EMPTY: Filters = { person: "", operator: "", equipment_type: "", type: "", kind: "", from: "", to: "" };

const IDENTITY_LABELS: Record<string, string> = {
  facial: "biometria facial",
  signed_term: "termo assinado e aprovado",
  paper_contingency: "contingência em papel"
};

function material(row: RegisterRow) {
  if (row.item_id) return <><a href={`/items/${row.item_id}`}>{row.identifier}</a> · {row.equipment_type}</>;
  return <>{formatQuantity(row.quantity ?? "0")} · {row.equipment_type}</>;
}

function roles(row: RegisterRow) {
  if (row.type === "checkout") return `Retirou: ${row.recipient ?? "—"} · Entregue por: ${row.operator}`;
  if (row.type === "return") return `Devolveu: ${row.recipient ?? "—"} · Recebido por: ${row.operator}`;
  return `Pessoa: ${row.recipient ?? "—"} · Registrado por: ${row.operator}`;
}

/** Registro filtrável de retiradas, devoluções e consumo (SIGAB-082, RF-52, RF-53, RF-55). */
export function MovementRegisterPage() {
  const [options, setOptions] = useState<RegisterOptions | null>(null);
  const [applied, applyFilters] = useUrlQuery({ ...EMPTY, offset: "0" });
  const [filters, setFilters] = useState<Filters>(applied);
  const [rows, setRows] = useState<RegisterRow[]>([]);
  const [count, setCount] = useState(0);
  const offset = Math.max(0, Number(applied.offset) || 0);
  const [optionsError, setOptionsError] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const beginRequest = useLatestRequest();

  async function load(nextOffset = offset, current = applied) {
    const isCurrent = beginRequest();
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(nextOffset) });
      for (const key of FILTERS) if (current[key]) params.set(key, current[key]);
      const page = await apiPage<RegisterRow>(`/movements/?${params}`);
      if (!isCurrent()) return;
      setRows(page.rows);
      setCount(page.count);

    } catch (cause) {
      if (isCurrent()) setError(describeError(cause));
    } finally {
      if (isCurrent()) setLoading(false);
    }
  }

  async function loadOptions() {
    setOptionsError("");
    try { setOptions(await apiRequest<RegisterOptions>("/movements/options/")); }
    catch (cause) { setOptionsError(`Não foi possível carregar as opções dos filtros: ${describeError(cause)}`); }
  }
  useEffect(() => { void loadOptions(); }, []);
  useEffect(() => { setFilters(applied); void load(); }, [applied]);

  function set(key: keyof Filters, value: string) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    applyFilters({ ...filters, offset: "0" });
  }

  return (
    <>
      <section className="page-heading">
        <div>
          <p className="context-label">Controle</p>
          <h1>Registro de movimentações</h1>
          <p>Retiradas e devoluções com material, quem retirou ou devolveu, quem entregou ou recebeu, unidade e data. Registros confirmados não são editados; correções aparecem como estorno.</p>
        </div>
      </section>

      {optionsError && <div className="feedback warning" role="alert">{optionsError}<button className="button button-secondary" type="button" onClick={() => void loadOptions()}>Tentar carregar opções</button></div>}
      <form className="filter-bar" onSubmit={submit} aria-label="Filtros do registro">
        <label className="field"><span>Pessoa</span><select value={filters.person} onChange={(event) => set("person", event.target.value)}><option value="">Todas</option>{options?.people.map((value) => <option key={value.id} value={value.id}>{value.name}</option>)}</select></label>
        <label className="field"><span>Operador</span><select value={filters.operator} onChange={(event) => set("operator", event.target.value)}><option value="">Todos</option>{options?.operators.map((value) => <option key={value.id} value={value.id}>{value.username}</option>)}</select></label>
        <label className="field"><span>Material</span><select value={filters.equipment_type} onChange={(event) => set("equipment_type", event.target.value)}><option value="">Todos</option>{options?.equipment_types.map((value) => <option key={value.id} value={value.id}>{value.name}</option>)}</select></label>
        <label className="field"><span>Movimento</span><select value={filters.type} onChange={(event) => set("type", event.target.value)}><option value="">Todos</option><option value="checkout">Retirada</option><option value="return">Devolução</option><option value="consume">Consumo</option></select></label>
        <label className="field"><span>Natureza</span><select value={filters.kind} onChange={(event) => set("kind", event.target.value)}><option value="">Com e sem registro</option><option value="individual">Com registro</option><option value="quantitative">Sem registro</option></select></label>
        <label className="field"><span>De</span><input type="date" value={filters.from} onChange={(event) => set("from", event.target.value)} /></label>
        <label className="field"><span>Até</span><input type="date" value={filters.to} onChange={(event) => set("to", event.target.value)} /></label>
        <button className="button button-primary">Filtrar</button>
        <button className="button button-quiet" type="button" onClick={() => { setFilters(EMPTY); applyFilters({ ...EMPTY, offset: "0" }); }}>Limpar</button>
      </form>

      {loading ? <LoadingState /> : error ? <ErrorState message={error} onRetry={() => void load(offset)} /> : (
        <section className="list-panel" aria-label="Movimentações">
          <div className="list-summary"><span><strong>{count}</strong> {count === 1 ? "movimentação" : "movimentações"}</span></div>
          {rows.length === 0 ? <p className="empty-state">Nenhuma movimentação para os filtros escolhidos.</p> : (
            <ul className="sub-list feed">
              {rows.map((row) => (
                <li key={`${row.kind}-${row.id}`}>
                  <span>
                    <strong>{row.type_label} · {material(row)}{row.condition === "unfit" && " · inapto"}</strong>
                    <small>{roles(row)} · {row.unit}{row.identity_method && IDENTITY_LABELS[row.identity_method] && ` · ${IDENTITY_LABELS[row.identity_method]}`}</small>
                  </span>
                  <small>{formatDateTime(row.occurred_at)}{row.receipt_code && ` · ${row.receipt_code}`}</small>
                </li>
              ))}
            </ul>
          )}
          {count > PAGE_SIZE && <div className="list-footer"><Pager offset={offset} limit={PAGE_SIZE} count={count} onChange={(next) => applyFilters({ offset: String(next) })} noun={["movimentação", "movimentações"]} /></div>}

        </section>
      )}
    </>
  );
}
