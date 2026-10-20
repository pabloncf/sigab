import { FormEvent, useEffect, useState } from "react";
import { ApiError, apiRequest, postJson } from "../api/client";
import type { ItemDetail, MovementResult, Recipient } from "../api/types";
import { ErrorState, LoadingState } from "../components/Feedback";
import { StatusBadge } from "../components/StatusBadge";

type Action = "checkout" | "return" | "condition";

const EVENT_LABELS: Record<string, string> = {
  "item.incorporated": "Item incorporado",
  "item.checked_out": "Saída registrada",
  "item.returned": "Devolução registrada",
  "item.condition_changed": "Condição alterada"
};

export function ItemDetailPage({ itemId }: { itemId: string }) {
  const [item, setItem] = useState<ItemDetail | null>(null);
  const [recipients, setRecipients] = useState<Recipient[]>([]);
  const [action, setAction] = useState<Action | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  async function loadItem() {
    setLoading(true);
    setError("");
    try {
      setItem(await apiRequest<ItemDetail>(`/items/${itemId}/`));
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadItem(); }, [itemId]);

  async function openAction(nextAction: Action) {
    setError("");
    setSuccess("");
    if (nextAction === "checkout" && recipients.length === 0) {
      try {
        setRecipients(await apiRequest<Recipient[]>(`/items/${itemId}/recipients/`));
      } catch (requestError) {
        setError(requestError instanceof ApiError ? requestError.message : "Erro inesperado.");
        return;
      }
    }
    setAction(nextAction);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!action || !item) return;
    setSubmitting(true);
    setError("");
    const form = new FormData(event.currentTarget);
    const body: Record<string, unknown> = {
      idempotency_key: crypto.randomUUID(),
      confirmed: form.get("confirmed") === "on"
    };
    if (action === "checkout") body.recipient_id = form.get("recipient_id");
    if (action === "return") {
      body.condition = form.get("condition");
      body.reason = form.get("reason");
    }
    if (action === "condition") {
      body.condition = item.condition === "fit" ? "unfit" : "fit";
      body.reason = form.get("reason");
    }

    try {
      const result = await postJson<MovementResult>(`/items/${itemId}/${action}/`, body);
      setSuccess(result.created ? "Operação registrada com sucesso." : "Esta operação já havia sido processada.");
      setAction(null);
      await loadItem();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Erro inesperado.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <LoadingState />;
  if (error && !item) return <ErrorState message={error} onRetry={() => void loadItem()} />;
  if (!item) return null;

  const canChangeCondition = item.permissions.can_set_condition && item.administrative_status === "active" && item.availability !== "in_custody";

  return (
    <>
      <a className="back-link" href="/">‹ Voltar ao acervo</a>
      <section className="detail-heading">
        <div><p className="context-label">{item.equipment_type}</p><h1>{item.identifier}</h1></div>
        <StatusBadge item={item} />
      </section>

      {success && <div className="feedback success" role="status">{success}</div>}
      {error && <div className="feedback error" role="alert">{error}</div>}

      <div className="detail-grid">
        <section className="detail-card">
          <h2>Situação atual</h2>
          <dl className="facts">
            <div><dt>Condição</dt><dd>{item.condition_label}{item.condition_reason && <small>{item.condition_reason}</small>}</dd></div>
            <div><dt>Unidade</dt><dd>{item.unit.code} · {item.unit.name}</dd></div>
            <div><dt>Local de guarda</dt><dd>{item.storage_location.code} · {item.storage_location.name}</dd></div>
            <div><dt>Responsável</dt><dd>{item.current_holder?.name ?? "Nenhum"}</dd></div>
          </dl>
          <div className="actions">
            {item.permissions.can_move && item.availability === "available" && item.condition === "fit" && <button className="button button-primary" onClick={() => void openAction("checkout")}>Registrar saída</button>}
            {item.permissions.can_move && item.availability === "in_custody" && <button className="button button-primary" onClick={() => void openAction("return")}>Registrar devolução</button>}
            {canChangeCondition && <button className="button button-secondary" onClick={() => void openAction("condition")}>{item.condition === "unfit" ? "Liberar como apto" : "Declarar inapto"}</button>}
          </div>
        </section>

        <section className="history-card">
          <h2>Histórico imutável</h2>
          {item.events.length === 0 ? <p className="muted">Sem eventos registrados.</p> : (
            <ol className="timeline">
              {[...item.events].reverse().map((event) => (
                <li key={event.id}><span className="timeline-dot" /><div><strong>{EVENT_LABELS[event.type] ?? event.type}</strong><small>{new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(event.occurred_at))} · {event.actor}</small></div></li>
              ))}
            </ol>
          )}
        </section>
      </div>

      {action && (
        <div className="dialog-backdrop" role="presentation" onMouseDown={() => setAction(null)}>
          <section className="dialog" role="dialog" aria-modal="true" aria-labelledby="action-title" onMouseDown={(event) => event.stopPropagation()}>
            <h2 id="action-title">{action === "checkout" ? "Registrar saída" : action === "return" ? "Registrar devolução" : item.condition === "fit" ? "Declarar item inapto" : "Liberar item como apto"}</h2>
            <p>Confira o item <strong>{item.identifier}</strong> antes de confirmar.</p>
            <form onSubmit={handleSubmit}>
              {action === "checkout" && <label><span>Destinatário</span><select name="recipient_id" required defaultValue=""><option value="" disabled>Selecione uma pessoa</option>{recipients.map((recipient) => <option value={recipient.id} key={recipient.id}>{recipient.name}</option>)}</select></label>}
              {action === "return" && <><label><span>Condição na devolução</span><select name="condition" required defaultValue="fit"><option value="fit">Apto</option><option value="unfit">Inapto</option></select></label><label><span>Motivo, se inapto</span><textarea name="reason" maxLength={200} /></label></>}
              {action === "condition" && <label><span>{item.condition === "fit" ? "Motivo de inapto" : "Referência da conferência"}</span><textarea name="reason" maxLength={200} required /></label>}
              <label className="confirmation"><input type="checkbox" name="confirmed" required /><span>Confirmo a operação após conferir o item.</span></label>
              <div className="dialog-actions"><button className="button button-quiet" type="button" onClick={() => setAction(null)}>Cancelar</button><button className="button button-primary" disabled={submitting}>{submitting ? "Registrando…" : "Confirmar"}</button></div>
            </form>
          </section>
        </div>
      )}
    </>
  );
}
