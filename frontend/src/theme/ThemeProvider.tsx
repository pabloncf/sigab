import { createContext, ReactNode, useContext, useEffect, useState } from "react";
import { BrandConfig, defaultBrand } from "./brand";
import { readableForeground } from "./contrast";

export type ColorScheme = "light" | "dark" | "system";

const SCHEME_KEY = "sigab:color-scheme";

interface ThemeContextValue {
  brand: BrandConfig;
  scheme: ColorScheme;
  setScheme: (scheme: ColorScheme) => void;
}

const ThemeContext = createContext<ThemeContextValue>({ brand: defaultBrand, scheme: "system", setScheme: () => {} });

/** Escreve a marca como variáveis CSS; o restante da paleta é derivado em tokens.css. */
export function applyBrand(brand: BrandConfig) {
  const root = document.documentElement;
  root.style.setProperty("--brand-primary", brand.colors.primary);
  root.style.setProperty("--brand-accent", brand.colors.accent);
  root.style.setProperty("--brand-on-primary", readableForeground(brand.colors.primary));
  if (brand.colors.sidebar) root.style.setProperty("--brand-sidebar", brand.colors.sidebar);
  root.style.setProperty("--radius", `${brand.radius}px`);
  root.style.setProperty("--font-sans", brand.fontFamily);
  root.dataset.density = brand.density;
  document.title = brand.name;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", brand.colors.primary);
}

export function readScheme(): ColorScheme {
  try {
    const stored = window.localStorage.getItem(SCHEME_KEY);
    return stored === "light" || stored === "dark" ? stored : "system";
  } catch {
    return "system";
  }
}

export function applyScheme(scheme: ColorScheme) {
  if (scheme === "system") delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = scheme;
}

export function ThemeProvider({ brand, children }: { brand: BrandConfig; children: ReactNode }) {
  const [scheme, setScheme] = useState<ColorScheme>(readScheme);

  useEffect(() => { applyBrand(brand); }, [brand]);
  useEffect(() => {
    applyScheme(scheme);
    try {
      if (scheme === "system") window.localStorage.removeItem(SCHEME_KEY);
      else window.localStorage.setItem(SCHEME_KEY, scheme);
    } catch {
      // Preferência visual apenas; sem armazenamento o padrão do sistema vale.
    }
  }, [scheme]);

  return <ThemeContext.Provider value={{ brand, scheme, setScheme }}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  return useContext(ThemeContext);
}
