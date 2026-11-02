import { useEffect, useMemo, useState } from "react";
import { ApiError, apiPage } from "../api/client";
import type { ItemSummary, Session } from "../api/types";
import { ErrorState, LoadingState } from "../components/Feedback";
import { IncorporateItemDialog } from "../components/IncorporateItemDialog";
import { StatusBadge } from "../components/StatusBadge";

const PAGE_LIMIT = 500;

export function ItemsPage({ session }: { session: Session }) {
  const [items, setItems] = useState<ItemSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [incorporating, setIncorporating] = useState(false);

  async function loadItems() {
    setLoading(true);
    setError("");
    try {
      const page = await apiPage<ItemSummary>(`/items/?limit=${PAGE_LIMIT}`);
      setItems(page.rows);
      setTotal(page.count);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadItems(); }, []);

  const filteredItems = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase("pt-BR");
    if (!normalizedQuery) return items;
    return items.filter((item) =>
      [item.identifier, item.equipment_type, item.current_holder?.name ?? ""]
        .some((value) => value.toLocaleLowerCase("pt-BR").includes(normalizedQuery))
    );
  }, [items, query]);

  return (
    <>
      <section className="page-heading">
        <div>
          <p className="context-label">Acervo individual</p>
          <h1>{session.organization.name}</h1>
          <p>Consulte a situação atual e registre movimentações dentro do seu escopo.</p>
        </div>
        <div className="stack">
          <label className="search-field">
            <span>Buscar item</span>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Número, tipo ou responsável" />
          </label>
          {session.permissions.can_create_item && <button className="button button-primary" type="button" onClick={() => setIncorporating(true)}>Incorporar item</button>}
        </div>
      </section>

      {loading ? <LoadingState /> : error ? <ErrorState message={error} onRetry={() => void loadItems()} /> : (
        <section className="list-panel" aria-label="Itens do acervo">
          <div className="list-summary"><strong>{filteredItems.length}</strong> {filteredItems.length === 1 ? "item encontrado" : "itens encontrados"}</div>
          {total > items.length && <div className="feedback warning" role="status">Exibindo os primeiros {items.length} de {total} itens. Refine a busca para localizar os demais.</div>}
          {filteredItems.length === 0 ? (
            <div className="empty-state">
              <h2>Nenhum item encontrado</h2>
              <p>Revise o termo de busca ou confirme seu escopo de acesso.</p>
            </div>
          ) : (
            <div className="item-list">
              {filteredItems.map((item) => (
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
