// Login is rendered by Django, before the React bundle. Use the same installation brand.
(() => {
  const root = document.documentElement;
  try {
    const scheme = localStorage.getItem("sigab:color-scheme");
    if (scheme === "light" || scheme === "dark") root.dataset.theme = scheme;
  } catch { /* A visual preference must not prevent sign-in. */ }

  const color = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 1500);
  fetch("/brand.json", { signal: controller.signal, cache: "no-cache" })
    .then((response) => response.ok ? response.json() : null)
    .then((brand) => {
      if (!brand || typeof brand !== "object") return;
      const primary = brand.colors?.primary;
      if (typeof primary === "string" && color.test(primary)) {
        root.style.setProperty("--login-primary", primary);
        const hex = primary.length === 4 ? primary.slice(1).split("").map((part) => part + part).join("") : primary.slice(1);
        const rgb = [0, 2, 4].map((offset) => {
          const value = parseInt(hex.slice(offset, offset + 2), 16) / 255;
          return value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4;
        });
        root.style.setProperty("--login-on-primary", (.2126 * rgb[0] + .7152 * rgb[1] + .0722 * rgb[2]) > .179 ? "#000" : "#fff");
      }
      if (Number.isFinite(brand.radius)) root.style.setProperty("--login-radius", `${Math.min(20, Math.max(0, brand.radius))}px`);
      if (typeof brand.fontFamily === "string") root.style.setProperty("--login-font", brand.fontFamily);
      const applyText = () => {
        for (const [key, selector] of [["name", "[data-brand-name]"], ["tagline", "[data-brand-tagline]"], ["monogram", "[data-brand-monogram]"]]) {
          if (typeof brand[key] === "string") document.querySelectorAll(selector).forEach((element) => { element.textContent = key === "monogram" ? brand[key].slice(0, 2) : brand[key]; });
        }
        if (typeof brand.name === "string") {
          document.title = `Entrar | ${brand.name}`;
          document.querySelector("a.brand")?.setAttribute("aria-label", `${brand.name}, início`);
        }
        if (typeof brand.logoUrl === "string" && brand.logoUrl.startsWith("/") && !brand.logoUrl.startsWith("//")) {
          const mark = document.querySelector("[data-brand-monogram]");
          const logo = document.createElement("img");
          logo.src = brand.logoUrl; logo.alt = ""; logo.className = "brand-logo";
          mark?.replaceWith(logo);
        }
      };
      if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", applyText, { once: true });
      else applyText();
    })
    .catch(() => { /* Missing or invalid configuration keeps the default brand. */ })
    .finally(() => clearTimeout(timer));
})();
