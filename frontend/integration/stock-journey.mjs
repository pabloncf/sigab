// Executed by pytest against its live Django server and disposable test database.
import { chromium, expect } from "@playwright/test";

const { origin, username, password, person, kind, unit, location } = JSON.parse(process.env.SIGAB_BROWSER_FIXTURE);
const browser = await chromium.launch({ headless: true });
try {
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto(`${origin}/entrar/`);
  await expect(page.locator('input[name="organization"]')).toHaveCount(0);
  await page.getByLabel("Matrícula ou usuário técnico").fill(username);
  await page.getByLabel("Senha", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).toHaveURL(`${origin}/`);
  await page.goto(`${origin}/estoque`);
  await page.getByRole("button", { name: "Registrar entrada" }).click();
  await page.getByLabel("Tipo de material").selectOption(kind);
  await page.getByLabel("Unidade de entrada").selectOption(unit);
  await page.getByLabel("Local de guarda").selectOption(location);
  await page.getByLabel("Quantidade", { exact: true }).fill("100");
  await page.getByLabel("Referência ou justificativa da entrada").fill("Aquisição sintética");
  await page.getByRole("button", { name: "Revisar operação" }).click();
  await page.getByText("Conferi material, quantidade, destino e justificativa desta operação.").click();
  await page.getByRole("button", { name: "Confirmar operação" }).click();
  await expect(page.getByText("Disponível: 100.000", { exact: true })).toBeVisible();

  let lost = false;
  const attempts = [];
  await page.route("**/api/v1/service-batches/", async (route) => {
    attempts.push(route.request().postDataJSON());
    const response = await route.fetch(); // This is the real Django transaction.
    if (!lost) {
      expect(response.status()).toBe(201);
      lost = true;
      await route.abort("failed");
    } else await route.fulfill({ response });
  });
  await page.goto(`${origin}/atendimento`);
  await page.getByLabel("Pessoa destinatária").selectOption(person);
  await page.getByLabel(/Munição integração.*saldo 100/).fill("50");
  await page.getByText("Confirmo destinatário, itens e modalidade.").click();
  await page.getByRole("button", { name: "Confirmar atendimento" }).click();
  await expect(page.getByRole("button", { name: "Verificar atendimento" })).toBeEnabled();
  await page.reload();
  await page.getByRole("button", { name: "Verificar atendimento" }).click();
  await expect(page.getByText(/Atendimento confirmado. Comprovante/)).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
  expect(attempts).toHaveLength(2);
  expect(attempts[0]).toEqual(attempts[1]);

  await page.goto(`${origin}/estoque`);
  for (const [button, quantity, reason, remaining] of [
    ["Devolver apto", "20", "", "30.000"],
    ["Justificar consumo", "10", "Treinamento sintético", "20.000"]
  ]) {
    await page.getByRole("button", { name: button }).click();
    await page.getByLabel("Quantidade", { exact: true }).fill(quantity);
    if (reason) await page.getByLabel("Justificativa do consumo").fill(reason);
    await page.getByRole("button", { name: "Revisar operação" }).click();
    await page.getByText("Conferi material, quantidade, destino e justificativa desta operação.").click();
    await page.getByRole("button", { name: "Confirmar operação" }).click();
    await expect(page.getByText(`Em aberto: ${remaining}`, { exact: true })).toBeVisible();
  }
  await expect(page.getByText("Disponível: 70.000", { exact: true })).toBeVisible();
  console.log("Jornada React/Django/PostgreSQL: entrada, resposta perdida, recarga, reenvio, devolução e consumo aprovados.");
} finally {
  await browser.close();
}
