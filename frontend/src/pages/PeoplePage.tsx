import { useLatestRequest } from "../hooks/useLatestRequest";
import { FormEvent, useEffect, useRef, useState } from "react";
import { apiPage, apiRequest, describeError, postForm, postJson } from "../api/client";
import type { PersonDetail, PersonSummary, Session, UnitOption } from "../api/types";
import { FormErrorState, FormErrorSummary, formError, text } from "../components/ActionDialog";
import { FaceCapture } from "../components/FaceCapture";
import { ErrorState, LoadingState, UpdatingState } from "../components/Feedback";
import { Field, FieldErrorsContext } from "../components/Field";
import { Modal } from "../components/Modal";
import { AppliedFilters, Pager, SearchForm, useListMemory, useUrlQuery } from "../components/Query";

export const PEOPLE_LIST_KEY = "sigab:lista:pessoas";
const PAGE_SIZE = 50;

export function PeoplePage({ session }: { session: Session }) {
  const [query, setQuery] = useUrlQuery({ q: "", pagina: "1" });
  const page = Math.max(1, Number(query.pagina) || 1);
  const offset = (page - 1) * PAGE_SIZE;
  const [people, setPeople] = useState<PersonSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadedOnce, setLoadedOnce] = useState(false);
  const [creating, setCreating] = useState(false);
  const listRef = useRef<HTMLElement>(null);
  useListMemory(PEOPLE_LIST_KEY, loadedOnce);

  const beginRequest = useLatestRequest();

  async function loadPeople() {
    const current = beginRequest();
    setLoading(true);
    setError("");
    try {
      const filters = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) });
      if (query.q) filters.set("q", query.q);
      const result = await apiPage<PersonSummary>(`/people/?${filters}`);
      if (!current()) return;
      setPeople(result.rows);
      setTotal(result.count);
    } catch (cause) {
      if (current()) setError(describeError(cause));
    } finally {
      if (current()) { setLoading(false); setLoadedOnce(true); }
    }
  }

  useEffect(() => { void loadPeople(); }, [query.q, page]);

  function goTo(nextOffset: number) {
    setQuery({ pagina: String(nextOffset / PAGE_SIZE + 1) });
    listRef.current?.scrollIntoView({ block: "start" });
  }

  return (
    <>
      <section className="page-heading">
        <div>
          <p className="context-label">{session.organization.name}</p>
          <h1>Pessoas</h1>
          <p>Cadastre pessoas e vínculos. A conta de acesso é criada separadamente, só quando necessária.</p>
        </div>
        <button className="button button-primary" type="button" onClick={() => setCreating(true)}>Cadastrar pessoa</button>
      </section>

      <div className="filter-bar">
        <SearchForm label="Buscar pessoa" placeholder="Nome, nome funcional ou matrícula" value={query.q} onSearch={(term) => setQuery({ q: term, pagina: "1" })} />
      </div>
      <AppliedFilters filters={query.q ? [{ label: "Busca", value: query.q, onRemove: () => setQuery({ q: "", pagina: "1" }) }] : []} />

      <section className="list-panel" aria-label="Pessoas da organização" ref={listRef} aria-busy={loading || undefined}>
        {loading && loadedOnce && <UpdatingState />}
        {loading && !loadedOnce ? <LoadingState /> : error ? <ErrorState message={error} onRetry={() => void loadPeople()} /> : (
          <div className="query-results" inert={loading || undefined}>
            <div className="list-summary">
              <Pager offset={offset} limit={PAGE_SIZE} count={total} onChange={goTo} noun={["pessoa", "pessoas"]} />
              {total === 0 && <span>Nenhuma pessoa</span>}
            </div>
            {people.length === 0 ? (
              <div className="empty-state">
                <h2>Nenhuma pessoa encontrada</h2>
                <p>{query.q ? "Revise o termo de busca ou cadastre uma nova pessoa." : "Cadastre a primeira pessoa da organização."}</p>
              </div>
            ) : (
              <div className="data-list">
                <div className="data-list-head person-columns" aria-hidden="true"><span>Pessoa</span><span>Situação</span><span>Matrícula · conta</span><span /></div>
                <ul className="item-list">
                  {people.map((person) => (
                    <li key={person.id}>
                      <a className="item-row person-columns" href={`/pessoas/${person.id}`}>
                        <span className="item-identity"><strong>{person.functional_name || person.name}</strong>{person.functional_name && <small>{person.name}</small>}</span>
                        <span className={`status-badge ${person.is_active ? "success" : "warning"}`}>{person.is_active ? "Ativa" : "Inativa"}</span>
                        <span className="holder"><span className="cell-label">Matrícula · conta: </span>{person.registrations.join(", ") || "Sem vínculo ativo"} · {person.has_account ? "com conta" : "sem conta"}</span>
                        <span className="row-arrow" aria-hidden="true">›</span>
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {total > PAGE_SIZE && <div className="list-footer"><Pager offset={offset} limit={PAGE_SIZE} count={total} onChange={goTo} noun={["pessoa", "pessoas"]} /></div>}
          </div>
        )}
      </section>

      {creating && <CreatePersonDialog canEnroll={Boolean(session.permissions.can_manage_biometrics)} onClose={() => setCreating(false)} />}
    </>
  );
}

/**
 * Cadastro de pessoa com o primeiro vínculo e a biometria facial (SIGAB-085).
 *
 * Pessoa e vínculo são criados juntos no servidor; a face é cadastrada em seguida, só com o
 * vínculo ativo. A captura fica apenas em memória até o envio.
 */
function CreatePersonDialog({ canEnroll, onClose }: { canEnroll: boolean; onClose: () => void }) {
  const [units, setUnits] = useState<UnitOption[]>([]);
  const [unitsError, setUnitsError] = useState("");
  const [registration, setRegistration] = useState("");
  const [unitId, setUnitId] = useState("");
  const [consent, setConsent] = useState(false);
  const [face, setFace] = useState<Blob | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<FormErrorState | null>(null);
  const [created, setCreated] = useState<{ id: string; message: string } | null>(null);
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    apiRequest<UnitOption[]>("/units/").then((rows) => setUnits(rows.filter((unit) => unit.is_active)))
      .catch((cause) => setUnitsError(`Não foi possível carregar as unidades: ${describeError(cause)}`));
  }, []);

  const withMembership = Boolean(registration.trim() && unitId);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSubmitting(true);
    setError(null);
    let person: PersonDetail;
    try {
      person = await postJson<PersonDetail>("/people/", {
        name: text(form, "name"),
        functional_name: text(form, "functional_name"),
        cpf: text(form, "cpf"),
        phone: text(form, "phone"),
        ...(registration.trim() ? { registration: registration.trim(), main_unit_id: unitId, rank: text(form, "rank") } : {})
      });
    } catch (cause) {
      setError(formError(cause, formRef.current));
      setSubmitting(false);
      return;
    }
    if (face && withMembership) {
      const upload = new FormData();
      upload.set("confirmed", "true");
      upload.set("image", face, "captura.jpg");
      try {
        await postForm(`/people/${person.id}/biometric/`, upload);
      } catch (cause) {
        // A pessoa já existe; a biometria pode ser refeita na ficha.
        setFace(null);
        setSubmitting(false);
        setCreated({ id: person.id, message: `A pessoa foi cadastrada, mas a biometria não foi registrada (${describeError(cause)}). Abra a ficha da pessoa e capture o rosto novamente.` });
        return;
      }
    }
    window.location.assign(`/pessoas/${person.id}`);
  }

  return (
    <Modal title="Cadastrar pessoa" size="wide" busy={submitting} onClose={onClose}
      description="Preencha as seções na ordem. Nenhuma conta de acesso é criada neste passo. Campos sem marcação são obrigatórios.">
      {created ? (
        <>
          <div className="feedback warning" role="alert">{created.message}</div>
          <div className="dialog-actions"><a className="button button-primary" href={`/pessoas/${created.id}`}>Abrir ficha</a></div>
        </>
      ) : (
        <FieldErrorsContext.Provider value={error?.fields ?? {}}>
          <FormErrorSummary error={error} />
          <form ref={formRef} onSubmit={submit} className="sectioned-form">
            <fieldset className="form-section">
              <legend><span className="step">1</span> Dados pessoais</legend>
              <div className="form-grid">
                <Field label="Nome completo"><input name="name" required maxLength={180} autoComplete="off" /></Field>
                <Field label="Nome funcional" optional><input name="functional_name" maxLength={120} autoComplete="off" /></Field>
                <Field label="CPF" optional hint="Fica fora das telas operacionais."><input name="cpf" inputMode="numeric" maxLength={14} autoComplete="off" /></Field>
                <Field label="Celular" optional><input name="phone" inputMode="tel" maxLength={24} autoComplete="off" /></Field>
              </div>
            </fieldset>

            <fieldset className="form-section">
              <legend><span className="step">2</span> Vínculo <span className="field-optional">(opcional)</span></legend>
              <p className="muted">Sem vínculo, a pessoa não recebe material nem cadastra biometria. Se informar a matrícula, a unidade passa a ser obrigatória.</p>
              {unitsError && <div className="feedback warning" role="alert">{unitsError}</div>}
              <div className="form-grid">
                <Field label="Matrícula" name="registration" optional><input value={registration} onChange={(event) => setRegistration(event.target.value)} maxLength={64} autoComplete="off" /></Field>
                <Field label="Unidade principal" name="main_unit_id" optional={!registration.trim()} hint={registration.trim() ? "Obrigatória ao informar matrícula." : undefined}><select value={unitId} required={Boolean(registration.trim())} onChange={(event) => setUnitId(event.target.value)}><option value="">Selecione</option>{units.map((unit) => <option key={unit.id} value={unit.id}>{unit.code} · {unit.name}</option>)}</select></Field>
                <Field label="Posto ou graduação" optional><input name="rank" maxLength={80} autoComplete="off" /></Field>
              </div>
            </fieldset>

            {canEnroll && (
              <fieldset className="form-section" aria-label="Biometria facial">
                <legend><span className="step">3</span> Biometria facial <span className="field-optional">(opcional)</span></legend>
                {!withMembership ? <p className="muted">Informe matrícula e unidade para cadastrar a face: a biometria exige vínculo ativo.</p> : face ? (
                  <div className="actions-inline">
                    <FacePreview image={face} />
                    <span className="status-badge success">Rosto capturado</span>
                    <button className="button button-quiet" type="button" onClick={() => setFace(null)}>Capturar de novo</button>
                  </div>
                ) : (
                  <>
                    <label className="confirmation"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /><span>A pessoa está presente e foi informada da finalidade, da retenção e de que a biometria é exigida para retirar e devolver material.</span></label>
                    <FaceCapture label="Capturar rosto" disabled={!consent || submitting} onCapture={setFace} />
                    <p className="muted">Sem a face, retirada e devolução dependem de termo aprovado pelo administrador do acervo. Pode ser cadastrada depois, na ficha.</p>
                  </>
                )}
              </fieldset>
            )}

            <div className="dialog-actions">
              <button className="button button-quiet" type="button" onClick={onClose} disabled={submitting}>Cancelar</button>
              <button className="button button-primary" disabled={submitting}>{submitting ? "Registrando…" : "Cadastrar"}</button>
            </div>
          </form>
        </FieldErrorsContext.Provider>
      )}
    </Modal>
  );
}

/** Miniatura do recorte enviado; o endereço temporário existe só em memória. */
function FacePreview({ image }: { image: Blob }) {
  const [url, setUrl] = useState("");
  useEffect(() => {
    const objectUrl = URL.createObjectURL(image);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [image]);
  return url ? <img className="face-preview" src={url} alt="Recorte do rosto que será cadastrado" /> : null;
}
