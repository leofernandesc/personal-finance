import { expect, test, type Page } from "@playwright/test";

function uniqueEmail() {
  return `e2e-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`;
}

async function register(page: Page) {
  await page.goto("/register");
  await page.getByLabel("Como podemos chamar você?", { exact: true }).fill("Usuário E2E");
  await page.getByLabel("E-mail", { exact: true }).fill(uniqueEmail());
  await page.getByLabel("Senha", { exact: true }).fill("e2e-password-123");

  await page.getByLabel("Confirme sua senha", { exact: true }).fill("senha-diferente-123");
  await page.getByRole("button", { name: "Criar minha conta" }).click();
  await expect(page.getByText("As senhas não coincidem.", { exact: true })).toBeVisible();

  const password = page.getByLabel("Senha", { exact: true });
  await page.getByRole("button", { name: "Mostrar a senha", exact: true }).click();
  await expect(password).toHaveAttribute("type", "text");
  await page.getByRole("button", { name: "Ocultar a senha", exact: true }).click();
  await expect(password).toHaveAttribute("type", "password");

  await page.getByLabel("Confirme sua senha", { exact: true }).fill("e2e-password-123");
  await page.getByRole("button", { name: "Criar minha conta" }).click();
  await expect(page).toHaveURL(/\/diagnostico/);
  await expect(page.getByRole("heading", { name: "Diagnóstico financeiro" }).first()).toBeVisible();
  await expect(page.getByText(/Etapa 1 de 13/)).toBeVisible();
  await page.getByRole("checkbox").nth(0).check();
  await page.getByRole("checkbox").nth(1).check();
  await page.getByRole("button", { name: "Próxima etapa" }).click();
  await expect(page.getByText(/Etapa 2 de 13/)).toBeVisible();

  if (test.info().project.name === "mobile-firefox") {
    const visitedSteps = page.getByLabel("Ir para uma etapa já visitada");
    await visitedSteps.selectOption("1");
    await expect(page.getByText(/Etapa 1 de 13/)).toBeVisible();
    await expect(page.getByRole("checkbox").nth(0)).toBeChecked();
    await expect(page.getByRole("checkbox").nth(1)).toBeChecked();
    await visitedSteps.selectOption("2");
  } else {
    await page.getByRole("button", { name: "Consentimento e privacidade" }).click();
    await expect(page.getByText(/Etapa 1 de 13/)).toBeVisible();
    await expect(page.getByRole("checkbox").nth(0)).toBeChecked();
    await expect(page.getByRole("checkbox").nth(1)).toBeChecked();
    await page.getByRole("button", { name: "Identificação" }).click();
  }
  await expect(page.getByText(/Etapa 2 de 13/)).toBeVisible();

  await page.getByRole("button", { name: "Salvar e continuar depois" }).click();
  await page.reload();
  await expect(page.getByText(/Etapa 2 de 13/)).toBeVisible();
}

function transactionFixture(id: number, description: string, amount: string) {
  return {
    id: `00000000-0000-4000-8000-${String(id).padStart(12, "0")}`,
    account_id: "00000000-0000-4000-8000-000000000100",
    category_id: "00000000-0000-4000-8000-000000000200",
    transfer_id: null,
    transfer_leg: null,
    type: "expense",
    description,
    amount,
    transaction_date: "2026-09-22",
    source: "web",
    created_at: "2026-09-22T12:00:00Z",
    account_name: "Conta E2E",
    category_name: "Alimentação",
  };
}

test("completa o fluxo financeiro essencial no desktop e no mobile", async ({ page }) => {
  test.setTimeout(90_000);
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

test("preserva a primeira página e permite repetir a próxima após uma falha", async ({ page }) => {
  await register(page);
  const firstPage = [
    transactionFixture(1, "Página 1 — almoço", "12.00"),
    transactionFixture(2, "Página 1 — mercado", "28.00"),
  ];
  const secondPage = [
    transactionFixture(3, "Página 2 — café", "8.00"),
    transactionFixture(4, "Página 2 — ônibus", "5.00"),
  ];
  let secondPageAttempts = 0;
  await page.route("**/api/v1/transactions*", async (route) => {
    if (route.request().method() !== "GET") {
      await route.continue();
      return;
    }
    const url = new URL(route.request().url());
    const headers = {
      "access-control-allow-origin": new URL(page.url()).origin,
      "access-control-allow-credentials": "true",
      "access-control-expose-headers": "X-Next-Cursor",
    };
    if (!url.searchParams.has("cursor")) {
      await route.fulfill({
        json: firstPage,
        headers: { ...headers, "x-next-cursor": "cursor-page-two" },
      });
      return;
    }
    secondPageAttempts += 1;
    if (secondPageAttempts === 1) {
      await route.fulfill({
        status: 503,
        json: { detail: "Falha de paginação simulada." },
        headers,
      });
      return;
    }
    await route.fulfill({ json: secondPage, headers });
  });

  await page.goto("/transactions");
  await expect(page.getByText("Página 1 — almoço", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Carregar mais movimentos" })).toBeVisible();
  await page.getByRole("button", { name: "Carregar mais movimentos" }).click();
  await expect(page.getByText("Falha de paginação simulada.", { exact: true })).toBeVisible();
  await expect(page.getByText("Página 1 — almoço", { exact: true })).toBeVisible();
  await expect(page.getByText("Página 1 — mercado", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Tentar carregar novamente" }).click();
  await expect(page.getByText("Página 1 — mercado", { exact: true })).toHaveCount(1);
  await expect(page.getByText("Página 2 — café", { exact: true })).toBeVisible();
  await expect(page.getByText("Página 2 — ônibus", { exact: true })).toBeVisible();
  await expect(page.getByText(/4 movimentos exibidos/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Carregar mais movimentos" })).toHaveCount(0);
  await expect(page.getByText("Página 1 — almoço", { exact: true })).toHaveCount(1);
});
