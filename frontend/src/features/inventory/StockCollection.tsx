import { useLatestRequest } from "../../hooks/useLatestRequest";
import { useEffect, useState } from "react";
import { apiPage, apiRequest, describeError } from "../../api/client";
import type { Session, StockHistoryEntry, StockSummaryRow } from "../../api/types";
import { ErrorState, LoadingState } from "../../components/Feedback";
import { formatDateTime, formatQuantity, scopeLabel } from "../../components/format";
import { AppliedFilter, AppliedFilters, SearchForm, useUrlQuery } from "../../components/Query";

const HISTORY_LIMIT = 50;

interface History {
  type: { id: string; name: string };
  rows: StockHistoryEntry[];
  count: number;
}

/** Aba "Sem registro" do acervo: saldos por tipo, unidade e local (SIGAB-081). */
export function StockCollection({ session, initialType }: { session: Session; initialType: string }) {
  const [rows, setRows] = useState<StockSummaryRow[]>([]);
  const [units, setUnits] = useState<Array<{ id: string; name: string }>>([]);
  const [filters, setFilters] = useUrlQuery({ q: "", unit: "" });
  const query = filters.q;
  const unit = filters.unit;
  const setUnit = (value: string) => setFilters({ unit: value });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [history, setHistory] = useState<History | null>(null);
  const [historyError, setHistoryError] = useState("");

  const beginRequest = useLatestRequest();

  async function load() {
    const isCurrent = beginRequest();
    setLoading(true);
    setError("");
    try {
      const filters = new URLSearchParams();
      if (initialType) filters.set("type", initialType);
      if (unit) filters.set("unit", unit);
      if (query.trim()) filters.set("q", query.trim());
      const loaded = await apiRequest<StockSummaryRow[]>(`/stock/summary/?${filters}`);
      if (!isCurrent()) return;
      setRows(loaded);
      if (!unit && !query.trim()) {
        const seen = new Map(loaded.map((row) => [row.unit.id, row.unit]));
        setUnits([...seen.values()]);
      }
    } catch (cause) {
      if (isCurrent()) setError(describeError(cause));
    } finally {
      if (isCurrent()) setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [unit, query]);

  const beginHistory = useLatestRequest();

  async function openHistory(type: { id: string; name: string }) {
    const isCurrent = beginHistory();
    setHistory(null);
    setHistoryError("");
    try {
      const page = await apiPage<StockHistoryEntry>(`/stock/entries/?type=${type.id}&limit=${HISTORY_LIMIT}`);
      if (isCurrent()) setHistory({ type, rows: page.rows, count: page.count });
    } catch (cause) {
      if (isCurrent()) setHistoryError(describeError(cause));
    }
  }

  function search(term: string) { setFilters({ q: term }); }

  const unitName = units.find((value) => value.id === unit)?.name;
  const applied: AppliedFilter[] = [
    ...(query ? [{ label: "Busca", value: query, onRemove: () => search("") }] : []),
    ...(unit ? [{ label: "Unidade", value: unitName ?? "selecionada", onRemove: () => setUnit("") }] : [])
  ];

  return (
    <>
      <div className="filter-bar">
        <SearchForm label="Buscar material" placeholder="Tipo, como munição 9 mm" value={query} onSearch={search} />
        <div className="field"><label htmlFor="filtro-unidade">Unidade</label><select id="filtro-unidade" value={unit} onChange={(event) => setUnit(event.target.value)}><option value="">Todas</option>{units.map((value) => <option key={value.id} value={value.id}>{value.name}</option>)}</select></div>
        {initialType && <a className="button button-quiet" href="/acervo?aba=sem-registro">Ver todos os tipos</a>}
        {session.permissions.can_use_stock && <a className="button button-secondary" href="/estoque">Operações no estoque</a>}
      </div>
      <AppliedFilters filters={applied} onClearAll={() => { setFilters({ q: "", unit: "" }); }} />

      {loading ? <LoadingState /> : error ? <ErrorState message={error} onRetry={() => void load()} /> : (
        <section className="list-panel" aria-label="Material sem registro">
          <div className="list-summary"><span><strong>{rows.length}</strong> {rows.length === 1 ? "posição de estoque" : "posições de estoque"}</span></div>
          {rows.length === 0 ? (
            <div className="empty-state">
              <h2>Nenhum material sem registro</h2>
              <p>{applied.length ? "Remova ou ajuste os filtros aplicados." : `Não há material sem registro ${scopeLabel(session)}.`}</p>
            </div>
          ) : (
            <ul className="sub-list feed">
              {rows.map((row) => (
                <li key={row.id}>
                  <span>
                    <strong>{row.equipment_type.name}</strong>
                    <small>{row.unit.name} · {row.storage_location.name}</small>
                    <span className="numbers">
                      <span>Em reserva: <strong>{formatQuantity(row.reserve)}</strong></span>
                      <span>Em posse: <strong>{formatQuantity(row.in_custody)}</strong></span>
                      <span>Total: <strong>{formatQuantity(row.total)}</strong></span>
                    </span>
                  </span>
                  <button className="button button-quiet" type="button" onClick={() => void openHistory(row.equipment_type)}>Histórico do tipo</button>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {historyError && <div className="feedback error" role="alert">{historyError}</div>}
      {history && (
        <section className="history-card stock-history" aria-label={`Histórico de ${history.type.name}`}>
          <h2>Histórico · {history.type.name}</h2>
          {history.count > history.rows.length && <p className="muted">Exibindo os {history.rows.length} lançamentos mais recentes de {history.count}.</p>}
          {history.rows.length === 0 ? <p className="muted">Nenhum lançamento {scopeLabel(session)}.</p> : (
            <ol className="timeline">
              {history.rows.map((entry) => (
                <li key={entry.id}>
                  <span className="timeline-dot" aria-hidden="true" />
                  <div>
                    <strong>{entry.type_label} de {formatQuantity(entry.quantity)} · {entry.unit} · {entry.storage_location}</strong>
                    <small>{formatDateTime(entry.occurred_at)} · operador {entry.operator}{entry.recipient && ` · pessoa ${entry.recipient}`}{entry.reason && ` · ${entry.reason}`}</small>
                  </div>
                </li>
              ))}
            </ol>
          )}
          <div className="actions"><button className="button button-quiet" type="button" onClick={() => setHistory(null)}>Fechar histórico</button></div>
        </section>
      )}
    </>
  );
}
