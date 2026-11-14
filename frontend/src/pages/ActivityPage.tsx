import { useUrlQuery } from "../components/Query";
import { useLatestRequest } from "../hooks/useLatestRequest";
import { FormEvent, useEffect, useState } from "react";
import { apiPage, describeError } from "../api/client";
import type { ActivityEvent, Session } from "../api/types";
import { ErrorState, LoadingState } from "../components/Feedback";
import { scopeLabel } from "../components/format";

const PAGE = 30;
const ACTIONS: Record<string, string> = {
  "item.incorporated": "Incorporação",
  "item.checked_out": "Saída",
  "item.returned": "Devolução",
  "item.condition_changed": "Alteração de condição",
  "item.movement_reversed": "Estorno"
};

function query(filters: Record<string, string>, offset: number) {
  const params = new URLSearchParams({ limit: String(PAGE), offset: String(offset) });
  Object.entries(filters).forEach(([key, value]) => value && params.set(key, value));
  return `/activity/?${params}`;
}

export function ActivityPage({ session }: { session?: Session }) {
  const [applied, applyFilters] = useUrlQuery({ action: "", from: "", to: "", item: "", person: "" });
  const [filters, setFilters] = useState(applied);
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [count, setCount] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const beginRequest = useLatestRequest();

  async function load(nextFilters = applied, offset = 0) {
    const isCurrent = beginRequest();
    setLoading(true);
    setError("");
    try {
      const page = await apiPage<ActivityEvent>(query(nextFilters, offset));
      if (!isCurrent()) return;
      setEvents((current) => offset === 0 ? page.rows : [...current, ...page.rows]);
      setCount(page.count);
    } catch (requestError) {
      if (isCurrent()) setError(describeError(requestError));
    } finally {
      if (isCurrent()) setLoading(false);
    }
  }

  useEffect(() => { setFilters(applied); void load(); }, [applied]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    applyFilters(filters);
  }

  return (
    <>
      <section className="page-heading">
        <div>
          <p className="context-label">Atividade</p>
          <h1>Movimentações recentes</h1>
          <p>Consulte as movimentações registradas {session ? scopeLabel(session) : "nas unidades permitidas à sua conta"}, da mais recente à mais antiga.</p>
        </div>
      </section>

      <form className="filter-bar" onSubmit={handleSubmit}>
        <label className="field"><span>Ação</span><select value={filters.action} onChange={(event) => setFilters({ ...filters, action: event.target.value })}><option value="">Todas</option>{Object.entries(ACTIONS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label className="field"><span>De</span><input type="date" value={filters.from} onChange={(event) => setFilters({ ...filters, from: event.target.value })} /></label>
        <label className="field"><span>Até</span><input type="date" value={filters.to} onChange={(event) => setFilters({ ...filters, to: event.target.value })} /></label>
        <button className="button button-secondary">Filtrar</button>
        {(filters.item || filters.person) && <button className="button button-quiet" type="button" onClick={() => { const cleared = { ...filters, item: "", person: "" }; setFilters(cleared); applyFilters(cleared); }}>Limpar item/pessoa</button>}
      </form>

      {loading ? <LoadingState /> : error ? <ErrorState message={error} onRetry={() => void load()} /> : (
        <section className="list-panel" aria-label="Atividade">
          <div className="list-summary"><span><strong>{count}</strong> {count === 1 ? "registro" : "registros"}</span></div>
          {events.length === 0 ? <div className="empty-state"><h2>Nenhuma atividade</h2><p>Revise os filtros ou o período.</p></div> : (
            <ul className="sub-list feed">
              {events.map((event) => (
                <li key={event.id}>
                  <span>
                    <strong>{ACTIONS[event.type] ?? event.type} · <a href={`/items/${event.item.id}`}>{event.item.identifier}</a>{event.movement.reversed && <span className="status-badge warning"> estornado</span>}</strong>
                    <small>
                      {new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(event.occurred_at))} · {event.actor} · {event.item.equipment_type}
                      {event.movement.recipient && <> · <a href={`/atividade?person=${event.movement.recipient.id}`}>{event.movement.recipient.name}</a></>}
                      {event.movement.reason && ` · ${event.movement.reason}`}
                    </small>
                  </span>
                </li>
              ))}
            </ul>
          )}
          {events.length < count && <div className="actions"><button className="button button-secondary" onClick={() => void load(applied, events.length)}>Carregar mais ({count - events.length})</button></div>}
        </section>
      )}
    </>
  );
}
