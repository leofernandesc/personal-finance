import { describe, expect, it } from "vitest";
import {
  answersFromForm,
  diagnosticDefaults,
  diagnosticSchema,
  hasValue,
  normalizeDiagnosticValues,
  sectionRequiredFields,
  visibleDiagnosticSections,
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
});

describe("diagnostic helpers", () => {
  it("remove consentimentos do payload de respostas", () => {
    const answers = answersFromForm({ ...diagnosticDefaults, consent_data_processing: true });
    expect(answers).not.toHaveProperty("consent_data_processing");
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
