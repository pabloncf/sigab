import { cloneElement, createContext, isValidElement, ReactElement, ReactNode, useContext, useId } from "react";

/** Erros de validação do servidor por nome de campo (ApiError.details). */
export const FieldErrorsContext = createContext<Record<string, string[]>>({});

interface FieldProps {
  label: ReactNode;
  /** Nome do campo no corpo da requisição; liga o erro do servidor ao campo. */
  name?: string;
  optional?: boolean;
  hint?: ReactNode;
  children: ReactElement<Record<string, unknown>>;
}

/**
 * Campo de formulário com rótulo associado, dica e erro junto do campo.
 *
 * Convenção do SIGAB: campos sem marcação são obrigatórios; os opcionais levam "(opcional)".
 */
export function Field({ label, name, optional = false, hint, children }: FieldProps) {
  const errors = useContext(FieldErrorsContext);
  const id = useId();
  const fieldName = name ?? (children.props.name as string | undefined);
  const messages = fieldName ? errors[fieldName] ?? [] : [];
  const hintId = hint ? `${id}-dica` : undefined;
  const errorId = messages.length ? `${id}-erro` : undefined;
  const control = isValidElement(children)
    ? cloneElement(children, {
        id,
        "aria-invalid": messages.length ? true : undefined,
        "aria-describedby": [hintId, errorId].filter(Boolean).join(" ") || undefined
      })
    : children;

  return (
    <div className="field" data-field-name={fieldName}>
      <label htmlFor={id}>{label}{optional && <span className="field-optional"> (opcional)</span>}</label>
      {control}
      {hint && <small className="field-hint" id={hintId}>{hint}</small>}
      {messages.length > 0 && <small className="field-error" id={errorId}>{messages.join(" ")}</small>}
    </div>
  );
}

/** Erros de campos que não estão no formulário aparecem no resumo do topo. */
export function unmatchedFieldErrors(form: HTMLElement | null, details: Record<string, string[]>): string[] {
  return Object.entries(details)
    .filter(([name]) => !form?.querySelector(`[data-field-name="${CSS.escape(name)}"]`))
    .flatMap(([, messages]) => messages);
}
