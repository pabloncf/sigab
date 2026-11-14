import type { Page } from "./types";

interface ApiEnvelope<T> {
  success: boolean;
  data?: T;
  error?: string;
  details?: Record<string, string[]>;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly details?: Record<string, string[]>,
    /** Mensagem geral, sem os erros por campo (exibidos junto de cada campo). */
    readonly summary: string = message
  ) {
    super(message);
  }
}

const NETWORK_ERROR = "Sem resposta do servidor. Verifique a conexão e tente novamente.";
const UNKNOWN_ERROR = "Não foi possível concluir a ação. Recarregue a página e tente de novo; se persistir, informe ao suporte o horário da tentativa.";

/** Mensagem que orienta a recuperação, em vez de um genérico "erro inesperado". */
export function describeError(cause: unknown): string {
  if (cause instanceof ApiError) return cause.message;
  if (cause instanceof TypeError) return NETWORK_ERROR;
  return UNKNOWN_ERROR;
}

function getCookie(name: string): string | undefined {
  return document.cookie
    .split(";")
    .map((cookie) => cookie.trim())
    .find((cookie) => cookie.startsWith(`${name}=`))
    ?.slice(name.length + 1);
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = init.method?.toUpperCase() ?? "GET";
  const headers = new Headers(init.headers);

  // FormData (captures) lets the browser set the multipart boundary itself.
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (!(["GET", "HEAD", "OPTIONS"].includes(method))) {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) headers.set("X-CSRFToken", decodeURIComponent(csrfToken));
  }

  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers,
    credentials: "same-origin"
  });
  let payload: ApiEnvelope<T>;
  try {
    payload = (await response.json()) as ApiEnvelope<T>;
  } catch {
    payload = {
      success: false,
      error: response.status === 403
        ? "A validação de segurança expirou. Atualize a página e tente novamente."
        : "O servidor retornou uma resposta inválida."
    };
  }

  if (!response.ok || !payload.success) {
    const fieldMessages = Object.values(payload.details ?? {}).flat();
    const summary = payload.error ?? "Não foi possível concluir a solicitação.";
    throw new ApiError([summary, ...fieldMessages].join(" "), response.status, payload.details, summary);
  }
  return payload.data as T;
}

export async function apiWithMeta<T, M>(path: string): Promise<{ data: T; meta: M }> {
  const response = await fetch(`/api/v1${path}`, { credentials: "same-origin" });
  const payload = (await response.json().catch(() => ({ success: false }))) as ApiEnvelope<T> & { meta?: M };
  if (!response.ok || !payload.success) {
    const fieldMessages = Object.values(payload.details ?? {}).flat();
    const summary = payload.error ?? "Não foi possível concluir a solicitação.";
    throw new ApiError([summary, ...fieldMessages].join(" "), response.status, payload.details, summary);
  }
  return { data: payload.data as T, meta: payload.meta as M };
}

export async function apiPage<T>(path: string): Promise<Page<T>> {
  const { data, meta } = await apiWithMeta<T[], { count: number }>(path);
  return { rows: data ?? [], count: meta?.count ?? 0 };
}

export function postJson<T>(path: string, body?: unknown): Promise<T> {
  return sendJson<T>("POST", path, body);
}

export function sendJson<T>(method: "POST" | "PATCH", path: string, body?: unknown): Promise<T> {
  return apiRequest<T>(path, {
    method,
    body: JSON.stringify(body ?? {})
  });
}

/** Multipart POST, used only for face captures; the image is never kept by the client. */
export function postForm<T>(path: string, form: FormData): Promise<T> {
  return apiRequest<T>(path, { method: "POST", body: form });
}
