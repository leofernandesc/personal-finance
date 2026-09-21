import { expect, test, type Page } from "@playwright/test";

function uniqueEmail() {
  return `e2e-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`;
}

async function register(page: Page) {
  await page.goto("/register");
  await page.getByLabel("Como podemos chamar você?", { exact: true }).fill("Usuário E2E");
  await page.getByLabel("E-mail", { exact: true }).fill(uniqueEmail());
  await page.getByLabel("Senha", { exact: true }).fill("e2e-password-123");
  await page.getByRole("button", { name: "Criar minha conta" }).click();
  await expect(page).toHaveURL(/\/diagnostico/);
  await expect(page.getByRole("heading", { name: "Diagnóstico financeiro" }).first()).toBeVisible();
  await expect(page.getByText(/Etapa 1 de 13/)).toBeVisible();
  await page.getByRole("checkbox").nth(0).check();
  await page.getByRole("checkbox").nth(1).check();
  await page.getByRole("button", { name: "Próxima etapa" }).click();
  await expect(page.getByText(/Etapa 2 de 13/)).toBeVisible();
  await page.getByRole("button", { name: "Salvar e continuar depois" }).click();
  await page.reload();
  await expect(page.getByText(/Etapa 2 de 13/)).toBeVisible();
}

test("completa o fluxo financeiro essencial no desktop e no mobile", async ({ page }) => {
  await register(page);

  await page.goto("/accounts");
  await page.getByRole("button", { name: "Nova conta" }).click();
  await page.getByLabel("Nome", { exact: true }).fill("Nubank E2E");
  await page.getByLabel("Saldo inicial", { exact: true }).fill("100,00");
  await page.getByRole("button", { name: "Criar conta" }).click();
  await expect(page.getByText("Nubank E2E", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Nova conta" }).click();
  await page.getByLabel("Nome", { exact: true }).fill("Inter E2E");
  await page.getByLabel("Saldo inicial", { exact: true }).fill("0,00");
  await page.getByRole("button", { name: "Criar conta" }).click();
  await expect(page.getByText("Inter E2E", { exact: true })).toBeVisible();

  await page.goto("/transactions");
  await page.getByRole("button", { name: "Nova transação" }).click();
  await page.getByLabel("Descrição", { exact: true }).fill("Almoço E2E");
  await page.getByLabel("Valor", { exact: true }).fill("42,00");
  await page.locator("#transaction-account").selectOption({ label: "Nubank E2E" });
  await page.locator("#transaction-category").selectOption({ label: "Alimentação" });
  await page.getByRole("button", { name: "Registrar movimento" }).click();
  await expect(page.getByText("Almoço E2E", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Transferir" }).click();
  await page.locator("#transfer-source").selectOption({ label: "Nubank E2E" });
  await page.locator("#transfer-destination").selectOption({ label: "Inter E2E" });
  await page.getByLabel("Descrição", { exact: true }).fill("Reserva E2E");
  await page.getByLabel("Valor", { exact: true }).fill("10,00");
  await page.getByRole("button", { name: "Realizar transferência" }).click();
  await expect(page.getByText("Reserva E2E", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Editar transferência" }).first().click();
  await page.locator("#transfer-description").fill("Reserva E2E editada");
  await page.locator("#transfer-amount").fill("12,00");
  await page.getByRole("button", { name: "Salvar alterações" }).click();
  await expect(page.getByText("Reserva E2E editada", { exact: true })).toBeVisible();

  await page.goto("/budgets");
  await page.getByRole("button", { name: "Novo orçamento" }).click();
  await page.getByLabel("Categoria", { exact: true }).selectOption({ label: "Alimentação" });
  await page.getByLabel("Limite", { exact: true }).fill("800,00");
  await page.getByRole("button", { name: "Criar limite" }).click();
  await expect(page.getByText("Alimentação", { exact: true })).toBeVisible();
  await expect(page.locator("body")).toContainText("800,00");

  await page.goto("/goals");
  await page.getByRole("button", { name: "Nova meta" }).click();
  await page.getByLabel("Nome da meta", { exact: true }).fill("Reserva E2E");
  await page.getByLabel("Valor alvo", { exact: true }).fill("1.000,00");
  await page.getByLabel("Já guardado", { exact: true }).fill("100,00");
  await page.getByRole("button", { name: "Criar meta" }).click();
  await expect(page.getByText("Reserva E2E", { exact: true })).toBeVisible();

  await page.goto("/dashboard");
  await expect(page.getByText("Saldo total", { exact: true })).toBeVisible();
  await expect(page.getByText("Almoço E2E", { exact: true })).toBeVisible();
  await expect(page.locator("body")).toContainText("R$ 58,00");

  if (test.info().project.name === "mobile-firefox") {
    await expect(page.getByRole("button", { name: "Abrir menu" })).toBeVisible();
    const dimensions = await page.evaluate(() => ({
      viewport: document.documentElement.clientWidth,
      content: document.documentElement.scrollWidth,
    }));
    expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport + 1);
  }
});
