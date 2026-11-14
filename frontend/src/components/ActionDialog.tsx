import { FormEvent, ReactNode, useEffect, useRef, useState } from "react";
import { ApiError, describeError } from "../api/client";
import { FieldErrorsContext, unmatchedFieldErrors } from "./Field";
import { Modal } from "./Modal";

interface ActionDialogProps {
  title: string;
  description?: ReactNode;
  confirmation?: string;
  /** Verbo específico da ação, ex.: "Desativar tipo". Evite "Confirmar" genérico. */
  submitLabel?: string;
  /** "danger" para ações de maior consequência (desativar, revogar, estornar). */
  tone?: "default" | "danger";
  size?: "default" | "wide";
  children?: ReactNode;
  onClose: () => void;
  onSubmit: (form: FormData) => Promise<void>;
}

export interface FormErrorState {
  summary: string;
  fields: Record<string, string[]>;
  unmatched: string[];
}

/** Converte uma falha de envio em resumo + erros por campo. */
export function formError(cause: unknown, form: HTMLElement | null): FormErrorState {
  if (cause instanceof ApiError && cause.details && Object.keys(cause.details).length > 0) {
    return { summary: cause.summary, fields: cause.details, unmatched: unmatchedFieldErrors(form, cause.details) };
  }
  return { summary: describeError(cause), fields: {}, unmatched: [] };
}

export function FormErrorSummary({ error }: { error: FormErrorState | null }) {
  const summary = useRef<HTMLDivElement>(null);
  useEffect(() => { if (error) summary.current?.focus(); }, [error]);
  if (!error) return null;
  const inline = Object.keys(error.fields).length > error.unmatched.length;
  return (
    <div className="feedback error" role="alert" ref={summary} tabIndex={-1}>
      <strong>{error.summary}</strong>
      {error.unmatched.length > 0 && <ul className="error-list">{error.unmatched.map((message) => <li key={message}>{message}</li>)}</ul>}
      {inline && <p>Revise os campos indicados abaixo. <button className="link-button" type="button" onClick={() => summary.current?.closest(".dialog")?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus()}>Ir ao primeiro campo com erro</button></p>}
    </div>
  );
}

export function ActionDialog({ title, description, confirmation, submitLabel = "Confirmar", tone = "default", size, children, onClose, onSubmit }: ActionDialogProps) {
  const [error, setError] = useState<FormErrorState | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit(new FormData(event.currentTarget));
      onClose();
    } catch (cause) {
      setError(formError(cause, formRef.current));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal title={title} description={description} size={size} busy={submitting} onClose={onClose}>
      <FormErrorSummary error={error} />
      <FieldErrorsContext.Provider value={error?.fields ?? {}}>
        <form ref={formRef} onSubmit={handleSubmit}>
          {children}
          {confirmation && <label className="confirmation"><input type="checkbox" name="confirmed" required /><span>{confirmation}</span></label>}
          <div className="dialog-actions">
            <button className="button button-quiet" type="button" onClick={onClose} disabled={submitting}>Cancelar</button>
            <button className={`button ${tone === "danger" ? "button-danger" : "button-primary"}`} disabled={submitting}>{submitting ? "Salvando alterações…" : submitLabel}</button>
          </div>
        </form>
      </FieldErrorsContext.Provider>
    </Modal>
  );
}

export function text(form: FormData, field: string): string {
  return String(form.get(field) ?? "");
}
