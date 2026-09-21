from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import EmailStr, Field, field_validator, model_validator

from app.schemas.common import APIModel, validate_money

DiagnosticStatus = Literal["not_started", "draft", "completed"]


def _empty_to_none(value: Any) -> Any:
    return None if value == "" else value


MONEY_FIELDS = (
    "monthly_net_income",
    "family_monthly_net_income",
    "monthly_expenses",
    "total_card_limit",
    "average_card_bill",
    "total_debt_amount",
    "monthly_debt_installments",
    "reserve_amount",
    "average_monthly_saving",
    "total_net_worth",
    "goal_amount",
    "goal_saved_amount",
)

CHOICES: dict[str, set[str]] = {
    "marital_status": {
        "single",
        "married",
        "stable_union",
        "separated_divorced",
        "widowed",
        "prefer_not_to_say",
    },
    "organization_type": {"individual", "couple", "family"},
    "improvement_timeline": {
        "up_to_3_months",
        "four_to_six_months",
        "seven_to_twelve_months",
        "over_twelve_months",
        "not_sure",
    },
    "income_type": {"fixed", "variable", "mixed", "no_income"},
    "extra_income": {"monthly", "occasionally", "no"},
    "income_sufficiency": {"surplus", "break_even", "not_always", "insufficient"},
    "tracks_expenses": {"all", "some", "tried", "none"},
    "overspending_frequency": {"frequently", "sometimes", "rarely", "never", "no_plan"},
    "unexpected_expense_strategy": {
        "reserve",
        "reduce_other_expenses",
        "credit_card",
        "overdraft",
        "loan",
        "borrow",
        "delay_bill",
        "other",
    },
    "pays_card_in_full": {
        "always",
        "most_months",
        "sometimes",
        "rarely",
        "minimum_or_installments",
        "no_credit_card",
    },
    "knows_installments": {"yes", "most", "no", "no_installments"},
    "uses_overdraft": {"frequently", "sometimes", "rarely", "never"},
    "has_debts": {"yes", "no"},
    "has_overdue_debt": {"yes", "no", "unknown"},
    "has_negative_record": {"yes", "no", "unknown"},
    "tried_debt_negotiation": {"agreement", "not_completed", "not_tried", "not_applicable"},
    "has_reserve": {"yes", "unorganized", "no"},
    "reserve_months": {"less_than_1", "one_to_three", "four_to_six", "over_six", "unknown", "none"},
    "can_save_monthly": {"every_month", "undefined_amount", "some_months", "no"},
    "goal_timeline": {
        "up_to_6_months",
        "seven_to_twelve_months",
        "one_to_two_years",
        "three_to_five_years",
        "over_five_years",
        "not_defined",
    },
    "has_goal_savings": {"yes", "no"},
    "impulse_purchase_frequency": {"frequently", "sometimes", "rarely", "never"},
    "money_conversations": {"calmly", "conflicts", "rarely", "no", "not_applicable"},
    "willing_to_track_expenses": {"yes", "with_guidance", "will_try", "no"},
    "document_delivery_preference": {"shared_folder", "email", "meeting", "other"},
    "meeting_preference": {"online", "in_person", "no_preference"},
    "how_found_service": {
        "referral",
        "instagram",
        "whatsapp",
        "facebook",
        "internet",
        "event",
        "other",
    },
}

LIST_CHOICE_FIELDS: dict[str, set[str]] = {
    "main_difficulties": {
        "no_control",
        "dont_know",
        "spend_more",
        "debts",
        "late_bills",
        "card_to_income",
        "variable_income",
        "cannot_save",
        "mix_personal_business",
        "family_organization",
        "goal",
        "other",
    },
    "organization_barriers": {
        "lack_of_planning",
        "lack_of_knowledge",
        "lack_of_discipline",
        "insufficient_income",
        "variable_income",
        "too_many_debts",
        "unexpected_expenses",
        "impulse_purchases",
        "family_participation",
        "lack_of_time",
        "other",
    },
    "income_sources": {
        "salary",
        "pro_labore",
        "self_employment",
        "commissions",
        "sales",
        "retirement_or_pension",
        "rent",
        "benefit",
        "family_help",
        "occasional_income",
        "other",
    },
    "current_tool": {
        "spreadsheet",
        "app",
        "notebook",
        "phone_notes",
        "bank_statement",
        "credit_card_bill",
        "none",
        "other",
    },
    "largest_expense_categories": {
        "housing",
        "food",
        "transport",
        "health",
        "education",
        "children_dependents",
        "leisure",
        "personal_shopping",
        "subscriptions",
        "debts_loans",
        "vehicle",
        "business_expenses",
        "other",
    },
    "seasonal_expenses": {
        "ipva",
        "iptu",
        "school",
        "insurance",
        "vehicle_maintenance",
        "income_tax",
        "gifts_dates",
        "travel",
        "home_maintenance",
        "none_or_planned",
        "other",
    },
    "debt_types": {
        "credit_card",
        "overdraft",
        "personal_loan",
        "payroll_loan",
        "vehicle_financing",
        "home_financing",
        "family_friends",
        "overdue_bills",
        "taxes",
        "business_debt",
        "other",
    },
    "assets": {
        "property",
        "vehicle",
        "checking_balance",
        "savings",
        "investments",
        "private_pension",
        "company_participation",
        "other_assets",
        "no_relevant_assets",
        "discuss_in_meeting",
    },
    "financial_goals": {
        "pay_debts",
        "emergency_fund",
        "buy_property",
        "buy_vehicle",
        "travel",
        "study",
        "business",
        "retirement",
        "marriage_children",
        "renovation",
        "other",
    },
    "possible_changes": {
        "reduce_nonessential",
        "set_limits",
        "track_expenses",
        "avoid_new_debts",
        "negotiate_debts",
        "create_reserve",
        "talk_with_family",
        "additional_income",
        "not_sure",
        "other",
    },
    "available_documents": {
        "bank_statements",
        "credit_card_bills",
        "income_proof",
        "debt_list",
        "loan_contracts",
        "installment_list",
        "current_spreadsheet",
        "need_to_organize",
    },
    "meeting_availability": {"morning", "afternoon", "evening", "saturday"},
}


class DiagnosticAnswers(APIModel):
    full_name: str | None = Field(default=None, max_length=120)
    birth_date: date | None = None
    contact_email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    city_state: str | None = Field(default=None, max_length=160)
    occupation: str | None = Field(default=None, max_length=160)
    marital_status: str | None = None
    organization_type: str | None = None
    financial_dependents: int | None = Field(default=None, ge=0, le=99)

    main_difficulties: list[str] | None = None
    main_difficulties_other: str | None = Field(default=None, max_length=240)
    financial_priority: str | None = None
    financial_priority_other: str | None = Field(default=None, max_length=240)
    expected_result: str | None = Field(default=None, max_length=2000)
    improvement_timeline: str | None = None
    financial_organization_score: int | None = Field(default=None, ge=1, le=5)
    organization_barriers: list[str] | None = None
    organization_barriers_other: str | None = Field(default=None, max_length=240)

    monthly_net_income: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    family_monthly_net_income: Decimal | None = Field(
        default=None, ge=0, max_digits=14, decimal_places=2
    )
    income_type: str | None = None
    income_sources: list[str] | None = None
    income_sources_other: str | None = Field(default=None, max_length=240)
    extra_income: str | None = None
    extra_income_details: str | None = Field(default=None, max_length=1000)
    income_sufficiency: str | None = None

    tracks_expenses: str | None = None
    current_tool: list[str] | None = None
    current_tool_other: str | None = Field(default=None, max_length=240)
    monthly_expenses: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    largest_expense_categories: list[str] | None = None
    largest_expense_categories_other: str | None = Field(default=None, max_length=240)
    overspending_frequency: str | None = None
    unexpected_expense_strategy: str | None = None
    unexpected_expense_other: str | None = Field(default=None, max_length=240)
    seasonal_expenses: list[str] | None = None
    seasonal_expenses_other: str | None = Field(default=None, max_length=240)

    bank_account_count: int | None = Field(default=None, ge=0, le=999)
    credit_card_count: int | None = Field(default=None, ge=0, le=999)
    total_card_limit: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    average_card_bill: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    pays_card_in_full: str | None = None
    knows_installments: str | None = None
    uses_overdraft: str | None = None

    has_debts: str | None = None
    debt_types: list[str] | None = None
    debt_types_other: str | None = Field(default=None, max_length=240)
    total_debt_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    monthly_debt_installments: Decimal | None = Field(
        default=None, ge=0, max_digits=14, decimal_places=2
    )
    has_overdue_debt: str | None = None
    has_negative_record: str | None = None
    main_debts_details: str | None = Field(default=None, max_length=3000)
    tried_debt_negotiation: str | None = None

    has_reserve: str | None = None
    reserve_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    reserve_months: str | None = None
    can_save_monthly: str | None = None
    average_monthly_saving: Decimal | None = Field(
        default=None, ge=0, max_digits=14, decimal_places=2
    )
    assets: list[str] | None = None
    total_net_worth: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    assets_other: str | None = Field(default=None, max_length=240)

    financial_goals: list[str] | None = None
    financial_goals_other: str | None = Field(default=None, max_length=240)
    most_important_goal: str | None = Field(default=None, max_length=240)
    goal_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    goal_timeline: str | None = None
    has_goal_savings: str | None = None
    goal_saved_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)

    impulse_purchase_frequency: str | None = None
    money_conversations: str | None = None
    willing_to_track_expenses: str | None = None
    possible_changes: list[str] | None = None
    possible_changes_other: str | None = Field(default=None, max_length=240)

    available_documents: list[str] | None = None
    available_documents_other: str | None = Field(default=None, max_length=240)
    document_delivery_preference: str | None = None
    document_delivery_other: str | None = Field(default=None, max_length=240)

    meeting_availability: list[str] | None = None
    meeting_preference: str | None = None
    additional_information: str | None = Field(default=None, max_length=3000)
    how_found_service: str | None = None
    how_found_service_other: str | None = Field(default=None, max_length=240)

    @field_validator("contact_email", mode="before")
    @classmethod
    def empty_email_to_none(cls, value: Any) -> Any:
        return _empty_to_none(value)

    @field_validator("birth_date", mode="before")
    @classmethod
    def empty_date_to_none(cls, value: Any) -> Any:
        return _empty_to_none(value)

    @field_validator(*MONEY_FIELDS, mode="before")
    @classmethod
    def empty_money_to_none(cls, value: Any) -> Any:
        return _empty_to_none(value)

    @field_validator(*MONEY_FIELDS)
    @classmethod
    def normalize_money(cls, value: Decimal | None) -> Decimal | None:
        return validate_money(value) if value is not None else None

    @field_validator("birth_date")
    @classmethod
    def birth_date_is_not_in_future(cls, value: date | None) -> date | None:
        if value and value > date.today():
            raise ValueError("A data de nascimento não pode estar no futuro")
        return value

    @model_validator(mode="after")
    def validate_choices(self):
        for field_name, allowed in CHOICES.items():
            value = getattr(self, field_name)
            if value is not None and value not in allowed:
                raise ValueError(f"Opção inválida em {field_name}")
        for field_name, allowed in LIST_CHOICE_FIELDS.items():
            value = getattr(self, field_name)
            if value is not None and any(item not in allowed for item in value):
                raise ValueError(f"Opção inválida em {field_name}")
        return self

    def validate_submission(self) -> "DiagnosticAnswers":
        required_fields = (
            "full_name",
            "birth_date",
            "contact_email",
            "phone",
            "city_state",
            "occupation",
            "financial_dependents",
            "main_difficulties",
            "financial_priority",
            "expected_result",
            "financial_organization_score",
            "organization_barriers",
            "monthly_net_income",
            "income_sources",
            "income_sufficiency",
            "tracks_expenses",
            "monthly_expenses",
            "largest_expense_categories",
            "credit_card_count",
            "has_debts",
            "has_reserve",
            "financial_goals",
            "most_important_goal",
            "willing_to_track_expenses",
        )
        missing = [field for field in required_fields if not self._has_answer(getattr(self, field))]
        if self.has_debts == "yes":
            for field in ("debt_types", "total_debt_amount"):
                if not self._has_answer(getattr(self, field)):
                    missing.append(field)
        if self.has_debts == "no":
            self.debt_types = None
            self.total_debt_amount = None
            self.monthly_debt_installments = None
            self.has_overdue_debt = None
            self.has_negative_record = None
            self.main_debts_details = None
            self.tried_debt_negotiation = None
            self.debt_types_other = None
        if missing:
            raise ValueError("Preencha os campos obrigatórios: " + ", ".join(missing))
        self._validate_other_fields()
        return self

    def _validate_other_fields(self) -> None:
        other_pairs = (
            (self.main_difficulties, self.main_difficulties_other, "main_difficulties_other"),
            (
                self.organization_barriers,
                self.organization_barriers_other,
                "organization_barriers_other",
            ),
            (self.income_sources, self.income_sources_other, "income_sources_other"),
            (self.current_tool, self.current_tool_other, "current_tool_other"),
            (
                self.largest_expense_categories,
                self.largest_expense_categories_other,
                "largest_expense_categories_other",
            ),
            (self.seasonal_expenses, self.seasonal_expenses_other, "seasonal_expenses_other"),
            (self.debt_types, self.debt_types_other, "debt_types_other"),
            (self.assets, self.assets_other, "assets_other"),
            (self.financial_goals, self.financial_goals_other, "financial_goals_other"),
            (self.possible_changes, self.possible_changes_other, "possible_changes_other"),
            (self.available_documents, self.available_documents_other, "available_documents_other"),
        )
        for values, other, field_name in other_pairs:
            if values and "other" in values and not self._has_answer(other):
                raise ValueError(f"Preencha {field_name} quando escolher Outra opção")
        if self.unexpected_expense_strategy == "other" and not self._has_answer(
            self.unexpected_expense_other
        ):
            raise ValueError("Preencha unexpected_expense_other quando escolher Outra opção")
        if self.document_delivery_preference == "other" and not self._has_answer(
            self.document_delivery_other
        ):
            raise ValueError("Preencha document_delivery_other quando escolher Outra opção")
        if self.how_found_service == "other" and not self._has_answer(self.how_found_service_other):
            raise ValueError("Preencha how_found_service_other quando escolher Outra opção")

    @staticmethod
    def _has_answer(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, list):
            return bool(value)
        return True


class DiagnosticDraftRequest(APIModel):
    current_section: int = Field(ge=1, le=13)
    answers: DiagnosticAnswers


class DiagnosticSubmitRequest(APIModel):
    answers: DiagnosticAnswers
    consent_data_processing: bool
    consent_service_disclaimer: bool


class DiagnosticResponse(APIModel):
    status: DiagnosticStatus
    current_section: int
    completion_percent: int
    version: int
    answers: dict[str, Any]
    consent_data_processing: bool
    consent_service_disclaimer: bool
    consent_version: str
    consented_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime | None
