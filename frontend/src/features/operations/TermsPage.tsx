import { useUrlQuery } from "../../components/Query";
import { useLatestRequest } from "../../hooks/useLatestRequest";
import { useEffect, useState } from "react";
import { ApiError, apiRequest, postJson, describeError } from "../../api/client";
import type { IdentityExceptionTerm, Session } from "../../api/types";
import { ErrorState, LoadingState } from "../../components/Feedback";
import { formatDateTime, formatQuantity } from "../../components/format";

const STATUS_FILTERS = [
  { value: "pending_approval", label: "Aguardando aprovação" },
  { value: "pending_signature", label: "Aguardando assinatura" },
  { value: "", label: "Todos" }
];

/** Fila de termos de retirada e devolução sem biometria (ADR 0008, seção 8). */
export function TermsPage({ session }: { session: Session }) {
  const approver = Boolean(session.permissions.can_approve_identity_exceptions);
  const [filters, setFilters] = useUrlQuery({ status: approver ? "pending_approval" : "" });
  const status = filters.status;
  const [terms, setTerms] = useState<IdentityExceptionTerm[] | null>(null);
  const [error, setError] = useState("");

  const beginRequest = useLatestRequest();

  async function load(value = status) {
    const isCurrent = beginRequest();
    setError("");
    setTerms(null);
    try {
      const result = await apiRequest<IdentityExceptionTerm[]>(`/identity-exceptions/${value ? `?status=${value}` : ""}`);
      if (isCurrent()) setTerms(result);
    } catch (cause) {
      if (isCurrent()) setError(describeError(cause));
    }
  }

  useEffect(() => { void load(); }, [status]);

  return (
    <>
      <section className="page-heading">
        <div>
          <p className="context-label">Retirada e devolução</p>
          <h1>Termos sem biometria</h1>
          <p>Quando a biometria facial não é possível, a operação gera um termo. A pessoa assina e somente o administrador do acervo aprova. Nada é movimentado antes da aprovação.</p>
        </div>
      </section>
      <div className="filter-bar">
        <label className="field"><span>Situação</span><select value={status} onChange={(event) => setFilters({ status: event.target.value })}>{STATUS_FILTERS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
      </div>
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : !terms ? <LoadingState /> : (
        <section className="list-panel" aria-label="Termos">
          <div className="list-summary"><span><strong>{terms.length}</strong> {terms.length === 1 ? "termo" : "termos"}</span></div>
          {terms.length === 0 ? <p className="empty-state">Nenhum termo nesta situação.</p> : (
            <ul className="sub-list feed">
              {terms.map((term) => (
                <li key={term.id}>
                  <span>
                    <strong><a href={`/atendimento/termos/${term.id}`}>{term.code}</a> · {term.operation_label} · {term.person.name}</strong>
                    <small>{term.status_label} · {term.reason_label} · registrado por {term.requested_by} em {formatDateTime(term.requested_at)}</small>
                  </span>
                  {term.permissions.can_decide && <a className="button button-primary" href={`/atendimento/termos/${term.id}`}>Analisar</a>}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </>
  );
}

/** Termo para impressão, assinatura e decisão. */
export function TermDetailPage({ termId }: { termId: string }) {
  const [term, setTerm] = useState<IdentityExceptionTerm | null>(null);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  const [busy, setBusy] = useState(false);
  const [decisionReason, setDecisionReason] = useState("");

  async function load() {
    setError("");
    try {
      setTerm(await apiRequest<IdentityExceptionTerm>(`/identity-exceptions/${termId}/`));
    } catch (cause) {
      setError(describeError(cause));
    }
  }

  useEffect(() => { void load(); }, [termId]);

  async function act(path: string, body: Record<string, unknown>) {
    setBusy(true);
    setActionError("");
    try {
      setTerm(await postJson<IdentityExceptionTerm>(`/identity-exceptions/${termId}/${path}/`, { ...body, confirmed: true }));
    } catch (cause) {
      setActionError(cause instanceof ApiError ? cause.message : "Não foi possível concluir.");
    } finally {
      setBusy(false);
    }
  }


  if (error) return <ErrorState message={error} onRetry={() => void load()} />;
  if (!term) return <LoadingState label="Carregando termo" />;
  const checkout = term.operation === "checkout";

  return (
    <>
      <a className="back-link no-print" href="/atendimento/termos">‹ Voltar aos termos</a>
      <article className="detail-card term" aria-label={`Termo ${term.code}`}>
        <p className="context-label">Termo de {checkout ? "retirada" : "devolução"} sem biometria</p>
        <h1>{term.code}</h1>
        <p className="term-status">{term.status_label}</p>
        <dl className="facts">
          <div><dt>Servidor público</dt><dd>{term.person.name}</dd></div>
          <div><dt>Matrícula</dt><dd>{term.person.registration ?? "—"}</dd></div>
          <div><dt>Operação</dt><dd>{term.operation_label}</dd></div>
          <div><dt>Registrado por</dt><dd>{term.requested_by} · {formatDateTime(term.requested_at)}</dd></div>
          <div><dt>Motivo da ausência de biometria</dt><dd>{term.reason_label}{term.reason && ` · ${term.reason}`}</dd></div>
          {checkout && <div><dt>Modalidade</dt><dd>{term.custody_mode === "shift" ? "Por turno" : term.custody_mode === "fixed_term" ? `Prazo determinado até ${term.due_at ? formatDateTime(term.due_at) : "—"}` : "Prazo indeterminado"}</dd></div>}
        </dl>
        <h2>Materiais</h2>
        <ul className="sub-list">
          {term.items.map((item) => <li key={item.id}><span><strong>{item.identifier} · {item.equipment_type}</strong><small>{item.unit}{item.condition && ` · ${item.condition === "fit" ? "apto" : `inapto: ${item.reason}`}`}</small></span></li>)}
          {term.stock.map((line, index) => <li key={index}><span><strong>{formatQuantity(line.quantity)} · {line.equipment_type}</strong><small>{line.unit}</small></span></li>)}
        </ul>
        <p className="term-statement">Declaro que {checkout ? "recebi" : "devolvi"} os materiais acima nesta data, sem validação biométrica pelo motivo indicado.</p>
        <div className="signatures">
          <div><span className="signature-line" /><small>{term.person.name} · servidor público</small></div>
          <div><span className="signature-line" /><small>Administrador do acervo</small></div>
        </div>
        {term.decided_at && <p className="muted">Decisão: {term.status_label} por {term.decided_by ?? "—"} em {formatDateTime(term.decided_at)}{term.decision_reason && ` · ${term.decision_reason}`}</p>}
      </article>

      <section className="detail-card no-print stock-action" aria-label="Ações do termo">
        {actionError && <div className="feedback error" role="alert">{actionError}</div>}
        <div className="dialog-actions">
          <button className="button button-secondary" type="button" onClick={() => window.print()}>Imprimir termo</button>
          {term.permissions.can_register_signature && <button className="button button-primary" type="button" disabled={busy} onClick={() => void act("signed", {})}>Registrar termo assinado</button>}
        </div>
        {term.permissions.can_decide && (
          <form className="dialog-form" aria-label="Decisão do administrador" onSubmit={(event) => { event.preventDefault(); void act("decision", { approve: true, reason: decisionReason.trim() }); }}>
            <p>Confira o termo assinado antes de decidir. A aprovação confirma a {checkout ? "retirada" : "devolução"} agora.</p>
            <label className="field"><span>Motivo (obrigatório para recusar)</span><textarea maxLength={500} value={decisionReason} onChange={(event) => setDecisionReason(event.target.value)} /></label>
            <div className="dialog-actions">
              <button className="button button-quiet" type="button" disabled={busy || !decisionReason.trim()} onClick={() => void act("decision", { approve: false, reason: decisionReason.trim() })}>Recusar</button>
              <button className="button button-primary" disabled={busy}>Aprovar {checkout ? "retirada" : "devolução"}</button>
            </div>
          </form>
        )}
        {term.permissions.can_cancel && (
          <form className="dialog-form" aria-label="Cancelar termo" onSubmit={(event) => {
            event.preventDefault();
            void act("cancel", { reason: String(new FormData(event.currentTarget).get("reason") ?? "").trim() });
          }}>
            <label className="field"><span>Motivo do cancelamento</span><input name="reason" required maxLength={500} /></label>
            <div className="dialog-actions"><button className="button button-quiet" disabled={busy}>Cancelar termo</button></div>
          </form>
        )}
      </section>
    </>
  );
}
