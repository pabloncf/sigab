import type { ReactNode } from "react";
import type { Session } from "../api/types";
import { postJson } from "../api/client";

interface AppShellProps {
  session: Session;
  children: ReactNode;
}

export function AppShell({ session, children }: AppShellProps) {
  async function handleLogout() {
    await postJson<null>("/session/logout/");
    window.location.assign("/entrar/");
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="SIGAB — início">
          <span className="brand-mark" aria-hidden="true">S</span>
          <span>
            <strong>SIGAB</strong>
            <small>Gestão de acervo</small>
          </span>
        </a>
        <div className="account">
          <span>
            <strong>{session.user.username}</strong>
            <small>{session.organization.name}</small>
          </span>
          <button className="button button-quiet" type="button" onClick={handleLogout}>Sair</button>
        </div>
      </header>
      <main className="content">{children}</main>
    </div>
  );
}
