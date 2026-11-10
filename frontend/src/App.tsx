import { useEffect, useState } from "react";
import { ApiError, apiRequest } from "./api/client";
import type { Session } from "./api/types";
import { availableModules, resolveRoute } from "./app/modules";
import { AppShell } from "./components/AppShell";
import { ErrorState, LoadingState } from "./components/Feedback";
import { useTheme } from "./theme/ThemeProvider";

export default function App() {
  const { brand } = useTheme();
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

  const modules = availableModules(session, brand);
  const { module, page } = resolveRoute(window.location.pathname, modules, session);
  return <AppShell session={session} modules={modules} active={module}>{page}</AppShell>;
}
