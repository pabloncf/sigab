import { useLatestRequest } from "../hooks/useLatestRequest";
import { useEffect, useRef, useState } from "react";
import { apiPage, apiWithMeta, describeError } from "../api/client";
import type { ItemSummary, PersonMatch, Session } from "../api/types";
import { ErrorState, LoadingState, UpdatingState } from "../components/Feedback";
import { scopeLabel } from "../components/format";
import { AppliedFilter, AppliedFilters, Pager, SearchForm, useListMemory, useUrlQuery } from "../components/Query";
import { StatusBadge } from "../components/StatusBadge";
import { StockCollection } from "../features/inventory/StockCollection";

export const ITEMS_LIST_KEY = "sigab:lista:acervo";
const PAGE_SIZE = 50;
const SEARCH_MIN = 2;
const AVAILABILITY: Record<string, string> = { available: "Disponível", in_custody: "Em posse", unavailable: "Indisponível" };

interface SearchResult {
  items: ItemSummary[];
  people: PersonMatch[];
}

/** Acervo com abas Com registro e Sem registro (SIGAB-081). */
export function ItemsPage({ session }: { session: Session }) {
  const params = new URLSearchParams(window.location.search);
  const holder = params.get("holder");
  const type = params.get("tipo") ?? "";
  const tab = !holder && params.get("aba") === "sem-registro" ? "sem-registro" : "com-registro";
  const canRegister = session.permissions.can_manage_catalog || session.permissions.can_create_item || session.permissions.can_receive_stock;
  const scope = scopeLabel(session);

  return (
    <>
      <section className="page-heading">
        <div>
          <p className="context-label">{session.organization.name}</p>
          <h1>{holder ? "Itens em posse" : "Acervo"}</h1>
          <p>{holder ? `Itens com registro com saída em aberto para esta pessoa, ${scope}.` : `Material com e sem registro ${scope}.`}</p>
        </div>
        {canRegister && !holder && <a className="button button-secondary" href="/equipamentos">Cadastrar equipamento</a>}
      </section>

      {!holder && (
        <nav className="tabs" aria-label="Natureza do material">
          <a href="/acervo" aria-current={tab === "com-registro" ? "page" : undefined}>Com registro</a>
          <a href="/acervo?aba=sem-registro" aria-current={tab === "sem-registro" ? "page" : undefined}>Sem registro</a>
        </nav>
      )}

      {tab === "sem-registro"
        ? <StockCollection session={session} initialType={type} />
        : <RegisteredItems holder={holder} type={type} scope={scope} />}
    </>
  );
}

function RegisteredItems({ holder, type, scope }: { holder: string | null; type: string; scope: string }) {
  const [query, setQuery] = useUrlQuery({ q: "", situacao: "", pagina: "1" });
  const availability = query.situacao in AVAILABILITY ? query.situacao : "";
  const page = Math.max(1, Number(query.pagina) || 1);
  const offset = (page - 1) * PAGE_SIZE;
  const [items, setItems] = useState<ItemSummary[]>([]);
  const [people, setPeople] = useState<PersonMatch[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadedOnce, setLoadedOnce] = useState(false);
  const listRef = useRef<HTMLElement>(null);
  useListMemory(ITEMS_LIST_KEY, loadedOnce);

  const beginRequest = useLatestRequest();

  async function loadItems() {
    const current = beginRequest();
    setLoading(true);
    setError("");
    try {
      const filters = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) });
      if (availability) filters.set("availability", availability);
      if (holder) filters.set("holder", holder);
      if (type) filters.set("type", type);
      const term = query.q.trim();
      if (term.length >= SEARCH_MIN) {
        // RF-50: one box for item numbers, types, units and people.
        filters.set("q", term);
        const result = await apiWithMeta<SearchResult, { items_count: number }>(`/search/?${filters}`);
        if (!current()) return;
        setItems(result.data.items);
        setPeople(result.data.people);
        setTotal(result.meta.items_count);
      } else {
        const result = await apiPage<ItemSummary>(`/items/?${filters}`);
        if (!current()) return;
        setItems(result.rows);
        setPeople([]);
        setTotal(result.count);
      }
    } catch (cause) {
      if (current()) setError(describeError(cause));
    } finally {
      if (current()) { setLoading(false); setLoadedOnce(true); }
    }
  }

  useEffect(() => { void loadItems(); }, [availability, query.q, page]);

  function goTo(nextOffset: number) {
    setQuery({ pagina: String(nextOffset / PAGE_SIZE + 1) });
    listRef.current?.scrollIntoView({ block: "start" });
  }

  const holderName = holder ? items[0]?.current_holder?.name : null;
  const applied: AppliedFilter[] = [
    ...(query.q ? [{ label: "Busca", value: query.q, onRemove: () => setQuery({ q: "", pagina: "1" }) }] : []),
    ...(availability ? [{ label: "Situação", value: AVAILABILITY[availability], onRemove: () => setQuery({ situacao: "", pagina: "1" }) }] : [])
  ];

  return (
    <>
      <div className="filter-bar">
        <SearchForm label="Buscar no acervo" placeholder="Número, tipo, unidade, nome ou matrícula" value={query.q} minLength={SEARCH_MIN}
          onSearch={(term) => setQuery({ q: term, pagina: "1" })} />
        <div className="field">
          <label htmlFor="filtro-situacao">Situação</label>
          <select id="filtro-situacao" value={availability} onChange={(event) => setQuery({ situacao: event.target.value, pagina: "1" })}>
            <option value="">Todas</option>
            {Object.entries(AVAILABILITY).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </div>
        {(holder || type) && <a className="button button-quiet" href="/acervo">Ver todo o acervo</a>}
      </div>

      <AppliedFilters filters={applied} onClearAll={() => setQuery({ q: "", situacao: "", pagina: "1" })} />

      {holder && <p className="muted">{holderName ?? "Pessoa sem itens com registro em posse"}</p>}

      {people.length > 0 && (
        <section inert={loading || undefined} className="list-panel people-results" aria-label="Pessoas encontradas">
          <div className="list-summary"><span><strong>{people.length}</strong> {people.length === 1 ? "pessoa encontrada" : "pessoas encontradas"}</span></div>
          <ul className="sub-list">
            {people.map((person) => (
              <li key={person.id}>
                <span><strong>{person.name}</strong><small>{person.registrations.join(", ") || "sem vínculo ativo"}{!person.is_active && " · inativa"}</small></span>
                <a className="button button-secondary" href={`/acervo?holder=${person.id}`}>Posse atual</a>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="list-panel" aria-label="Itens com registro" ref={listRef} aria-busy={loading || undefined}>
        {loading && loadedOnce && <UpdatingState />}
        {loading && !loadedOnce ? <LoadingState /> : error ? <ErrorState message={error} onRetry={() => void loadItems()} /> : (
          <div className="query-results" inert={loading || undefined}>
            <div className="list-summary">
              <Pager offset={offset} limit={PAGE_SIZE} count={total} onChange={goTo} noun={["item", "itens"]} />
              {total === 0 && <span>Nenhum item</span>}
            </div>
            {items.length === 0 ? (
              <div className="empty-state">
                <h2>Nenhum item encontrado</h2>
                <p>{applied.length ? "Remova ou ajuste os filtros aplicados." : `Não há itens com registro ${scope}.`}</p>
              </div>
            ) : (
              <div className="data-list">
                <div className="data-list-head item-columns" aria-hidden="true"><span>Item</span><span>Situação · condição</span><span>Responsável</span><span /></div>
                <ul className="item-list">
                  {items.map((item) => (
                    <li key={item.id}>
                      <a className="item-row item-columns" href={`/items/${item.id}`}>
                        <span className="item-identity"><strong>{item.identifier}</strong><small>{item.equipment_type}</small></span>
                        <StatusBadge item={item} />
                        <span className="holder"><span className="cell-label">Responsável: </span>{item.current_holder?.name ?? "Reserva"}</span>
                        <span className="row-arrow" aria-hidden="true">›</span>
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {total > PAGE_SIZE && <div className="list-footer"><Pager offset={offset} limit={PAGE_SIZE} count={total} onChange={goTo} noun={["item", "itens"]} /></div>}
          </div>
        )}
      </section>
    </>
  );
}
