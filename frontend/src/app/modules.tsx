import type { ReactNode } from "react";
import type { Session } from "../api/types";
import type { IconName } from "../components/Icon";
import { ActivityPage } from "../features/audit";
import { CatalogPage } from "../features/catalog";
import { PeoplePage, PersonDetailPage } from "../features/identity";
import { ItemDetailPage, ItemsPage } from "../features/inventory";
import { ServiceBatchPage } from "../features/operations";
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
    id: "acervo", href: "/", label: "Acervo", icon: "archive", group: "operacao",
    allowed: () => true,
    routes: [
      { pattern: new RegExp(`^/items/${ID}/?$`, "i"), render: ([id]) => <ItemDetailPage itemId={id} /> },
      { pattern: /^\/?$/, render: (_, session) => <ItemsPage session={session} /> }
    ]
  },
  {
    id: "atendimento", href: "/atendimento", label: "Atendimento", icon: "handoff", group: "operacao",
    allowed: (p) => p.can_checkout,
    routes: [{ pattern: /^\/atendimento\/?$/, render: (_, session) => <ServiceBatchPage session={session} /> }]
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
    id: "pessoas", href: "/pessoas", label: "Pessoas", icon: "users", group: "gestao",
    allowed: (p) => p.can_manage_identity,
    routes: [
      { pattern: new RegExp(`^/pessoas/${ID}/?$`, "i"), render: ([id]) => <PersonDetailPage personId={id} /> },
      { pattern: /^\/pessoas\/?$/, render: () => <PeoplePage /> }
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
    routes: [{ pattern: /^\/atividade\/?$/, render: () => <ActivityPage /> }]
  }
];

/** Módulos permitidos à sessão, com rótulos e ocultação da marca aplicados. */
export function availableModules(session: Session, brand: BrandConfig): AppModule[] {
  return modules
    .filter((module) => module.allowed(session.permissions))
    // O acervo é a página inicial e de fallback; não pode ser ocultado.
    .filter((module) => module.id === "acervo" || !brand.modules[module.id]?.hidden)
    .map((module) => ({ ...module, label: brand.modules[module.id]?.label ?? module.label }));
}

export function resolveRoute(path: string, available: AppModule[], session: Session) {
  for (const module of available) {
    for (const route of module.routes) {
      const match = path.match(route.pattern);
      if (match) return { module, page: route.render(match.slice(1), session) };
    }
  }
  const home = available.find((module) => module.id === "acervo")!;
  return { module: home, page: <ItemsPage session={session} /> };
}
