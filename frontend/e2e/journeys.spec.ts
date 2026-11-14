import { addRegistered, mockIdentify } from "./counter-helpers";
import { expect, test, type Page } from "@playwright/test";

const ids = {
  person: "10000000-0000-4000-8000-000000000001",
  item: "20000000-0000-4000-8000-000000000001",
  movement: "30000000-0000-4000-8000-000000000001",
  batch: "40000000-0000-4000-8000-000000000001"
};

async function session(page: Page, overrides = {}) {
  await page.route("**/api/v1/session/", (route) => route.fulfill({ json: {
    success: true,
    data: {
      user: { id: "50000000-0000-4000-8000-000000000001", username: "operador" },
      organization: { id: "60000000-0000-4000-8000-000000000001", name: "Organização E2E" },
      permissions: {
        can_manage_identity: true,
        can_manage_catalog: true,
        can_create_item: true,
        can_view_items: true,
        can_view_audit: true,
        can_checkout: true,
        can_manage_restrictions: true,
        can_use_self_service: true,
        ...overrides
      }
    }
  }}));
}

const availableItem = {
  id: ids.item,
  identifier: "E2E-001",
  equipment_type: "Pistola de teste",
  administrative_status: "active",
  administrative_status_label: "Ativo",
  condition: "fit",
  condition_label: "Apto",
  condition_reason: "",
  availability: "available",
  availability_label: "Disponível",
  current_holder: null,
  unit: { id: "70000000-0000-4000-8000-000000000001", code: "U1", name: "Unidade" },
  storage_location: { id: "80000000-0000-4000-8000-000000000001", code: "R1", name: "Reserva" },
  serial_number: "E2E-001",
  asset_number: "",
  official_identifier: "",
  reversible_movement_id: null,
  permissions: { can_checkout: true, can_return: true, can_reverse: true, can_set_condition: true }
};

test("sessão ausente redireciona para o login preservando o destino", async ({ page }) => {
  await page.route("**/api/v1/session/", (route) => route.fulfill({
    status: 401,
    json: { success: false, error: "Autenticação necessária." }
  }));
  await page.route("**/entrar/**", (route) => route.fulfill({
    contentType: "text/html",
    body: "<h1>Entrar</h1>"
  }));
  await page.goto("/");
  await expect(page).toHaveURL(/\/entrar\/\?next=%2F$/);
  await expect(page.getByRole("heading", { name: "Entrar" })).toBeVisible();
});

test("gestor cadastra, altera e encerra restrição com confirmação", async ({ page }) => {
  await session(page);
  const restrictionId = "a0000000-0000-4000-8000-000000000001";
  let value: Record<string, unknown> | null = null;
  const actions: string[] = [];
  await page.route("**/api/v1/restrictions/", async (route) => {
    if (route.request().method() === "POST") {
      const body = route.request().postDataJSON();
      expect(body.confirmed).toBe(true);
      expect(body.person_id).toBe(ids.person);
      value = { ...body, id: restrictionId, person_name: "Pessoa E2E", closed_at: null, history: [] };
      await route.fulfill({ status: 201, json: { success: true, data: value } });
    } else {
      await route.fulfill({ json: { success: true, data: {
        restrictions: value ? [value] : [], people: [{ id: ids.person, name: "Pessoa E2E" }], equipment_types: []
      } } });
    }
  });
  await page.route(`**/api/v1/restrictions/${restrictionId}/`, async (route) => {
    if (route.request().method() === "POST") {
      const body = route.request().postDataJSON();
      expect(body.confirmed).toBe(true);
      expect(body.reason).toBeTruthy();
      actions.push(body.action);
      value = { ...value, ...body, ...(body.action === "close" ? { closed_at: "2026-11-09T18:00:00Z" } : {}) };
    }
    await route.fulfill({ json: { success: true, data: value } });
  });
  await page.goto("/restricoes");
  await page.getByRole("button", { name: "Cadastrar restrição" }).click();
  await page.locator('select[name="person_id"]').selectOption(ids.person);
  await page.getByLabel("Motivo resumido").fill("Impedimento administrativo");
  await page.getByLabel("Fonte", { exact: true }).fill("Comando");
  await page.getByLabel("Início", { exact: true }).fill("2026-11-09T08:00");
  await page.getByText("Confirmo os dados e o escopo desta restrição.").click();
  await page.getByRole("dialog").getByRole("button", { name: "Cadastrar restrição" }).click();
  await expect(page.getByRole("button", { name: "Alterar", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Alterar", exact: true }).click();
  await page.getByLabel("Motivo da alteração ou encerramento").fill("Prorrogação autorizada");
  await page.getByText("Confirmo os dados e o escopo desta restrição.").click();
  await page.getByRole("dialog").getByRole("button", { name: "Salvar alteração" }).click();
  await page.getByRole("button", { name: "Encerrar", exact: true }).click();
  await page.getByLabel("Motivo da alteração ou encerramento").fill("Impedimento encerrado");
  await page.getByText("Confirmo os dados e o escopo desta restrição.").click();
  await page.getByRole("dialog").getByRole("button", { name: "Encerrar restrição" }).click();
  await expect(page.getByText(/Encerrada · desde/)).toBeVisible();
  expect(actions).toEqual(["change", "close"]);
});

test("operador não recebe navegação de gestão de restrições", async ({ page }) => {
  await session(page, { can_manage_restrictions: false });
  await page.route("**/api/v1/items/**", (route) => route.fulfill({ json: { success: true, data: [], meta: { count: 0 } } }));
  await page.goto("/acervo");
  await expect(page.getByRole("heading", { name: "Acervo", level: 1 })).toBeVisible();
  await expect(page.getByRole("link", { name: "Restrições", exact: true })).toHaveCount(0);
});
test("incorporação percorre o formulário React e abre o item criado", async ({ page }) => {
  await session(page);
  await page.route("**/api/v1/items/?**", (route) => route.fulfill({ json: {
    success: true, data: [], meta: { count: 0, limit: 100, offset: 0 }
  }}));
  await page.route("**/api/v1/units/", (route) => route.fulfill({ json: {
    success: true,
    data: [{ id: availableItem.unit.id, code: "U1", name: "Unidade", is_active: true, locations: [{ id: availableItem.storage_location.id, code: "R1", name: "Reserva", is_active: true }] }]
  }}));
  await page.route("**/api/v1/equipment-types/", (route) => route.fulfill({ json: {
    success: true,
    data: [{ id: "90000000-0000-4000-8000-000000000001", name: "Pistola de teste", description: "", classification: "individual", classification_label: "Individual", is_active: true }]
  }}));
  await page.route("**/api/v1/items/", async (route) => {
    if (route.request().method() === "POST") {
      const body = route.request().postDataJSON();
      expect(body.confirmed).toBe(true);
      expect(body.serial_number).toBe("E2E-001");
      await route.fulfill({ status: 201, json: { success: true, data: availableItem } });
    } else {
      await route.fulfill({ json: { success: true, data: [], meta: { count: 0, limit: 100, offset: 0 } } });
    }
  });
  await page.route(`**/api/v1/items/${ids.item}/`, (route) => route.fulfill({ json: { success: true, data: availableItem } }));
  await page.route(`**/api/v1/items/${ids.item}/events/**`, (route) => route.fulfill({ json: { success: true, data: [], meta: { count: 0, limit: 20, offset: 0 } } }));

  // SIGAB-080: o item com registro é cadastrado a partir do tipo, no módulo Equipamentos.
  await page.goto("/equipamentos");
  await page.getByRole("button", { name: "Cadastrar item" }).click();
  await expect(page.getByLabel("Tipo de equipamento")).toHaveValue("90000000-0000-4000-8000-000000000001");
  await page.locator('select[name="unit_id"]').selectOption(availableItem.unit.id);
  await page.locator('select[name="storage_location_id"]').selectOption(availableItem.storage_location.id);
  await page.getByLabel("Número de série").fill("E2E-001");
  await page.getByText(/Confirmo a incorporação/).click();
  await page.getByRole("button", { name: "Incorporar", exact: true }).click();
  await expect(page).toHaveURL(`/items/${ids.item}`);
  await expect(page.getByRole("heading", { name: "E2E-001" })).toBeVisible();
});

test("navegação respeita permissões e autosserviço mostra apenas a própria posse", async ({ page }) => {
  await session(page);
  await page.route("**/api/v1/me/history/", (route) => route.fulfill({ json: {
    success: true,
    data: { individual: [{ id: ids.movement, type: "checkout", equipment_type: "Pistola de teste", identifier: "HIST-001", occurred_at: "2026-11-09T12:00:00Z" }], quantitative: [], receipts: [{ id: ids.batch, code: "AT-PESSOAL", confirmed_at: "2026-11-09T12:00:00Z" }] }
  }}));
  await page.route(`**/api/v1/me/receipts/${ids.batch}/`, (route) => route.fulfill({ json: {
    success: true,
    data: { receipt_code: "AT-PESSOAL", confirmed_at: "2026-11-09T12:00:00Z", recipient: { id: ids.person, name: "Pessoa E2E" }, operator: { id: "operador", username: "operador" }, custody_mode: "indefinite", due_at: null, items: [{ id: ids.item, identifier: "COMPROVANTE-001", equipment_type: "Pistola de teste" }], stock: [] }
  }}));
  await page.route("**/api/v1/items/**", (route) => route.fulfill({ json: {
    success: true, data: [availableItem], meta: { count: 1, limit: 100, offset: 0 }
  }}));
  await page.route("**/api/v1/me/possessions/", (route) => route.fulfill({ json: {
    success: true,
    data: {
      person: { id: ids.person, name: "Pessoa E2E" },
      possessions: [{ kind: "individual", id: ids.item, equipment_type: "Pistola de teste", identifier: "E2E-001", unit: "Unidade" }]
    }
  }}));
  await page.goto("/acervo");
  await expect(page.getByRole("link", { name: "Retirada e devolução" })).toBeVisible();
  await page.getByRole("link", { name: "Minha posse" }).click();
  await expect(page.getByRole("heading", { name: "Minha posse" })).toBeVisible();
  await expect(page.getByText("E2E-001")).toBeVisible();
  await expect(page.getByText(/HIST-001/)).toBeVisible();
  await page.getByRole("button", { name: "Abrir AT-PESSOAL" }).click();
  await expect(page.getByRole("article", { name: "Comprovante AT-PESSOAL" })).toContainText("COMPROVANTE-001");
});

test("atendimento envia uma cesta confirmada uma única vez e exibe comprovante", async ({ page }) => {
  await session(page);
  let requests = 0;
  await page.route("**/api/v1/service-batches/options/", (route) => route.fulfill({ json: {
    success: true,
    data: {
      people: [{ id: ids.person, name: "Pessoa E2E" }],
      items: [{ id: ids.item, identifier: "E2E-001", equipment_type: "Pistola de teste", unit: "Unidade" }],
      stock: []
    }
  }}));
  await page.route("**/api/v1/service-batches/", async (route) => {
    requests += 1;
    const body = route.request().postDataJSON();
    expect(body.recipient_id).toBe(ids.person);
    expect(body.item_ids).toEqual([ids.item]);
    expect(body.confirmed).toBe(true);
    await route.fulfill({ json: {
      success: true,
      data: { id: ids.batch, receipt_code: "AT-E2E", custody_mode: "indefinite", due_at: null }
    }});
  });
  await mockIdentify(page, ids.person, { name: "Pessoa E2E" });
  await page.goto("/atendimento");
  const entry = page.getByRole("region", { name: "Identificação" });
  await entry.getByLabel("Matrícula de quem retira ou devolve").fill("MAT-1");
  await entry.getByRole("button", { name: "Identificar" }).click();
  await entry.getByRole("link", { name: "Seguir para a saída (retirada)" }).click();
  await expect(page.getByRole("region", { name: "Pessoa identificada" })).toContainText("Pessoa E2E");
  await addRegistered(page, "E2E-001");
  await expect(page.getByRole("list", { name: "Com registro selecionados" })).toContainText("E2E-001 · Pistola de teste");
  await page.getByText("Confirmo pessoa, materiais e modalidade.").click();
  await page.getByRole("button", { name: "Confirmar retirada" }).click();
  await expect(page.getByText(/Comprovante AT-E2E/)).toBeVisible();
  expect(requests).toBe(1);
});

test("jornada individual cobre saída, contingência, devolução e estorno", async ({ page }) => {
  await session(page);
  let state = { ...availableItem };
  await page.route(`**/api/v1/items/${ids.item}/`, (route) => route.fulfill({ json: { success: true, data: state } }));
  await page.route(`**/api/v1/items/${ids.item}/events/**`, (route) => route.fulfill({ json: { success: true, data: [], meta: { count: 0, limit: 20, offset: 0 } } }));
  await page.route(`**/api/v1/items/${ids.item}/recipients/`, (route) => route.fulfill({ json: { success: true, data: [{ id: ids.person, name: "Pessoa E2E" }] } }));
  await page.route(`**/api/v1/items/${ids.item}/checkout/`, async (route) => {
    const body = route.request().postDataJSON();
    expect(body.contingency.paper_reference).toBe("F03/L07");
    state = { ...state, availability: "in_custody", availability_label: "Em posse", current_holder: { id: ids.person, name: "Pessoa E2E" }, reversible_movement_id: ids.movement };
    await route.fulfill({ json: { success: true, data: { movement_id: ids.movement, created: true, item: state } } });
  });
  await page.route(`**/api/v1/items/${ids.item}/return/`, async (route) => {
    state = { ...state, availability: "available", availability_label: "Disponível", current_holder: null, reversible_movement_id: ids.movement };
    await route.fulfill({ json: { success: true, data: { movement_id: ids.movement, created: true, item: state } } });
  });
  await page.route(`**/api/v1/movements/${ids.movement}/reverse/`, (route) => route.fulfill({ json: { success: true, data: { movement_id: ids.movement, created: true, item: state } } }));

  await page.goto(`/items/${ids.item}`);
  await page.getByRole("button", { name: "Registrar saída" }).click();
  await page.getByLabel("Destinatário").selectOption(ids.person);
  await page.getByText(/livro de contingência/).click();
  await page.getByLabel(/Data e hora do fato/).fill("2026-11-09T10:00");
  await page.getByLabel("Folha/linha do livro").fill("F03/L07");
  await page.getByText(/Confirmo a operação/).click();
  await page.getByRole("dialog").getByRole("button", { name: "Registrar saída" }).click();
  await expect(page.getByRole("button", { name: "Registrar devolução" })).toBeVisible();

  await page.getByRole("button", { name: "Registrar devolução" }).click();
  await page.getByText(/Confirmo a operação/).click();
  await page.getByRole("dialog").getByRole("button", { name: "Registrar devolução" }).click();
  await page.getByRole("button", { name: "Estornar último registro" }).click();
  await expect(page.getByRole("dialog")).toContainText("O registro original continua no histórico");
  await page.getByLabel("Motivo do estorno").fill("Correção E2E");
  await page.getByText(/Confirmo a operação/).click();
  await page.getByRole("dialog").getByRole("button", { name: "Estornar registro" }).click();
  await expect(page.getByText("Operação registrada com sucesso.")).toBeVisible();
});
