import { describe, expect, it } from "vitest";
import {
  answersFromForm,
  diagnosticDefaults,
  diagnosticSchema,
  hasValue,
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
});
