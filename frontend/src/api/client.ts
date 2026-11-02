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
    readonly details?: Record<string, string[]>
  ) {
    super(message);
  }
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

  if (init.body) {
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
    const message = [payload.error ?? "Não foi possível concluir a solicitação.", ...fieldMessages].join(" ");
    throw new ApiError(message, response.status, payload.details);
  }
  return payload.data as T;
}

export async function apiWithMeta<T, M>(path: string): Promise<{ data: T; meta: M }> {
  const response = await fetch(`/api/v1${path}`, { credentials: "same-origin" });
  const payload = (await response.json().catch(() => ({ success: false }))) as ApiEnvelope<T> & { meta?: M };
  if (!response.ok || !payload.success) {
    const fieldMessages = Object.values(payload.details ?? {}).flat();
    throw new ApiError([payload.error ?? "Não foi possível concluir a solicitação.", ...fieldMessages].join(" "), response.status, payload.details);
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
