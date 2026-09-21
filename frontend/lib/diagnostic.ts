import { z } from "zod";
import { normalizeMoneyInput } from "./utils";

const optionalText = (max = 3000) => z.string().max(max).optional();
const optionalMoney = z.string().max(30).optional().refine((value) => {
  if (!value) return true;
  const normalized = normalizeMoneyInput(value);
  return normalized !== null && !normalized.startsWith("-");
}, "Informe um valor válido, com no máximo duas casas decimais.");
const optionalInteger = z.string().max(4).optional().refine((value) => {
  if (!value) return true;
  return /^\d+$/.test(value);
}, "Informe somente números inteiros.");
const optionalDate = z.string().optional().refine((value) => {
  if (!value) return true;
  const parsed = new Date(`${value}T00:00:00`);
  return !Number.isNaN(parsed.getTime()) && parsed <= new Date();
}, "Informe uma data válida que não esteja no futuro.");
const choices = () => z.array(z.string()).optional();

export const diagnosticSchema = z.object({
  consent_data_processing: z.boolean().optional(),
  consent_service_disclaimer: z.boolean().optional(),

  full_name: optionalText(120),
  birth_date: optionalDate,
  contact_email: z.string().email("Digite um e-mail válido.").or(z.literal("")).optional(),
  phone: optionalText(40),
  city_state: optionalText(160),
  occupation: optionalText(160),
  marital_status: optionalText(40),
  organization_type: optionalText(40),
  financial_dependents: optionalInteger,

  main_difficulties: choices(),
  main_difficulties_other: optionalText(240),
  financial_priority: optionalText(40),
  financial_priority_other: optionalText(240),
  expected_result: optionalText(2000),
  improvement_timeline: optionalText(40),
  financial_organization_score: optionalText(2),
  organization_barriers: choices(),
  organization_barriers_other: optionalText(240),

  monthly_net_income: optionalMoney,
  family_monthly_net_income: optionalMoney,
  income_type: optionalText(40),
  income_sources: choices(),
  income_sources_other: optionalText(240),
  extra_income: optionalText(40),
  extra_income_details: optionalText(1000),
  income_sufficiency: optionalText(40),

  tracks_expenses: optionalText(40),
  current_tool: choices(),
  current_tool_other: optionalText(240),
  monthly_expenses: optionalMoney,
  largest_expense_categories: choices(),
  largest_expense_categories_other: optionalText(240),
  overspending_frequency: optionalText(40),
  unexpected_expense_strategy: optionalText(40),
  unexpected_expense_other: optionalText(240),
  seasonal_expenses: choices(),
  seasonal_expenses_other: optionalText(240),

  bank_account_count: optionalInteger,
  credit_card_count: optionalInteger,
  total_card_limit: optionalMoney,
  average_card_bill: optionalMoney,
  pays_card_in_full: optionalText(40),
  knows_installments: optionalText(40),
  uses_overdraft: optionalText(40),

  has_debts: optionalText(10),
  debt_types: choices(),
  debt_types_other: optionalText(240),
  total_debt_amount: optionalMoney,
  monthly_debt_installments: optionalMoney,
  has_overdue_debt: optionalText(20),
  has_negative_record: optionalText(20),
  main_debts_details: optionalText(3000),
  tried_debt_negotiation: optionalText(40),

  has_reserve: optionalText(40),
  reserve_amount: optionalMoney,
  reserve_months: optionalText(40),
  can_save_monthly: optionalText(40),
  average_monthly_saving: optionalMoney,
  assets: choices(),
  total_net_worth: optionalMoney,
  assets_other: optionalText(240),

  financial_goals: choices(),
  financial_goals_other: optionalText(240),
  most_important_goal: optionalText(240),
  goal_amount: optionalMoney,
  goal_timeline: optionalText(40),
  has_goal_savings: optionalText(20),
  goal_saved_amount: optionalMoney,

  impulse_purchase_frequency: optionalText(40),
  money_conversations: optionalText(40),
  willing_to_track_expenses: optionalText(40),
  possible_changes: choices(),
  possible_changes_other: optionalText(240),

  available_documents: choices(),
  available_documents_other: optionalText(240),
  document_delivery_preference: optionalText(40),
  document_delivery_other: optionalText(240),
  meeting_availability: choices(),
  meeting_preference: optionalText(40),
  additional_information: optionalText(3000),
  how_found_service: optionalText(40),
  how_found_service_other: optionalText(240),
}).superRefine((values, context) => {
  if (values.financial_organization_score && !["1", "2", "3", "4", "5"].includes(values.financial_organization_score)) {
    context.addIssue({ code: "custom", path: ["financial_organization_score"], message: "Escolha uma nota de 1 a 5." });
  }
  if (values.has_debts === "yes" && !values.debt_types?.length) {
    context.addIssue({ code: "custom", path: ["debt_types"], message: "Selecione pelo menos um tipo de dívida." });
  }
  if (values.has_debts === "yes" && !values.total_debt_amount) {
    context.addIssue({ code: "custom", path: ["total_debt_amount"], message: "Informe o valor aproximado das dívidas." });
  }
});

export type DiagnosticFormValues = z.infer<typeof diagnosticSchema>;

export const diagnosticDefaults: DiagnosticFormValues = {
  consent_data_processing: false,
  consent_service_disclaimer: false,
  main_difficulties: [],
  organization_barriers: [],
  income_sources: [],
  current_tool: [],
  largest_expense_categories: [],
  seasonal_expenses: [],
  debt_types: [],
  assets: [],
  financial_goals: [],
  possible_changes: [],
  available_documents: [],
  meeting_availability: [],
};

export type DiagnosticField = keyof DiagnosticFormValues;

export type Option = { value: string; label: string };

export const options: Record<string, Option[]> = {
  marital_status: [
    { value: "single", label: "Solteiro(a)" },
    { value: "married", label: "Casado(a)" },
    { value: "stable_union", label: "União estável" },
    { value: "separated_divorced", label: "Separado(a) ou divorciado(a)" },
    { value: "widowed", label: "Viúvo(a)" },
    { value: "prefer_not_to_say", label: "Prefiro não informar" },
  ],
  organization_type: [
    { value: "individual", label: "Individual" },
    { value: "couple", label: "Do casal" },
    { value: "family", label: "Familiar" },
  ],
  improvement_timeline: [
    { value: "up_to_3_months", label: "Até 3 meses" },
    { value: "four_to_six_months", label: "De 4 a 6 meses" },
    { value: "seven_to_twelve_months", label: "De 7 a 12 meses" },
    { value: "over_twelve_months", label: "Mais de 12 meses" },
    { value: "not_sure", label: "Ainda não sei" },
  ],
  income_type: [
    { value: "fixed", label: "Fixa" },
    { value: "variable", label: "Variável" },
    { value: "mixed", label: "Parcialmente fixa e parcialmente variável" },
    { value: "no_income", label: "Não possuo renda atualmente" },
  ],
  extra_income: [
    { value: "monthly", label: "Sim, mensalmente" },
    { value: "occasionally", label: "Sim, ocasionalmente" },
    { value: "no", label: "Não" },
  ],
  income_sufficiency: [
    { value: "surplus", label: "Sim, e ainda sobra dinheiro" },
    { value: "break_even", label: "Sim, mas não sobra dinheiro" },
    { value: "not_always", label: "Nem sempre" },
    { value: "insufficient", label: "Não" },
  ],
  tracks_expenses: [
    { value: "all", label: "Sim, registro todas" },
    { value: "some", label: "Registro somente algumas" },
    { value: "tried", label: "Já tentei, mas não consegui manter" },
    { value: "none", label: "Não registro" },
  ],
  overspending_frequency: [
    { value: "frequently", label: "Frequentemente" },
    { value: "sometimes", label: "Algumas vezes" },
    { value: "rarely", label: "Raramente" },
    { value: "never", label: "Nunca" },
    { value: "no_plan", label: "Não faço planejamento" },
  ],
  unexpected_expense_strategy: [
    { value: "reserve", label: "Utiliza sua reserva" },
    { value: "reduce_other_expenses", label: "Reduz outros gastos" },
    { value: "credit_card", label: "Utiliza o cartão de crédito" },
    { value: "overdraft", label: "Utiliza o cheque especial" },
    { value: "loan", label: "Faz um empréstimo" },
    { value: "borrow", label: "Pede dinheiro emprestado" },
    { value: "delay_bill", label: "Atrasa outra conta" },
    { value: "other", label: "Outro" },
  ],
  pays_card_in_full: [
    { value: "always", label: "Sempre" },
    { value: "most_months", label: "Na maioria dos meses" },
    { value: "sometimes", label: "Às vezes" },
    { value: "rarely", label: "Raramente" },
    { value: "minimum_or_installments", label: "Pago o mínimo ou parcelo a fatura" },
    { value: "no_credit_card", label: "Não utilizo cartão de crédito" },
  ],
  knows_installments: [
    { value: "yes", label: "Sim" },
    { value: "most", label: "Conheço a maioria" },
    { value: "no", label: "Não" },
    { value: "no_installments", label: "Não possuo compras parceladas" },
  ],
  uses_overdraft: [
    { value: "frequently", label: "Frequentemente" },
    { value: "sometimes", label: "Algumas vezes" },
    { value: "rarely", label: "Raramente" },
    { value: "never", label: "Nunca" },
  ],
  has_debts: [{ value: "yes", label: "Sim" }, { value: "no", label: "Não" }],
  has_overdue_debt: [{ value: "yes", label: "Sim" }, { value: "no", label: "Não" }, { value: "unknown", label: "Não sei informar" }],
  has_negative_record: [{ value: "yes", label: "Sim" }, { value: "no", label: "Não" }, { value: "unknown", label: "Não sei informar" }],
  tried_debt_negotiation: [
    { value: "agreement", label: "Sim, e consegui um acordo" },
    { value: "not_completed", label: "Sim, mas não consegui concluir" },
    { value: "not_tried", label: "Ainda não tentei" },
    { value: "not_applicable", label: "Não se aplica" },
  ],
  has_reserve: [
    { value: "yes", label: "Sim" },
    { value: "unorganized", label: "Possuo algum dinheiro guardado, mas sem organização" },
    { value: "no", label: "Não" },
  ],
  reserve_months: [
    { value: "less_than_1", label: "Menos de 1 mês" },
    { value: "one_to_three", label: "De 1 a 3 meses" },
    { value: "four_to_six", label: "De 4 a 6 meses" },
    { value: "over_six", label: "Mais de 6 meses" },
    { value: "unknown", label: "Não sei calcular" },
    { value: "none", label: "Não possuo reserva" },
  ],
  can_save_monthly: [
    { value: "every_month", label: "Sim, todos os meses" },
    { value: "undefined_amount", label: "Sim, mas sem valor definido" },
    { value: "some_months", label: "Somente em alguns meses" },
    { value: "no", label: "Não" },
  ],
  goal_timeline: [
    { value: "up_to_6_months", label: "Até 6 meses" },
    { value: "seven_to_twelve_months", label: "De 7 a 12 meses" },
    { value: "one_to_two_years", label: "De 1 a 2 anos" },
    { value: "three_to_five_years", label: "De 3 a 5 anos" },
    { value: "over_five_years", label: "Mais de 5 anos" },
    { value: "not_defined", label: "Ainda não defini" },
  ],
  has_goal_savings: [{ value: "yes", label: "Sim" }, { value: "no", label: "Não" }],
  impulse_purchase_frequency: [
    { value: "frequently", label: "Frequentemente" },
    { value: "sometimes", label: "Algumas vezes" },
    { value: "rarely", label: "Raramente" },
    { value: "never", label: "Nunca" },
  ],
  money_conversations: [
    { value: "calmly", label: "Sim, com tranquilidade" },
    { value: "conflicts", label: "Sim, mas normalmente gera conflitos" },
    { value: "rarely", label: "Raramente" },
    { value: "no", label: "Não" },
    { value: "not_applicable", label: "Não se aplica" },
  ],
  willing_to_track_expenses: [
    { value: "yes", label: "Sim" },
    { value: "with_guidance", label: "Sim, mas precisarei de orientação" },
    { value: "will_try", label: "Tenho dificuldade, mas posso tentar" },
    { value: "no", label: "Não" },
  ],
  document_delivery_preference: [
    { value: "shared_folder", label: "Link de pasta compartilhada" },
    { value: "email", label: "E-mail" },
    { value: "meeting", label: "Entrega durante a reunião" },
    { value: "other", label: "Outra forma combinada" },
  ],
  meeting_preference: [
    { value: "online", label: "On-line" },
    { value: "in_person", label: "Presencial" },
    { value: "no_preference", label: "Sem preferência" },
  ],
  how_found_service: [
    { value: "referral", label: "Indicação" },
    { value: "instagram", label: "Instagram" },
    { value: "whatsapp", label: "WhatsApp" },
    { value: "facebook", label: "Facebook" },
    { value: "internet", label: "Pesquisa na internet" },
    { value: "event", label: "Evento" },
    { value: "other", label: "Outro" },
  ],
};

export const multiOptions: Record<string, Option[]> = {
  main_difficulties: [
    ["no_control", "Não consigo controlar meus gastos"],
    ["dont_know", "Não sei para onde meu dinheiro está indo"],
    ["spend_more", "Gasto mais do que recebo"],
    ["debts", "Tenho dívidas"],
    ["late_bills", "Tenho dificuldade para pagar as contas em dia"],
    ["card_to_income", "Uso cartão de crédito para completar a renda"],
    ["variable_income", "Minha renda varia muito"],
    ["cannot_save", "Não consigo guardar dinheiro"],
    ["mix_personal_business", "Misturo dinheiro pessoal e empresarial"],
    ["family_organization", "Preciso organizar as finanças do casal ou da família"],
    ["goal", "Quero me preparar para uma meta"],
    ["other", "Outro"],
  ].map(([value, label]) => ({ value, label })),
  organization_barriers: [
    ["lack_of_planning", "Falta de planejamento"], ["lack_of_knowledge", "Falta de conhecimento"], ["lack_of_discipline", "Falta de disciplina"], ["insufficient_income", "Renda insuficiente"], ["variable_income", "Renda variável"], ["too_many_debts", "Excesso de dívidas"], ["unexpected_expenses", "Gastos inesperados"], ["impulse_purchases", "Compras por impulso"], ["family_participation", "Falta de participação do cônjuge ou da família"], ["lack_of_time", "Falta de tempo"], ["other", "Outro"],
  ].map(([value, label]) => ({ value, label })),
  income_sources: [
    ["salary", "Salário"], ["pro_labore", "Pró-labore"], ["self_employment", "Trabalho autônomo"], ["commissions", "Comissões"], ["sales", "Vendas"], ["retirement_or_pension", "Aposentadoria ou pensão"], ["rent", "Aluguel"], ["benefit", "Benefício"], ["family_help", "Ajuda familiar"], ["occasional_income", "Renda eventual"], ["other", "Outra"],
  ].map(([value, label]) => ({ value, label })),
  current_tool: [
    ["spreadsheet", "Planilha"], ["app", "Aplicativo"], ["notebook", "Caderno"], ["phone_notes", "Anotações no celular"], ["bank_statement", "Extrato bancário"], ["credit_card_bill", "Fatura do cartão"], ["none", "Não utilizo nenhuma ferramenta"], ["other", "Outra"],
  ].map(([value, label]) => ({ value, label })),
  largest_expense_categories: [
    ["housing", "Moradia"], ["food", "Alimentação"], ["transport", "Transporte"], ["health", "Saúde"], ["education", "Educação"], ["children_dependents", "Filhos ou dependentes"], ["leisure", "Lazer"], ["personal_shopping", "Compras pessoais"], ["subscriptions", "Assinaturas"], ["debts_loans", "Dívidas e empréstimos"], ["vehicle", "Veículo"], ["business_expenses", "Despesas empresariais"], ["other", "Outra"],
  ].map(([value, label]) => ({ value, label })),
  seasonal_expenses: [
    ["ipva", "IPVA"], ["iptu", "IPTU"], ["school", "Matrícula ou material escolar"], ["insurance", "Seguros"], ["vehicle_maintenance", "Manutenção de veículo"], ["income_tax", "Imposto de renda"], ["gifts_dates", "Presentes e datas comemorativas"], ["travel", "Viagens"], ["home_maintenance", "Manutenção residencial"], ["none_or_planned", "Não possuo ou já planejo essas despesas"], ["other", "Outra"],
  ].map(([value, label]) => ({ value, label })),
  debt_types: [
    ["credit_card", "Cartão de crédito"], ["overdraft", "Cheque especial"], ["personal_loan", "Empréstimo pessoal"], ["payroll_loan", "Empréstimo consignado"], ["vehicle_financing", "Financiamento de veículo"], ["home_financing", "Financiamento imobiliário"], ["family_friends", "Dívida com familiares ou amigos"], ["overdue_bills", "Contas atrasadas"], ["taxes", "Impostos"], ["business_debt", "Dívida empresarial"], ["other", "Outra"],
  ].map(([value, label]) => ({ value, label })),
  assets: [
    ["property", "Imóvel"], ["vehicle", "Veículo"], ["checking_balance", "Saldo em conta"], ["savings", "Poupança"], ["investments", "Investimentos"], ["private_pension", "Previdência privada"], ["company_participation", "Participação em empresa"], ["other_assets", "Outros bens"], ["no_relevant_assets", "Não possuo patrimônio relevante"], ["discuss_in_meeting", "Prefiro detalhar durante a reunião"],
  ].map(([value, label]) => ({ value, label })),
  financial_goals: [
    ["pay_debts", "Quitar dívidas"], ["emergency_fund", "Criar reserva de emergência"], ["buy_property", "Comprar um imóvel"], ["buy_vehicle", "Comprar ou trocar de veículo"], ["travel", "Fazer uma viagem"], ["study", "Estudar ou fazer uma especialização"], ["business", "Abrir ou investir em um negócio"], ["retirement", "Organizar a aposentadoria"], ["marriage_children", "Preparar-se para casamento ou filhos"], ["renovation", "Realizar uma reforma"], ["other", "Outra"],
  ].map(([value, label]) => ({ value, label })),
  possible_changes: [
    ["reduce_nonessential", "Reduzir gastos não essenciais"], ["set_limits", "Definir limites de consumo"], ["track_expenses", "Registrar despesas"], ["avoid_new_debts", "Evitar novas dívidas"], ["negotiate_debts", "Negociar dívidas existentes"], ["create_reserve", "Criar uma reserva"], ["talk_with_family", "Conversar sobre dinheiro com a família"], ["additional_income", "Buscar renda adicional"], ["not_sure", "Ainda não sei"], ["other", "Outra"],
  ].map(([value, label]) => ({ value, label })),
  available_documents: [
    ["bank_statements", "Extratos bancários dos últimos três meses"], ["credit_card_bills", "Faturas dos cartões dos últimos três meses"], ["income_proof", "Comprovantes de renda"], ["debt_list", "Relação de dívidas"], ["loan_contracts", "Contratos de empréstimos ou financiamentos"], ["installment_list", "Relação de compras parceladas"], ["current_spreadsheet", "Planilha ou controle financeiro atual"], ["need_to_organize", "Ainda preciso organizar os documentos"],
  ].map(([value, label]) => ({ value, label })),
  meeting_availability: [
    ["morning", "Manhã"], ["afternoon", "Tarde"], ["evening", "Noite"], ["saturday", "Sábado"],
  ].map(([value, label]) => ({ value, label })),
};

export const sectionRequiredFields: Record<number, DiagnosticField[]> = {
  1: ["consent_data_processing", "consent_service_disclaimer"],
  2: ["full_name", "birth_date", "contact_email", "phone", "city_state", "occupation", "financial_dependents"],
  3: ["main_difficulties", "financial_priority", "expected_result", "financial_organization_score", "organization_barriers"],
  4: ["monthly_net_income", "income_sources", "income_sufficiency"],
  5: ["tracks_expenses", "monthly_expenses", "largest_expense_categories"],
  6: ["credit_card_count"],
  7: ["has_debts"],
  8: ["debt_types", "total_debt_amount"],
  9: ["has_reserve"],
  10: ["financial_goals", "most_important_goal"],
  11: ["willing_to_track_expenses"],
  12: [],
  13: [],
};

export const sectionTitles = [
  "Consentimento e privacidade",
  "Identificação",
  "Objetivos e dificuldades",
  "Renda",
  "Despesas e controle",
  "Contas e cartões",
  "Dívidas",
  "Detalhamento das dívidas",
  "Reserva e patrimônio",
  "Metas financeiras",
  "Comportamento financeiro",
  "Documentos para análise",
  "Disponibilidade e observações",
];

export function valuesFromDiagnostic(answers: Record<string, unknown>): Partial<DiagnosticFormValues> {
  return Object.fromEntries(Object.entries(answers).map(([key, value]) => {
    if (Array.isArray(value)) return [key, value];
    if (typeof value === "number") return [key, String(value)];
    return [key, value ?? ""];
  })) as Partial<DiagnosticFormValues>;
}

export function answersFromForm(values: DiagnosticFormValues): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(values)
      .filter(([key]) => !key.startsWith("consent_"))
      .map(([key, value]) => [key, value === "" ? null : value]),
  );
}

export function hasValue(value: unknown): boolean {
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === "string") return value.trim().length > 0;
  return value !== null && value !== undefined;
}
