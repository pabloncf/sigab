import { FormEvent, ReactNode, useEffect, useState } from "react";
import { apiPage, apiRequest, postJson, describeError } from "../api/client";
import type { ItemDetail, ItemEvent, MovementResult, Recipient, Session } from "../api/types";
import { ErrorState, LoadingState } from "../components/Feedback";
import { Field } from "../components/Field";
import { Modal } from "../components/Modal";
import { lastListUrl } from "../components/Query";
import { StatusBadge } from "../components/StatusBadge";
import { ITEMS_LIST_KEY } from "./ItemsPage";

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

export function ItemDetailPage({ itemId, session }: { itemId: string; session?: Session }) {
  // ADR 0008: fora da contingência, retirada e devolução passam pela tela do balcão.
  const paperOnly = Boolean(session?.permissions.identity_check_required);
  const [item, setItem] = useState<ItemDetail | null>(null);
  const [events, setEvents] = useState<ItemEvent[]>([]);
  const [eventCount, setEventCount] = useState(0);
  const [recipients, setRecipients] = useState<Recipient[]>([]);
  const [action, setAction] = useState<Action | null>(null);
  // Reconciliation of the paper book after an outage (SIGAB-046, ADR 0004).
  const [contingency, setContingency] = useState(paperOnly);
  // One key per opened dialog: resubmitting after a network failure replays, never duplicates.
  const [idempotencyKey, setIdempotencyKey] = useState("");
  const [error, setError] = useState("");
  const [dialogError, setDialogError] = useState("");
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
      setError(describeError(requestError));
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
      setError(describeError(requestError));
    }
  }

  async function openAction(nextAction: Action) {
    setError("");
    setSuccess("");
    if (nextAction === "checkout" && recipients.length === 0) {
      try {
        setRecipients(await apiRequest<Recipient[]>(`/items/${itemId}/recipients/`));
      } catch (requestError) {
        setError(describeError(requestError));
        return;
      }
    }
    setDialogError("");
    setIdempotencyKey(crypto.randomUUID());
    setContingency(paperOnly);
    setAction(nextAction);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!action || !item) return;
    setSubmitting(true);
    setDialogError("");
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
      setDialogError(describeError(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <LoadingState />;
  if (error && !item) return <ErrorState message={error} onRetry={() => void loadItem()} />;
  if (!item) return null;

  const canChangeCondition = item.permissions.can_set_condition && item.administrative_status === "active" && item.availability !== "in_custody";
  // O último registro em vigor, para que o estorno diga exatamente o que será desfeito.
  const reversible = item.reversible_movement_id ? events.find((event) => event.movement.id === item.reversible_movement_id) : undefined;
  const reversibleLabel = reversible
    ? `${EVENT_LABELS[reversible.type] ?? reversible.type} em ${formatInstant(reversible.occurred_at)}${reversible.movement.recipient ? ` · ${reversible.movement.recipient.name}` : ""}`
    : "o último registro em vigor";
  const dialog = action ? ACTION_TEXT[action](item, reversibleLabel) : null;

  return (
    <>
      <a className="back-link" href={lastListUrl(ITEMS_LIST_KEY, "/acervo")}>‹ Voltar ao acervo</a>
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
            {item.permissions.can_checkout && item.availability === "available" && item.condition === "fit" && <button className="button button-primary" onClick={() => void openAction("checkout")}>{paperOnly ? "Lançar saída da contingência" : "Registrar saída"}</button>}
            {item.permissions.can_return && item.availability === "in_custody" && <button className="button button-primary" onClick={() => void openAction("return")}>{paperOnly ? "Lançar devolução da contingência" : "Registrar devolução"}</button>}
            {canChangeCondition && <button className="button button-secondary" onClick={() => void openAction("condition")}>{item.condition === "unfit" ? "Liberar como apto" : "Declarar inapto"}</button>}
          </div>
          {item.reversible_movement_id && (
            <div className="danger-zone">
              <div>
                <strong>Correção de registro</strong>
                <p>Desfaz o registro {reversible ? <em>{reversibleLabel}</em> : "mais recente em vigor"} por lançamento compensatório. Use só para corrigir erro de registro.</p>
              </div>
              <button className="button button-danger-quiet" onClick={() => void openAction("reverse")}>Estornar último registro</button>
            </div>
          )}
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

      {action && dialog && (
        <Modal title={dialog.title} description={dialog.description} busy={submitting} onClose={() => setAction(null)}>
          {dialogError && <div className="feedback error" role="alert">{dialogError}</div>}
          <form onSubmit={handleSubmit}>
            {action === "checkout" && <Field label="Destinatário"><select name="recipient_id" required defaultValue=""><option value="" disabled>Selecione uma pessoa</option>{recipients.map((recipient) => <option value={recipient.id} key={recipient.id}>{recipient.name}</option>)}</select></Field>}
            {action === "return" && <><Field label="Condição na devolução"><select name="condition" required defaultValue="fit"><option value="fit">Apto</option><option value="unfit">Inapto</option></select></Field><Field label="Motivo, se inapto" optional><textarea name="reason" maxLength={200} /></Field></>}
            {action === "reverse" && <Field label="Motivo do estorno"><textarea name="reason" maxLength={500} required /></Field>}
            {(action === "checkout" || action === "return") && (paperOnly
              ? <p className="muted">Aqui só se lança o livro de contingência. Retirada e devolução normais são feitas em <a href={action === "checkout" ? "/atendimento" : "/atendimento/devolucao"}>Retirada e devolução</a>, com biometria facial ou termo aprovado.</p>
              : <label className="confirmation"><input type="checkbox" checked={contingency} onChange={(event) => setContingency(event.target.checked)} /><span>Lançar registro do livro de contingência (fato ocorrido no papel)</span></label>)}
            {contingency && (action === "checkout" || action === "return") && <><Field label="Data e hora do fato, conforme o livro"><input type="datetime-local" name="occurred_at" required /></Field><Field label="Folha/linha do livro" hint="Ex.: F03/L07"><input name="paper_reference" maxLength={64} required /></Field></>}
            {action === "condition" && <Field label={item.condition === "fit" ? "Motivo de inapto" : "Referência da conferência"}><textarea name="reason" maxLength={200} required /></Field>}
            <label className="confirmation"><input type="checkbox" name="confirmed" required /><span>Confirmo a operação após conferir o item {item.identifier}.</span></label>
            <div className="dialog-actions"><button className="button button-quiet" type="button" onClick={() => setAction(null)} disabled={submitting}>Cancelar</button><button className={`button ${action === "reverse" ? "button-danger" : "button-primary"}`} disabled={submitting}>{submitting ? "Registrando…" : dialog.submit}</button></div>
          </form>
        </Modal>
      )}
    </>
  );
}

type ActionText = (item: ItemDetail, reversibleLabel: string) => { title: string; description: ReactNode; submit: string };

const ACTION_TEXT: Record<Action, ActionText> = {
  checkout: (item) => ({
    title: `Registrar saída de ${item.identifier}`,
    description: <>O item <strong>{item.identifier}</strong> ({item.equipment_type}) passa a ficar <strong>em posse</strong> do destinatário até a devolução.</>,
    submit: "Registrar saída"
  }),
  return: (item) => ({
    title: `Registrar devolução de ${item.identifier}`,
    description: <>Devolvido como apto, <strong>{item.identifier}</strong> fica disponível; como inapto, permanece indisponível até ser liberado.</>,
    submit: "Registrar devolução"
  }),
  condition: (item) => item.condition === "fit"
    ? { title: `Declarar ${item.identifier} inapto`, description: <><strong>{item.identifier}</strong> fica indisponível para saída até ser liberado como apto.</>, submit: "Declarar inapto" }
    : { title: `Liberar ${item.identifier} como apto`, description: <><strong>{item.identifier}</strong> volta a ficar disponível para saída.</>, submit: "Liberar como apto" },
  reverse: (item, reversibleLabel) => ({
    title: `Estornar registro de ${item.identifier}`,
    description: <>Será estornado: <strong>{reversibleLabel}</strong>. O registro original continua no histórico, marcado como estornado, e a situação do item volta à anterior. Use para corrigir erro de registro, não para registrar um fato novo.</>,
    submit: "Estornar registro"
  })
};
