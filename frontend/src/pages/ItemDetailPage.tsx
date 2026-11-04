import { FormEvent, useEffect, useState } from "react";
import { ApiError, apiPage, apiRequest, postJson } from "../api/client";
import type { ItemDetail, ItemEvent, MovementResult, Recipient } from "../api/types";
import { ErrorState, LoadingState } from "../components/Feedback";
import { StatusBadge } from "../components/StatusBadge";

type Action = "checkout" | "return" | "condition" | "reverse";

const HISTORY_PAGE = 20;

const formatInstant = (value: string) => new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));

const EVENT_LABELS: Record<string, string> = {
  "item.incorporated": "Item incorporado",
  "item.checked_out": "Saída registrada",
  "item.returned": "Devolução registrada",
  "item.condition_changed": "Condição alterada",
  "item.movement_reversed": "Estorno"
};

export function ItemDetailPage({ itemId }: { itemId: string }) {
  const [item, setItem] = useState<ItemDetail | null>(null);
  const [events, setEvents] = useState<ItemEvent[]>([]);
  const [eventCount, setEventCount] = useState(0);
  const [recipients, setRecipients] = useState<Recipient[]>([]);
  const [action, setAction] = useState<Action | null>(null);
  // Reconciliation of the paper book after an outage (SIGAB-046, ADR 0004).
  const [contingency, setContingency] = useState(false);
  // One key per opened dialog: resubmitting after a network failure replays, never duplicates.
  const [idempotencyKey, setIdempotencyKey] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  async function loadItem() {
    setLoading(true);
    setError("");
    try {
      setItem(await apiRequest<ItemDetail>(`/items/${itemId}/`));
      const page = await apiPage<ItemEvent>(`/items/${itemId}/events/?limit=${HISTORY_PAGE}`);
      setEvents(page.rows);
      setEventCount(page.count);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadItem(); }, [itemId]);

  async function loadMoreEvents() {
    try {
      const page = await apiPage<ItemEvent>(`/items/${itemId}/events/?limit=${HISTORY_PAGE}&offset=${events.length}`);
      setEvents([...events, ...page.rows]);
      setEventCount(page.count);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Erro inesperado.");
    }
  }

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
    setIdempotencyKey(crypto.randomUUID());
    setContingency(false);
    setAction(nextAction);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!action || !item) return;
    setSubmitting(true);
    setError("");
    const form = new FormData(event.currentTarget);
    const body: Record<string, unknown> = {
      idempotency_key: idempotencyKey,
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
    if (action === "reverse") body.reason = form.get("reason");
    if (contingency && (action === "checkout" || action === "return")) {
      // datetime-local has no zone: it is read in the browser's zone and sent in UTC.
      body.contingency = {
        occurred_at: new Date(String(form.get("occurred_at"))).toISOString(),
        paper_reference: form.get("paper_reference")
      };
    }
    const url = action === "reverse" ? `/movements/${item.reversible_movement_id}/reverse/` : `/items/${itemId}/${action}/`;

    try {
      const result = await postJson<MovementResult>(url, body);
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
            <div><dt>Série · Patrimônio</dt><dd>{item.serial_number || "—"} · {item.asset_number || "—"}</dd></div>
            {item.official_identifier && <div><dt>Registro oficial</dt><dd>{item.official_identifier}</dd></div>}
          </dl>
          <div className="actions">
            {item.permissions.can_checkout && item.availability === "available" && item.condition === "fit" && <button className="button button-primary" onClick={() => void openAction("checkout")}>Registrar saída</button>}
            {item.permissions.can_return && item.availability === "in_custody" && <button className="button button-primary" onClick={() => void openAction("return")}>Registrar devolução</button>}
            {canChangeCondition && <button className="button button-secondary" onClick={() => void openAction("condition")}>{item.condition === "unfit" ? "Liberar como apto" : "Declarar inapto"}</button>}
            {item.reversible_movement_id && <button className="button button-quiet" onClick={() => void openAction("reverse")}>Estornar último registro</button>}
          </div>
        </section>

        <section className="history-card">
          <h2>Histórico imutável</h2>
          {events.length === 0 ? <p className="muted">Sem eventos registrados.</p> : (
            <ol className="timeline">
              {events.map((event) => (
                <li key={event.id}><span className="timeline-dot" /><div><strong>{EVENT_LABELS[event.type] ?? event.type}{event.movement.reversed && <span className="status-badge warning"> estornado</span>}</strong><small>{formatInstant(event.occurred_at)} · {event.actor}{event.movement.recipient && ` · ${event.movement.recipient.name}`}{event.movement.condition && ` · ${event.movement.condition === "fit" ? "apto" : "inapto"}`}</small>{event.movement.origin === "contingency" && <small>Contingência · {event.movement.paper_reference} · lançado em {formatInstant(event.movement.recorded_at)}</small>}{event.movement.reason && <small>{event.movement.reason}</small>}</div></li>
              ))}
            </ol>
          )}
          {events.length < eventCount && <button className="button button-secondary" onClick={() => void loadMoreEvents()}>Carregar eventos seguintes ({eventCount - events.length})</button>}
        </section>
      </div>

      {action && (
        <div className="dialog-backdrop" role="presentation" onMouseDown={() => setAction(null)}>
          <section className="dialog" role="dialog" aria-modal="true" aria-labelledby="action-title" onMouseDown={(event) => event.stopPropagation()}>
            <h2 id="action-title">{action === "checkout" ? "Registrar saída" : action === "return" ? "Registrar devolução" : action === "reverse" ? "Estornar último registro" : item.condition === "fit" ? "Declarar item inapto" : "Liberar item como apto"}</h2>
            <p>Confira o item <strong>{item.identifier}</strong> antes de confirmar.</p>
            <form onSubmit={handleSubmit}>
              {action === "checkout" && <label><span>Destinatário</span><select name="recipient_id" required defaultValue=""><option value="" disabled>Selecione uma pessoa</option>{recipients.map((recipient) => <option value={recipient.id} key={recipient.id}>{recipient.name}</option>)}</select></label>}
              {action === "return" && <><label><span>Condição na devolução</span><select name="condition" required defaultValue="fit"><option value="fit">Apto</option><option value="unfit">Inapto</option></select></label><label><span>Motivo, se inapto</span><textarea name="reason" maxLength={200} /></label></>}
              {action === "reverse" && <><p className="muted">O registro original continua no histórico, marcado como estornado. Use para corrigir erro de registro, não para registrar um fato novo.</p><label><span>Motivo do estorno</span><textarea name="reason" maxLength={500} required /></label></>}
              {(action === "checkout" || action === "return") && <label className="confirmation"><input type="checkbox" checked={contingency} onChange={(event) => setContingency(event.target.checked)} /><span>Lançar registro do livro de contingência (fato ocorrido no papel)</span></label>}
              {contingency && (action === "checkout" || action === "return") && <><label><span>Data e hora do fato, conforme o livro</span><input type="datetime-local" name="occurred_at" required /></label><label><span>Folha/linha do livro</span><input name="paper_reference" maxLength={64} required placeholder="Ex.: F03/L07" /></label></>}
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
