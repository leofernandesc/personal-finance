import { describe, expect, it } from "vitest";
import { normalizeMoneyInput, percent } from "./utils";

describe("normalizeMoneyInput", () => {
  it.each([
    ["42", "42"],
    ["42,50", "42.50"],
    ["42.50", "42.50"],
    ["1.234,56", "1234.56"],
    ["1,234.56", "1234.56"],
    ["R$ 2.500,00", "2500.00"],
    ["-25,90", "-25.90"],
  ])("normaliza %s sem alterar a ordem de grandeza", (input, expected) => {
    expect(normalizeMoneyInput(input)).toBe(expected);
  });

  it.each(["", "abc", "12,3456", "1.2.3,45"])("rejeita o valor ambíguo %s", (input) => {
    expect(normalizeMoneyInput(input)).toBeNull();
  });
});

describe("percent", () => {
  it("preserva estouros de orçamento em vez de escondê-los em 100%", () => {
    expect(percent(125.5)).toBe("125,5%");
  });

  it("não exibe percentual negativo", () => {
    expect(percent(-5)).toBe("0%");
  });
});
