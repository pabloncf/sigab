import { useEffect, useState } from "react";
import { ApiError, apiRequest } from "./api/client";
import type { Session } from "./api/types";
import { AppShell } from "./components/AppShell";
import { ErrorState, LoadingState } from "./components/Feedback";
import { ItemDetailPage } from "./pages/ItemDetailPage";
import { ItemsPage } from "./pages/ItemsPage";

function currentItemId(): string | null {
  return window.location.pathname.match(/^\/items\/([0-9a-f-]+)\/?$/i)?.[1] ?? null;
}

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [error, setError] = useState("");

  async function loadSession() {
    setError("");
    try {
      setSession(await apiRequest<Session>("/session/"));
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 401) {
        window.location.assign(`/entrar/?next=${encodeURIComponent(window.location.pathname)}`);
        return;
      }
      setError(requestError instanceof ApiError ? requestError.message : "Erro inesperado.");
    }
  }

  useEffect(() => { void loadSession(); }, []);

  if (error) return <main className="content standalone"><ErrorState message={error} onRetry={() => void loadSession()} /></main>;
  if (!session) return <main className="content standalone"><LoadingState label="Carregando sessão" /></main>;

  const itemId = currentItemId();
  return <AppShell session={session}>{itemId ? <ItemDetailPage itemId={itemId} /> : <ItemsPage session={session} />}</AppShell>;
}
