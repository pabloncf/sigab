import { useEffect, useState } from "react";
import { ApiError, apiRequest } from "./api/client";
import type { Session } from "./api/types";
import { AppShell } from "./components/AppShell";
import { ErrorState, LoadingState } from "./components/Feedback";
import { ActivityPage } from "./features/audit";
import { CatalogPage } from "./features/catalog";
import { PeoplePage, PersonDetailPage } from "./features/identity";
import { ItemDetailPage, ItemsPage } from "./features/inventory";
import { StockPage } from "./features/operations/StockPage";
import { ServiceBatchPage } from "./features/operations";
import { MyPossessionsPage } from "./features/self-service";
import { RestrictionsPage } from "./features/restrictions/RestrictionsPage";

function routeId(prefix: string): string | null {
  return window.location.pathname.match(new RegExp(`^/${prefix}/([0-9a-f-]+)/?$`, "i"))?.[1] ?? null;
}

function Page({ session }: { session: Session }) {
  const path = window.location.pathname;
  if (session.permissions.can_manage_restrictions && /^\/restricoes\/?$/.test(path)) return <RestrictionsPage />;
  if (session.permissions.can_use_self_service && /^\/minha-posse\/?$/.test(path)) return <MyPossessionsPage />;
  if (session.permissions.can_checkout && /^\/atendimento\/?$/.test(path)) return <ServiceBatchPage session={session} />;
  if (session.permissions.can_use_stock && /^\/estoque\/?$/.test(path)) return <StockPage session={session} />;
  const itemId = routeId("items");
  if (itemId) return <ItemDetailPage itemId={itemId} />;
  if (session.permissions.can_manage_catalog && /^\/cadastros\/?$/.test(path)) return <CatalogPage />;
  if (session.permissions.can_view_items && /^\/atividade\/?$/.test(path)) return <ActivityPage />;
  if (session.permissions.can_manage_identity) {
    const personId = routeId("pessoas");
    if (personId) return <PersonDetailPage personId={personId} />;
    if (/^\/pessoas\/?$/.test(path)) return <PeoplePage />;
  }
  return <ItemsPage session={session} />;
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

  return <AppShell session={session}><Page session={session} /></AppShell>;
}
