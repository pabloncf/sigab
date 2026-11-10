import { useRef, useState } from "react";
import { ApiError, postJson } from "../api/client";

type Body = Record<string, unknown>;
interface PendingRequest {
  path: string;
  body: Body;
  summary: string;
}

function restore(key: string): PendingRequest | null {
  try {
    const value = JSON.parse(sessionStorage.getItem(key) ?? "null") as PendingRequest | null;
    return value && typeof value.path === "string" && typeof value.summary === "string"
      && value.body && typeof value.body.idempotency_key === "string" ? value : null;
  } catch { return null; }
}

// Keep the immutable attempt across retries and reloads, scoped to the current account/tenant.
export function useConfirmedRequest<T>(key: string) {
  const [pending, setPending] = useState(() => restore(key));
  const pendingRef = useRef(pending);
  const busy = useRef(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function execute(path?: string, body?: Body, summary?: string): Promise<T | undefined> {
    if (busy.current) return;
    const recovering = pendingRef.current !== null;
    const attempt = pendingRef.current ?? (path && body && summary ? {
      path, body: { ...body, idempotency_key: crypto.randomUUID() }, summary
    } : null);
    if (!attempt) return;
    busy.current = true;
    setSubmitting(true);
    setError("");
    try {
      // Persist before sending: a reload while the response is in flight remains recoverable.
      sessionStorage.setItem(key, JSON.stringify(attempt));
    } catch {
      busy.current = false;
      setSubmitting(false);
      setError("Não foi possível guardar a tentativa neste navegador. Libere o armazenamento da sessão e tente novamente.");
      return;
    }
    pendingRef.current = attempt;
    setPending(attempt);
    try {
      const result = await postJson<T>(attempt.path, attempt.body);
      sessionStorage.removeItem(key);
      pendingRef.current = null;
      setPending(null);
      return result;
    } catch (requestError) {
      // A definite refusal of the first attempt permits editing. An uncertain earlier
      // result must first be recovered with the original key and original payload.
      if (!recovering && requestError instanceof ApiError
          && requestError.status >= 400 && requestError.status < 500
          && ![408, 429].includes(requestError.status)) {
        sessionStorage.removeItem(key);
        pendingRef.current = null;
        setPending(null);
      }
      setError(requestError instanceof ApiError ? requestError.message : "Sem confirmação do servidor. Verifique o resultado antes de iniciar outra operação.");
    } finally {
      busy.current = false;
      setSubmitting(false);
    }
  }

  return { pending, submitting, error, execute };
}
