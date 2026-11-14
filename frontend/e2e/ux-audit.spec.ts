import { expect, test, type Page } from "@playwright/test";

// Auditoria de UX: modais acessíveis, busca explícita, paginação e hierarquia de ações.
// Dados inteiramente sintéticos; a API é simulada e as permissões reais ficam no backend.
const ids = {
  user: "10000000-0000-4000-8000-000000000009",
  unit: "40000000-0000-4000-8000-000000000001",
  pistol: "30000000-0000-4000-8000-000000000001"
};

const permissions = {
  can_manage_identity: true, can_manage_catalog: true, can_create_item: true, can_view_items: true,
  can_view_audit: false, can_checkout: true, can_return: true, can_use_stock: true, can_receive_stock: true,
  can_manage_restrictions: false, can_use_self_service: false, can_manage_biometrics: false
};

async function session(page: Page, itemScope = { all_units: false, units: [{ id: ids.unit, code: "U1", name: "Sede" }] }) {
  await page.route("**/api/v1/session/", (route) => route.fulfill({ json: { success: true, data: {
    user: { id: ids.user, username: "gestor" },
    organization: { id: "org", name: "Organização teste" },
    item_scope: itemScope,
    permissions
  } } }));
  await page.route("**/api/v1/units/", (route) => route.fulfill({ json: { success: true, data: [
    { id: ids.unit, code: "U1", name: "Sede", is_active: true, locations: [] }
  ] } }));
}

function people(offset: number, limit: number, total: number) {
  return Array.from({ length: Math.max(0, Math.min(limit, total - offset)) }, (_, index) => ({
    id: `p-${offset + index}`, name: `Pessoa ${String(offset + index + 1).padStart(3, "0")}`, functional_name: "",
    is_active: true, registrations: [`M-${offset + index + 1}`], has_account: false
  }));
}

async function peopleApi(page: Page, total: number, seen: string[] = []) {
  await page.route("**/api/v1/people/?**", (route) => {
    const url = new URL(route.request().url());
    seen.push(url.search);
    const offset = Number(url.searchParams.get("offset") ?? 0);
    const limit = Number(url.searchParams.get("limit") ?? 100);
    return route.fulfill({ json: { success: true, data: people(offset, limit, total), meta: { count: total, limit, offset } } });
  });
}

test("modal recebe o foco, prende o Tab, fecha com Esc e devolve o foco à origem", async ({ page }) => {
  await session(page);
  await peopleApi(page, 3);
  await page.goto("/pessoas");
  const opener = page.getByRole("button", { name: "Cadastrar pessoa" });
  await opener.click();
  const dialog = page.getByRole("dialog", { name: "Cadastrar pessoa" });
  await expect(dialog.getByLabel("Nome completo")).toBeFocused();

  // O fundo fica inerte enquanto o diálogo está aberto.
  await expect(page.locator("#root")).toHaveAttribute("inert", "");

  // Shift+Tab a partir do primeiro campo vai ao último controle, sem sair do diálogo.
  await page.keyboard.press("Shift+Tab");
  await expect(dialog.getByRole("button", { name: "Cadastrar", exact: true })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(dialog.getByLabel("Nome completo")).toBeFocused();

  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(opener).toBeFocused();
  await expect(page.locator("#root")).not.toHaveAttribute("inert", "");
});

test("formulário preenchido não fecha por clique fora e pede segundo Esc", async ({ page }) => {
  await session(page);
  await peopleApi(page, 1);
  await page.goto("/pessoas");
  await page.getByRole("button", { name: "Cadastrar pessoa" }).click();
  const dialog = page.getByRole("dialog", { name: "Cadastrar pessoa" });
  await dialog.getByLabel("Nome completo").fill("Pessoa em digitação");

  await page.mouse.click(5, 5);
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("Use “Cancelar” para descartá-los");

  await page.keyboard.press("Escape");
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("Pressione Esc novamente");
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
});

test("durante o envio o diálogo não fecha e o erro aparece junto do campo", async ({ page }) => {
  await session(page);
  await peopleApi(page, 0);
  let release: () => void = () => {};
  const held = new Promise<void>((resolve) => { release = resolve; });
  await page.route("**/api/v1/people/", async (route) => {
    await held;
    await route.fulfill({ status: 400, json: { success: false, error: "Dados inválidos.", details: { name: ["Informe o nome completo da pessoa."] } } });
  });
  await page.goto("/pessoas");
  await page.getByRole("button", { name: "Cadastrar pessoa" }).click();
  const dialog = page.getByRole("dialog", { name: "Cadastrar pessoa" });
  await dialog.getByLabel("Nome completo").fill("X");
  await dialog.getByRole("button", { name: "Cadastrar", exact: true }).click();
  await expect(dialog.getByRole("button", { name: "Cancelar" })).toBeDisabled();
  await page.keyboard.press("Escape");
  await expect(dialog).toContainText("O envio está em andamento");
  release();
  await expect(dialog.getByRole("alert")).toContainText("Dados inválidos.");
  const name = dialog.getByLabel("Nome completo");
  await expect(name).toHaveAttribute("aria-invalid", "true");
  await expect(dialog.locator(".field-error")).toHaveText("Informe o nome completo da pessoa.");
});

test("busca de pessoas tem rótulo, botão Buscar, Limpar e filtro aplicado", async ({ page }) => {
  await session(page);
  const seen: string[] = [];
  await peopleApi(page, 2, seen);
  await page.goto("/pessoas");
  const search = page.getByRole("searchbox", { name: "Buscar pessoa" });
  await search.fill("Silva");
  await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await expect(page).toHaveURL(/q=Silva/);
  await expect(page.getByLabel("Filtros aplicados")).toContainText("Busca: Silva");
  expect(seen.at(-1)).toContain("q=Silva");
  await page.getByRole("button", { name: "Limpar", exact: true }).click();
  await expect(page.getByLabel("Filtros aplicados")).toHaveCount(0);
  await expect(page).not.toHaveURL(/q=/);
});

test("pessoas paginam com intervalo exibido e preservam a página ao voltar do detalhe", async ({ page }) => {
  await session(page);
  await peopleApi(page, 120);
  await page.goto("/pessoas");
  await expect(page.locator(".list-summary")).toContainText("Exibindo 1–50 de 120 pessoas");
  await page.locator(".list-summary").getByRole("button", { name: "Próxima ›" }).click();
  await expect(page).toHaveURL(/pagina=2/);
  await expect(page.locator(".list-summary")).toContainText("Exibindo 51–100 de 120 pessoas");
  // O "Voltar" da ficha usa a última consulta, com a página e os filtros.
  await page.getByRole("link", { name: /Pessoa 051/ }).click();
  await page.waitForURL("**/pessoas/p-50");
  expect(await page.evaluate(() => sessionStorage.getItem("sigab:lista:pessoas"))).toBe("/pessoas?pagina=2");
  await page.goBack();
  await expect(page.locator(".list-summary")).toContainText("Exibindo 51–100 de 120 pessoas");
});

test("acervo comunica o mínimo de caracteres e usa o nome da tela como título", async ({ page }) => {
  await session(page);
  const seen: string[] = [];
  await page.route("**/api/v1/items/?**", (route) => {
    seen.push(new URL(route.request().url()).search);
    return route.fulfill({ json: { success: true, data: [], meta: { count: 0, limit: 50, offset: 0 } } });
  });
  await page.goto("/acervo");
  await expect(page.getByRole("heading", { name: "Acervo", level: 1 })).toBeVisible();
  await expect(page.getByText("na unidade U1 · Sede").first()).toBeVisible();
  const search = page.getByRole("searchbox", { name: "Buscar no acervo" });
  await search.fill("A");
  await page.getByRole("button", { name: "Buscar", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText("Digite ao menos 2 caracteres para buscar.");
  expect(seen.every((query) => !query.includes("q="))).toBe(true);
});

test("equipamentos separa a desativação e a confirmação nomeia o tipo e o efeito", async ({ page }) => {
  await session(page);
  await page.route("**/api/v1/equipment-types/", (route) => route.fulfill({ json: { success: true, data: [
    { id: ids.pistol, name: "Pistola", description: "", classification: "individual", classification_label: "Individual", is_active: true, item_count: 2, stock_quantity: null }
  ] } }));
  await page.goto("/equipamentos");
  await expect(page.getByRole("link", { name: "Ver no acervo" })).toHaveClass(/text-link/);
  await page.getByRole("button", { name: "Desativar" }).click();
  const dialog = page.getByRole("dialog", { name: "Desativar o tipo “Pistola”?" });
  await expect(dialog).toContainText("deixa de aceitar cadastro de novos itens");
  await expect(dialog.getByRole("button", { name: "Desativar tipo" })).toHaveClass(/button-danger/);
});
