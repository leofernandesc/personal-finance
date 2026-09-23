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
      const menuButton = page.getByRole("button", { name: "Abrir menu" });
      await menuButton.click();
      const dialog = page.getByRole("dialog", { name: "Menu de navegação" });
      await expect(dialog).toBeVisible();
      const menuLinks = dialog.getByRole("link");
      const closeButton = dialog.getByRole("button", { name: "Fechar menu" });
      await expect(menuLinks.first()).toBeFocused();
      await page.keyboard.press("Shift+Tab");
      await expect(closeButton).toBeFocused();
      await page.keyboard.press("Tab");
      await expect(menuLinks.first()).toBeFocused();
    }
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
    expect(results.violations, `violações encontradas em ${route}`).toEqual([]);
    if (test.info().project.name === "mobile-firefox") {
      const menuButton = page.getByRole("button", { name: "Abrir menu" });
      const dialog = page.getByRole("dialog", { name: "Menu de navegação" });
      await page.keyboard.press("Escape");
      await expect(dialog).toBeHidden();
      await expect(menuButton).toBeFocused();
      expect(await page.evaluate(() => document.querySelector("#mobile-navigation-dialog")?.contains(document.activeElement))).toBe(false);
    }
  }
});
