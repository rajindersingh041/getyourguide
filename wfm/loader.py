"""Workbook loading + schema contract.

Deliberately schema-driven rather than cell-indexed so a new month, a new
language or a new BPO flows through without code changes. Every read is
validated and anything unexpected is raised as a DataError, not silently
coerced.
"""
from __future__ import annotations
import re
import openpyxl
import pandas as pd

from .config import VISIBLE_SHEETS, EXCLUDED_SHEETS, CHANNELS


class DataError(Exception):
    pass


CHANNEL_PATTERNS = {
    "Email":    re.compile(r"\bemail\b", re.I),
    "Inbound":  re.compile(r"\binbound\b", re.I),
    "Outbound": re.compile(r"\boutbound\b", re.I),
    "Chat":     re.compile(r"\bchat\b", re.I),
}
TOTAL_PATTERN = re.compile(r"\btot(al)?\b", re.I)


class Workbook:
    def __init__(self, path: str):
        self.path = path
        self.wb = openpyxl.load_workbook(path, data_only=True)
        self.sheet_states = {ws.title: ws.sheet_state for ws in self.wb.worksheets}
        self._audit_sheets()

    # ---------- guard rails ----------
    def _audit_sheets(self) -> None:
        hidden = [t for t, s in self.sheet_states.items() if s != "visible"]
        for t in hidden:
            if t not in EXCLUDED_SHEETS:
                raise DataError(f"unexpected hidden sheet {t!r}; refusing to guess")
        missing = [s for s in VISIBLE_SHEETS if s not in self.sheet_states]
        if missing:
            raise DataError(f"missing expected sheets: {missing}")
        self.excluded = hidden

    def _sheet(self, name: str):
        if name in EXCLUDED_SHEETS:
            raise DataError(f"sheet {name!r} is excluded by instruction")
        return self.wb[name]

    @staticmethod
    def _rows(ws, max_row=None):
        for row in ws.iter_rows(min_row=1, max_row=max_row or ws.max_row):
            yield row

    # ---------- Contact Volume ----------
    def contact_volume(self) -> pd.DataFrame:
        """-> long frame: language, channel, month, contacts  (+ a totals frame)."""
        ws = self._sheet("Contact Volume ")
        months = [str(c.value).strip() for c in ws[1][1:] if c.value]
        recs, totals, current = [], [], None
        for row in self._rows(ws):
            label = row[0].value
            if not isinstance(label, str) or not label.strip():
                continue
            vals = [row[i + 1].value for i in range(len(months))]
            if not any(isinstance(v, (int, float)) for v in vals):
                continue
            if TOTAL_PATTERN.search(label):
                current = label.split()[0]
                totals += [{"language": current, "month": m, "contacts": float(v)}
                           for m, v in zip(months, vals)]
                continue
            channel = next((c for c, p in CHANNEL_PATTERNS.items() if p.search(label)), None)
            if channel is None:
                raise DataError(f"unclassifiable Contact Volume row: {label!r}")
            if current is None:
                raise DataError(f"channel row {label!r} before any language total")
            recs += [{"language": current, "channel": channel, "month": m,
                      "contacts": float(v)} for m, v in zip(months, vals)]
        df = pd.DataFrame(recs)
        tot = pd.DataFrame(totals)
        if set(df.channel.unique()) != set(CHANNELS):
            raise DataError(f"channel set mismatch: {sorted(df.channel.unique())}")
        return df, tot

    # ---------- AHT assumptions ----------
    def aht_assumptions(self) -> pd.DataFrame:
        ws = self._sheet("AHT Assumptions by BPO and lang")
        header = [c.value for c in ws[1]]
        colmap = {}
        for i, h in enumerate(header):
            if not isinstance(h, str):
                continue
            if re.search(r"concurren", h, re.I):
                colmap["concurrency"] = i
            else:
                for ch, pat in CHANNEL_PATTERNS.items():
                    if pat.search(h):
                        colmap[ch] = i
        missing = set(CHANNELS) - set(colmap)
        if missing:
            raise DataError(f"AHT assumptions missing channels {missing}")
        recs = []
        for row in self._rows(ws):
            bpo, lang = row[0].value, row[1].value
            if not isinstance(bpo, str) or not isinstance(lang, str):
                continue
            if bpo.strip().lower() == "bpo":
                continue
            rec = {"bpo": bpo.strip(), "language": lang.strip(),
                   "concurrency": row[colmap["concurrency"]].value}
            for ch in CHANNELS:
                rec[ch] = float(row[colmap[ch]].value)
            recs.append(rec)
        return pd.DataFrame(recs)

    # ---------- Shrinkage ----------
    def shrinkage(self) -> pd.DataFrame:
        ws = self._sheet("Shrinkage")
        recs = []
        for row in self._rows(ws):
            lang, cat, bpo, pct = (row[i].value for i in range(4))
            if not isinstance(pct, (int, float)):
                continue
            recs.append({"language": str(lang).strip(), "category": str(cat).strip(),
                         "bpo": re.sub(r"BPO\s*", "BPO ", str(bpo).strip()),
                         "pct": float(pct)})
        return pd.DataFrame(recs)

    # ---------- English reason-level ----------
    def en_reasons(self) -> pd.DataFrame:
        """Tickets + CSAT per reason per month, plus the trailing SLA/Refunds rows."""
        ws = self._sheet("EN CSAT")
        hdr = [c.value for c in ws[2]]
        months, cols = [], []
        for i, v in enumerate(hdr):
            if isinstance(v, str) and v.strip():
                m = v.strip()
                if m not in months:
                    months.append(m)
                    cols.append(i)
        recs, extra = [], []
        for row in ws.iter_rows(min_row=4):
            label = row[0].value
            vals = [row[i].value for i in range(1, 13)]
            if not any(isinstance(v, (int, float)) for v in vals):
                continue
            if isinstance(label, str) and label.strip().rstrip().lower() in ("sla", "refunds"):
                extra += [{"series": label.strip(), "month": m,
                           "value": row[c + 1].value}
                          for m, c in zip(months, cols)]
                continue
            name = label.strip() if isinstance(label, str) and label.strip() else None
            for m, c in zip(months, cols):
                recs.append({"reason": name, "month": m,
                             "tickets": row[c].value, "csat": row[c + 1].value})
        return pd.DataFrame(recs), pd.DataFrame(extra)

    def en_aht(self) -> pd.DataFrame:
        ws = self._sheet("EN AHT by Contact reason")
        months = [str(c.value).strip() for c in ws[2][1:] if c.value]
        recs = []
        for row in ws.iter_rows(min_row=3):
            label = row[0].value
            if not isinstance(label, str) or not label.strip():
                continue
            for i, m in enumerate(months):
                v = row[i + 1].value
                if isinstance(v, (int, float)):
                    recs.append({"reason": label.strip(), "month": m, "aht": float(v)})
        return pd.DataFrame(recs)

    def other_information(self) -> dict:
        ws = self._sheet("Other information")
        return {str(r[0].value).strip(): r[1].value
                for r in ws.iter_rows(min_row=1) if r[0].value}
