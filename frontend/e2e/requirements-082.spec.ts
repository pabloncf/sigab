import { addRegistered, addUnregistered, mockIdentify } from "./counter-helpers";
import { expect, test, type Page } from "@playwright/test";

// Dados inteiramente sintéticos; a API é simulada e a autorização real fica no backend.
const ids = {
  person: "10000000-0000-4000-8000-000000000001",
  item1: "20000000-0000-4000-8000-000000000001",
  item2: "20000000-0000-4000-8000-000000000002",
  loan: "60000000-0000-4000-8000-000000000001",
  batch: "70000000-0000-4000-8000-000000000001",
  operator: "80000000-0000-4000-8000-000000000001"
};

async function session(page: Page, overrides: Record<string, boolean> = {}) {
  await page.route("**/api/v1/session/", (route) => route.fulfill({ json: { success: true, data: {
    user: { id: ids.operator, username: "armeiro" },
    organization: { id: ids.person, name: "Organização teste" },
    permissions: {
      can_manage_identity: false, can_manage_catalog: false, can_create_item: false, can_view_items: true,
      can_view_audit: false, can_checkout: true, can_return: true, can_use_stock: true, can_receive_stock: false,
      can_manage_restrictions: false, can_use_self_service: false, ...overrides
    }
  } } }));
}

const possession = {
  people: [{ id: ids.person, name: "Pessoa teste" }],
  items: [
    { id: ids.item1, identifier: "ARMA-001", equipment_type: "Pistola", unit: "Sede" },
    { id: ids.item2, identifier: "ARMA-002", equipment_type: "Pistola", unit: "Sede" }
  ],
  stock: [{ loan_id: ids.loan, equipment_type: "Munição 9 mm", unit: "Sede", open_quantity: "50.000", due_at: null }]
};

test("devolução em lote confere item a item, sobrevive à resposta perdida e não duplica", async ({ page }) => {
  await session(page);
  let returned = false;
  const bodies: Record<string, unknown>[] = [];
  const saved = new Map<string, unknown>();
  await page.route("**/api/v1/return-batches/options/**", (route) => {
    const withPerson = new URL(route.request().url()).searchParams.has("person");
    if (returned) return route.fulfill({ json: { success: true, data: withPerson ? { people: [], items: [], stock: [] } : { people: [] } } });
    return route.fulfill({ json: { success: true, data: withPerson ? possession : { people: possession.people } } });
  });
  await page.route("**/api/v1/return-batches/", async (route) => {
    const body = route.request().postDataJSON();
    bodies.push(body);
    if (!saved.has(body.idempotency_key)) {
      returned = true;
      saved.set(body.idempotency_key, {
        id: ids.batch, receipt_code: "DV-TESTE", person: { id: ids.person, name: "Pessoa teste" },
        operator: { id: ids.operator, username: "armeiro" }, confirmed_at: "2026-11-13T12:00:00Z",
        items: [{ id: ids.item1, identifier: "ARMA-001", equipment_type: "Pistola", condition: "fit" },
          { id: ids.item2, identifier: "ARMA-002", equipment_type: "Pistola", condition: "unfit" }],
        stock: [{ loan_id: ids.loan, equipment_type: "Munição 9 mm", quantity: "20.000" }]
      });
      await route.abort("failed");
    } else await route.fulfill({ json: { success: true, data: saved.get(body.idempotency_key) } });
  });

  await mockIdentify(page, ids.person, { open_possessions: 3 });
  await page.goto("/atendimento/devolucao");
  await expect(page.getByRole("link", { name: "Devolução", exact: true })).toHaveAttribute("aria-current", "page");
  const entry = page.getByRole("region", { name: "Identificação" });
  await entry.getByLabel("Matrícula de quem retira ou devolve").fill("MAT-1");
  await entry.getByRole("button", { name: "Identificar" }).click();
  await entry.getByRole("link", { name: "Seguir para a entrada (devolução)" }).click();
  await expect(page.getByRole("region", { name: "Pessoa identificada" })).toContainText("Devolução por");
  await addRegistered(page, "arma-001");
  await addRegistered(page, "ARMA-002");
  await addRegistered(page, "ARMA-999");
  await expect(page.getByRole("region", { name: "Materiais com registro" }).getByRole("alert")).toContainText('Nenhum material com registro disponível com o número "ARMA-999"');
  await page.getByLabel("Condição de ARMA-002").selectOption("unfit");
  await page.getByLabel("Motivo de inapto de ARMA-002").fill("Cano danificado");
  await addUnregistered(page, "Munição 9 mm", "60");
  await expect(page.getByRole("region", { name: "Materiais sem registro" }).getByRole("alert")).toContainText("Quantidade acima do disponível");
  await addUnregistered(page, "Munição 9 mm", "20");
  // Com e sem registro ficam sempre em listas separadas.
  await expect(page.getByRole("region", { name: "Materiais com registro" }).getByRole("listitem")).toHaveCount(2);
  await expect(page.getByRole("region", { name: "Materiais sem registro" }).getByRole("listitem")).toHaveCount(1);
  await page.getByRole("button", { name: "Revisar devolução" }).click();
  const summary = page.getByRole("form", { name: "Resumo da devolução" });
  await expect(summary).toContainText("ARMA-002 · Pistola · inapto (Cano danificado)");
  await expect(summary).toContainText("20 de Munição 9 mm · apto");
  expect(bodies).toHaveLength(0);
  await page.getByText("Conferi pessoa, materiais, quantidades e condição de cada item.").click();
  await page.getByRole("button", { name: "Confirmar devolução" }).dblclick();

  await expect(page.getByRole("button", { name: "Verificar devolução" })).toBeEnabled();
  await page.reload();
  await page.getByRole("button", { name: "Verificar devolução" }).click();
  await expect(page.getByText(/Comprovante DV-TESTE/)).toBeVisible();
  expect(bodies).toHaveLength(2);
  expect(bodies[1]).toEqual(bodies[0]);
  expect(bodies[0]).toMatchObject({
    person_id: ids.person,
    confirmed: true,
    items: [{ item_id: ids.item1, condition: "fit", reason: "" }, { item_id: ids.item2, condition: "unfit", reason: "Cano danificado" }],
    stock: [{ loan_id: ids.loan, quantity: "20" }]
  });
  expect(saved.size).toBe(1);
});

test("registro de movimentações mostra quem retirou e quem entregou e aplica filtros", async ({ page }) => {
  await session(page);
  const queries: string[] = [];
  await page.route("**/api/v1/movements/options/", (route) => route.fulfill({ json: { success: true, data: {
    people: [{ id: ids.person, name: "Pessoa teste" }], operators: [{ id: ids.operator, username: "armeiro" }],
    equipment_types: [{ id: "t1", name: "Pistola" }]
  } } }));
  await page.route(/\/api\/v1\/movements\/\?/, (route) => {
    queries.push(new URL(route.request().url()).search);
    return route.fulfill({ json: { success: true, data: [
      { kind: "individual", id: "m2", type: "return", type_label: "Devolução", equipment_type: "Pistola", identifier: "ARMA-002",
        item_id: ids.item2, quantity: null, condition: "unfit", unit: "Sede", operator: "armeiro", recipient: "Pessoa teste",
        recipient_id: ids.person, receipt_code: "DV-TESTE", origin: "system", occurred_at: "2026-11-13T12:00:00Z" },
      { kind: "quantitative", id: "e1", type: "checkout", type_label: "Saída", equipment_type: "Munição 9 mm", identifier: null,
        item_id: null, quantity: "50.000", condition: null, unit: "Sede", operator: "armeiro", recipient: "Pessoa teste",
        recipient_id: ids.person, receipt_code: "AT-TESTE", origin: "system", occurred_at: "2026-11-12T12:00:00Z" }
    ], meta: { count: 2, limit: 50, offset: 0 } } });
  });

  await page.goto("/atendimento/registro");
  const list = page.getByRole("region", { name: "Movimentações" });
  await expect(list).toContainText("Devolveu: Pessoa teste · Recebido por: armeiro");
  await expect(list).toContainText("ARMA-002 · Pistola · inapto");
  await expect(list).toContainText("Retirou: Pessoa teste · Entregue por: armeiro");
  await expect(list).toContainText("DV-TESTE");
  await page.getByLabel("Pessoa").selectOption(ids.person);
  await page.getByLabel("Operador").selectOption(ids.operator);
  await page.getByLabel("Movimento").selectOption("return");
  await page.getByLabel("De", { exact: true }).fill("2026-11-01");
  await page.getByRole("button", { name: "Filtrar" }).click();
  await expect.poll(() => queries.at(-1)).toContain(`person=${ids.person}`);
  const last = new URLSearchParams(queries.at(-1));
  expect(last.get("operator")).toBe(ids.operator);
  expect(last.get("type")).toBe("return");
  expect(last.get("from")).toBe("2026-11-01");
});

test("abas do balcão seguem as permissões do perfil", async ({ page }) => {
  await session(page, { can_checkout: false, can_view_items: false });
  await page.route("**/api/v1/return-batches/options/**", (route) => route.fulfill({ json: { success: true, data: { people: [] } } }));
  await page.goto("/atendimento");
  await expect(page.getByRole("link", { name: "Retirada e devolução" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Devolução" })).toBeVisible();
  const tabs = page.getByRole("navigation", { name: "Retirada e devolução" });
  await expect(tabs.getByRole("link", { name: "Retirada" })).toHaveCount(0);
  await expect(tabs.getByRole("link", { name: "Registro de movimentações" })).toHaveCount(0);
});
