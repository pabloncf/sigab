import { addRegistered, mockIdentify } from "./counter-helpers";
import { expect, test, type Page } from "@playwright/test";

// Câmera falsa do Chromium: vídeo sintético, nenhuma imagem real de pessoa.
test.use({
  permissions: ["camera"],
  launchOptions: { args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"] }
});

const ids = {
  person: "10000000-0000-4000-8000-000000000001",
  item: "20000000-0000-4000-8000-000000000001",
  verification: "90000000-0000-4000-8000-000000000001",
  term: "a0000000-0000-4000-8000-000000000001",
  batch: "70000000-0000-4000-8000-000000000001"
};

async function session(page: Page, overrides: Record<string, boolean> = {}) {
  await page.route("**/api/v1/session/", (route) => route.fulfill({ json: { success: true, data: {
    user: { id: "u1", username: "armeiro" },
    organization: { id: "o1", name: "Organização teste" },
    permissions: {
      can_manage_identity: false, can_manage_catalog: false, can_create_item: false, can_view_items: true,
      can_view_audit: false, can_checkout: true, can_return: true, can_use_stock: false, can_receive_stock: false,
      can_manage_restrictions: false, can_use_self_service: false, can_manage_biometrics: false,
      can_approve_identity_exceptions: false, identity_check_required: true, ...overrides
    }
  } } }));
}

async function basketOptions(page: Page) {
  await page.route("**/api/v1/service-batches/options/", (route) => route.fulfill({ json: { success: true, data: {
    people: [{ id: ids.person, name: "Pessoa teste" }],
    items: [{ id: ids.item, identifier: "ARMA-001", equipment_type: "Pistola", unit: "Sede" }],
    stock: []
  } } }));
}

async function fillBasket(page: Page) {
  // Pessoa identificada pela matrícula, sem verificação facial ainda (caminho do termo).
  await mockIdentify(page, ids.person);
  await page.goto(`/atendimento?pessoa=${ids.person}`);
  await addRegistered(page, "ARMA-001");
  await page.getByText("Confirmo pessoa, materiais e modalidade.").click();
  await page.getByRole("button", { name: "Confirmar identidade" }).click();
}

const term = {
  id: ids.term, code: "TM-TESTE", operation: "checkout", operation_label: "Retirada", status: "pending_signature",
  status_label: "Aguardando assinatura", person: { id: ids.person, name: "Pessoa teste", registration: "MAT-1" },
  requested_by: "armeiro", requested_at: "2026-11-13T12:00:00Z", reason_code: "verification_failed",
  reason_label: "Verificação facial recusada", reason: "", custody_mode: "indefinite", due_at: null,
  items: [{ id: ids.item, identifier: "ARMA-001", equipment_type: "Pistola", unit: "Sede", condition: null }],
  stock: [], signed_collected_at: null, decided_by: null, decided_at: null, decision_reason: "",
  permissions: { can_register_signature: true, can_cancel: true, can_decide: false }
};

test("retirada só é enviada com a verificação facial aprovada", async ({ page }) => {
  await session(page);
  await basketOptions(page);
  const verifications: string[] = [];
  const baskets: Record<string, unknown>[] = [];
  await page.route("**/api/v1/face-verifications/", async (route) => {
    const body = route.request().postData() ?? "";
    verifications.push(body);
    await route.fulfill({ status: 201, json: { success: true, data: { id: ids.verification, result: "approved", expires_at: "2026-11-13T12:02:00Z" } } });
  });
  await page.route("**/api/v1/service-batches/", (route) => {
    baskets.push(route.request().postDataJSON());
    return route.fulfill({ status: 201, json: { success: true, data: { id: ids.batch, receipt_code: "AT-FACIAL", custody_mode: "indefinite", due_at: null } } });
  });

  await fillBasket(page);
  const step = page.getByRole("region", { name: "Confirmação de identidade" });
  await expect(step).toBeVisible();
  expect(baskets).toHaveLength(0);
  const capture = step.getByRole("button", { name: "Capturar e verificar" });
  await expect(capture).toBeDisabled();
  await step.getByText("Conferi visualmente que Pessoa teste está presente no balcão.").click();
  await step.getByRole("button", { name: "Ativar câmera", exact: true }).click();
  await expect(capture).toBeEnabled();
  await capture.click();
  await expect(page.getByText(/Comprovante AT-FACIAL/)).toBeVisible();
  expect(verifications[0]).toContain(ids.person);
  expect(verifications[0]).toContain('name="operation"\r\n\r\ncheckout');
  expect(verifications[0]).toContain('name="operator_confirmed"\r\n\r\ntrue');
  expect(baskets).toHaveLength(1);
  expect(baskets[0]).toMatchObject({ recipient_id: ids.person, item_ids: [ids.item], face_verification_id: ids.verification });
});

test("biometria recusada leva ao termo, que a pessoa assina antes da aprovação", async ({ page }) => {
  await session(page);
  await basketOptions(page);
  const terms: Record<string, unknown>[] = [];
  let signed = false;
  await page.route("**/api/v1/face-verifications/", (route) => route.fulfill({ status: 201, json: { success: true, data: { id: ids.verification, result: "rejected", expires_at: "2026-11-13T12:02:00Z" } } }));
  await page.route("**/api/v1/service-batches/", () => { throw new Error("nenhuma retirada pode ser enviada"); });
  await page.route("**/api/v1/identity-exceptions/", (route) => {
    terms.push(route.request().postDataJSON());
    return route.fulfill({ status: 201, json: { success: true, data: term } });
  });
  await page.route(`**/api/v1/identity-exceptions/${ids.term}/`, (route) => route.fulfill({ json: { success: true, data: signed ? { ...term, status: "pending_approval", status_label: "Aguardando aprovação", permissions: { ...term.permissions, can_register_signature: false } } : term } }));
  await page.route(`**/api/v1/identity-exceptions/${ids.term}/signed/`, (route) => {
    signed = true;
    return route.fulfill({ json: { success: true, data: { ...term, status: "pending_approval", status_label: "Aguardando aprovação", permissions: { ...term.permissions, can_register_signature: false } } } });
  });

  await fillBasket(page);
  const step = page.getByRole("region", { name: "Confirmação de identidade" });
  await step.getByText("Conferi visualmente que Pessoa teste está presente no balcão.").click();
  await step.getByRole("button", { name: "Ativar câmera", exact: true }).click();
  await step.getByRole("button", { name: "Capturar e verificar" }).click();
  await expect(step.getByRole("alert")).toContainText("Verificação recusada");
  await step.getByRole("button", { name: "Biometria não foi possível: gerar termo" }).click();
  await expect(step.getByRole("combobox", { name: /^Motivo/ })).toHaveValue("verification_failed");
  await step.getByText("Confirmo que a biometria não foi possível e que a pessoa assinará o termo.").click();
  await step.getByRole("button", { name: "Gerar termo" }).click();

  await expect(page).toHaveURL(`/atendimento/termos/${ids.term}`);
  expect(terms[0]).toMatchObject({
    operation: "checkout", person_id: ids.person, reason_code: "verification_failed", confirmed: true,
    request: { items: [ids.item], stock: [], custody_mode: "indefinite", due_at: null }
  });
  const document = page.getByRole("article", { name: "Termo TM-TESTE" });
  await expect(document).toContainText("MAT-1");
  await expect(document).toContainText("Declaro que recebi os materiais acima");
  await expect(document).toContainText("Administrador do acervo");
  await expect(page.getByRole("button", { name: /Aprovar/ })).toHaveCount(0);
  await page.getByRole("button", { name: "Registrar termo assinado" }).click();
  await expect(document).toContainText("Aguardando aprovação");
});

test("somente o administrador do acervo aprova o termo", async ({ page }) => {
  await session(page, { can_checkout: false, can_return: false, can_approve_identity_exceptions: true });
  const decisions: Record<string, unknown>[] = [];
  const pending = { ...term, status: "pending_approval", status_label: "Aguardando aprovação", permissions: { can_register_signature: false, can_cancel: false, can_decide: true } };
  await page.route("**/api/v1/identity-exceptions/?status=pending_approval", (route) => route.fulfill({ json: { success: true, data: [pending] } }));
  await page.route(`**/api/v1/identity-exceptions/${ids.term}/`, (route) => route.fulfill({ json: { success: true, data: pending } }));
  await page.route(`**/api/v1/identity-exceptions/${ids.term}/decision/`, (route) => {
    decisions.push(route.request().postDataJSON());
    return route.fulfill({ json: { success: true, data: { ...pending, status: "approved", status_label: "Aprovado", decided_by: "gestor", decided_at: "2026-11-13T12:10:00Z", permissions: { can_register_signature: false, can_cancel: false, can_decide: false } } } });
  });

  await page.goto("/atendimento");
  await expect(page.getByRole("link", { name: "Termos" })).toHaveAttribute("aria-current", "page");
  await page.getByRole("link", { name: "Analisar" }).click();
  const recusar = page.getByRole("button", { name: "Recusar" });
  await expect(recusar).toBeDisabled();
  await page.getByRole("button", { name: "Aprovar retirada" }).click();
  await expect(page.getByRole("article", { name: "Termo TM-TESTE" })).toContainText("Decisão: Aprovado por gestor");
  expect(decisions).toEqual([{ approve: true, reason: "", confirmed: true }]);
});

test("gestor cadastra a biometria facial de quem ainda não tem cadastro", async ({ page }) => {
  await session(page, { can_checkout: false, can_return: false, can_manage_biometrics: true });
  let enrolled = false;
  const uploads: string[] = [];
  await page.route("**/api/v1/biometrics/", (route) => route.fulfill({ json: { success: true, data: [
    { id: ids.person, name: "Pessoa teste", registrations: ["MAT-1"], enrolled, enrolled_at: enrolled ? "2026-11-13T12:00:00Z" : null, engine_version: null }
  ] } }));
  await page.route(`**/api/v1/people/${ids.person}/biometric/`, (route) => {
    if (route.request().method() === "POST") {
      uploads.push(route.request().postData() ?? "");
      enrolled = true;
      return route.fulfill({ status: 201, json: { success: true, data: { enrolled: true, enrolled_at: "2026-11-13T12:00:00Z", engine_version: "x" } } });
    }
    return route.fulfill({ json: { success: true, data: { enrolled: false, enrolled_at: null, engine_version: null } } });
  });

  await page.goto("/biometria");
  await expect(page.getByLabel("Pessoas e biometria")).toContainText("1 sem cadastro");
  await page.getByRole("button", { name: "Cadastrar biometria de Pessoa teste" }).click();
  const panel = page.getByRole("region", { name: "Biometria facial de Pessoa teste" });
  await expect(panel).toContainText("Não cadastrada");
  await panel.getByRole("button", { name: "Cadastrar" }).click();
  await panel.getByText(/está presente e foi informada da finalidade/).click();
  await panel.getByRole("button", { name: "Ativar câmera", exact: true }).click();
  await panel.getByRole("button", { name: "Capturar e cadastrar" }).click();
  await expect(panel).toContainText("Biometria cadastrada.");
  expect(uploads[0]).toContain('name="confirmed"\r\n\r\ntrue');
  expect(uploads[0]).toContain("image/jpeg");
});

test("ficha do item aceita apenas lançamento de contingência", async ({ page }) => {
  await session(page);
  const item = {
    id: ids.item, identifier: "ARMA-001", equipment_type: "Pistola", administrative_status: "active", administrative_status_label: "Ativo",
    condition: "fit", condition_label: "Apto", condition_reason: "", availability: "available", availability_label: "Disponível",
    current_holder: null, unit: { id: "u", code: "U1", name: "Sede" }, storage_location: { id: "l", code: "R1", name: "Reserva" },
    serial_number: "ARMA-001", asset_number: "", official_identifier: "", reversible_movement_id: null,
    permissions: { can_checkout: true, can_return: true, can_reverse: false, can_set_condition: false }
  };
  await page.route(`**/api/v1/items/${ids.item}/`, (route) => route.fulfill({ json: { success: true, data: item } }));
  await page.route(`**/api/v1/items/${ids.item}/events/**`, (route) => route.fulfill({ json: { success: true, data: [], meta: { count: 0 } } }));
  await page.route(`**/api/v1/items/${ids.item}/recipients/**`, (route) => route.fulfill({ json: { success: true, data: [{ id: ids.person, name: "Pessoa teste" }] } }));
  await page.goto(`/items/${ids.item}`);
  await page.getByRole("button", { name: "Lançar saída da contingência" }).click();
  await expect(page.getByText("Aqui só se lança o livro de contingência.")).toBeVisible();
  await expect(page.getByLabel("Folha/linha do livro")).toBeVisible();
});

const emptyOverview = {
  individual: { totals: { available: 0, in_custody: 0, unavailable: 0, total: 0 }, by_type: [] },
  quantitative: [], pending: { individual_in_custody: 0, quantitative_open: 0, quantitative_overdue: 0 }, recent: []
};

const identified = {
  id: ids.person, name: "Pessoa teste", registration: "MAT-1", biometric_enrolled: true,
  open_possessions: 0, own: false, operations: { checkout: true, return: true }
};

test("entrada e saída: matrícula, reconhecimento facial e materiais sem nova verificação", async ({ page }) => {
  await session(page);
  await basketOptions(page);
  await page.route("**/api/v1/overview/", (route) => route.fulfill({ json: { success: true, data: emptyOverview } }));
  const lookups: string[] = [];
  await page.route("**/api/v1/counter/identify/**", (route) => {
    lookups.push(route.request().url());
    return route.fulfill({ json: { success: true, data: identified } });
  });
  const verifications: string[] = [];
  await page.route("**/api/v1/face-verifications/", (route) => {
    verifications.push(route.request().postData() ?? "");
    return route.fulfill({ status: 201, json: { success: true, data: { id: ids.verification, result: "approved", expires_at: "2026-11-13T12:10:00Z" } } });
  });
  const baskets: Record<string, unknown>[] = [];
  await page.route("**/api/v1/service-batches/", (route) => {
    baskets.push(route.request().postDataJSON());
    return route.fulfill({ status: 201, json: { success: true, data: { id: ids.batch, receipt_code: "AT-ENTRADA", custody_mode: "indefinite", due_at: null } } });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Entrada e saída" }).click();
  const entry = page.getByRole("region", { name: "Entrada e saída" });
  await entry.getByLabel("Matrícula de quem retira ou devolve").fill("MAT-1");
  await entry.getByRole("button", { name: "Identificar" }).click();
  await expect(entry).toContainText("Pessoa teste · matrícula MAT-1");
  expect(lookups[0]).toContain("registration=MAT-1");
  await expect(entry.getByLabel("Saída (retirada)")).toBeChecked();
  const recognize = entry.getByRole("button", { name: "Reconhecer rosto" });
  await expect(recognize).toBeDisabled();
  await entry.getByText("Conferi visualmente que Pessoa teste está presente no balcão.").click();
  await entry.getByRole("button", { name: "Ativar câmera", exact: true }).click();
  await recognize.click();

  await page.waitForURL(`**/atendimento?pessoa=${ids.person}&verificacao=${ids.verification}`);
  expect(verifications[0]).toContain('name="operation"\r\n\r\ncheckout');
  const card = page.getByRole("region", { name: "Pessoa identificada" });
  await expect(card).toContainText("Retirada por");
  await expect(card).toContainText("Pessoa teste");
  await expect(card).toContainText("Matrícula MAT-1");
  await expect(card).toContainText("Identidade confirmada por reconhecimento facial.");
  await addRegistered(page, "ARMA-001");
  await page.getByText("Confirmo pessoa, materiais e modalidade.").click();
  await page.getByRole("button", { name: "Confirmar retirada" }).click();
  await expect(page.getByText(/Comprovante AT-ENTRADA/)).toBeVisible();
  expect(verifications).toHaveLength(1);
  expect(baskets[0]).toMatchObject({ recipient_id: ids.person, item_ids: [ids.item], face_verification_id: ids.verification });
  // Uso único: a verificação sai da URL depois da confirmação.
  expect(page.url()).not.toContain("verificacao=");
});

test("entrada e saída sem biometria cadastrada segue para a operação por termo", async ({ page }) => {
  await session(page);
  await page.route("**/api/v1/overview/", (route) => route.fulfill({ json: { success: true, data: emptyOverview } }));
  await page.route("**/api/v1/counter/identify/**", (route) => route.fulfill({ json: { success: true, data: { ...identified, biometric_enrolled: false, open_possessions: 2 } } }));
  await page.goto("/");
  await page.getByRole("button", { name: "Entrada e saída" }).click();
  const entry = page.getByRole("region", { name: "Entrada e saída" });
  await entry.getByLabel("Matrícula de quem retira ou devolve").fill("MAT-1");
  await entry.getByRole("button", { name: "Identificar" }).click();
  await expect(entry.getByLabel("Entrada (devolução)")).toBeChecked();
  await expect(entry).toContainText("não tem biometria facial cadastrada");
  await expect(entry.getByRole("button", { name: "Reconhecer rosto" })).toHaveCount(0);
  await expect(entry.getByRole("link", { name: "Seguir para a entrada (devolução)" })).toHaveAttribute("href", `/atendimento/devolucao?pessoa=${ids.person}`);
});

test("matrícula desconhecida não identifica ninguém", async ({ page }) => {
  await session(page);
  await page.route("**/api/v1/overview/", (route) => route.fulfill({ json: { success: true, data: emptyOverview } }));
  await page.route("**/api/v1/counter/identify/**", (route) => route.fulfill({ status: 404, json: { success: false, error: "Recurso não encontrado." } }));
  await page.goto("/");
  await page.getByRole("button", { name: "Entrada e saída" }).click();
  const entry = page.getByRole("region", { name: "Entrada e saída" });
  await entry.getByLabel("Matrícula de quem retira ou devolve").fill("X-9");
  await entry.getByRole("button", { name: "Identificar" }).click();
  await expect(entry.getByRole("alert")).toHaveText("Matrícula não encontrada ou sem vínculo ativo.");
});

test("cadastro de pessoa com vínculo e captura facial", async ({ page }) => {
  await session(page, { can_checkout: false, can_return: false, can_manage_identity: true, can_manage_biometrics: true });
  await page.route("**/api/v1/people/?**", (route) => route.fulfill({ json: { success: true, data: [], meta: { count: 0, limit: 200, offset: 0 } } }));
  await page.route("**/api/v1/units/", (route) => route.fulfill({ json: { success: true, data: [{ id: "u-1", code: "SEDE", name: "Sede", is_active: true }] } }));
  const created: Record<string, unknown>[] = [];
  await page.route("**/api/v1/people/", (route) => {
    created.push(route.request().postDataJSON());
    return route.fulfill({ status: 201, json: { success: true, data: { id: ids.person, name: "Pessoa nova", functional_name: "", phone: "", cpf_masked: "", is_active: true, memberships: [], accounts: [] } } });
  });
  const uploads: string[] = [];
  await page.route(`**/api/v1/people/${ids.person}/biometric/`, (route) => {
    uploads.push(route.request().postData() ?? "");
    return route.fulfill({ status: 201, json: { success: true, data: { enrolled: true, enrolled_at: "2026-11-13T12:00:00Z", engine_version: "x" } } });
  });

  await page.goto("/pessoas");
  await page.getByRole("button", { name: "Cadastrar pessoa" }).click();
  const dialog = page.getByRole("dialog", { name: "Cadastrar pessoa" });
  await dialog.getByLabel("Nome completo").fill("Pessoa nova");
  const face = dialog.getByRole("group", { name: "Biometria facial" });
  await expect(face).toContainText("Informe matrícula e unidade");
  await dialog.getByLabel("Matrícula").fill("MAT-9");
  await dialog.getByLabel("Unidade principal").selectOption("u-1");
  const capture = face.getByRole("button", { name: "Capturar rosto" });
  await expect(capture).toBeDisabled();
  await face.getByText(/está presente e foi informada da finalidade/).click();
  await face.getByRole("button", { name: "Ativar câmera", exact: true }).click();
  await capture.click();
  await expect(face).toContainText("Rosto capturado");
  // Só a área da moldura é enviada: recorte retrato, menor que o quadro 640×480 da câmera simulada.
  const preview = face.getByRole("img", { name: "Recorte do rosto que será cadastrado" });
  await expect(preview).toBeVisible();
  const size = await preview.evaluate((img: HTMLImageElement) => ({ width: img.naturalWidth, height: img.naturalHeight }));
  expect(size).toEqual({ width: 333, height: 442 });
  await dialog.getByRole("button", { name: "Cadastrar", exact: true }).click();
  await page.waitForURL(`**/pessoas/${ids.person}`);
  expect(created[0]).toMatchObject({ name: "Pessoa nova", registration: "MAT-9", main_unit_id: "u-1" });
  expect(uploads[0]).toContain('name="confirmed"\r\n\r\ntrue');
  expect(uploads[0]).toContain("image/jpeg");
});

test("operador cancela a operação depois da identidade confirmada", async ({ page }) => {
  await session(page);
  await basketOptions(page);
  await page.route("**/api/v1/overview/", (route) => route.fulfill({ json: { success: true, data: emptyOverview } }));
  const cancels: Record<string, unknown>[] = [];
  await page.route(`**/api/v1/face-verifications/${ids.verification}/cancel/`, (route) => {
    cancels.push(route.request().postDataJSON());
    return route.fulfill({ json: { success: true, data: { id: ids.verification, cancelled: true } } });
  });
  await page.route("**/api/v1/service-batches/", () => { throw new Error("nenhuma retirada pode ser enviada"); });

  await page.goto(`/atendimento?pessoa=${ids.person}&verificacao=${ids.verification}`);
  await mockIdentify(page, ids.person);
  const banner = page.getByRole("region", { name: "Pessoa identificada" });
  await banner.getByRole("button", { name: "Cancelar operação" }).click();
  await expect(banner).toContainText("Nada será movimentado.");
  await banner.getByRole("button", { name: "Continuar operação" }).click();
  expect(cancels).toHaveLength(0);
  await banner.getByRole("button", { name: "Cancelar operação" }).click();
  await banner.getByRole("button", { name: "Sim, cancelar" }).click();
  await page.waitForURL((url) => url.pathname === "/");
  expect(cancels).toEqual([{ confirmed: true }]);
  await expect(page.getByRole("button", { name: "Entrada e saída" })).toBeVisible();
});

test("prazo só aparece no prazo determinado e erro de preenchimento não descarta a identificação", async ({ page }) => {
  await session(page);
  await basketOptions(page);
  const baskets: Record<string, unknown>[] = [];
  await page.route("**/api/v1/service-batches/", (route) => {
    baskets.push(route.request().postDataJSON());
    if (baskets.length === 1) return route.fulfill({ status: 400, json: { success: false, error: "Dados inválidos. O prazo deve estar no futuro." } });
    return route.fulfill({ status: 201, json: { success: true, data: { id: ids.batch, receipt_code: "AT-PRAZO", custody_mode: "fixed_term", due_at: "2030-01-01T12:00:00Z" } } });
  });

  await mockIdentify(page, ids.person);
  await page.goto(`/atendimento?pessoa=${ids.person}&verificacao=${ids.verification}`);
  await expect(page.getByLabel("Prazo de devolução")).toHaveCount(0);
  await page.getByRole("combobox", { name: /^Modalidade/ }).selectOption("fixed_term");
  await page.getByLabel("Prazo de devolução").fill("2030-01-01T09:00");
  await addRegistered(page, "ARMA-001");
  await page.getByText("Confirmo pessoa, materiais e modalidade.").click();
  await page.getByRole("button", { name: "Confirmar retirada" }).click();
  await expect(page.getByRole("alert")).toContainText("O prazo deve estar no futuro.");
  // A verificação continua valendo: a nova tentativa a reutiliza sem nova captura.
  await expect(page.getByRole("region", { name: "Pessoa identificada" })).toContainText("Identidade confirmada por reconhecimento facial.");
  await page.getByRole("button", { name: "Confirmar retirada" }).click();
  await expect(page.getByText(/Comprovante AT-PRAZO/)).toBeVisible();
  expect(baskets[1]).toMatchObject({ custody_mode: "fixed_term", face_verification_id: ids.verification });

  // Concluída a retirada, o balcão volta à identificação da próxima pessoa.
  await expect(page.getByRole("region", { name: "Identificação" })).toBeVisible();
  expect(page.url()).not.toContain("pessoa=");
});

test("operador não registra a própria retirada: outro operador precisa atender", async ({ page }) => {
  await session(page);
  await page.route("**/api/v1/overview/", (route) => route.fulfill({ json: { success: true, data: emptyOverview } }));
  await page.route("**/api/v1/counter/identify/**", (route) => route.fulfill({ json: { success: true, data: { ...identified, own: true, operations: { checkout: false, return: false } } } }));
  await page.route("**/api/v1/face-verifications/", () => { throw new Error("nenhuma verificação pode ser enviada"); });
  await page.goto("/");
  await page.getByRole("button", { name: "Entrada e saída" }).click();
  const entry = page.getByRole("region", { name: "Entrada e saída" });
  await entry.getByLabel("Matrícula de quem retira ou devolve").fill("MAT-1");
  await entry.getByRole("button", { name: "Identificar" }).click();
  await expect(entry.getByRole("alert")).toContainText("peça a outro operador");
  await expect(entry.getByRole("button", { name: "Reconhecer rosto" })).toHaveCount(0);
});
