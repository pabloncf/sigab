import type { ReactNode } from "react";
import type { Session } from "../api/types";
import { postJson } from "../api/client";

interface AppShellProps {
  session: Session;
  children: ReactNode;
}

function areas(session: Session) {
  return [
    { href: "/", label: "Acervo" },
    ...(session.permissions.can_manage_restrictions ? [{ href: "/restricoes", label: "Restrições" }] : []),
    ...(session.permissions.can_checkout ? [{ href: "/atendimento", label: "Atendimento" }] : []),
    ...(session.permissions.can_use_self_service ? [{ href: "/minha-posse", label: "Minha posse" }] : []),
    ...(session.permissions.can_view_items ? [{ href: "/atividade", label: "Atividade" }] : []),
    ...(session.permissions.can_manage_identity ? [{ href: "/pessoas", label: "Pessoas" }] : []),
    ...(session.permissions.can_manage_catalog ? [{ href: "/cadastros", label: "Cadastros" }] : [])
  ];
}

function currentArea(session: Session) {
  const match = areas(session).find((area) => area.href !== "/" && window.location.pathname.startsWith(area.href));
  return match?.href ?? "/";
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
        {areas(session).length > 1 && (
          <nav className="main-nav" aria-label="Áreas">
            {areas(session).map((area) => (
              <a key={area.href} href={area.href} aria-current={currentArea(session) === area.href ? "page" : undefined}>{area.label}</a>
            ))}
          </nav>
        )}
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
