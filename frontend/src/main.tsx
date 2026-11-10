import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { loadBrand } from "./theme/brand";
import { applyBrand, ThemeProvider } from "./theme/ThemeProvider";
import "./styles/index.css";

// A marca é aplicada antes do primeiro render para evitar troca visível de cores.
const brand = await loadBrand();
applyBrand(brand);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider brand={brand}>
      <App />
    </ThemeProvider>
  </StrictMode>
);
