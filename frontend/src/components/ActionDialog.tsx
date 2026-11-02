import { FormEvent, ReactNode, useState } from "react";
import { ApiError } from "../api/client";

interface ActionDialogProps {
  title: string;
  description?: ReactNode;
  confirmation?: string;
  submitLabel?: string;
  children?: ReactNode;
  onClose: () => void;
  onSubmit: (form: FormData) => Promise<void>;
}

export function ActionDialog({ title, description, confirmation, submitLabel = "Confirmar", children, onClose, onSubmit }: ActionDialogProps) {
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await onSubmit(new FormData(event.currentTarget));
      onClose();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "Erro inesperado.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title" onMouseDown={(event) => event.stopPropagation()}>
        <h2 id="dialog-title">{title}</h2>
        {description && <p>{description}</p>}
        {error && <div className="feedback error" role="alert">{error}</div>}
        <form onSubmit={handleSubmit}>
          {children}
          {confirmation && <label className="confirmation"><input type="checkbox" name="confirmed" required /><span>{confirmation}</span></label>}
          <div className="dialog-actions">
            <button className="button button-quiet" type="button" onClick={onClose}>Cancelar</button>
            <button className="button button-primary" disabled={submitting}>{submitting ? "Registrando…" : submitLabel}</button>
          </div>
        </form>
      </section>
    </div>
  );
}

export function text(form: FormData, field: string): string {
  return String(form.get(field) ?? "");
}
