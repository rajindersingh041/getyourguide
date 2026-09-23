"""Volume forecasting.

Deliberately simple and explainable: 6 months of history containing a
structural break cannot support a fitted seasonal model, so the forecast is
scenario-based off a declared baseline, with the uncertainty quantified
separately from the point estimate.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

from .erlang import norm_ppf


def month_order(df) -> list[str]:
    return list(dict.fromkeys(df.month))


def detect_break(totals: pd.DataFrame, threshold: float = 0.5) -> dict | None:
    """Find a month where every language steps together - a level shift."""
    order = month_order(totals)
    piv = totals.pivot_table(index="month", columns="language", values="contacts").loc[order]
    tot = piv.sum(axis=1)
    for i in range(1, len(order)):
        if tot.iloc[i] / tot.iloc[i - 1] - 1 > threshold:
            r = piv.iloc[i] / piv.iloc[i - 1]
            return {"month": order[i], "total_ratio": tot.iloc[i] / tot.iloc[i - 1],
                    "per_language": r.to_dict(),
                    "uniform": bool(r.min() > 1 + threshold * 0.6)}
    return None


def ols(y: list[float]) -> tuple[float, float]:
    """(intercept, slope) of the least-squares line through y at x=0..n-1."""
    n = len(y)
    x = np.arange(n, dtype=float)
    yv = np.array(y, dtype=float)
    b = ((x - x.mean()) * (yv - yv.mean())).sum() / ((x - x.mean()) ** 2).sum()
    return float(yv.mean() - b * x.mean()), float(b)


def linear_trend(y: list[float], steps_ahead: int) -> float:
    """Fitted line projected `steps_ahead` months beyond the last observation."""
    a, b = ols(y)
    return float(a + b * (len(y) - 1 + steps_ahead))


def trend_r2(y: list[float]) -> float:
    n = len(y); x = np.arange(n, dtype=float); yv = np.array(y, dtype=float)
    a, b = ols(y)
    resid = yv - (a + b * x)
    ss_tot = ((yv - yv.mean()) ** 2).sum()
    return float(1 - (resid ** 2).sum() / ss_tot) if ss_tot else 1.0


def volatility(series: list[float], skip_index: int | None = None) -> float:
    """Std-dev of month-over-month log returns, optionally dropping the
    structural-break return so seasonality is not counted as forecast error."""
    rets = [math.log(series[i] / series[i - 1]) for i in range(1, len(series))
            if skip_index is None or i != skip_index]
    return float(np.std(rets, ddof=1))


class VolumeForecast:
    def __init__(self, volume: pd.DataFrame, totals: pd.DataFrame,
                 forecast_months, uplift: float, break_month: str | None):
        self.volume, self.totals = volume, totals
        self.forecast_months = list(forecast_months)
        self.uplift = uplift
        self.order = month_order(totals)
        self.break_month = break_month
        self.break_idx = self.order.index(break_month) if break_month else 0
        self.baseline_month = self.order[-1]
        # language totals are DERIVED from the channel rows, not read from the
        # 'X Tot' rows (which carry a +/-2 rounding residue). See DQ check.
        self.piv = volume.pivot_table(index="month", columns="language",
                                      values="contacts", aggfunc="sum").loc[self.order]
        self.channel_base = (volume[volume.month == self.order[-1]]
                             .set_index(["language", "channel"]).contacts)
        # post-break window used for trend / growth tests
        self.post = self.piv.iloc[self.break_idx:]

    # ---- per-language growth diagnosis ----
    def growth_profile(self) -> pd.DataFrame:
        rows = []
        for lang in self.piv.columns:
            y = list(self.post[lang])
            last = y[-1]
            _, slope_pm = ols(y)
            r2 = trend_r2(y)
            rows.append({
                "language": lang,
                "baseline": last,
                "post_break_first": y[0],
                "post_break_change": last / y[0] - 1,
                "trend_per_month": slope_pm,
                "trend_pct_of_baseline": slope_pm / last,
                "r2": r2,
                "sigma_logret": volatility(list(self.piv[lang]), self.break_idx),
                # only a POSITIVE, reasonably well-fitted trend justifies
                # extrapolating above the baseline in the HIGH case
                "growing": bool(slope_pm > 0 and slope_pm / last > 0.03 and r2 > 0.4),
            })
        return pd.DataFrame(rows).set_index("language")

    # ---- scenarios ----
    def scenarios(self) -> pd.DataFrame:
        gp = self.growth_profile()
        recs = []
        for si, month in enumerate(self.forecast_months, start=1):
            for lang in self.piv.columns:
                base = gp.loc[lang, "baseline"]
                trended = (linear_trend(list(self.post[lang]), si)
                           if gp.loc[lang, "growing"] else base)
                trended = max(trended, base)   # HIGH is an upside case by definition
                recs += [
                    {"scenario": "LOW", "month": month, "language": lang,
                     "contacts": base},
                    {"scenario": "BASE", "month": month, "language": lang,
                     "contacts": base * self.uplift},
                    {"scenario": "HIGH", "month": month, "language": lang,
                     "contacts": trended * self.uplift},
                ]
        return pd.DataFrame(recs)

    def channel_mix(self) -> pd.DataFrame:
        """Baseline-month channel shares per language."""
        b = self.volume[self.volume.month == self.baseline_month]
        mix = b.pivot_table(index="language", columns="channel", values="contacts")
        return mix.div(mix.sum(axis=1), axis=0)

    def by_channel(self) -> pd.DataFrame:
        """Scenario volumes at channel grain.

        Each channel is grown by its own language's scenario multiplier, applied
        to that channel's own baseline - so channel rows sum exactly to the
        language forecast by construction."""
        sc = self.scenarios()
        base = self.piv.loc[self.baseline_month]
        sc = sc.assign(mult=[r.contacts / base[r.language] for r in sc.itertuples()])
        rows = []
        for r in sc.itertuples():
            for ch in self.volume.channel.unique():
                rows.append({"scenario": r.scenario, "month": r.month,
                             "language": r.language, "channel": ch,
                             "contacts": self.channel_base[(r.language, ch)] * r.mult})
        return pd.DataFrame(rows)

    # ---- uncertainty ----
    def intervals(self, percentiles=(0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95),
                  sigma_override: float | None = None) -> pd.DataFrame:
        """Log-normal band around the BASE median. FTE is linear in volume, so
        the same multipliers apply to headcount."""
        totals_series = list(self.piv.sum(axis=1))
        sigma = sigma_override or volatility(totals_series, self.break_idx)
        base = self.scenarios().query("scenario=='BASE'").groupby("month").contacts.sum()
        rows = []
        for month in self.forecast_months:
            for p in percentiles:
                mult = math.exp(norm_ppf(p) * sigma)
                rows.append({"month": month, "percentile": p, "sigma": sigma,
                             "multiplier": mult, "contacts": base[month] * mult})
        return pd.DataFrame(rows)
