import { FormEvent, useEffect, useState } from "react";
import { ApiError, apiPage, postJson } from "../api/client";
import type { PersonDetail, PersonSummary } from "../api/types";
import { ActionDialog, text } from "../components/ActionDialog";
import { ErrorState, LoadingState } from "../components/Feedback";

export function PeoplePage() {
  const [people, setPeople] = useState<PersonSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  async function loadPeople(search = query) {
    setLoading(true);
    setError("");
    try {
      const page = await apiPage<PersonSummary>(`/people/?limit=200&q=${encodeURIComponent(search.trim())}`);
      setPeople(page.rows);
      setTotal(page.count);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadPeople(""); }, []);

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void loadPeople();
  }

  async function createPerson(form: FormData) {
    const person = await postJson<PersonDetail>("/people/", {
      name: text(form, "name"),
      functional_name: text(form, "functional_name"),
      cpf: text(form, "cpf"),
      phone: text(form, "phone")
    });
    window.location.assign(`/pessoas/${person.id}`);
  }

  return (
    <>
      <section className="page-heading">
        <div>
          <p className="context-label">Identidade</p>
          <h1>Pessoas</h1>
          <p>Cadastre pessoas e vínculos. A conta de acesso é criada separadamente, só quando necessária.</p>
        </div>
        <div className="stack">
          <form className="search-field" onSubmit={handleSearch} role="search">
            <span>Buscar pessoa</span>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Nome, nome funcional ou matrícula" />
          </form>
          <button className="button button-primary" type="button" onClick={() => setCreating(true)}>Cadastrar pessoa</button>
        </div>
      </section>

      {loading ? <LoadingState /> : error ? <ErrorState message={error} onRetry={() => void loadPeople()} /> : (
        <section className="list-panel" aria-label="Pessoas da organização">
          <div className="list-summary"><strong>{total}</strong> {total === 1 ? "pessoa encontrada" : "pessoas encontradas"}</div>
          {total > people.length && <div className="feedback warning" role="status">Exibindo as primeiras {people.length}. Refine a busca para localizar as demais.</div>}
          {people.length === 0 ? (
            <div className="empty-state">
              <h2>Nenhuma pessoa encontrada</h2>
              <p>Revise o termo de busca ou cadastre uma nova pessoa.</p>
            </div>
          ) : (
            <div className="item-list">
              {people.map((person) => (
                <a className="item-row" href={`/pessoas/${person.id}`} key={person.id}>
                  <span className="item-identity"><strong>{person.functional_name || person.name}</strong><small>{person.functional_name ? person.name : "Sem nome funcional"}</small></span>
                  <span className={`status-badge ${person.is_active ? "success" : "warning"}`}>{person.is_active ? "Ativa" : "Inativa"}</span>
                  <span className="holder"><small>Matrícula · Conta</small>{person.registrations.join(", ") || "Sem vínculo ativo"} · {person.has_account ? "com conta" : "sem conta"}</span>
                  <span className="row-arrow" aria-hidden="true">›</span>
                </a>
              ))}
            </div>
          )}
        </section>
      )}

      {creating && (
        <ActionDialog title="Cadastrar pessoa" description="Nenhuma conta de acesso é criada neste passo." submitLabel="Cadastrar" onClose={() => setCreating(false)} onSubmit={createPerson}>
          <label><span>Nome completo</span><input name="name" required maxLength={180} /></label>
          <label><span>Nome funcional</span><input name="functional_name" maxLength={120} /></label>
          <label><span>CPF (opcional)</span><input name="cpf" inputMode="numeric" maxLength={14} autoComplete="off" /></label>
          <label><span>Celular</span><input name="phone" inputMode="tel" maxLength={24} /></label>
        </ActionDialog>
      )}
    </>
  );
}
