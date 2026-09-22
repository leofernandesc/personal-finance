"use client";

import React from "react";
import { Check, ChevronLeft, ChevronRight, CircleHelp, Save, ShieldCheck } from "lucide-react";
import {
  Controller,
  type FieldErrors,
  type FieldPath,
  useForm,
  useWatch,
} from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ApiError, api } from "@/lib/api";
import type { Diagnostic, User } from "@/lib/types";
import {
  answersFromForm,
  diagnosticDefaults,
  diagnosticSchema,
  exclusiveDiagnosticChoices,
  hasValue,
  maskBrazilianDateInput,
  multiOptions,
  normalizeDiagnosticValues,
  options,
  requiredFieldsForSubmission,
  sectionRequiredFields,
  sectionTitles,
  type DiagnosticField,
  type DiagnosticFormValues,
  type Option,
  valuesFromDiagnostic,
  visibleDiagnosticSections,
} from "@/lib/diagnostic";
import { Button, Card, CardDescription, CardHeader, CardTitle, Input, Select } from "@/components/ui";

type DiagnosticFormProps = {
  user: User;
  diagnostic: Diagnostic;
};

const requiredForStep = (section: number, values: DiagnosticFormValues): DiagnosticField[] => {
  if (section === 8 && values.has_debts !== "yes") return [];
  return sectionRequiredFields[section] ?? [];
};

function messageFor(errors: FieldErrors<DiagnosticFormValues>, name: DiagnosticField) {
  const error = errors[name as keyof DiagnosticFormValues] as { message?: unknown } | undefined;
  return error && typeof error.message === "string" ? error.message : undefined;
}

function FieldLabel({ children, required = false }: { children: React.ReactNode; required?: boolean }) {
  return <label className="label">{children}{required && <span className="ml-1 text-rust" aria-hidden="true">*</span>}</label>;
}

function TextField({
  name,
  register,
  errors,
  label,
  required = false,
  type = "text",
  inputMode,
  placeholder,
  help,
}: {
  name: DiagnosticField;
  register: ReturnType<typeof useForm<DiagnosticFormValues>>["register"];
  errors: FieldErrors<DiagnosticFormValues>;
  label: string;
  required?: boolean;
  type?: string;
  inputMode?: React.InputHTMLAttributes<HTMLInputElement>["inputMode"];
  placeholder?: string;
  help?: string;
}) {
  const error = messageFor(errors, name);
  return <div>
    <FieldLabel required={required}>{label}</FieldLabel>
    <Input type={type} inputMode={inputMode} placeholder={placeholder} {...register(name)} aria-invalid={Boolean(error)} />
    {help && <p className="mt-1.5 text-xs leading-5 text-muted">{help}</p>}
    {error && <p className="mt-1.5 text-xs text-rust">{error}</p>}
  </div>;
}

function MoneyField(props: Omit<React.ComponentProps<typeof TextField>, "type">) {
  return <TextField {...props} type="text" placeholder="R$ 0,00" inputMode="decimal" />;
}

function BrazilianDateField({
  control,
  errors,
}: {
  control: ReturnType<typeof useForm<DiagnosticFormValues>>["control"];
  errors: FieldErrors<DiagnosticFormValues>;
}) {
  const error = messageFor(errors, "birth_date");
  return <Controller name="birth_date" control={control} render={({ field }) => <div>
    <label htmlFor="diagnostic-birth-date" className="label">Data de nascimento<span className="ml-1 text-rust" aria-hidden="true">*</span></label>
    <Input
      id="diagnostic-birth-date"
      type="text"
      inputMode="numeric"
      autoComplete="bday"
      maxLength={10}
      placeholder="DD/MM/AAAA"
      value={typeof field.value === "string" ? field.value : ""}
      onChange={(event) => field.onChange(maskBrazilianDateInput(event.target.value))}
      onBlur={field.onBlur}
      ref={field.ref}
      aria-invalid={Boolean(error)}
      aria-describedby={error ? "diagnostic-birth-date-help diagnostic-birth-date-error" : "diagnostic-birth-date-help"}
    />
    <p id="diagnostic-birth-date-help" className="mt-1.5 text-xs leading-5 text-muted">Use o formato dia/mês/ano.</p>
    {error && <p id="diagnostic-birth-date-error" className="mt-1.5 text-xs text-rust">{error}</p>}
  </div>} />;
}

function SelectField({
  name,
  register,
  errors,
  label,
  items,
  required = false,
  placeholder = "Selecione uma opção",
}: {
  name: DiagnosticField;
  register: ReturnType<typeof useForm<DiagnosticFormValues>>["register"];
  errors: FieldErrors<DiagnosticFormValues>;
  label: string;
  items: Option[];
  required?: boolean;
  placeholder?: string;
}) {
  const error = messageFor(errors, name);
  return <div>
    <FieldLabel required={required}>{label}</FieldLabel>
    <Select defaultValue="" {...register(name)} aria-invalid={Boolean(error)}>
      <option value="">{placeholder}</option>
      {items.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
    </Select>
    {error && <p className="mt-1.5 text-xs text-rust">{error}</p>}
  </div>;
}

function TextAreaField({
  name,
  register,
  errors,
  label,
  required = false,
  placeholder,
  help,
}: {
  name: DiagnosticField;
  register: ReturnType<typeof useForm<DiagnosticFormValues>>["register"];
  errors: FieldErrors<DiagnosticFormValues>;
  label: string;
  required?: boolean;
  placeholder?: string;
  help?: string;
}) {
  const error = messageFor(errors, name);
  return <div>
    <FieldLabel required={required}>{label}</FieldLabel>
    <textarea className="min-h-28 w-full resize-y rounded-xl border border-line bg-white px-3 py-3 text-sm text-ink placeholder:text-muted/70 focus:border-moss focus:outline-none focus:ring-2 focus:ring-mint" placeholder={placeholder} {...register(name)} aria-invalid={Boolean(error)} />
    {help && <p className="mt-1.5 text-xs leading-5 text-muted">{help}</p>}
    {error && <p className="mt-1.5 text-xs text-rust">{error}</p>}
  </div>;
}

function RadioGroup({
  name,
  register,
  errors,
  label,
  items,
  required = false,
}: {
  name: DiagnosticField;
  register: ReturnType<typeof useForm<DiagnosticFormValues>>["register"];
  errors: FieldErrors<DiagnosticFormValues>;
  label: string;
  items: Option[];
  required?: boolean;
}) {
  const error = messageFor(errors, name);
  return <fieldset>
    <legend className="label">{label}{required && <span className="ml-1 text-rust" aria-hidden="true">*</span>}</legend>
    <div className="grid gap-2 sm:grid-cols-2">
      {items.map((item) => <label key={item.value} className="flex cursor-pointer items-start gap-3 rounded-xl border border-line bg-white px-3 py-3 text-sm text-ink transition hover:border-brand-pink">
        <input type="radio" value={item.value} className="mt-0.5 h-4 w-4 accent-brand-brown" {...register(name)} />
        <span>{item.label}</span>
      </label>)}
    </div>
    {error && <p className="mt-1.5 text-xs text-rust">{error}</p>}
  </fieldset>;
}

function CheckboxGroup({
  name,
  control,
  label,
  items,
  required = false,
  exclusiveValues = [],
}: {
  name: DiagnosticField;
  control: ReturnType<typeof useForm<DiagnosticFormValues>>["control"];
  label: string;
  items: Option[];
  required?: boolean;
  exclusiveValues?: string[];
}) {
  return <Controller name={name} control={control} render={({ field, fieldState }) => {
    const selected = Array.isArray(field.value) ? field.value as string[] : [];
    return <fieldset>
      <legend className="label">{label}{required && <span className="ml-1 text-rust" aria-hidden="true">*</span>}</legend>
      <div className="grid gap-2 sm:grid-cols-2">
        {items.map((item) => {
          const checked = selected.includes(item.value);
          return <label key={item.value} className={`flex cursor-pointer items-start gap-3 rounded-xl border px-3 py-3 text-sm transition ${checked ? "border-brand-pink bg-brand-pink-soft text-brand-brown-dark" : "border-line bg-white text-ink hover:border-brand-pink"}`}>
            <input type="checkbox" checked={checked} onChange={() => {
              if (checked) field.onChange(selected.filter((value) => value !== item.value));
              else if (exclusiveValues.includes(item.value)) field.onChange([item.value]);
              else field.onChange([...selected.filter((value) => !exclusiveValues.includes(value)), item.value]);
            }} className="mt-0.5 h-4 w-4 rounded accent-brand-brown" />
            <span>{item.label}</span>
          </label>;
        })}
      </div>
      {fieldState.error?.message && <p className="mt-1.5 text-xs text-rust">{fieldState.error.message}</p>}
    </fieldset>;
  }} />;
}

function OtherField({
  values,
  name,
  otherName,
  register,
  errors,
  label = "Descreva a outra opção",
  triggerValue = "other",
}: {
  values: unknown;
  name: DiagnosticField;
  otherName: DiagnosticField;
  register: ReturnType<typeof useForm<DiagnosticFormValues>>["register"];
  errors: FieldErrors<DiagnosticFormValues>;
  label?: string;
  triggerValue?: string;
}) {
  const selected = Array.isArray(values) ? values.includes(triggerValue) : values === triggerValue;
  if (!selected) return null;
  return <div data-source-field={name}><TextField name={otherName} register={register} errors={errors} label={label} required placeholder="Conte um pouco mais" /></div>;
}

function SectionIntro({ title, description }: { title: string; description: string }) {
  return <div className="mb-6"><p className="eyebrow">Etapa do diagnóstico</p><h2 className="mt-2 font-display text-3xl tracking-[-0.035em] text-ink">{title}</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{description}</p></div>;
}

export function DiagnosticForm({ user, diagnostic }: DiagnosticFormProps) {
  const savedAnswers = valuesFromDiagnostic(diagnostic.answers);
  const form = useForm<DiagnosticFormValues>({
    resolver: zodResolver(diagnosticSchema),
    defaultValues: { ...diagnosticDefaults, full_name: user.full_name, contact_email: user.email, ...savedAnswers },
    mode: "onBlur",
  });
  const { control, register, handleSubmit, trigger, setError, clearErrors, formState: { errors, isSubmitting } } = form;
  const watchedValues = useWatch({ control });
  const hasDebts = watchedValues.has_debts;
  const visibleSections = React.useMemo(() => visibleDiagnosticSections(hasDebts), [hasDebts]);
  const initialSection = diagnostic.status === "completed" ? 1 : Math.min(Math.max(diagnostic.current_section, 1), 13);
  const [section, setSection] = React.useState(initialSection === 8 && hasDebts !== "yes" ? 7 : initialSection);
  const [busy, setBusy] = React.useState(false);
  const [notice, setNotice] = React.useState<string | null>(null);
  const currentIndex = visibleSections.indexOf(section);
  const currentVisibleIndex = currentIndex < 0 ? 0 : currentIndex;

  React.useEffect(() => {
    if (!visibleSections.includes(section)) setSection(hasDebts === "no" && section === 8 ? 7 : visibleSections[0]);
  }, [hasDebts, section, visibleSections]);

  const saveDraft = async (nextSection: number) => {
    setBusy(true);
    setNotice(null);
    try {
      await api.saveDiagnosticDraft({ current_section: nextSection, answers: answersFromForm(form.getValues()) });
      window.dispatchEvent(new Event("diagnostic-changed"));
      setNotice("Progresso salvo. Você pode continuar quando quiser.");
    } catch (reason) {
      setError("root", { message: reason instanceof ApiError ? reason.message : "Não foi possível salvar seu progresso." });
    } finally {
      setBusy(false);
    }
  };

  const validateSection = async () => {
    clearErrors("root");
    const values = form.getValues();
    if (section === 1 && (!values.consent_data_processing || !values.consent_service_disclaimer)) {
      setError("root", { message: "Leia e marque os dois consentimentos para continuar." });
      return false;
    }
    const requiredFields = requiredForStep(section, values);
    const missing = requiredFields.filter((field) => !hasValue(values[field]));
    if (missing.length) {
      setError("root", { message: "Preencha os campos obrigatórios desta etapa antes de continuar." });
      return false;
    }
    return trigger(requiredFields as FieldPath<DiagnosticFormValues>[]);
  };

  const next = async () => {
    if (!(await validateSection())) return;
    const nextSection = section === 7 && hasDebts === "no" ? 9 : visibleSections[currentVisibleIndex + 1];
    await saveDraft(nextSection ?? section);
    if (nextSection) setSection(nextSection);
  };

  const previous = () => {
    const previousSection = section === 9 && hasDebts === "no" ? 7 : visibleSections[currentVisibleIndex - 1];
    if (previousSection) setSection(previousSection);
  };

  const onSubmit = async (values: DiagnosticFormValues) => {
    setBusy(true);
    setNotice(null);
    clearErrors("root");
    try {
      const normalizedValues = normalizeDiagnosticValues(values) as DiagnosticFormValues;
      const missing = requiredFieldsForSubmission(normalizedValues).filter((field) => !hasValue(normalizedValues[field]));
      if (missing.length) {
        setError("root", { message: "Preencha os campos obrigatórios antes de enviar o diagnóstico." });
        setBusy(false);
        return;
      }
      await api.submitDiagnostic({
        answers: answersFromForm(normalizedValues),
        consent_data_processing: Boolean(normalizedValues.consent_data_processing),
        consent_service_disclaimer: Boolean(normalizedValues.consent_service_disclaimer),
      });
      window.dispatchEvent(new Event("diagnostic-changed"));
      setNotice("Diagnóstico enviado com sucesso. Você poderá editá-lo quando quiser.");
    } catch (reason) {
      setError("root", { message: reason instanceof ApiError ? reason.message : "Não foi possível enviar o diagnóstico." });
    } finally {
      setBusy(false);
    }
  };

  const renderSection = () => {
    const common = { register, errors, control };
    switch (section) {
      case 1:
        return <>
          <SectionIntro title="Um ponto de partida seguro" description="Estas duas confirmações explicam como suas respostas serão usadas e os limites do serviço." />
          <div className="space-y-3">
            <label className="flex cursor-pointer items-start gap-3 rounded-2xl border border-line bg-brand-pink-soft p-4 text-sm leading-6 text-ink"><input type="checkbox" className="mt-1 h-4 w-4 rounded accent-brand-brown" {...register("consent_data_processing")} /><span><strong>Consentimento para tratamento dos dados</strong><br />Declaro que forneço voluntariamente as informações deste formulário e autorizo sua utilização exclusivamente para a realização do Diagnóstico e Organização Financeira Pessoal.</span></label>
            <label className="flex cursor-pointer items-start gap-3 rounded-2xl border border-line bg-white p-4 text-sm leading-6 text-ink"><input type="checkbox" className="mt-1 h-4 w-4 rounded accent-brand-brown" {...register("consent_service_disclaimer")} /><span><strong>Declaração sobre o serviço</strong><br />Estou ciente de que o serviço tem caráter de organização e educação financeira e não envolve movimentação de recursos, promessa de resultados ou recomendação individualizada de investimentos.</span></label>
          </div>
          <div className="mt-5 flex items-start gap-3 rounded-xl bg-paper p-4 text-sm leading-6 text-muted"><ShieldCheck size={18} className="mt-0.5 shrink-0 text-moss" /><p>Não informe senhas bancárias, senhas de cartões, tokens, códigos de autenticação ou qualquer credencial de acesso.</p></div>
        </>;
      case 2:
        return <><SectionIntro title="Vamos conhecer você" description="Essas informações ajudam a organizar o diagnóstico sem misturar seus dados de acesso com as respostas financeiras." /><div className="grid gap-5 md:grid-cols-2"><TextField {...common} name="full_name" label="Nome completo" required /><BrazilianDateField control={control} errors={errors} /><TextField {...common} name="contact_email" label="E-mail" required type="email" /><TextField {...common} name="phone" label="Telefone/WhatsApp" required /><TextField {...common} name="city_state" label="Cidade e estado" required /><TextField {...common} name="occupation" label="Profissão ou principal ocupação" required /><SelectField {...common} name="marital_status" label="Estado civil" items={options.marital_status} /><SelectField {...common} name="organization_type" label="Sua organização financeira será" items={options.organization_type} /><TextField {...common} name="financial_dependents" label="Quantas pessoas dependem da renda familiar?" required inputMode="numeric" help="Inclua filhos, familiares ou outras pessoas que dependam total ou parcialmente dessa renda." /></div></>;
      case 3:
        return <><SectionIntro title="Objetivos e dificuldades" description="Não existe resposta certa. O objetivo é entender o que mais pesa hoje e onde você quer chegar." /><div className="space-y-6"><CheckboxGroup {...common} name="main_difficulties" label="Qual é sua principal dificuldade financeira atualmente?" items={multiOptions.main_difficulties} required /><OtherField values={watchedValues.main_difficulties} name="main_difficulties" otherName="main_difficulties_other" {...common} /><SelectField {...common} name="financial_priority" label="Qual é sua prioridade financeira neste momento?" items={options.financial_priority} required /><OtherField values={watchedValues.financial_priority} name="financial_priority" otherName="financial_priority_other" {...common} /><TextAreaField {...common} name="expected_result" label="Descreva o resultado que você espera alcançar com a consultoria" required placeholder="O que faria você sentir que o processo valeu a pena?" /><SelectField {...common} name="improvement_timeline" label="Em quanto tempo você gostaria de perceber uma melhora significativa?" items={options.improvement_timeline} /><fieldset><legend className="label">Como você avalia sua situação financeira atual? <span className="ml-1 text-rust" aria-hidden="true">*</span></legend><div className="grid grid-cols-5 gap-2">{[1, 2, 3, 4, 5].map((value) => <label key={value} className={`cursor-pointer rounded-xl border px-2 py-3 text-center text-sm ${watchedValues.financial_organization_score === String(value) ? "border-brand-pink bg-brand-pink-soft font-semibold text-brand-brown-dark" : "border-line bg-white"}`}><input className="sr-only" type="radio" value={value} {...register("financial_organization_score")} /><span className="block text-lg">{value}</span><span className="mt-1 block text-[0.65rem] leading-4 text-muted">{value === 1 ? "Desorganizada" : value === 5 ? "Organizada" : ""}</span></label>)}</div>{messageFor(errors, "financial_organization_score") && <p className="mt-1.5 text-xs text-rust">{messageFor(errors, "financial_organization_score")}</p>}</fieldset><CheckboxGroup {...common} name="organization_barriers" label="O que mais dificulta sua organização financeira?" items={multiOptions.organization_barriers} required /><OtherField values={watchedValues.organization_barriers} name="organization_barriers" otherName="organization_barriers_other" {...common} /></div></>;
      case 4:
        return <><SectionIntro title="Renda" description="Use valores líquidos, depois dos descontos. Se sua renda varia, informe uma média realista." /><div className="space-y-6"><div className="grid gap-5 md:grid-cols-2"><MoneyField {...common} name="monthly_net_income" label="Renda líquida mensal média" required /><MoneyField {...common} name="family_monthly_net_income" label="Renda líquida mensal total da família" required help="Se o diagnóstico for somente individual, repita sua renda pessoal." /><SelectField {...common} name="income_type" label="Sua principal renda é" items={options.income_type} /></div><CheckboxGroup {...common} name="income_sources" label="Quais são suas fontes de renda?" items={multiOptions.income_sources} required /><OtherField values={watchedValues.income_sources} name="income_sources" otherName="income_sources_other" {...common} /><RadioGroup {...common} name="extra_income" label="Você possui alguma renda extra?" items={options.extra_income} />{watchedValues.extra_income && watchedValues.extra_income !== "no" && <TextAreaField {...common} name="extra_income_details" label="Se possui renda extra, informe a origem e o valor médio mensal" help="Opcional. Você pode explicar a origem e o valor médio." />}<RadioGroup {...common} name="income_sufficiency" label="Sua renda é suficiente para pagar todas as despesas do mês?" items={options.income_sufficiency} required /></div></>;
      case 5:
        return <><SectionIntro title="Despesas e controle" description="Uma estimativa honesta já é suficiente para começarmos. Você poderá ajustar o diagnóstico depois." /><div className="space-y-6"><RadioGroup {...common} name="tracks_expenses" label="Você registra suas despesas?" items={options.tracks_expenses} required /><CheckboxGroup {...common} name="current_tool" label="Qual ferramenta você utiliza atualmente?" items={multiOptions.current_tool} exclusiveValues={exclusiveDiagnosticChoices.current_tool} /><OtherField values={watchedValues.current_tool} name="current_tool" otherName="current_tool_other" {...common} /><MoneyField {...common} name="monthly_expenses" label="Qual é o valor médio das suas despesas mensais?" required help="Caso não saiba, informe uma estimativa." /><CheckboxGroup {...common} name="largest_expense_categories" label="Quais são suas maiores categorias de gastos?" items={multiOptions.largest_expense_categories} required /><OtherField values={watchedValues.largest_expense_categories} name="largest_expense_categories" otherName="largest_expense_categories_other" {...common} /><RadioGroup {...common} name="overspending_frequency" label="Você costuma gastar mais do que planejou?" items={options.overspending_frequency} /><RadioGroup {...common} name="unexpected_expense_strategy" label="Quando surge uma despesa inesperada, normalmente você:" items={options.unexpected_expense_strategy} /><OtherField values={watchedValues.unexpected_expense_strategy} name="unexpected_expense_strategy" otherName="unexpected_expense_other" {...common} /><CheckboxGroup {...common} name="seasonal_expenses" label="Você possui despesas anuais ou sazonais que não costuma planejar?" items={multiOptions.seasonal_expenses} exclusiveValues={exclusiveDiagnosticChoices.seasonal_expenses} /><OtherField values={watchedValues.seasonal_expenses} name="seasonal_expenses" otherName="seasonal_expenses_other" {...common} /></div></>;
      case 6:
        return <><SectionIntro title="Contas e cartões" description="Queremos entender a estrutura que você já utiliza hoje, sem solicitar dados de acesso ou números de cartão." /><div className="grid gap-5 md:grid-cols-2"><TextField {...common} name="bank_account_count" label="Quantas contas bancárias você utiliza?" type="number" inputMode="numeric" /><TextField {...common} name="credit_card_count" label="Quantos cartões de crédito você utiliza?" type="number" inputMode="numeric" required />{watchedValues.credit_card_count !== "0" && <><MoneyField {...common} name="total_card_limit" label="Qual é o limite total disponível nos cartões?" /><MoneyField {...common} name="average_card_bill" label="Qual é o valor médio mensal das faturas?" /></>}</div><div className="mt-6 space-y-6">{watchedValues.credit_card_count !== "0" && <><RadioGroup {...common} name="pays_card_in_full" label="Você paga a fatura integralmente?" items={options.pays_card_in_full} /><RadioGroup {...common} name="knows_installments" label="Você conhece todas as compras parceladas que ainda serão cobradas?" items={options.knows_installments} /></>}<RadioGroup {...common} name="uses_overdraft" label="Você utiliza limite bancário ou cheque especial?" items={options.uses_overdraft} /></div></>;
      case 7:
        return <><SectionIntro title="Dívidas" description="Esta resposta define se vamos abrir o detalhamento. Você poderá atualizar essa informação depois." /><RadioGroup {...common} name="has_debts" label="Você possui dívidas atualmente?" items={options.has_debts} required /></>;
      case 8:
        return <><SectionIntro title="Detalhamento das dívidas" description="Informe somente o que se sentir confortável em compartilhar. Estimativas são suficientes para o diagnóstico." /><div className="space-y-6"><CheckboxGroup {...common} name="debt_types" label="Quais tipos de dívida você possui?" items={multiOptions.debt_types} required /><OtherField values={watchedValues.debt_types} name="debt_types" otherName="debt_types_other" {...common} /><div className="grid gap-5 md:grid-cols-2"><MoneyField {...common} name="total_debt_amount" label="Qual é o valor total aproximado das dívidas?" required /><MoneyField {...common} name="monthly_debt_installments" label="Qual é o valor total das parcelas mensais?" /></div><RadioGroup {...common} name="has_overdue_debt" label="Existem dívidas atrasadas?" items={options.has_overdue_debt} /><RadioGroup {...common} name="has_negative_record" label="Alguma dívida está negativada?" items={options.has_negative_record} /><TextAreaField {...common} name="main_debts_details" label="Informe as principais dívidas" placeholder="Tipo, instituição ou credor, saldo, parcela, parcelas restantes, juros se souber e situação." /><RadioGroup {...common} name="tried_debt_negotiation" label="Você já tentou negociar essas dívidas?" items={options.tried_debt_negotiation} /></div></>;
      case 9:
        return <><SectionIntro title="Reserva e patrimônio" description="Essas informações ajudam a enxergar sua margem de segurança e seus recursos atuais." /><div className="space-y-6"><RadioGroup {...common} name="has_reserve" label="Você possui reserva financeira?" items={options.has_reserve} required />{watchedValues.has_reserve !== "no" && <div className="grid gap-5 md:grid-cols-2"><MoneyField {...common} name="reserve_amount" label="Qual é o valor aproximado disponível?" /><SelectField {...common} name="reserve_months" label="Por quantos meses essa reserva manteria suas despesas essenciais?" items={options.reserve_months} /></div>}<div className="grid gap-5 md:grid-cols-2"><RadioGroup {...common} name="can_save_monthly" label="Você consegue guardar dinheiro mensalmente?" items={options.can_save_monthly} /><>{watchedValues.can_save_monthly !== "no" && <MoneyField {...common} name="average_monthly_saving" label="Quanto consegue guardar em média por mês?" />}</></div><CheckboxGroup {...common} name="assets" label="Quais bens ou recursos você possui?" items={multiOptions.assets} exclusiveValues={exclusiveDiagnosticChoices.assets} /><OtherField values={watchedValues.assets} name="assets" otherName="assets_other" triggerValue="other_assets" label="Descreva outros bens" {...common} /><MoneyField {...common} name="total_net_worth" label="Qual é o valor aproximado do seu patrimônio total?" help="Campo opcional. Considere bens, saldos e aplicações, sem descontar as dívidas." /></div></>;
      case 10:
        return <><SectionIntro title="Metas financeiras" description="Uma meta clara ajuda a transformar organização em próximos passos concretos." /><div className="space-y-6"><CheckboxGroup {...common} name="financial_goals" label="Quais são suas principais metas financeiras?" items={multiOptions.financial_goals} required /><OtherField values={watchedValues.financial_goals} name="financial_goals" otherName="financial_goals_other" {...common} /><div className="grid gap-5 md:grid-cols-2"><TextField {...common} name="most_important_goal" label="Qual é sua meta mais importante?" required /><MoneyField {...common} name="goal_amount" label="Qual é o valor necessário para essa meta?" /><SelectField {...common} name="goal_timeline" label="Em quanto tempo você deseja alcançá-la?" items={options.goal_timeline} /><RadioGroup {...common} name="has_goal_savings" label="Você já possui algum valor reservado para essa meta?" items={options.has_goal_savings} /></div>{watchedValues.has_goal_savings === "yes" && <MoneyField {...common} name="goal_saved_amount" label="Caso possua, qual é o valor acumulado?" />}</div></>;
      case 11:
        return <><SectionIntro title="Comportamento financeiro" description="Esta etapa ajuda a identificar hábitos e mudanças possíveis, sem julgamento." /><div className="space-y-6"><RadioGroup {...common} name="impulse_purchase_frequency" label="Com que frequência você realiza compras por impulso?" items={options.impulse_purchase_frequency} /><RadioGroup {...common} name="money_conversations" label="Você costuma conversar sobre dinheiro com seu cônjuge ou sua família?" items={options.money_conversations} /><RadioGroup {...common} name="willing_to_track_expenses" label="Você estaria disposto(a) a registrar seus gastos durante o processo?" items={options.willing_to_track_expenses} required /><CheckboxGroup {...common} name="possible_changes" label="Quais mudanças você acredita que conseguirá realizar?" items={multiOptions.possible_changes} exclusiveValues={exclusiveDiagnosticChoices.possible_changes} /><OtherField values={watchedValues.possible_changes} name="possible_changes" otherName="possible_changes_other" {...common} /></div></>;
      case 12:
        return <><SectionIntro title="Documentos para análise" description="Aqui você apenas indica o que poderá disponibilizar. O envio será combinado por um canal seguro, nunca por link público." /><div className="space-y-6"><CheckboxGroup {...common} name="available_documents" label="Quais documentos você poderá disponibilizar?" items={multiOptions.available_documents} exclusiveValues={exclusiveDiagnosticChoices.available_documents} /><RadioGroup {...common} name="document_delivery_preference" label="Forma preferida de envio dos documentos" items={options.document_delivery_preference} /><OtherField values={watchedValues.document_delivery_preference} name="document_delivery_preference" otherName="document_delivery_other" {...common} /></div></>;
      case 13:
        return <><SectionIntro title="Disponibilidade e observações" description="Estamos quase lá. Estas últimas respostas ajudam a organizar o próximo contato." /><div className="space-y-6"><CheckboxGroup {...common} name="meeting_availability" label="Qual é o melhor período para a reunião?" items={multiOptions.meeting_availability} /><RadioGroup {...common} name="meeting_preference" label="A reunião será preferencialmente:" items={options.meeting_preference} /><TextAreaField {...common} name="additional_information" label="Existe alguma informação importante que não foi abordada?" /><SelectField {...common} name="how_found_service" label="Como conheceu o serviço?" items={options.how_found_service} /><OtherField values={watchedValues.how_found_service} name="how_found_service" otherName="how_found_service_other" {...common} /></div></>;
      default:
        return null;
    }
  };

  const rootError = errors.root?.message;
  const isLast = currentVisibleIndex === visibleSections.length - 1;
  return <div className="grid gap-6 xl:grid-cols-[240px_minmax(0,760px)] xl:items-start">
    <aside className="surface hidden p-4 xl:block xl:sticky xl:top-24">
      <p className="px-2 text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-muted">Seu progresso</p>
      <div className="mt-4 space-y-1">{visibleSections.map((item, index) => <button key={item} type="button" onClick={() => index <= currentVisibleIndex && setSection(item)} className={`flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-xs transition ${item === section ? "bg-brand-pink-soft font-semibold text-brand-brown-dark" : index < currentVisibleIndex ? "text-moss" : "text-muted"}`}><span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[0.65rem] ${index < currentVisibleIndex ? "border-moss bg-mint text-moss" : item === section ? "border-brand-brown text-brand-brown" : "border-line"}`}>{index < currentVisibleIndex ? <Check size={12} /> : index + 1}</span><span>{sectionTitles[item - 1]}</span></button>)}</div>
    </aside>
    <Card className="overflow-hidden">
      <CardHeader className="border-b border-line bg-white"><div><CardTitle>Diagnóstico financeiro</CardTitle><CardDescription>Etapa {currentVisibleIndex + 1} de {visibleSections.length} · {Math.round(((currentVisibleIndex) / visibleSections.length) * 100)}% concluído</CardDescription></div><CircleHelp size={19} className="text-muted" /></CardHeader>
      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <div className="p-5 md:p-8">{renderSection()}{rootError && <div role="alert" className="mt-6 rounded-xl border border-rust/20 bg-rust/5 px-4 py-3 text-sm leading-6 text-rust">{rootError}</div>}{notice && <div role="status" className="mt-6 rounded-xl border border-moss/20 bg-mint/35 px-4 py-3 text-sm leading-6 text-moss">{notice}</div>}</div>
        <div className="flex flex-col-reverse gap-3 border-t border-line bg-paper px-5 py-4 sm:flex-row sm:items-center sm:justify-between md:px-8"><Button type="button" variant="quiet" onClick={previous} disabled={currentVisibleIndex === 0 || busy}><ChevronLeft size={16} /> Voltar</Button><div className="flex flex-col gap-3 sm:flex-row"><Button type="button" variant="secondary" onClick={() => saveDraft(section)} disabled={busy}><Save size={15} /> Salvar e continuar depois</Button>{isLast ? <Button type="submit" disabled={busy || isSubmitting}>{busy || isSubmitting ? "Enviando…" : <>Enviar diagnóstico <Check size={16} /></>}</Button> : <Button type="button" onClick={next} disabled={busy}>{busy ? "Salvando…" : <>Próxima etapa <ChevronRight size={16} /></>}</Button>}</div></div>
      </form>
    </Card>
  </div>;
}
