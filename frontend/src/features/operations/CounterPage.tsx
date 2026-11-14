import type { Session } from "../../api/types";
import { MovementRegisterPage } from "./MovementRegisterPage";
import { ReturnBatchPage } from "./ReturnBatchPage";
import { ServiceBatchPage } from "./ServiceBatchPage";
import { TermDetailPage, TermsPage } from "./TermsPage";

export type CounterTab = "retirada" | "devolucao" | "registro" | "termos";

interface TabDefinition {
  id: CounterTab;
  href: string;
  label: string;
  allowed: (permissions: Session["permissions"]) => boolean;
}

// Espelham a permissão do backend apenas para navegação; a API continua decidindo.
const tabs: TabDefinition[] = [
  { id: "retirada", href: "/atendimento", label: "Retirada", allowed: (p) => p.can_checkout },
  { id: "devolucao", href: "/atendimento/devolucao", label: "Devolução", allowed: (p) => p.can_return },
  { id: "termos", href: "/atendimento/termos", label: "Termos", allowed: (p) => Boolean(p.identity_check_required) && (p.can_checkout || p.can_return || Boolean(p.can_approve_identity_exceptions)) },
  { id: "registro", href: "/atendimento/registro", label: "Registro de movimentações", allowed: (p) => p.can_view_items }
];

/** Módulo Retirada e devolução (SIGAB-082). */
export function CounterPage({ session, tab, termId }: { session: Session; tab: CounterTab; termId?: string }) {
  const visible = tabs.filter((entry) => entry.allowed(session.permissions));
  const active = visible.find((entry) => entry.id === tab) ?? visible[0];
  if (!active) return null;
  return (
    <>
      <nav className="tabs no-print" aria-label="Retirada e devolução">
        {visible.map((entry) => (
          <a key={entry.id} href={entry.href} aria-current={entry.id === active.id ? "page" : undefined}>{entry.label}</a>
        ))}
      </nav>
      {active.id === "retirada" && <ServiceBatchPage session={session} />}
      {active.id === "devolucao" && <ReturnBatchPage session={session} />}
      {active.id === "registro" && <MovementRegisterPage />}
      {active.id === "termos" && (termId ? <TermDetailPage termId={termId} /> : <TermsPage session={session} />)}
    </>
  );
}
