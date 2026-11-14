import type { Page } from "@playwright/test";

/** Identificação simulada pela matrícula (dados sintéticos). */
export async function mockIdentify(page: Page, id: string, overrides: Record<string, unknown> = {}) {
  await page.route("**/api/v1/counter/identify/**", (route) => route.fulfill({ json: { success: true, data: {
    id, name: "Pessoa teste", registration: "MAT-1", biometric_enrolled: true, open_possessions: 0, own: false,
    operations: { checkout: true, return: true }, ...overrides
  } } }));
}

export async function addRegistered(page: Page, code: string) {
  await page.getByLabel("Número do material (série ou patrimônio)").fill(code);
  await page.getByRole("button", { name: "Adicionar material com registro" }).click();
}

export async function addUnregistered(page: Page, name: string, quantity: string) {
  await page.getByLabel("Nome do material").fill(name);
  await page.getByLabel("Quantidade", { exact: true }).fill(quantity);
  await page.getByRole("button", { name: "Adicionar material sem registro" }).click();
}
