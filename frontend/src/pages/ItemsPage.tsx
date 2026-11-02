import { FormEvent, useEffect, useState } from "react";
import { ApiError, apiPage, apiWithMeta } from "../api/client";
import type { ItemSummary, PersonMatch, Session } from "../api/types";
import { ErrorState, LoadingState } from "../components/Feedback";
import { IncorporateItemDialog } from "../components/IncorporateItemDialog";
import { StatusBadge } from "../components/StatusBadge";

const PAGE_LIMIT = 100;

interface SearchResult {
  items: ItemSummary[];
  people: PersonMatch[];
}

export function ItemsPage({ session }: { session: Session }) {
  const holder = new URLSearchParams(window.location.search).get("holder");
  const [items, setItems] = useState<ItemSummary[]>([]);
  const [people, setPeople] = useState<PersonMatch[]>([]);
  const [total, setTotal] = useState(0);
  const [query, setQuery] = useState("");
  const [availability, setAvailability] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [incorporating, setIncorporating] = useState(false);

  async function loadItems() {
    setLoading(true);
    setError("");
    try {
      const filters = new URLSearchParams({ limit: String(PAGE_LIMIT) });
      if (availability) filters.set("availability", availability);
      if (holder) filters.set("holder", holder);
      const term = query.trim();
      if (term.length >= 2) {
        // RF-50: one box for item numbers, types, units and people.
        filters.set("q", term);
        const result = await apiWithMeta<SearchResult, { items_count: number }>(`/search/?${filters}`);
        setItems(result.data.items);
        setPeople(result.data.people);
        setTotal(result.meta.items_count);
      } else {
        const page = await apiPage<ItemSummary>(`/items/?${filters}`);
        setItems(page.rows);
        setPeople([]);
        setTotal(page.count);
      }
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadItems(); }, [availability]);

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void loadItems();
  }

  const holderName = holder ? items[0]?.current_holder?.name : null;

  return (
    <>
      <section className="page-heading">
        <div>
          <p className="context-label">{holder ? "Posse atual" : "Acervo individual"}</p>
          <h1>{holder ? holderName ?? "Pessoa sem itens em posse" : session.organization.name}</h1>
          <p>{holder ? "Itens com saída em aberto para esta pessoa, no seu escopo." : "Consulte a situação atual e registre movimentações dentro do seu escopo."}</p>
        </div>
        <div className="stack">
          <form className="search-field" onSubmit={handleSearch} role="search">
            <span>Buscar</span>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Número, tipo, unidade, nome ou matrícula" />
          </form>
          {session.permissions.can_create_item && !holder && <button className="button button-primary" type="button" onClick={() => setIncorporating(true)}>Incorporar item</button>}
        </div>
      </section>

      <div className="filter-bar">
        <label><span>Situação</span><select value={availability} onChange={(event) => setAvailability(event.target.value)}><option value="">Todas</option><option value="available">Disponível</option><option value="in_custody">Em posse</option><option value="unavailable">Indisponível</option></select></label>
        {holder && <a className="button button-quiet" href="/">Ver todo o acervo</a>}
      </div>

      {people.length > 0 && (
        <section className="list-panel people-results" aria-label="Pessoas encontradas">
          <div className="list-summary"><strong>{people.length}</strong> {people.length === 1 ? "pessoa encontrada" : "pessoas encontradas"}</div>
          <ul className="sub-list">
            {people.map((person) => (
              <li key={person.id}>
                <span><strong>{person.name}</strong><small>{person.registrations.join(", ") || "sem vínculo ativo"}{!person.is_active && " · inativa"}</small></span>
                <a className="button button-secondary" href={`/?holder=${person.id}`}>Posse atual</a>
              </li>
            ))}
          </ul>
        </section>
      )}

      {loading ? <LoadingState /> : error ? <ErrorState message={error} onRetry={() => void loadItems()} /> : (
        <section className="list-panel" aria-label="Itens do acervo">
          <div className="list-summary"><strong>{total}</strong> {total === 1 ? "item encontrado" : "itens encontrados"}</div>
          {total > items.length && <div className="feedback warning" role="status">Exibindo os primeiros {items.length} de {total} itens. Refine a busca para localizar os demais.</div>}
          {items.length === 0 ? (
            <div className="empty-state">
              <h2>Nenhum item encontrado</h2>
              <p>Revise o termo de busca ou confirme seu escopo de acesso.</p>
            </div>
          ) : (
            <div className="item-list">
              {items.map((item) => (
                <a className="item-row" href={`/items/${item.id}`} key={item.id}>
                  <span className="item-identity"><strong>{item.identifier}</strong><small>{item.equipment_type}</small></span>
                  <StatusBadge item={item} />
                  <span className="holder"><small>Responsável</small>{item.current_holder?.name ?? "Reserva"}</span>
                  <span className="row-arrow" aria-hidden="true">›</span>
                </a>
              ))}
            </div>
          )}
        </section>
      )}

      {incorporating && <IncorporateItemDialog onClose={() => setIncorporating(false)} onCreated={(item) => window.location.assign(`/items/${item.id}`)} />}
    </>
  );
}
