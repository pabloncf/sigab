import { expect, test, type Page } from "@playwright/test";
import { readFile } from "node:fs/promises";

// Synthetic fixtures only. No real identity, image or application write is used here.
const person = (id: string, name: string) => ({ id, name: `${name} Sobrenome composto de demonstração para conferir a quebra de linha`, functional_name: "", is_active: true, registrations: [id.padEnd(64, "X")], has_account: false });
const material = (id: string) => ({ id, identifier: id, equipment_type: "Equipamento com descrição longa para conferir a leitura", condition: "fit", condition_label: "Apto", availability: "available", availability_label: "Disponível", current_holder: null });
const bioStatus = { enrolled: true, enrolled_at: "2026-11-13T12:00:00Z", engine_version: "synthetic" };
const bioRows = ["Ana", "Bruno"].map((name) => ({ id: name.toLowerCase(), name, registrations: [`MAT-${name}`], ...bioStatus }));

async function boot(page: Page) {
  await page.route("**/brand.json", (route) => route.fulfill({ json: {} }));
  await page.route("**/api/v1/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    let data: unknown = [];
    if (path.endsWith("/session/")) data = {
      user: { id: "synthetic-user", username: "gestor" }, organization: { id: "test-org", name: "Organização de demonstração" },
      item_scope: { all_units: true, units: [] },
      permissions: { can_view_items: true, can_manage_identity: true, can_manage_catalog: true, can_create_item: true, can_manage_biometrics: true, can_use_stock: true, can_receive_stock: true, can_checkout: true, can_return: true, can_use_self_service: true, identity_check_required: true }
    };
    else if (path.endsWith("/people/")) data = [person("ana", "Ana"), person("bruno", "Bruno")];
    else if (path.endsWith("/items/")) data = [material("ITEM-001"), material("ITEM-002")];
    else if (path.endsWith("/biometrics/")) data = bioRows;
    else if (path.endsWith("/biometric/")) data = bioStatus;
    else if (path.endsWith("/units/")) data = [{ id: "u1", code: "U1", name: "Sede", is_active: true, locations: [{ id: "r1", code: "R1", name: "Reserva", is_active: true }] }];
    else if (path.endsWith("/stock/options/")) data = { equipment_types: [], units: [] };
    else if (path.endsWith("/movements/options/")) data = { people: [], operators: [], equipment_types: [] };
    else if (path.endsWith("/me/possessions/")) data = { person: { id: "ana", name: "Ana" }, possessions: [{ id: "item1", kind: "individual", identifier: "ITEM-ATUAL", equipment_type: "Equipamento", unit: "Sede" }] };
    else if (path.endsWith("/me/history/")) data = { individual: [{ id: "h1", type: "checkout", equipment_type: "Equipamento", identifier: "ITEM-HISTORICO", occurred_at: "2026-11-13T12:00:00Z" }], quantitative: [], receipts: [{ id: "receipt1", code: "AT-TESTE", confirmed_at: "2026-11-13T12:00:00Z" }] };
    return route.fulfill({ json: { success: true, data, meta: { count: Array.isArray(data) ? data.length : 0 } } });
  });
}

for (const area of ["pessoas", "acervo"]) {
  test(`${area}: resposta antiga não substitui a consulta mais recente`, async ({ page }) => {
    await boot(page);
    let release = () => {};
    const held = new Promise<void>((resolve) => { release = resolve; });
    await page.route(area === "pessoas" ? "**/api/v1/people/?**" : "**/api/v1/search/?**", async (route) => {
      const term = new URL(route.request().url()).searchParams.get("q");
      if (term === "antiga") await held;
      const rows = area === "pessoas" ? [person(term ?? "initial", term ?? "Inicial")] : [material(term ?? "Inicial")];
      await route.fulfill({ json: { success: true, data: area === "pessoas" ? rows : { items: rows, people: [] }, meta: { count: 1, items_count: 1 } } });
    });
    await page.goto(`/${area}`);
    const search = page.getByRole("searchbox");
    const list = page.getByRole("region", { name: area === "pessoas" ? "Pessoas da organização" : "Itens com registro" });
    await expect(list).toContainText(area === "pessoas" ? "Inicial" : "ITEM-001");
    await search.fill("antiga");
    const firstRequest = page.waitForRequest((request) => request.url().includes("q=antiga"));
    await page.getByRole("button", { name: "Buscar", exact: true }).click();
    await firstRequest;
    await expect(list.getByRole("status")).toContainText("Atualizando resultados");
    await expect(list.locator(".query-results")).toHaveAttribute("inert", "");
    await search.fill("recente");
    await page.getByRole("button", { name: "Buscar", exact: true }).click();
    await expect(list).toContainText("recente");
    const oldResponse = page.waitForResponse((response) => response.url().includes("q=antiga"));
    release();
    await (await oldResponse).finished();
    await expect(list).toContainText("recente");
    await expect(list).not.toContainText("antiga");
  });
}

test("biometria identifica a pessoa e descarta a exclusão iniciada ao trocar de seleção", async ({ page }) => {
  await boot(page);
  await page.goto("/biometria");
  const ana = page.getByRole("button", { name: "Gerenciar biometria de Ana" });
  await ana.click();
  const panel = page.getByRole("region", { name: "Biometria facial de Ana" });
  await expect(panel).toBeFocused();
  await expect(panel).toContainText("Ana · matrícula MAT-Ana");
  await panel.getByRole("button", { name: "Excluir", exact: true }).click();
  await panel.getByLabel("Motivo da exclusão").fill("Motivo referente a Ana");
  await page.getByRole("button", { name: "Gerenciar biometria de Bruno" }).click();
  const next = page.getByRole("region", { name: "Biometria facial de Bruno" });
  await expect(next).toContainText("Bruno · matrícula MAT-Bruno");
  await expect(next.getByRole("form", { name: "Excluir biometria" })).toHaveCount(0);
  await expect(next).not.toContainText("Motivo referente a Ana");
  await next.getByRole("button", { name: "Fechar painel" }).click();
  await expect(page.getByRole("button", { name: "Gerenciar biometria de Bruno" })).toBeFocused();
});

test("biometria não permite fechar ou trocar a pessoa enquanto a exclusão aguarda resposta", async ({ page }) => {
  await boot(page);
  let release = () => {};
  const held = new Promise<void>((resolve) => { release = resolve; });
  await page.route("**/biometric/delete/", async (route) => {
    await held;
    await route.fulfill({ status: 400, json: { success: false, error: "Tentativa sintética recusada." } });
  });
  await page.goto("/biometria");
  await page.getByRole("button", { name: "Gerenciar biometria de Ana" }).click();
  const panel = page.getByRole("region", { name: "Biometria facial de Ana" });
  await panel.getByRole("button", { name: "Excluir", exact: true }).click();
  await panel.getByLabel("Motivo da exclusão").fill("Teste sintético");
  await panel.getByRole("button", { name: "Excluir biometria" }).click();
  await expect(panel.getByRole("button", { name: "Fechar painel" })).toBeDisabled();
  await expect(page.getByRole("region", { name: "Pessoas e biometria" }).locator("ul")).toHaveAttribute("inert", "");
  release();
  await expect(panel.getByRole("alert")).toHaveText("Tentativa sintética recusada.");
  await expect(panel.getByRole("button", { name: "Fechar painel" })).toBeEnabled();
});

test("a câmera só é solicitada após ativação e permite recuperar a permissão negada", async ({ page }) => {
  await boot(page);
  await page.addInitScript(() => {
    let requests = 0;
    Object.defineProperty(window, "cameraRequests", { get: () => requests });
    Object.defineProperty(navigator.mediaDevices, "getUserMedia", { value: () => {
      requests += 1;
      return Promise.reject(new DOMException("synthetic", requests === 1 ? "NotAllowedError" : "NotFoundError"));
    } });
  });
  await page.goto("/biometria");
  await page.getByRole("button", { name: "Gerenciar biometria de Ana" }).click();
  const panel = page.getByRole("region", { name: "Biometria facial de Ana" });
  await panel.getByRole("button", { name: "Recadastrar" }).click();
  expect(await page.evaluate(() => Reflect.get(window, "cameraRequests"))).toBe(0);
  await expect(panel.getByRole("button", { name: "Ativar câmera", exact: true })).toBeDisabled();
  await panel.getByRole("checkbox").check();
  await panel.getByRole("button", { name: "Ativar câmera", exact: true }).click();
  await expect(panel.getByRole("alert")).toContainText("Acesso à câmera negado");
  await panel.getByRole("button", { name: "Tentar ativar câmera novamente" }).click();
  await expect(panel.getByRole("alert")).toContainText("Nenhuma câmera encontrada");
  expect(await page.evaluate(() => Reflect.get(window, "cameraRequests"))).toBe(2);
});

test("falha de comprovante é local e repete a abertura, preservando materiais e histórico", async ({ page }) => {
  await boot(page);
  let attempts = 0;
  await page.route("**/me/receipts/receipt1/", (route) => {
    attempts += 1;
    return route.fulfill({ status: 503, json: { success: false, error: "Comprovante temporariamente indisponível." } });
  });
  await page.goto("/minha-posse");
  await page.getByRole("button", { name: "Abrir AT-TESTE" }).click();
  await expect(page.getByRole("region", { name: "Materiais sob minha responsabilidade" })).toContainText("ITEM-ATUAL");
  await expect(page.getByRole("region", { name: "Meu histórico" })).toContainText("ITEM-HISTORICO");
  await page.getByRole("region", { name: "Meus comprovantes" }).getByRole("button", { name: "Tentar novamente" }).click();
  await expect.poll(() => attempts).toBe(2);
  const historyText = page.locator(".timeline li > div");
  expect((await historyText.boundingBox())!.width).toBeGreaterThan(200);
});

test("menu móvel contém o foco, fecha por Escape e devolve o foco ao botão", async ({ page }) => {
  await boot(page);
  await page.setViewportSize({ width: 400, height: 800 });
  await page.goto("/pessoas");
  const opener = page.getByRole("button", { name: "Abrir menu" });
  await opener.click();
  const drawer = page.getByRole("dialog", { name: "Menu de navegação" });
  await expect(drawer.getByRole("link", { name: "Início", exact: true })).toBeFocused();
  await expect(page.locator("main")).toHaveAttribute("inert", "");
  await drawer.getByRole("button", { name: "Sair" }).focus();
  await page.keyboard.press("Tab");
  await expect(drawer.getByRole("link", { name: "SIGAB — início" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(opener).toBeFocused();
  await expect(page.locator("main")).not.toHaveAttribute("inert", "");
});

test("busca e filtros voltam pelo histórico do navegador sem perder o contexto", async ({ page }) => {
  await boot(page);
  await page.goto("/pessoas");
  await page.getByRole("searchbox").fill("Ana");
  await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await expect(page).toHaveURL(/q=Ana/);
  await page.getByRole("searchbox").fill("Bruno");
  await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await expect(page).toHaveURL(/q=Bruno/);
  await page.goBack();
  await expect(page.getByRole("searchbox")).toHaveValue("Ana");
  await expect(page.getByLabel("Filtros aplicados")).toContainText("Ana");
});

for (const width of [320, 400, 768, 970, 1024, 1440]) {
  for (const colorScheme of ["light", "dark"] as const) {
    test(`layout ${width}px, tema ${colorScheme}: páginas e formulário cabem sem rolagem horizontal`, async ({ page }, info) => {
      await boot(page);
      await page.setViewportSize({ width, height: 900 });
      await page.emulateMedia({ colorScheme });
      for (const path of ["/acervo", "/pessoas", "/cadastros", "/biometria", "/estoque", "/atividade", "/atendimento/registro", "/minha-posse"]) {
        await page.goto(path);
        await expect(page.locator("main h1")).toBeVisible();
        await expect(page.locator(".loading-state")).toHaveCount(0);
        await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(1);
        const outside = await page.locator("main").evaluate((main) => [...main.querySelectorAll<HTMLElement>("input, select, button, .item-row, .timeline li > div")].filter((element) => {
          const rect = element.getBoundingClientRect();
          return rect.width > 0 && (rect.left < -1 || rect.right > innerWidth + 1);
        }).map((element) => element.textContent?.slice(0, 60) || element.tagName));
        expect(outside, path).toEqual([]);
        if ([400, 1440].includes(width) && ["/cadastros", "/acervo"].includes(path)) {
          await page.screenshot({ path: info.outputPath(`${path.slice(1)}-${colorScheme}-${width}.png`), fullPage: true });
        }
      }
      await page.goto("/pessoas");
      if (width <= 1024) expect((await page.locator(".mobile-bar").boundingBox())!.height).toBeLessThanOrEqual(72);
      else await expect(page.getByRole("button", { name: "Fechar menu" })).toBeHidden();
      await page.getByRole("button", { name: "Cadastrar pessoa" }).click();
      const dialog = page.getByRole("dialog", { name: "Cadastrar pessoa" });
      const bounds = await dialog.boundingBox();
      expect(bounds!.x).toBeGreaterThanOrEqual(0);
      expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(width);
      expect(await dialog.evaluate((element) => element.scrollWidth - element.clientWidth)).toBeLessThanOrEqual(1);
      await page.keyboard.press("Escape");
    });
  }
}

test("marca clara mantém contraste do botão e login usa a mesma identidade", async ({ page }) => {
  await boot(page);
  const brand = { name: "Reserva teste", tagline: "Acervo institucional", monogram: "RT", colors: { primary: "#ffffaa", accent: "#ffffff", sidebar: "#ffffff" } };
  await page.route("**/brand.json", (route) => route.fulfill({ json: brand }));
  await page.goto("/pessoas");
  const foreground = await page.getByRole("button", { name: "Cadastrar pessoa" }).evaluate((element) => getComputedStyle(element).color);
  expect(foreground).toBe("rgb(0, 0, 0)");
  const template = await readFile(new URL("../../backend/templates/registration/login.html", import.meta.url), "utf8");
  await page.route("**/entrar/", (route) => route.fulfill({ contentType: "text/html", body: template }));
  await page.goto("/entrar/");
  await expect(page.locator("[data-brand-name]")).toHaveText("Reserva teste");
  await expect(page).toHaveTitle("Entrar | Reserva teste");
  await expect(page.locator(".submit")).toHaveCSS("color", "rgb(0, 0, 0)");
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(page.locator(".login-card")).toHaveCSS("background-color", "rgb(21, 26, 25)");
});

for (const colorScheme of ["light", "dark"] as const) {
  test(`contraste de textos e campos no tema ${colorScheme}, incluindo marcas extremas`, async ({ page }) => {
    await boot(page);
    await page.emulateMedia({ colorScheme });
    for (const primary of ["#1d5c4a", "#ffffff", "#000000", "#ffffaa"]) {
      await page.route("**/brand.json", (route) => route.fulfill({ json: { colors: { primary, sidebar: "#ffffff", accent: "#ffffff" } } }));
      await page.goto("/pessoas");
      await expect(page.getByRole("button", { name: "Cadastrar pessoa" })).toBeVisible();
      const results = await page.evaluate(() => {
        const canvas = document.createElement("canvas"); canvas.width = canvas.height = 1;
        const context = canvas.getContext("2d", { willReadFrequently: true })!;
        const rgba = (css: string) => {
          context.clearRect(0, 0, 1, 1); context.fillStyle = css; context.fillRect(0, 0, 1, 1);
          return [...context.getImageData(0, 0, 1, 1).data].map((value) => value / 255);
        };
        const over = (front: number[], back: number[]) => front.slice(0, 3).map((value, i) => value * front[3] + back[i] * (1 - front[3])).concat(1);
        const luminance = (color: number[]) => color.slice(0, 3).map((v) => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4).reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
        const ratio = (a: number[], b: number[]) => (Math.max(luminance(a), luminance(b)) + .05) / (Math.min(luminance(a), luminance(b)) + .05);
        const selectors = [".button-primary", ".button-secondary", ".field-hint", ".nav-group a", ".nav-group-label", ".brand-text small", ".context-label", ".item-identity strong", ".search-form input"];
        return selectors.flatMap((selector) => [...document.querySelectorAll<HTMLElement>(selector)].filter((element) => element.offsetParent !== null).map((element) => {
          const ancestors: HTMLElement[] = [];
          for (let current: HTMLElement | null = element; current; current = current.parentElement) ancestors.unshift(current);
          const bg = ancestors.reduce((background, ancestor) => over(rgba(getComputedStyle(ancestor).backgroundColor), background), [1, 1, 1, 1]);
          const style = getComputedStyle(element);
          return { selector, text: ratio(over(rgba(style.color), bg), bg), boundary: selector === ".search-form input" ? ratio(rgba(style.borderTopColor), bg) : null };
        }));
      });
      for (const result of results) {
        expect(result.text, `${primary} ${result.selector}`).toBeGreaterThanOrEqual(4.5);
        if (result.boundary !== null) expect(result.boundary, `${primary} input border`).toBeGreaterThanOrEqual(3);
      }
    }
  });
}

test("termo impresso mantém identificação e assinaturas e oculta ações e navegação", async ({ page }, info) => {
  await boot(page);
  await page.route("**/identity-exceptions/10000000-0000-4000-8000-000000000001/", (route) => route.fulfill({ json: { success: true, data: {
    id: "t1", code: "TM-TESTE", operation: "checkout", operation_label: "Retirada", status: "pending_signature", status_label: "Aguardando assinatura",
    person: { id: "ana", name: "Pessoa sintética", registration: "MAT-TESTE" }, requested_by: "operador", requested_at: "2026-11-13T12:00:00Z",
    reason_label: "Câmera indisponível", reason: "", custody_mode: "indefinite", due_at: null,
    items: [{ id: "i1", identifier: "ITEM-TESTE", equipment_type: "Equipamento", unit: "Sede" }], stock: [], permissions: {}
  } } }));
  await page.goto("/atendimento/termos/10000000-0000-4000-8000-000000000001");
  await expect(page.getByRole("article")).toContainText("TM-TESTE");
  await page.emulateMedia({ media: "print" });
  await expect(page.locator(".sidebar")).toBeHidden();
  await expect(page.getByRole("button", { name: "Imprimir termo" })).toBeHidden();
  await expect(page.getByRole("article")).toContainText("MAT-TESTE");
  await expect(page.locator(".signatures")).toContainText("Administrador do acervo");
  await page.pdf({ path: info.outputPath("termo-sintetico.pdf"), format: "A4", printBackground: true });
});
