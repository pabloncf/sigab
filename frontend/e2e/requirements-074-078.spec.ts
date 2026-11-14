import { addRegistered, addUnregistered, mockIdentify } from "./counter-helpers";
import { expect, test, type Page } from "@playwright/test";

const person = "10000000-0000-4000-8000-000000000001";
const item = "20000000-0000-4000-8000-000000000001";
const kind = "30000000-0000-4000-8000-000000000001";
const unit = "40000000-0000-4000-8000-000000000001";
const location = "50000000-0000-4000-8000-000000000001";
const loan = "60000000-0000-4000-8000-000000000001";
const batch = "70000000-0000-4000-8000-000000000001";

async function session(page: Page, stock = true) {
  await page.route("**/api/v1/session/", (route) => route.fulfill({ json: { success: true, data: {
    user: { id: person, username: "operador" }, organization: { id: unit, name: "Organização teste" },
    permissions: { can_manage_identity: false, can_manage_catalog: false, can_create_item: false,
      can_view_items: true, can_view_audit: false, can_checkout: true,
      can_manage_restrictions: false, can_use_self_service: false, can_use_stock: stock }
  } } }));
}

for (const mode of ["quantitative", "mixed", "individual"]) {
  test(`recupera cesta ${mode} após resposta perdida e recarga sem duplicar`, async ({ page }) => {
    await session(page);
    let available = true;
    let balance = 100;
    let commits = 0;
    const requests: Record<string, unknown>[] = [];
    const saved = new Map<string, unknown>();
    await page.route("**/api/v1/service-batches/options/", (route) => route.fulfill({ json: { success: true, data: {
      people: [{ id: person, name: "Pessoa teste" }],
      items: available ? [{ id: item, identifier: "ARMA-001", equipment_type: "Pistola", unit: "Sede" }] : [],
      stock: [{ id: kind, equipment_type_id: kind, equipment_type: "Munição", unit_id: unit,
        unit: "Sede", storage_location_id: location, storage_location: "Reserva", quantity: String(balance) }]
    } } }));
    await page.route("**/api/v1/service-batches/", async (route) => {
      const body = route.request().postDataJSON();
      requests.push(body);
      if (!saved.has(body.idempotency_key)) {
        commits += 1;
        available = false;
        balance -= mode === "individual" ? 0 : 50;
        saved.set(body.idempotency_key, { id: batch, receipt_code: "AT-RECUPERADO", custody_mode: "indefinite", due_at: null });
        await route.abort("failed");
      } else await route.fulfill({ json: { success: true, data: saved.get(body.idempotency_key) } });
    });
    await mockIdentify(page, person);
    await page.goto(`/atendimento?pessoa=${person}`);
    if (mode !== "quantitative") await addRegistered(page, "ARMA-001");
    if (mode !== "individual") await addUnregistered(page, "Munição", "50");
    await page.getByText("Confirmo pessoa, materiais e modalidade.").click();
    if (mode === "mixed") await page.getByRole("button", { name: "Confirmar retirada" }).dblclick();
    else await page.getByRole("button", { name: "Confirmar retirada" }).click();
    await expect(page.getByRole("button", { name: "Verificar retirada" })).toBeEnabled();
    await expect(page.getByLabel("Nome do material")).toBeDisabled();
    await page.reload();
    await page.getByRole("button", { name: "Verificar retirada" }).click();
    await expect(page.getByText(/Comprovante AT-RECUPERADO/)).toBeVisible();
    await expect(page.getByRole("alert")).toHaveCount(0);
    // Concluída a retirada, o balcão volta a pedir a próxima matrícula.
    await expect(page.getByLabel("Matrícula de quem retira ou devolve")).toHaveValue("");
    expect(requests).toHaveLength(2);
    expect(requests[1]).toEqual(requests[0]);
    expect(commits).toBe(1);
    expect(balance).toBe(mode === "individual" ? 100 : 50);
  });
}

test("sucesso limpa formulário; falha de atualização não vira falha da saída", async ({ page }) => {
  await session(page);
  let committed = false;
  let failRefresh = true;
  const keys: string[] = [];
  await page.route("**/api/v1/service-batches/options/", (route) => {
    if (committed && failRefresh) return route.fulfill({ status: 503, json: { success: false, error: "Opções indisponíveis" } });
    return route.fulfill({ json: { success: true, data: { people: [{ id: person, name: "Pessoa teste" }], items: [],
      stock: [{ id: kind, equipment_type_id: kind, equipment_type: "Munição", unit_id: unit, unit: "Sede",
        storage_location_id: location, storage_location: "Reserva", quantity: committed ? "50" : "100" }] } } });
  });
  await page.route("**/api/v1/service-batches/", (route) => {
    keys.push(route.request().postDataJSON().idempotency_key);
    committed = true;
    return route.fulfill({ json: { success: true, data: { id: batch, receipt_code: "AT-SUCESSO", custody_mode: "indefinite", due_at: null } } });
  });
  await mockIdentify(page, person);
  await page.goto(`/atendimento?pessoa=${person}`);
  await addUnregistered(page, "Munição", "50");
  await page.getByText("Confirmo pessoa, materiais e modalidade.").click();
  await page.getByRole("button", { name: "Confirmar retirada" }).click();
  await expect(page.getByText(/Comprovante AT-SUCESSO/)).toBeVisible();
  await expect(page.getByText(/Falha ao atualizar opções/)).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(page.getByLabel("Nome do material")).toHaveCount(0);
  failRefresh = false;
  await page.getByRole("button", { name: "Atualizar materiais" }).click();
  await expect(page.getByText(/Falha ao atualizar opções/)).toHaveCount(0);
  const entry = page.getByRole("region", { name: "Identificação" });
  await entry.getByLabel("Matrícula de quem retira ou devolve").fill("MAT-1");
  await entry.getByRole("button", { name: "Identificar" }).click();
  await entry.getByRole("link", { name: "Seguir para a saída (retirada)" }).click();
  await addUnregistered(page, "Munição", "10");
  await expect(page.getByRole("list", { name: "Sem registro selecionados" })).toContainText("10 · Munição");
  await page.getByText("Confirmo pessoa, materiais e modalidade.").click();
  await page.getByRole("button", { name: "Confirmar retirada" }).click();
  await expect.poll(() => keys.length).toBe(2);
  expect(keys[0]).not.toBe(keys[1]);
});

test("estoque exige revisão e confirma entrada, devolução parcial e consumo", async ({ page }) => {
  await session(page);
  let balance = 0;
  let remaining = 50;
  const entries: unknown[] = [];
  await page.route("**/api/v1/stock/options/", (route) => route.fulfill({ json: { success: true, data: {
    equipment_types: [{ id: kind, name: "Munição" }], units: [{ id: unit, name: "Sede", can_receive: true,
      locations: [{ id: location, name: "Reserva" }] }]
  } } }));
  await page.route("**/api/v1/stock/positions/", (route) => {
    if (route.request().method() === "POST") {
      const body = route.request().postDataJSON();
      expect(body.confirmed).toBe(true);
      entries.push(body); balance += Number(body.quantity);
      return route.fulfill({ json: { success: true, data: { id: kind } } });
    }
    return route.fulfill({ json: { success: true, data: [{ id: kind, equipment_type: "Munição", quantity: String(balance), unit: { id: unit, name: "Sede" }, storage_location: { id: location, name: "Reserva" } }] } });
  });
  await page.route("**/api/v1/stock/loans/", (route) => route.fulfill({ json: { success: true, data: [
    { id: loan, person: "Pessoa teste", equipment_type: "Munição", unit: "Sede", location: "Reserva", quantity: String(remaining), can_settle: true }
  ] } }));
  await page.route(`**/api/v1/stock/loans/${loan}/settle/`, (route) => {
    const body = route.request().postDataJSON();
    expect(body.confirmed).toBe(true);
    if (body.disposition === "consume") expect(body.reason).toBe("Treinamento");
    entries.push(body); remaining -= Number(body.quantity);
    if (body.disposition === "return") balance += Number(body.quantity);
    return route.fulfill({ json: { success: true, data: { id: loan } } });
  });
  await page.goto("/estoque");
  await page.getByRole("button", { name: "Registrar entrada" }).click();
  await page.getByLabel("Tipo de material").selectOption(kind);
  await page.getByLabel("Unidade de entrada").selectOption(unit);
  await page.getByLabel("Local de guarda").selectOption(location);
  await page.getByLabel("Quantidade", { exact: true }).fill("50");
  await page.getByLabel("Referência ou justificativa da entrada").fill("Aquisição");
  await page.getByRole("button", { name: "Revisar operação" }).click();
  expect(entries).toHaveLength(0);
  await expect(page.getByRole("form", { name: "Resumo da operação" })).toContainText("Entrada de 50");
  await page.getByText("Conferi material, quantidade, destino e justificativa desta operação.").click();
  await page.getByRole("button", { name: "Confirmar operação" }).click();
  await expect(page.getByText("Disponível: 50", { exact: true })).toBeVisible();
  for (const [button, quantity, reason] of [["Devolver apto", "20", ""], ["Justificar consumo", "10", "Treinamento"]]) {
    await page.getByRole("button", { name: button }).click();
    await page.getByLabel("Quantidade", { exact: true }).fill(quantity);
    if (reason) await page.getByLabel("Justificativa do consumo").fill(reason);
    await page.getByRole("button", { name: "Revisar operação" }).click();
    await page.getByText("Conferi material, quantidade, destino e justificativa desta operação.").click();
    await page.getByRole("button", { name: "Confirmar operação" }).click();
    await expect(page.getByRole("heading", { name: button === "Devolver apto" ? "Devolução apta" : "Justificar consumo", exact: true })).toHaveCount(0);
  }
  await expect(page.getByText("Em aberto: 20", { exact: true })).toBeVisible();
  expect(entries).toHaveLength(3);
});

test("estoque não aparece sem permissão", async ({ page }) => {
  await session(page, false);
  await page.route("**/api/v1/items/**", (route) => route.fulfill({ json: { success: true, data: [], meta: { count: 0 } } }));
  await page.goto("/acervo");
  await expect(page.getByRole("link", { name: "Estoque", exact: true })).toHaveCount(0);
});

test("recusa de validação preserva campos e permite corrigir a cesta", async ({ page }) => {
  await session(page);
  await page.route("**/api/v1/service-batches/options/", (route) => route.fulfill({ json: {
    success: true, data: { people: [{ id: person, name: "Pessoa teste" }], items: [],
      stock: [{ id: kind, equipment_type_id: kind, equipment_type: "Munição", unit_id: unit,
        unit: "Sede", storage_location_id: location, storage_location: "Reserva", quantity: "100" }] }
  } }));
  const keys: string[] = [];
  await page.route("**/api/v1/service-batches/", (route) => {
    const body = route.request().postDataJSON(); keys.push(body.idempotency_key);
    if (keys.length === 1) return route.fulfill({ status: 400, json: { success: false, error: "Revise a quantidade" } });
    expect(body.stock[0].quantity).toBe("20");
    return route.fulfill({ json: { success: true, data: { id: batch, receipt_code: "AT-CORRIGIDO", custody_mode: "indefinite", due_at: null } } });
  });
  await mockIdentify(page, person);
  await page.goto(`/atendimento?pessoa=${person}`);
  await addUnregistered(page, "Munição", "50");
  await page.getByText("Confirmo pessoa, materiais e modalidade.").click();
  await page.getByRole("button", { name: "Confirmar retirada" }).click();
  await expect(page.getByRole("alert")).toContainText("Revise a quantidade");
  await expect(page.getByRole("region", { name: "Pessoa identificada" })).toContainText("Pessoa teste");
  const picked = page.getByRole("list", { name: "Sem registro selecionados" });
  await expect(picked).toContainText("50 · Munição");
  // Adicionar de novo o mesmo material corrige a quantidade.
  await addUnregistered(page, "Munição", "20");
  await expect(picked).toContainText("20 · Munição");
  await page.getByRole("button", { name: "Confirmar retirada" }).click();
  await expect(page.getByText(/Comprovante AT-CORRIGIDO/)).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
  expect(keys[0]).not.toBe(keys[1]);
});
