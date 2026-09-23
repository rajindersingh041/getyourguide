"""All planning assumptions in one place.

Every constant here is either read from the workbook ('Other information')
or is an explicit modelling assumption flagged as such. Nothing is hard-coded
elsewhere in the pipeline.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict

WORKBOOK = "WFM_Manager_-_Case_Study_Data.xlsx"

# Sheets we are permitted to read. The workbook also contains a HIDDEN sheet
# named 'CSAT' which is excluded by explicit instruction.
VISIBLE_SHEETS = (
    "EN CSAT",
    "EN AHT by Contact reason",
    "Contact Volume ",
    "Shrinkage",
    "AHT Assumptions by BPO and lang",
    "Other information",
)
EXCLUDED_SHEETS = ("CSAT",)

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun")
FORECAST_MONTHS = ("Jul", "Aug", "Sep")
CHANNELS = ("Email", "Inbound", "Outbound", "Chat")
REALTIME_CHANNELS = ("Inbound", "Chat")      # Erlang C
DEFERRED_CHANNELS = ("Email", "Outbound")    # workload / occupancy


@dataclass(frozen=True)
class Assumptions:
    # --- read from 'Other information' ---
    hours_per_week: float = 40.0                 # B2
    shrinkage: float = 0.18                      # 'Shrinkage' sheet, Tot Shrink
    ops_hours_per_month: float = 730.0           # B7: 24/7 -> 8760/12
    sla_phone: tuple[float, float] = (0.80, 20)  # B8  (target, seconds)
    sla_chat: tuple[float, float] = (0.80, 60)   # B9
    sla_email: tuple[float, float] = (0.80, 7200)# B10 (120 min)
    attrition_annual: float = 0.36               # B12
    training_weeks: float = 4.0                  # B13
    # B4: newbie AHT multipliers, months 1-3
    learning_curve: tuple[float, ...] = (1.20, 1.10, 1.05)
    # B5/B6 routing constraint
    bpo_languages: dict = field(default_factory=lambda: {
        "BPO 1": ("English",),
        "BPO 2": ("English",),
        "BPO 3": ("German", "Italian", "French", "Spanish"),
    })

    # --- explicit modelling ASSUMPTIONS (not in the workbook) ---
    deferred_occupancy: float = 0.85   # ASSUMPTION: email/outbound planned occupancy
    seasonal_uplift: float = 1.10      # mandated by the brief
    attrition_compounding: bool = True # 36%/yr -> 3.65%/mo (vs 3.00% linear)
    english_bpo_split: dict = field(default_factory=lambda: {"BPO 1": 0.5, "BPO 2": 0.5})
    # Which English AHT source drives capacity. 'channel' is defensible because it
    # is channel-resolved (needed for Erlang) and consistent with every other
    # language. 'reason' is carried as a sensitivity. See DQ finding #7.
    english_aht_source: str = "channel"

    @property
    def hours_per_fte_month(self) -> float:
        return self.hours_per_week * 52.0 / 12.0    # 173.333

    @property
    def shrink_divisor(self) -> float:
        return 1.0 - self.shrinkage                 # 0.82

    @property
    def attrition_monthly(self) -> float:
        if self.attrition_compounding:
            return 1.0 - (1.0 - self.attrition_annual) ** (1.0 / 12.0)
        return self.attrition_annual / 12.0

    @property
    def tenure_efficiency(self) -> float:
        """Steady-state productivity of the agent population given attrition and
        the 3-month learning curve. Each monthly cohort is `attrition_monthly`
        of headcount and handles 1/multiplier of a tenured agent's volume."""
        a = self.attrition_monthly
        return 1.0 - a * sum(1.0 - 1.0 / m for m in self.learning_curve)

    def sla_for(self, channel: str) -> tuple[float, float]:
        return {"Inbound": self.sla_phone, "Outbound": self.sla_phone,
                "Chat": self.sla_chat, "Email": self.sla_email}[channel]

    def to_dict(self) -> dict:
        d = asdict(self)
        d.update(hours_per_fte_month=self.hours_per_fte_month,
                 shrink_divisor=self.shrink_divisor,
                 attrition_monthly=self.attrition_monthly,
                 tenure_efficiency=self.tenure_efficiency)
        return d


DEFAULT = Assumptions()
