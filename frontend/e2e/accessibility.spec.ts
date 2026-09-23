import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

for (const route of ["/login", "/register"]) {
  test(`não cria violações WCAG conhecidas em ${route}`, async ({ page }) => {
    await page.goto(route);
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();

    expect(results.violations).toEqual([]);
  });
}

test("mantém dashboard e histórico acessíveis após autenticação", async ({ page }) => {
  await page.goto("/register");
  await page.getByLabel("Como podemos chamar você?", { exact: true }).fill("Acessibilidade E2E");
  await page.getByLabel("E-mail", { exact: true }).fill(
    `axe-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`,
  );
  await page.getByLabel("Senha", { exact: true }).fill("axe-accessibility-pass-123");
  await page.getByLabel("Confirme sua senha", { exact: true }).fill("axe-accessibility-pass-123");
  await page.getByRole("button", { name: "Criar minha conta" }).click();
  await expect(page).toHaveURL(/\/diagnostico/);

  for (const route of ["/dashboard", "/transactions"]) {
    await page.goto(route);
    if (route === "/dashboard") {
      await expect(page.getByText("Saldo total", { exact: true })).toBeVisible();
    } else {
      await expect(page.getByRole("heading", { name: "Transações", exact: true })).toBeVisible();
    }
    if (test.info().project.name === "mobile-firefox") {
      await page.getByRole("button", { name: "Abrir menu" }).click();
      await expect(page.getByRole("navigation", { name: "Navegação principal" })).toBeVisible();
    }
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
    expect(results.violations, `violações encontradas em ${route}`).toEqual([]);
  }
});
