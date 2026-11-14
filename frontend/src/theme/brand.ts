/**
 * Identidade visual da instalação.
 *
 * O SIGAB é single-tenant (ADR 0007): cada cliente tem sua própria instalação,
 * então a personalização é feita por instalação, não por usuário. Os valores
 * abaixo são o padrão; uma instalação pode sobrescrevê-los publicando
 * `/brand.json` ao lado do build (ver `public/brand.example.json`), sem rebuild.
 *
 * Personalização é apenas apresentação: ocultar um módulo aqui não substitui a
 * autorização do backend.
 */

export type ModuleId =
  | "inicio"
  | "acervo"
  | "equipamentos"
  | "atendimento"
  | "estoque"
  | "minha-posse"
  | "restricoes"
  | "pessoas"
  | "biometria"
  | "cadastros"
  | "atividade";

export type Density = "comfortable" | "compact";

export interface BrandConfig {
  /** Nome curto exibido na navegação e no título da aba. */
  name: string;
  /** Linha de apoio sob o nome. */
  tagline: string;
  /** Até 2 caracteres usados quando não há logotipo. */
  monogram: string;
  /** URL de imagem (SVG/PNG) servida pela própria instalação. */
  logoUrl?: string;
  colors: {
    /** Cor institucional: ações primárias, item ativo, destaques. */
    primary: string;
    /** Cor de apoio: foco de teclado e detalhes. */
    accent: string;
    /** Fundo da navegação lateral. Derivado da primária quando ausente. */
    sidebar?: string;
  };
  /** Raio base dos componentes, em px. */
  radius: number;
  /** Pilha de fontes. Prefira fontes locais: instalações podem não ter internet. */
  fontFamily: string;
  density: Density;
  /** Renomeia ou oculta módulos da navegação. */
  modules: Partial<Record<ModuleId, { label?: string; hidden?: boolean }>>;
}

export const defaultBrand: BrandConfig = {
  name: "SIGAB",
  tagline: "Gestão de acervo",
  monogram: "S",
  colors: {
    primary: "#1d5c4a",
    accent: "#d18b39"
  },
  radius: 10,
  fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  density: "comfortable",
  modules: {}
};

type BrandOverride = Partial<Omit<BrandConfig, "colors" | "modules">> & {
  colors?: Partial<BrandConfig["colors"]>;
  modules?: BrandConfig["modules"];
};

const COLOR = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;

function mergeBrand(override: BrandOverride): BrandConfig {
  const colors = { ...defaultBrand.colors };
  for (const key of ["primary", "accent", "sidebar"] as const) {
    const value = override.colors?.[key];
    if (typeof value === "string" && COLOR.test(value)) colors[key] = value;
  }
  return {
    ...defaultBrand,
    ...(typeof override.name === "string" && { name: override.name }),
    ...(typeof override.tagline === "string" && { tagline: override.tagline }),
    ...(typeof override.monogram === "string" && { monogram: override.monogram.slice(0, 2) }),
    ...(typeof override.logoUrl === "string" && override.logoUrl.startsWith("/") && !override.logoUrl.startsWith("//") && { logoUrl: override.logoUrl }),
    ...(typeof override.radius === "number" && { radius: Math.min(Math.max(override.radius, 0), 20) }),
    ...(typeof override.fontFamily === "string" && { fontFamily: override.fontFamily }),
    ...((override.density === "compact" || override.density === "comfortable") && { density: override.density }),
    colors,
    modules: { ...defaultBrand.modules, ...(override.modules ?? {}) }
  };
}

/** Lê `/brand.json` se existir; qualquer falha mantém o padrão. */
export async function loadBrand(timeoutMs = 1500): Promise<BrandConfig> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch("/brand.json", { signal: controller.signal, cache: "no-cache" });
    if (!response.ok) return defaultBrand;
    // Servidores com fallback de SPA respondem index.html para arquivo ausente; o parse falha e vale o padrão.
    const override: unknown = await response.json();
    if (!override || typeof override !== "object") return defaultBrand;
    return mergeBrand(override as BrandOverride);
  } catch {
    return defaultBrand;
  } finally {
    window.clearTimeout(timer);
  }
}
