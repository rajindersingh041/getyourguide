"""Excel export - one sheet per artefact, formatted for an ops audience."""
from __future__ import annotations
import pandas as pd


def write_excel(path: str, frames: dict[str, pd.DataFrame]) -> None:
    with pd.ExcelWriter(path, engine="xlsxwriter") as xl:
        book = xl.book
        hdr = book.add_format({"bold": True, "bg_color": "#1F3864",
                               "font_color": "white", "border": 1, "text_wrap": True,
                               "valign": "top"})
        num = book.add_format({"num_format": "#,##0.0"})
        intf = book.add_format({"num_format": "#,##0"})
        pct = book.add_format({"num_format": "0.0%"})
        for name, df in frames.items():
            sheet = name[:31]
            df.to_excel(xl, sheet_name=sheet, index=False, startrow=1, header=False)
            ws = xl.sheets[sheet]
            for c, col in enumerate(df.columns):
                ws.write(0, c, str(col), hdr)
                series = df[col]
                width = max(len(str(col)) + 2,
                            min(46, int(series.astype(str).str.len().max() or 10) + 2))
                fmt = None
                if pd.api.types.is_numeric_dtype(series):
                    lc = str(col).lower()
                    if any(k in lc for k in ("pct", "occupancy", "share", "ratio",
                                             "_level", "csat", "uplift", "sigma",
                                             "percentile", "change", "r2")):
                        fmt = pct
                    elif any(k in lc for k in ("contact", "hours", "tickets", "seat_hours")):
                        fmt = intf
                    else:
                        fmt = num
                ws.set_column(c, c, width, fmt)
            ws.freeze_panes(1, 0)
            ws.autofilter(0, 0, max(len(df), 1), max(len(df.columns) - 1, 0))
