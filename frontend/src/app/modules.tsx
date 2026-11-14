import type { ReactNode } from "react";
import type { Session } from "../api/types";
import type { IconName } from "../components/Icon";
import { ActivityPage } from "../features/audit";
import { CatalogPage, EquipmentPage } from "../features/catalog";
import { HomePage } from "../features/home/HomePage";
import { PeoplePage, PersonDetailPage } from "../features/identity";
import { BiometricsPage } from "../features/identity/BiometricsPage";
import { ItemDetailPage, ItemsPage } from "../features/inventory";
import { CounterPage } from "../features/operations/CounterPage";
import { StockPage } from "../features/operations/StockPage";
import { RestrictionsPage } from "../features/restrictions/RestrictionsPage";
import { MyPossessionsPage } from "../features/self-service";
import type { BrandConfig, ModuleId } from "../theme/brand";

type Permissions = Session["permissions"];

interface Route {
  pattern: RegExp;
  render: (params: string[], session: Session) => ReactNode;
}

export interface AppModule {
  id: ModuleId;
  href: string;
  label: string;
  icon: IconName;
  group: ModuleGroup;
  /** Espelha a permissão do backend apenas para navegação; a API continua decidindo. */
  allowed: (permissions: Permissions) => boolean;
  routes: Route[];
}

export type ModuleGroup = "operacao" | "gestao" | "controle";

export const groupLabels: Record<ModuleGroup, string> = {
  operacao: "Operação",
  gestao: "Gestão",
  controle: "Controle"
};

const ID = "([0-9a-f-]+)";

// A ordem define a ordem da navegação dentro de cada grupo.
const modules: AppModule[] = [
  {
    id: "inicio", href: "/", label: "Início", icon: "home", group: "operacao",
    allowed: (p) => p.can_view_items,
    routes: [{ pattern: /^\/?$/, render: (_, session) => <HomePage session={session} /> }]
  },
  {
    id: "acervo", href: "/acervo", label: "Acervo", icon: "archive", group: "operacao",
    allowed: () => true,
    routes: [
      // /items/<id> é o endereço histórico da ficha e continua válido (SIGAB-079).
      { pattern: new RegExp(`^/items/${ID}/?$`, "i"), render: ([id], session) => <ItemDetailPage itemId={id} session={session} /> },
      { pattern: /^\/acervo\/?$/, render: (_, session) => <ItemsPage session={session} /> }
    ]
  },
  {
    id: "atendimento", href: "/atendimento", label: "Retirada e devolução", icon: "handoff", group: "operacao",
    allowed: (p) => p.can_checkout || p.can_return || Boolean(p.can_approve_identity_exceptions),
    routes: [
      { pattern: new RegExp(`^/atendimento/termos/${ID}/?$`, "i"), render: ([id], session) => <CounterPage session={session} tab="termos" termId={id} /> },
      { pattern: /^\/atendimento\/termos\/?$/, render: (_, session) => <CounterPage session={session} tab="termos" /> },
      { pattern: /^\/atendimento\/devolucao\/?$/, render: (_, session) => <CounterPage session={session} tab="devolucao" /> },
      { pattern: /^\/atendimento\/registro\/?$/, render: (_, session) => <CounterPage session={session} tab="registro" /> },
      { pattern: /^\/atendimento\/?$/, render: (_, session) => <CounterPage session={session} tab="retirada" /> }
    ]
  },
  {
    id: "estoque", href: "/estoque", label: "Estoque", icon: "boxes", group: "operacao",
    allowed: (p) => p.can_use_stock,
    routes: [{ pattern: /^\/estoque\/?$/, render: (_, session) => <StockPage session={session} /> }]
  },
  {
    id: "minha-posse", href: "/minha-posse", label: "Minha posse", icon: "user", group: "operacao",
    allowed: (p) => p.can_use_self_service,
    routes: [{ pattern: /^\/minha-posse\/?$/, render: () => <MyPossessionsPage /> }]
  },
  {
    id: "equipamentos", href: "/equipamentos", label: "Equipamentos", icon: "tag", group: "gestao",
    allowed: (p) => p.can_manage_catalog || p.can_create_item || p.can_receive_stock,
    routes: [{ pattern: /^\/equipamentos\/?$/, render: (_, session) => <EquipmentPage session={session} /> }]
  },
  {
    id: "biometria", href: "/biometria", label: "Biometria", icon: "user", group: "gestao",
    allowed: (p) => Boolean(p.can_manage_biometrics),
    routes: [{ pattern: /^\/biometria\/?$/, render: () => <BiometricsPage /> }]
  },
  {
    id: "pessoas", href: "/pessoas", label: "Pessoas", icon: "users", group: "gestao",
    allowed: (p) => p.can_manage_identity,
    routes: [
      { pattern: new RegExp(`^/pessoas/${ID}/?$`, "i"), render: ([id], session) => <PersonDetailPage personId={id} session={session} /> },
      { pattern: /^\/pessoas\/?$/, render: (_params, session) => <PeoplePage session={session} /> }
    ]
  },
  {
    id: "restricoes", href: "/restricoes", label: "Restrições", icon: "shield", group: "gestao",
    allowed: (p) => p.can_manage_restrictions,
    routes: [{ pattern: /^\/restricoes\/?$/, render: () => <RestrictionsPage /> }]
  },
  {
    id: "cadastros", href: "/cadastros", label: "Cadastros", icon: "sliders", group: "gestao",
    allowed: (p) => p.can_manage_catalog,
    routes: [{ pattern: /^\/cadastros\/?$/, render: () => <CatalogPage /> }]
  },
  {
    id: "atividade", href: "/atividade", label: "Atividade", icon: "activity", group: "controle",
    allowed: (p) => p.can_view_items,
    routes: [{ pattern: /^\/atividade\/?$/, render: (_, session) => <ActivityPage session={session} /> }]
  }
];

// Início e acervo são entradas de navegação e não podem ser ocultados pela marca.
const ALWAYS_VISIBLE: ModuleId[] = ["inicio", "acervo"];
// Destino quando a rota não existe ou o módulo não é permitido: quem não opera a
// reserva cai na própria posse (SIGAB-079).
const FALLBACK_ORDER: ModuleId[] = ["inicio", "minha-posse", "acervo"];

/** Módulos permitidos à sessão, com rótulos e ocultação da marca aplicados. */
export function availableModules(session: Session, brand: BrandConfig): AppModule[] {
  return modules
    .filter((module) => module.allowed(session.permissions))
    .filter((module) => ALWAYS_VISIBLE.includes(module.id) || !brand.modules[module.id]?.hidden)
    .map((module) => ({ ...module, label: brand.modules[module.id]?.label ?? module.label }));
}

/** Endereços antigos que mudaram de lugar; devolve o novo destino ou null. */
export function legacyRedirect(path: string, search: string): string | null {
  // Antes da SIGAB-079 a posse por pessoa vivia em /?holder=<id>.
  if (/^\/?$/.test(path) && new URLSearchParams(search).has("holder")) return `/acervo${search}`;
  return null;
}

export function resolveRoute(path: string, available: AppModule[], session: Session) {
  for (const module of available) {
    for (const route of module.routes) {
      const match = path.match(route.pattern);
      if (match) return { module, page: route.render(match.slice(1), session) };
    }
  }
  const home = FALLBACK_ORDER.map((id) => available.find((module) => module.id === id)).find(Boolean)!;
  return { module: home, page: home.routes[home.routes.length - 1].render([], session) };
}
