import { ReactNode, useEffect, useState } from "react";
import { postJson } from "../api/client";
import type { Session } from "../api/types";
import { AppModule, groupLabels, ModuleGroup } from "../app/modules";
import { ColorScheme, useTheme } from "../theme/ThemeProvider";
import { Icon, IconName } from "./Icon";

interface AppShellProps {
  session: Session;
  modules: AppModule[];
  active: AppModule;
  children: ReactNode;
}

const schemes: Array<{ value: ColorScheme; label: string; icon: IconName }> = [
  { value: "light", label: "Claro", icon: "sun" },
  { value: "dark", label: "Escuro", icon: "moon" },
  { value: "system", label: "Sistema", icon: "monitor" }
];

function BrandMark() {
  const { brand } = useTheme();
  return (
    <a className="brand" href="/" aria-label={`${brand.name} — início`}>
      {brand.logoUrl
        ? <img className="brand-logo" src={brand.logoUrl} alt="" />
        : <span className="brand-mark" aria-hidden="true">{brand.monogram}</span>}
      <span className="brand-text">
        <strong>{brand.name}</strong>
        <small>{brand.tagline}</small>
      </span>
    </a>
  );
}

function SchemeSwitch() {
  const { scheme, setScheme } = useTheme();
  return (
    <div className="segmented" role="radiogroup" aria-label="Aparência">
      {schemes.map((option) => (
        <button key={option.value} type="button" role="radio" aria-checked={scheme === option.value}
          title={option.label} onClick={() => setScheme(option.value)}>
          <Icon name={option.icon} size={16} />
          <span className="sr-only">{option.label}</span>
        </button>
      ))}
    </div>
  );
}

function initials(name: string) {
  return name.split(/[\s._-]+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}

export function AppShell({ session, modules, active, children }: AppShellProps) {
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!menuOpen) return;
    // Leva o foco para a navegação aberta, para quem usa teclado ou leitor de tela.
    document.querySelector<HTMLElement>("#sidebar .sidebar-nav a")?.focus();
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") setMenuOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen]);

  async function handleLogout() {
    await postJson<null>("/session/logout/");
    window.location.assign("/entrar/");
  }

  const groups = (Object.keys(groupLabels) as ModuleGroup[])
    .map((group) => ({ group, items: modules.filter((module) => module.group === group) }))
    .filter((entry) => entry.items.length > 0);

  return (
    <div className="app-shell" data-menu-open={menuOpen || undefined}>
      <a className="skip-link" href="#conteudo">Ir para o conteúdo</a>

      <header className="mobile-bar">
        <BrandMark />
        <button className="icon-button" type="button" aria-expanded={menuOpen} aria-controls="sidebar"
          onClick={() => setMenuOpen((open) => !open)}>
          <Icon name={menuOpen ? "close" : "menu"} />
          <span className="sr-only">{menuOpen ? "Fechar menu" : "Abrir menu"}</span>
        </button>
      </header>

      <aside className="sidebar" id="sidebar">
        <div className="sidebar-brand"><BrandMark /></div>
        <nav className="sidebar-nav" aria-label="Áreas">
          {groups.map(({ group, items }) => (
            <div className="nav-group" key={group}>
              {groups.length > 1 && <p className="nav-group-label">{groupLabels[group]}</p>}
              <ul>
                {items.map((module) => (
                  <li key={module.id}>
                    <a href={module.href} aria-current={module.id === active.id ? "page" : undefined}>
                      <Icon name={module.icon} />
                      <span>{module.label}</span>
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
        <div className="sidebar-footer">
          <SchemeSwitch />
          <div className="account">
            <span className="avatar" aria-hidden="true">{initials(session.user.username)}</span>
            <span className="account-text">
              <strong>{session.user.username}</strong>
              <small>{session.organization.name}</small>
            </span>
            <button className="icon-button" type="button" onClick={handleLogout} title="Sair">
              <Icon name="logout" size={18} />
              <span className="sr-only">Sair</span>
            </button>
          </div>
        </div>
      </aside>
      <button className="sidebar-scrim" type="button" tabIndex={-1} aria-hidden="true" onClick={() => setMenuOpen(false)} />

      <main className="content" id="conteudo" tabIndex={-1}>{children}</main>
    </div>
  );
}
