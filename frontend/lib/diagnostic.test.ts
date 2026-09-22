import { describe, expect, it } from "vitest";
import {
  answersFromForm,
  birthDateToIso,
  diagnosticDefaults,
  diagnosticSchema,
  formatBirthDateForInput,
  hasValue,
  maskBrazilianDateInput,
  normalizeDiagnosticValues,
  sectionRequiredFields,
  visibleDiagnosticSections,
  valuesFromDiagnostic,
} from "./diagnostic";

describe("diagnosticSchema", () => {
  it("aceita rascunho vazio e valida dinheiro quando informado", () => {
    expect(diagnosticSchema.safeParse(diagnosticDefaults).success).toBe(true);
    expect(diagnosticSchema.safeParse({ ...diagnosticDefaults, monthly_net_income: "12,50" }).success).toBe(true);
    expect(diagnosticSchema.safeParse({ ...diagnosticDefaults, monthly_net_income: "12,3456" }).success).toBe(false);
  });

  it("exige detalhes de dívida quando a pessoa informa que possui dívidas", () => {
    const result = diagnosticSchema.safeParse({ ...diagnosticDefaults, has_debts: "yes" });
    expect(result.success).toBe(false);
  });

  it("mantém a renda familiar como campo obrigatório da etapa de renda", () => {
    expect(sectionRequiredFields[4]).toContain("family_monthly_net_income");
  });

  it("exige detalhes de outra prioridade", () => {
    const missingOther = diagnosticSchema.safeParse({
      ...diagnosticDefaults,
      financial_priority: "other",
    });
    expect(missingOther.success).toBe(false);
  });

  it("valida data brasileira, datas reais e datas futuras", () => {
    expect(diagnosticSchema.safeParse({ ...diagnosticDefaults, birth_date: "29/02/2000" }).success).toBe(true);
    expect(diagnosticSchema.safeParse({ ...diagnosticDefaults, birth_date: "31/02/2000" }).success).toBe(false);
    expect(diagnosticSchema.safeParse({ ...diagnosticDefaults, birth_date: "2000-02-29" }).success).toBe(true);
    expect(diagnosticSchema.safeParse({ ...diagnosticDefaults, birth_date: "29/02/00" }).success).toBe(false);

    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const futureDate = `${String(tomorrow.getDate()).padStart(2, "0")}/${String(tomorrow.getMonth() + 1).padStart(2, "0")}/${tomorrow.getFullYear()}`;
    expect(diagnosticSchema.safeParse({ ...diagnosticDefaults, birth_date: futureDate }).success).toBe(false);
  });
});

describe("diagnostic helpers", () => {
  it("remove consentimentos do payload de respostas", () => {
    const answers = answersFromForm({ ...diagnosticDefaults, consent_data_processing: true });
    expect(answers).not.toHaveProperty("consent_data_processing");
  });

  it("mantém a data brasileira na edição e envia ISO para a API", () => {
    expect(formatBirthDateForInput("1990-05-10")).toBe("10/05/1990");
    expect(valuesFromDiagnostic({ birth_date: "1990-05-10" }).birth_date).toBe("10/05/1990");
    expect(answersFromForm({ ...diagnosticDefaults, birth_date: "10/05/1990" }).birth_date).toBe("1990-05-10");
    expect(answersFromForm({ ...diagnosticDefaults, birth_date: "10/05/" }).birth_date).toBeNull();
  });

  it("aplica máscara brasileira progressiva sem exceder oito dígitos", () => {
    expect(maskBrazilianDateInput("10051990")).toBe("10/05/1990");
    expect(maskBrazilianDateInput("10/05/1990abc")).toBe("10/05/1990");
    expect(maskBrazilianDateInput("1")).toBe("1");
  });

  it("converte a data brasileira para ISO somente quando ela é válida", () => {
    expect(birthDateToIso("10/05/1990")).toBe("1990-05-10");
    expect(birthDateToIso("31/04/1990")).toBeNull();
  });

  it("considera zero uma resposta válida e texto vazio uma ausência", () => {
    expect(hasValue(0)).toBe(true);
    expect(hasValue("")).toBe(false);
    expect(hasValue([])).toBe(false);
  });

  it("remove respostas que deixam de ser aplicáveis", () => {
    const normalized = normalizeDiagnosticValues({
      ...diagnosticDefaults,
      has_debts: "no",
      total_debt_amount: "1000",
      extra_income: "no",
      extra_income_details: "Renda antiga",
      credit_card_count: "0",
      average_card_bill: "300",
      has_goal_savings: "no",
      goal_saved_amount: "500",
    });
    expect(normalized).not.toHaveProperty("total_debt_amount");
    expect(normalized).not.toHaveProperty("extra_income_details");
    expect(normalized).not.toHaveProperty("average_card_bill");
    expect(normalized).not.toHaveProperty("goal_saved_amount");
  });

  it("oculta a etapa de dívidas quando a resposta é negativa", () => {
    expect(visibleDiagnosticSections("no")).not.toContain(8);
    expect(visibleDiagnosticSections("yes")).toContain(8);
  });
});
