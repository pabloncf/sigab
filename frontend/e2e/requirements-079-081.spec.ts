import { expect, test, type Page } from "@playwright/test";

// Dados inteiramente sintéticos; a API é simulada e as permissões reais ficam no backend.
const ids = {
  person: "10000000-0000-4000-8000-000000000001",
  item: "20000000-0000-4000-8000-000000000001",
  pistol: "30000000-0000-4000-8000-000000000001",
  ammo: "30000000-0000-4000-8000-000000000002",
  unit: "40000000-0000-4000-8000-000000000001",
  location: "50000000-0000-4000-8000-000000000001",
  balance: "60000000-0000-4000-8000-000000000001"
};

const operator = {
  can_manage_identity: false, can_manage_catalog: false, can_create_item: false, can_view_items: true,
  can_view_audit: false, can_checkout: true, can_return: true, can_use_stock: true, can_receive_stock: false,
  can_manage_restrictions: false, can_use_self_service: false
};

async function session(page: Page, overrides: Partial<typeof operator> = {}) {
  await page.route("**/api/v1/session/", (route) => route.fulfill({ json: { success: true, data: {
    user: { id: ids.person, username: "operador" },
    organization: { id: ids.unit, name: "Organização teste" },
    permissions: { ...operator, ...overrides }
  } } }));
}

const overview = {
  individual: {
    totals: { available: 4, in_custody: 2, unavailable: 1, total: 7 },
    by_type: [{ equipment_type_id: ids.pistol, equipment_type: "Pistola", available: 4, in_custody: 2, unavailable: 1 }]
  },
  quantitative: [{ equipment_type_id: ids.ammo, equipment_type: "Munição 9 mm", reserve: "1200.000", in_custody: "300.000", total: "1500.000" }],
  pending: { individual_in_custody: 2, quantitative_open: 3, quantitative_overdue: 1 },
  recent: [{
    kind: "individual", id: "m1", type: "checkout", type_label: "Saída", equipment_type: "Pistola",
    identifier: "ARMA-001", item_id: ids.item, quantity: null, unit: "Sede", operator: "armeiro",
    recipient: "Pessoa teste", occurred_at: "2026-11-12T12:00:00Z"
  }]
};

const types = [
  { id: ids.pistol, name: "Pistola", description: "", classification: "individual", classification_label: "Individual", is_active: true, item_count: 7, stock_quantity: null },
  { id: ids.ammo, name: "Munição 9 mm", description: "", classification: "quantitative", classification_label: "Quantitativo", is_active: true, item_count: null, stock_quantity: "1500.000" }
];

test("início mostra totais, pendências, últimas movimentações e atalhos do perfil", async ({ page }) => {
  await session(page);
  await page.route("**/api/v1/overview/", (route) => route.fulfill({ json: { success: true, data: overview } }));
  await page.goto("/");
  await expect(page.getByRole("link", { name: "Início", exact: true })).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("list", { name: "Itens com registro por situação" })).toContainText("Disponível4");
  await expect(page.getByLabel("Saldos de material sem registro")).toContainText("Em reserva: 1.200");
  await expect(page.getByLabel("Saldos de material sem registro")).toContainText("Em posse: 300");
  await expect(page.getByLabel("Últimas retiradas e devoluções")).toContainText("Retirou: Pessoa teste · Entregue por: armeiro");
  // Início tem um único acesso operacional: entrada e saída pelo balcão.
  await expect(page.getByRole("button", { name: "Entrada e saída" })).toBeVisible();
  for (const name of ["Retirada", "Devolução", "Estoque", "Cadastrar equipamento", "Ver no estoque"]) {
    await expect(page.getByRole("main").getByRole("link", { name, exact: true })).toHaveCount(0);
  }
});

test("pessoa sem permissão operacional é levada à própria posse", async ({ page }) => {
  await session(page, { can_view_items: false, can_checkout: false, can_return: false, can_use_stock: false, can_use_self_service: true });
  let overviewCalls = 0;
  await page.route("**/api/v1/overview/", (route) => { overviewCalls += 1; return route.fulfill({ status: 403, json: { success: false, error: "Sem permissão." } }); });
  await page.route("**/api/v1/me/possessions/", (route) => route.fulfill({ json: { success: true, data: { person: { id: ids.person, name: "Pessoa teste" }, possessions: [] } } }));
  await page.route("**/api/v1/me/history/", (route) => route.fulfill({ json: { success: true, data: { individual: [], quantitative: [], receipts: [] } } }));
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Minha posse" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Início", exact: true })).toHaveCount(0);
  expect(overviewCalls).toBe(0);
});

test("endereço antigo de posse por pessoa redireciona para o acervo", async ({ page }) => {
  await session(page);
  let filter = "";
  await page.route("**/api/v1/items/?**", (route) => {
    filter = new URL(route.request().url()).searchParams.get("holder") ?? "";
    return route.fulfill({ json: { success: true, data: [], meta: { count: 0, limit: 100, offset: 0 } } });
  });
  await page.goto(`/?holder=${ids.person}`);
  await expect(page).toHaveURL(`/acervo?holder=${ids.person}`);
  await expect(page.getByRole("heading", { name: "Itens em posse" })).toBeVisible();
  expect(filter).toBe(ids.person);
});

test("equipamentos separa com e sem registro e leva à entrada de estoque do tipo", async ({ page }) => {
  await session(page, { can_manage_catalog: true, can_create_item: true, can_receive_stock: true });
  const created: Record<string, unknown>[] = [];
  await page.route("**/api/v1/equipment-types/", (route) => {
    if (route.request().method() === "POST") {
      created.push(route.request().postDataJSON());
      return route.fulfill({ status: 201, json: { success: true, data: types[0] } });
    }
    return route.fulfill({ json: { success: true, data: types } });
  });
  await page.route("**/api/v1/stock/options/", (route) => route.fulfill({ json: { success: true, data: {
    equipment_types: [{ id: ids.ammo, name: "Munição 9 mm" }],
    units: [{ id: ids.unit, name: "Sede", can_receive: true, locations: [{ id: ids.location, name: "Reserva" }] }]
  } } }));
  await page.route("**/api/v1/stock/positions/", (route) => route.fulfill({ json: { success: true, data: [] } }));
  await page.route("**/api/v1/stock/loans/", (route) => route.fulfill({ json: { success: true, data: [] } }));

  await page.goto("/equipamentos");
  const registered = page.getByRole("region", { name: "Com registro" });
  const unregistered = page.getByRole("region", { name: "Sem registro" });
  await expect(registered).toContainText("Pistola");
  await expect(registered).toContainText("7 itens");
  await expect(unregistered).toContainText("Munição 9 mm");
  await expect(unregistered).toContainText("1.500 no total");
  await expect(page.getByText("Individual", { exact: true })).toHaveCount(0);

  await page.getByRole("button", { name: "Novo tipo" }).click();
  await expect(page.getByRole("dialog")).toContainText("não pode ser alterada");
  await page.getByLabel("Nome").fill("Carabina");
  await page.getByLabel("Classificação").selectOption("individual");
  await page.getByRole("button", { name: "Cadastrar", exact: true }).click();
  await expect.poll(() => created).toEqual([{ name: "Carabina", classification: "individual", description: "" }]);

  await unregistered.getByRole("link", { name: "Registrar entrada" }).click();
  await expect(page).toHaveURL(`/estoque?entrada=${ids.ammo}`);
  await expect(page.getByRole("heading", { name: "Entrada de estoque" })).toBeVisible();
  await expect(page.getByLabel("Tipo de material")).toHaveValue(ids.ammo);
});

test("equipamentos não oferece cadastro sem a permissão correspondente", async ({ page }) => {
  await session(page, { can_create_item: true });
  await page.route("**/api/v1/equipment-types/", (route) => route.fulfill({ json: { success: true, data: types } }));
  await page.goto("/equipamentos");
  await expect(page.getByRole("button", { name: "Cadastrar item" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Registrar entrada" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Novo tipo" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Desativar" })).toHaveCount(0);
});

test("acervo separa itens com registro do material sem registro", async ({ page }) => {
  await session(page);
  await page.route("**/api/v1/items/?**", (route) => route.fulfill({ json: { success: true, data: [{
    id: ids.item, identifier: "ARMA-001", equipment_type: "Pistola", administrative_status: "active",
    administrative_status_label: "Ativo", condition: "fit", condition_label: "Apto", condition_reason: "",
    availability: "available", availability_label: "Disponível", current_holder: null
  }], meta: { count: 1, limit: 100, offset: 0 } } }));
  await page.route("**/api/v1/stock/summary/**", (route) => route.fulfill({ json: { success: true, data: [{
    id: ids.balance, equipment_type: { id: ids.ammo, name: "Munição 9 mm" }, unit: { id: ids.unit, name: "Sede" },
    storage_location: { id: ids.location, name: "Reserva" }, reserve: "1200.000", in_custody: "300.000", total: "1500.000"
  }] } }));
  await page.route("**/api/v1/stock/entries/**", (route) => route.fulfill({ json: { success: true, data: [{
    id: "e1", type: "checkout", type_label: "Saída", equipment_type: "Munição 9 mm", quantity: "300.000",
    balance_delta: "-300.000", unit: "Sede", storage_location: "Reserva", operator: "armeiro",
    recipient: "Pessoa teste", reason: "", reverses: null, occurred_at: "2026-11-12T12:00:00Z"
  }], meta: { count: 1, limit: 50, offset: 0 } } }));

  await page.goto("/acervo");
  await expect(page.getByRole("link", { name: "Com registro" })).toHaveAttribute("aria-current", "page");
  await expect(page.getByLabel("Itens com registro")).toContainText("ARMA-001");
  await expect(page.getByText("Munição 9 mm")).toHaveCount(0);

  await page.getByRole("link", { name: "Sem registro" }).click();
  const stock = page.getByLabel("Material sem registro");
  await expect(stock).toContainText("Em reserva: 1.200");
  await expect(stock).toContainText("Em posse: 300");
  await expect(stock).toContainText("Total: 1.500");
  await expect(page.getByText("ARMA-001")).toHaveCount(0);
  await stock.getByRole("button", { name: "Histórico do tipo" }).click();
  await expect(page.getByLabel("Histórico de Munição 9 mm")).toContainText("operador armeiro · pessoa Pessoa teste");
});
