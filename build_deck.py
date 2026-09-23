#!/usr/bin/env python
"""Renders the submission deck to HTML (then Chromium -> PDF).

Every figure is pulled from the model's own output, so the deck cannot drift
from run_model.py. Charts are hand-built SVG: no library, no CDN, no network.
"""
from __future__ import annotations
import json, math, subprocess, sys
from pathlib import Path

D = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "deck_data.json"))

# ---------------------------------------------------------------- palette
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, RULE, SURF = "#e1e0d9", "#c3c2b7", "#fcfcfb"
S1, S2, S3, S4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"   # validated, light
WASH, DEEMPH = "#cde2fb", "#d9d8d2"
GOOD, CRIT = "#0ca30c", "#d03b3b"

def f(x, d=0):
    return f"{x:,.{d}f}"

def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

# ---------------------------------------------------------------- helpers
def txt(x, y, s, size=9, fill=INK2, anchor="start", weight=400, ls=0, op=1):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}" letter-spacing="{ls}" '
            f'opacity="{op}">{esc(s)}</text>')

def line(x1, y1, x2, y2, stroke=GRID, w=1, op=1, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{w}" opacity="{op}"{d}/>')

def rrect(x, y, w, h, fill, r=3, top_only=True):
    """Bar with rounded data-end, square at the baseline."""
    if h <= 0.5:
        return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{max(h,0.5):.1f}" fill="{fill}"/>'
    r = min(r, w / 2, h)
    if not top_only:
        return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}" rx="{r}"/>'
    return (f'<path d="M{x:.1f},{y+h:.1f} L{x:.1f},{y+r:.1f} Q{x:.1f},{y:.1f} {x+r:.1f},{y:.1f} '
            f'L{x+w-r:.1f},{y:.1f} Q{x+w:.1f},{y:.1f} {x+w:.1f},{y+r:.1f} L{x+w:.1f},{y+h:.1f} Z" fill="{fill}"/>')

def hbar(x, y, w, h, fill, r=3):
    """Horizontal bar, rounded at the data end (right)."""
    if w <= 0.5:
        return f'<rect x="{x:.1f}" y="{y:.1f}" width="0.5" height="{h:.1f}" fill="{fill}"/>'
    r = min(r, h / 2, w)
    return (f'<path d="M{x:.1f},{y:.1f} L{x+w-r:.1f},{y:.1f} Q{x+w:.1f},{y:.1f} {x+w:.1f},{y+r:.1f} '
            f'L{x+w:.1f},{y+h-r:.1f} Q{x+w:.1f},{y+h:.1f} {x+w-r:.1f},{y+h:.1f} L{x:.1f},{y+h:.1f} Z" fill="{fill}"/>')

def svg(w, h, body, cls="chart"):
    return (f'<svg class="{cls}" viewBox="0 0 {w} {h}" width="100%" '
            f'preserveAspectRatio="xMidYMid meet" role="img">{body}</svg>')

# ================================================================ CHARTS
def chart_waterfall():
    """Headcount build-up. Emphasis form: the SLA step is the story, the rest recede."""
    b = [r for r in D["build"] if r["scenario"] == "BASE" and r["month"] == "Jul"][0]
    base = b["fte_workload_only"]
    steps = [("Workload\n÷ shrinkage", base, None, "total"),
             ("+ service level\n(Erlang C)", b["fte_sla"] - base, base, "hero"),
             ("+ learning\ncurve", b["fte_on_floor"] - b["fte_sla"], b["fte_sla"], "step"),
             ("+ training\nclass", b["fte_paid"] - b["fte_on_floor"], b["fte_on_floor"], "step"),
             ("Paid FTE", b["fte_paid"], None, "total")]
    W, H = 330, 296
    L, R, T, B = 4, 4, 34, 50
    mx = b["fte_paid"] * 1.16
    pw, ph = W - L - R, H - T - B
    n = len(steps)
    slot = pw / n
    bw = min(34, slot * 0.54)
    o = [line(L, T + ph, W - R, T + ph, RULE, 1)]
    for i, (lab, val, bot, kind) in enumerate(steps):
        cx = L + slot * i + slot / 2
        x = cx - bw / 2
        if kind == "total":
            y = T + ph - val / mx * ph
            o.append(rrect(x, y, bw, val / mx * ph, S1 if i == n - 1 else DEEMPH))
            o.append(txt(cx, y - 8, f(val), 15, INK if i == n - 1 else INK2, "middle", 700))
        else:
            y0 = T + ph - bot / mx * ph
            y1 = T + ph - (bot + val) / mx * ph
            col = S1 if kind == "hero" else DEEMPH
            o.append(rrect(x, y1, bw, y0 - y1, col))
            o.append(txt(cx, y1 - 8, f"+{f(val)}", 12 if kind == "hero" else 10,
                         INK if kind == "hero" else INK2, "middle", 700))
            # connector from the previous bar top
            px = L + slot * (i - 1) + slot / 2 + bw / 2
            o.append(line(px, y0, x, y0, RULE, 1, .9, "2 2"))
        for j, ln in enumerate(lab.split("\n")):
            o.append(txt(cx, T + ph + 16 + j * 11, ln, 8.5, MUTED, "middle"))
    # the callout
    hx = L + slot * 1 + slot / 2
    o.append(txt(hx, T - 14, f"+{SLA_UPLIFT*100:.0f}% — this is the brief's requirement", 9, S1, "middle", 700))
    return svg(W, H, "".join(o))


def chart_fan():
    """Actual volume + the three forecast scenarios as a band. One hue."""
    W, H = 376, 252
    L, R, T, B = 30, 52, 20, 30
    pw, ph = W - L - R, H - T - B
    act = D["hist_total"]
    months = D["hist_months"] + ["Jul", "Aug", "Sep"]
    lo = [r["contacts"] for r in D["build"] if r["scenario"] == "LOW"]
    ba = [r["contacts"] for r in D["build"] if r["scenario"] == "BASE"]
    hi = [r["contacts"] for r in D["build"] if r["scenario"] == "HIGH"]
    ymax = 380000
    X = lambda i: L + pw * i / (len(months) - 1)
    Y = lambda v: T + ph - v / ymax * ph
    o = []
    for gv in range(0, 400000, 100000):
        o.append(line(L, Y(gv), W - R, Y(gv), GRID, 1))
        o.append(txt(L - 7, Y(gv) + 3, f"{gv//1000}k" if gv else "0", 8, MUTED, "end"))
    # forecast band (LOW..HIGH), anchored at the last actual
    up = [(X(5), Y(act[-1]))] + [(X(6 + i), Y(hi[i])) for i in range(3)]
    dn = [(X(6 + i), Y(lo[i])) for i in range(2, -1, -1)] + [(X(5), Y(act[-1]))]
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in up + dn)
    o.append(f'<polygon points="{pts}" fill="{S1}" opacity="0.10"/>')
    # actual
    ap = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(act))
    o.append(f'<polyline points="{ap}" fill="none" stroke="{S1}" stroke-width="2" '
             f'stroke-linejoin="round" stroke-linecap="round"/>')
    # BASE forward
    bp = f"{X(5):.1f},{Y(act[-1]):.1f} " + " ".join(f"{X(6+i):.1f},{Y(ba[i]):.1f}" for i in range(3))
    o.append(f'<polyline points="{bp}" fill="none" stroke="{S1}" stroke-width="2" '
             f'stroke-linecap="round" stroke-dasharray="5 3"/>')
    for i, v in enumerate(act):
        o.append(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="3.2" fill="{S1}" '
                 f'stroke="{SURF}" stroke-width="2"/>')
    # direct labels at the right edge, nudged apart with leader lines so the
    # BASE/LOW pair (only ~12pt apart on the scale) never overlaps
    ends = [(hi[2], "HIGH 338k", 400), (ba[2], "BASE 294k", 700), (lo[2], "LOW 267k", 400)]
    ys, min_gap = [Y(v) for v, _, _ in ends], 11.0
    for i in range(1, len(ys)):
        if ys[i] - ys[i - 1] < min_gap:
            ys[i] = ys[i - 1] + min_gap
    for (v, lab, wt), ly in zip(ends, ys):
        o.append(line(X(8) + 3, Y(v), W - R + 3, ly, RULE, 1, .85))
        o.append(txt(W - R + 6, ly + 3, lab, 8.5, INK if wt == 700 else INK2, "start", wt))
    # the structural break
    o.append(line(X(2), T, X(2), T + ph, CRIT, 1, .5, "3 3"))
    o.append(txt(X(2) + 4, T + 10, "March +87%", 8, CRIT, "start", 700))
    o.append(txt(X(2) + 4, T + 20, "all 5 languages", 7.5, MUTED, "start"))
    o.append(line(X(5.5), T, X(5.5), T + ph, RULE, 1, .8))
    o.append(txt(X(5.5) - 5, T + ph - 4, "actual", 7.5, MUTED, "end", 400, .3))
    o.append(txt(X(5.5) + 5, T + ph - 4, "forecast", 7.5, MUTED, "start", 400, .3))
    for i, m in enumerate(months):
        o.append(txt(X(i), T + ph + 14, m, 8, MUTED, "middle"))
    return svg(W, H, "".join(o))


def chart_occupancy():
    """Evidence for lever 1. One series, one hue; the pooled result as a reference."""
    qs = sorted([r for r in D["queues"] if r["model"] == "ErlangC"], key=lambda r: r["occupancy"])
    W = 560
    rowh, T, L, R = 19, 26, 96, 74
    H = T + rowh * len(qs) + 18
    pw = W - L - R
    o = [txt(L, 12, "Occupancy at the solved seat count — idle time IS the service level",
             8.5, MUTED, "start")]
    for i, r in enumerate(qs):
        y = T + i * rowh
        nonen = r["language"] != "English"
        col = S1 if nonen else DEEMPH
        o.append(txt(L - 7, y + 12, f'{r["language"]} {r["channel"].lower()}', 8.5,
                     INK if nonen else MUTED, "end", 700 if nonen else 400))
        o.append(hbar(L, y + 3, pw * r["occupancy"], 13, col))
        o.append(txt(L + pw * r["occupancy"] + 5, y + 13, f'{r["occupancy"]*100:.0f}%', 9,
                     INK if nonen else MUTED, "start", 700 if nonen else 400))
        o.append(txt(W - 2, y + 13, f'{int(r["seats_raw"])} seats', 8, MUTED, "end"))
    o.append(line(L + pw * .595, T - 6, L + pw * .595, T + rowh * len(qs), S1, 1, .55, "3 2"))
    o.append(txt(L, T + rowh * len(qs) + 14,
                 "59.5% — where the four pooled phone queues land", 8.5, S1, "start", 700))
    return svg(W, H, "".join(o))


def chart_conc():
    """Chat concurrency sensitivity. Ordered scale, one hue; two steps emphasised."""
    rows = D["conc"]
    W, H = 228, 196
    L, R, T, B = 6, 6, 32, 40
    pw, ph = W - L - R, H - T - B
    mx = max(r["chat_fte"] for r in rows) * 1.2
    slot = pw / len(rows)
    bw = min(34, slot * .56)
    o = [line(L, T + ph, W - R, T + ph, RULE, 1)]
    for i, r in enumerate(rows):
        cx = L + slot * i + slot / 2
        h = r["chat_fte"] / mx * ph
        hero = r["concurrency"] in (1.2, 2.0)
        col = S1 if hero else DEEMPH
        o.append(rrect(cx - bw / 2, T + ph - h, bw, h, col))
        o.append(txt(cx, T + ph - h - 7, f'{r["chat_fte"]:.0f}', 10,
                     INK if hero else MUTED, "middle", 700 if hero else 400))
        o.append(txt(cx, T + ph + 14, f'{r["concurrency"]:g}', 8.5,
                     INK if hero else MUTED, "middle", 700 if hero else 400))
    o.append(txt(L + pw / 2, T + ph + 28, "chats handled per agent, concurrently", 7.5, MUTED, "middle"))
    o.append(txt(L, 11, "Chat FTE", 8, MUTED, "start"))
    y0 = T + ph - rows[0]["chat_fte"] / mx * ph
    y2 = T + ph - rows[2]["chat_fte"] / mx * ph
    o.append(line(L + slot * .5, y0 - 18, L + slot * 2.5, y0 - 18, S1, 1, .8))
    o.append(line(L + slot * 2.5, y0 - 18, L + slot * 2.5, y2 - 7, S1, 1, .8))
    o.append(txt(L + slot * 1.5, y0 - 22, "−75.3 FTE", 10, S1, "middle", 700))
    return svg(W, H, "".join(o))


def chart_channel_mix():
    """FTE by channel. 4 validated categorical slots; every segment direct-labelled
    (the palette's contrast WARN makes labels mandatory, not optional).
    Segments too narrow to hold their label get it above the bar instead of
    clipped inside it."""
    rows = {r["channel"]: r["fte"] for r in D["by_channel"]}
    order = [("Chat", S1), ("Email", S2), ("Inbound", S3), ("Outbound", S4)]
    tot = sum(rows.values())
    W, H = 500, 96
    T, bh = 26, 30
    pw = W
    o, x = [], 0.0
    for name, col in order:
        w = rows[name] / tot * pw
        val = f'{rows[name]:.0f}'
        o.append(f'<rect x="{x:.1f}" y="{T}" width="{max(w-2,1):.1f}" height="{bh}" fill="{col}" rx="2"/>')
        # a value only goes inside the fill if it actually fits with padding
        fits = w - 2 >= len(val) * 7.6 + 12
        if fits:
            o.append(txt(x + 7, T + 20, val, 12, "#ffffff", "start", 700))
        else:
            o.append(txt(min(x + w / 2, W - 10), T - 6, val, 11, INK, "middle", 700))
            o.append(line(min(x + w / 2, W - 10), T - 3, x + w / 2, T + 4, RULE, 1))
        # category labels below; the last one right-aligns so it cannot run off
        last = name == order[-1][0]
        lx = W if last else x
        anc = "end" if last else "start"
        o.append(txt(lx, T + bh + 15, name, 10, INK2, anc, 700))
        o.append(txt(lx, T + bh + 28, f'{rows[name]/tot*100:.0f}%', 9.5, MUTED, anc))
        x += w
    return svg(W, H, "".join(o))


def chart_small_multiples():
    """Only English is growing - five one-series panels, emphasis on the one that is."""
    langs = ["English", "German", "Spanish", "French", "Italian"]
    growth = {r["language"]: r for r in D["growth"]}
    W, H = 820, 150
    panel = W / 5
    T, B = 26, 34
    ph = H - T - B
    o = []
    for i, lg in enumerate(langs):
        vals = D["hist"][lg]
        x0 = i * panel + 8
        pwid = panel - 22
        mx = max(max(v for v in D["hist"][l]) for l in langs)
        X = lambda k: x0 + pwid * k / 5
        Y = lambda v: T + ph - v / mx * ph
        grow = growth[lg]["growing"]
        col = S1 if grow else DEEMPH
        o.append(line(x0, T + ph, x0 + pwid, T + ph, GRID, 1))
        pts = " ".join(f"{X(k):.1f},{Y(v):.1f}" for k, v in enumerate(vals))
        o.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2" '
                 f'stroke-linejoin="round" stroke-linecap="round"/>')
        o.append(f'<circle cx="{X(5):.1f}" cy="{Y(vals[5]):.1f}" r="3" fill="{col}" '
                 f'stroke="{SURF}" stroke-width="2"/>')
        o.append(txt(x0, 11, lg, 9, INK if grow else INK2, "start", 700 if grow else 400))
        sl = growth[lg]["trend_per_month"]
        o.append(txt(x0, 21, f'{"+" if sl>0 else "−"}{abs(sl):,.0f}/mo', 7.5,
                     S1 if grow else MUTED, "start", 700 if grow else 400))
        o.append(txt(x0, T + ph + 13, "Jan", 7, MUTED, "start"))
        o.append(txt(x0 + pwid, T + ph + 13, "Jun", 7, MUTED, "end"))
        if grow:
            o.append(txt(x0, T + ph + 26, "the only growing series", 7.5, S1, "start", 700))
        else:
            o.append(txt(x0, T + ph + 26, "flat since March", 7.5, MUTED, "start"))
    return svg(W, H, "".join(o))


def chart_intervals():
    """Uncertainty band on paid FTE. One hue, ordinal steps."""
    b = [r for r in D["build"] if r["scenario"] == "BASE" and r["month"] == "Jul"][0]
    paid = b["fte_paid"]
    iv = {round(r["percentile"], 2): r["multiplier"] for r in D["intervals"]}
    W, H = 228, 124
    L, R, T = 24, 24, 44
    pw = W - L - R
    lo, hi = paid * iv[0.05], paid * iv[0.95]
    X = lambda v: L + pw * (v - lo) / (hi - lo)
    o = [txt(0, 12, "Paid FTE — 80% confidence band", 8.5, MUTED, "start"),
         txt(0, 24, f'σ = {D["sigma"]*100:.1f}% (log-return SD, March break excluded)', 7.5, MUTED, "start")]
    o.append(f'<rect x="{X(paid*iv[0.05]):.1f}" y="{T}" width="{X(paid*iv[0.95])-X(paid*iv[0.05]):.1f}" '
             f'height="16" fill="{S1}" opacity="0.12" rx="2"/>')
    o.append(f'<rect x="{X(paid*iv[0.10]):.1f}" y="{T}" width="{X(paid*iv[0.90])-X(paid*iv[0.10]):.1f}" '
             f'height="16" fill="{S1}" opacity="0.22" rx="2"/>')
    o.append(f'<rect x="{X(paid)-1.5:.1f}" y="{T-5}" width="3" height="26" fill="{S1}" rx="1.5"/>')
    o.append(txt(X(paid), T - 10, f"{paid:.0f}", 13, INK, "middle", 700))
    for p, anc in ((0.10, "middle"), (0.90, "middle")):
        v = paid * iv[p]
        o.append(txt(X(v), T + 32, f"{v:.0f}", 9.5, INK2, anc, 700))
        o.append(txt(X(v), T + 43, f"P{int(p*100)}", 7.5, MUTED, anc))
    o.append(txt(L + pw / 2, T + 60, "hire to the core; flex the band", 8, MUTED, "middle"))
    return svg(W, H, "".join(o))


# ================================================================ CSS
CSS = """
@page { size: 13.333in 7.5in; margin: 0; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin:0; background:#f2f2ef; font-family:"Noto Sans","Liberation Sans",system-ui,sans-serif;
       color:#0b0b0b; font-size:11.5px; line-height:1.5; }
.slide { width:13.333in; height:7.5in; background:#fcfcfb; position:relative;
         padding:0.52in 0.62in 0.40in; page-break-after:always; overflow:hidden;
         display:flex; flex-direction:column; }
.slide:last-child { page-break-after:auto; }
/* ---- header ---- */
.eyebrow { font-size:8.5px; letter-spacing:.14em; text-transform:uppercase; color:#898781;
           display:flex; gap:10px; align-items:baseline; }
.eyebrow .tag { color:#2a78d6; font-weight:700; }
h1 { font-size:27px; font-weight:700; margin:7px 0 0; letter-spacing:-.018em; line-height:1.15; }
.dek { font-size:12.5px; color:#52514e; margin:5px 0 0; max-width:62ch; line-height:1.5; }
.hr { height:1px; background:#e1e0d9; margin:13px 0 0; }
.body { flex:1; min-height:0; padding-top:14px; }
/* ---- grid ---- */
.row { display:flex; gap:26px; }
.col { flex:1; min-width:0; }
.g2 { display:grid; grid-template-columns:1fr 1fr; gap:26px; }
.g3 { display:grid; grid-template-columns:1fr 1fr 1fr; gap:22px; }
.g4 { display:grid; grid-template-columns:repeat(4,1fr); gap:16px; }
/* ---- type ---- */
h2 { font-size:9.5px; letter-spacing:.13em; text-transform:uppercase; color:#898781;
     font-weight:700; margin:0 0 8px; }
h3 { font-size:13px; font-weight:700; margin:0 0 4px; letter-spacing:-.005em; }
p { margin:0 0 9px; color:#52514e; }
p.tight { margin:0 0 3px; }
strong { color:#0b0b0b; font-weight:700; }
.accent { color:#2a78d6; font-weight:700; }
.crit { color:#d03b3b; font-weight:700; }
.good { color:#0ca30c; font-weight:700; }
.mute { color:#898781; }
.sm { font-size:10.5px; }
.xs { font-size:9.5px; }
ul { margin:0; padding-left:13px; color:#52514e; }
li { margin-bottom:6px; }
li::marker { color:#c3c2b7; }
/* ---- hero ---- */
.hero { display:flex; align-items:flex-start; gap:8px; }
.hero .n { font-size:78px; font-weight:700; letter-spacing:-.04em; line-height:.86; color:#0b0b0b; }
.hero .u { font-size:12px; color:#52514e; padding-top:7px; font-weight:700; }
/* ---- stat tiles ---- */
.tile { border-top:1px solid #e1e0d9; padding-top:8px; }
.tile .k { font-size:8.5px; letter-spacing:.1em; text-transform:uppercase; color:#898781; }
.tile .v { font-size:27px; font-weight:700; letter-spacing:-.025em; margin-top:3px; line-height:1.05; }
.tile .s { font-size:9.5px; color:#898781; margin-top:2px; }
/* ---- callout ---- */
.note { border-left:2px solid #2a78d6; padding:2px 0 2px 11px; }
.note.red { border-color:#d03b3b; }
.note.grey { border-color:#c3c2b7; }
/* ---- table ---- */
table { width:100%; border-collapse:collapse; font-size:9.5px; font-variant-numeric:tabular-nums; }
th { text-align:left; font-size:8px; letter-spacing:.09em; text-transform:uppercase;
     color:#898781; font-weight:700; padding:0 7px 5px 0; border-bottom:1px solid #c3c2b7; }
td { padding:5.5px 8px 5.5px 0; border-bottom:1px solid #e1e0d9; color:#52514e; }
td.n, th.n { text-align:right; }
tr.tot td { font-weight:700; color:#0b0b0b; border-bottom:none; border-top:1px solid #c3c2b7; }
.pill { display:inline-block; font-size:7.5px; font-weight:700; letter-spacing:.06em;
        padding:1.5px 5px; border-radius:2px; text-transform:uppercase; }
.pill.pass { background:#e4f5e4; color:#0a6b0a; }
.pill.fix  { background:#e9f1fd; color:#1c5cab; }
.pill.warn { background:#fdf0e6; color:#9c4a18; }
/* ---- footer ---- */
.foot { display:flex; justify-content:space-between; align-items:baseline;
        font-size:8.5px; color:#898781; border-top:1px solid #e1e0d9;
        padding-top:7px; margin-top:auto; letter-spacing:.04em; }
.pg { font-weight:700; color:#52514e; }
.chart { display:block; }
table.dense { font-size:8.2px; }
table.dense td { padding:3.2px 6px 3.2px 0; line-height:1.34; }
table.dense th { font-size:7.2px; padding:0 6px 4px 0; }
table.dense .pill { font-size:6.5px; padding:1px 4px; }
.chart { display:block; }
.apx .eyebrow .tag { color:#898781; }
.apx h1 { font-size:22px; }
"""

# ================================================================ PAGE SHELL
def slide(n, tag, title, dek, body, total, apx=False):
    return f"""<section class="slide{' apx' if apx else ''}">
  <div class="eyebrow"><span class="tag">{esc(tag)}</span><span>Manager, Workforce Management &middot; Care Experience &amp; Strategy</span></div>
  <h1>{title}</h1>
  {f'<p class="dek">{dek}</p>' if dek else ''}
  <div class="hr"></div>
  <div class="body">{body}</div>
  <div class="foot"><span>GetYourGuide &middot; WFM take-home &middot; all figures reproduced by <span style="font-family:monospace">run_model.py</span>, verified by <span style="font-family:monospace">crosscheck.py</span> (72/72)</span><span class="pg">{n} / {total}</span></div>
</section>"""


def clip(text, n):
    """Truncate on a word boundary with an ellipsis - a mid-word cut reads as a
    rendering fault, not an editorial choice."""
    text = str(text)
    if len(text) <= n:
        return text
    cut = text[:n]
    sp = cut.rfind(" ")
    return (cut[:sp] if sp > n * 0.6 else cut).rstrip(" ,;:(") + "\u2026"


def tile(k, v, s):
    return f'<div class="tile"><div class="k">{k}</div><div class="v">{v}</div><div class="s">{s}</div></div>'


# ================================================================ SLIDES
B = {(r["scenario"], r["month"]): r for r in D["build"]}
bj = B[("BASE", "Jul")]
EN_IN = [r for r in D["queues"] if r["language"] == "English" and r["channel"] == "Inbound"][0]
SLA_UPLIFT = bj["fte_sla"] / bj["fte_workload_only"] - 1
POOL = sum(p["fte_saved"] for p in D["pools"])
CONC = -[r for r in D["conc"] if r["concurrency"] == 2.0][0]["delta_vs_1.2"]

def s1():
    body = f"""
<div class="row">
  <div class="col" style="flex:0 0 30%">
    <h2>The answer — July to September</h2>
    <div class="hero"><span class="n">508</span><span class="u">paid<br>FTE</span></div>
    <p class="sm" style="margin-top:9px">per month to hold <strong>80% / 20s</strong> phone and
      <strong>80% / 60s</strong> chat at the June run-rate <strong>+10%</strong> seasonal uplift.</p>
    <div class="g2" style="margin-top:14px; gap:14px">
      {tile("Productive hours", f'{bj["productive_hours"]:,.0f}', "per month — the BPO bill")}
      {tile("Contacts", f'{bj["contacts"]/1000:.0f}k', "all languages, all channels")}
    </div>
    <div class="g2" style="margin-top:12px; gap:14px">
      {tile("Scenario range", "462–579", "LOW flat &rarr; HIGH trend")}
      {tile("P10–P90", "425–606", f'σ = {D["sigma"]*100:.1f}%')}
    </div>
  </div>
  <div class="col" style="flex:0 0 40%">
    <h2>A quarter of the requirement is service level, not workload</h2>
    {chart_waterfall()}
    <p class="sm" style="margin-top:4px">A workload model returns <strong>360 FTE</strong> and
      <strong class="crit">misses SLA</strong> — it implicitly assumes 100% occupancy. Erlang C says
      English inbound runs at <strong>{EN_IN["occupancy"]*100:.0f}%</strong>; the idle {(1-EN_IN["occupancy"])*100:.0f}% <em>is</em> the 20-second answer time.</p>
  </div>
  <div class="col" style="flex:0 0 30%">
    <h2>Two levers, both from the same evidence</h2>
    <div class="note" style="margin-bottom:11px">
      <h3>Pool the four non-English queues <span class="accent">−{POOL:.0f} FTE</span></h3>
      <p class="sm tight">German phone runs at 42% occupancy, Italian at 28% — four small queues
      each paying the 80/20 minimum-seat floor separately. All four are already in BPO 3.</p>
    </div>
    <div class="note" style="margin-bottom:11px">
      <h3>Validate chat concurrency <span class="accent">−{CONC:.0f} FTE</span></h3>
      <p class="sm tight">Chat is 39% of the whole operation. The given 1.2 is far below the
      industry 2–3 and repeats on every row — it reads as a placeholder, not a measurement.</p>
    </div>
    <div class="note red">
      <h3>One number needs an owner <span class="crit">±78 FTE</span></h3>
      <p class="sm tight">The workbook states English AHT twice — <strong>908.8s</strong> by reason,
      <strong>709.8s</strong> by channel. Run both ways the answer is <strong>508 vs 585</strong>.
      That is 15% of the plan, unresolvable without the business.</p>
    </div>
  </div>
</div>"""
    return slide(1, "01 · Executive summary", "508 paid FTE per month to meet service level", "", body, 5)


def s2():
    dq = D["dq"]
    rows = "".join(
        f'<tr><td><span class="pill {("pass" if r["status"]=="PASS" else "warn" if r["status"]=="WARN" else "fix")}">'
        f'{"pass" if r["status"]=="PASS" else "warn" if r["status"]=="WARN" else "fix"}</span></td>'
        f'<td>{esc(r["check"])}</td><td class="mute">{esc(clip(r["finding"], 76))}</td></tr>'
        for r in dq[:7])
    body = f"""
<div class="row">
  <div class="col" style="flex:0 0 33%">
    <h2>The chain</h2>
    <table style="font-size:10px; line-height:1.9">
      <tr><td style="width:52%"><strong>contacts × AHT</strong></td><td class="mute">workload hours</td></tr>
      <tr><td><strong>phone &amp; chat → Erlang C</strong></td><td class="accent">concurrent seats</td></tr>
      <tr><td><strong>email &amp; outbound ÷ occupancy</strong></td><td class="mute">seat-equivalent hours</td></tr>
      <tr><td><strong>÷ (1 − 18% shrinkage)</strong></td><td class="mute">paid hours</td></tr>
      <tr><td><strong>÷ 173.33 h per FTE</strong></td><td class="mute">FTE meeting SLA</td></tr>
      <tr><td><strong>÷ tenure efficiency</strong></td><td class="mute">on-floor FTE</td></tr>
      <tr class="tot"><td><strong>+ training class</strong></td><td><strong>paid FTE</strong></td></tr>
    </table>
    <div class="note" style="margin-top:13px">
      <p class="sm tight"><strong>Erlang C returns seats, not FTE.</strong>
      {int(EN_IN["seats_raw"])} concurrent seats × 730 h ÷ 0.82 ÷ 173.33 =
      <strong>{EN_IN["fte"]:.1f} FTE</strong>, against {EN_IN["fte_workload_only"]:.1f} from workload
      alone on the same queue.</p>
    </div>
    <p class="sm mute" style="margin-top:12px">Monthly-average arrival rates make this a <em>floor</em>:
    real intraday peaks and overnight minimum-staffing push interval-level staffing up, never down.</p>
    <div class="note grey" style="margin-top:14px">
      <p class="sm tight"><strong>Everything here is reproducible.</strong> One command regenerates the
      whole plan from the workbook; a second re-verifies it with 72 independent checks, including
      Erlang C against a discrete-event simulation and the full July chain re-derived from raw cells
      through a separate code path. Appendix A5 has the detail.</p>
    </div>
  </div>
  <div class="col" style="flex:0 0 40%">
    <h2>Data quality — 12 checks, every decision logged</h2>
    <table>{rows}</table>
    <p class="sm" style="margin-top:9px"><strong>The validation that passed matters most:</strong>
    the per-reason ticket counts tie to the English contact volume in all six months at a ratio of
    <strong>exactly 1.000000</strong> — so the two sheets describe the same population and the
    reason-mix join is safe.</p>
    <div class="note red" style="margin-top:10px">
      <p class="sm tight"><strong>SLA attainment has fallen 95% → 92% while volume doubled</strong>
      (<span class="mute">February reports 110%, which is impossible</span>). That is the business
      case for this transformation, sitting unused in the source data.</p>
    </div>
  </div>
  <div class="col" style="flex:0 0 27%">
    <h2>Two open questions, priced</h2>
    <h3>1 · Which English AHT is authoritative?</h3>
    <p class="sm">Reason-level <strong>908.8s</strong> vs channel-level <strong>709.8s</strong>.
      Both cannot be right — 25% of English contacts are outbound at 107s.
      <span class="crit">Worth 78 FTE (15%).</span></p>
    <h3 style="margin-top:11px">2 · Is chat concurrency measured or assumed?</h3>
    <p class="sm">1.2 on every BPO and every language, under a header that says "English".
      <span class="crit">Worth {CONC:.0f} FTE.</span></p>
    <h2 style="margin-top:15px">Also requested</h2>
    <ul class="sm">
      <li>24+ months of history — 6 cannot support a seasonal model</li>
      <li>15/30-minute arrival data — monthly Erlang is a floor</li>
      <li>What changed in March — system, market, or demand?</li>
      <li>Cost per productive hour by BPO — to rank levers in €</li>
      <li>True outbound volumes — the mirrored columns cannot be real</li>
    </ul>
    <div class="note grey" style="margin-top:12px">
      <p class="xs tight"><strong>Structural finding:</strong> 45 reason codes collapse to
      <strong>{D["clusters"]}</strong> distinct AHT profiles, and <strong>{D["crossing"]}</strong>
      of those clusters cross reason families — AHT is measured on a different taxonomy than the
      reason codes, and neither nests inside the other.</p>
    </div>
  </div>
</div>"""
    return slide(2, "02 · Method", "How the number is built — and what the data would not tell us",
                 "", body, 5)


def s3():
    bl = {r["language"]: r for r in D["by_lang"]}
    bp = {r["bpo"]: r for r in D["by_bpo"]}
    lang_rows = "".join(
        f'<tr><td><strong>{esc(l)}</strong></td><td class="n">{bl[l]["contacts"]:,.0f}</td>'
        f'<td class="n">{bl[l]["ph"]:,.0f}</td><td class="n">{bl[l]["fwo"]:.0f}</td>'
        f'<td class="n"><strong>{bl[l]["fte"]:.0f}</strong></td></tr>'
        for l in ["English", "German", "Spanish", "French", "Italian"])
    scen = "".join(
        f'<tr><td><strong>{s}</strong></td>'
        + "".join(f'<td class="n">{B[(s,m)]["fte_paid"]:.0f}</td>' for m in ("Jul", "Aug", "Sep"))
        + f'<td class="n mute">{note}</td></tr>'
        for s, note in (("LOW", "June run-rate, no uplift"),
                        ("BASE", "June × 1.10, held flat"),
                        ("HIGH", "English on trend × 1.10")))
    body = f"""
<div class="row">
  <div class="col" style="flex:0 0 46%">
    <h2>Volume — six months of actuals, three of forecast</h2>
    {chart_fan()}
    <p class="sm" style="margin-top:6px"><strong>The baseline is June, not an average.</strong> March is
    a <span class="crit">structural break</span>, not seasonality — all five languages step together
    (1.60×–2.06×) across every channel and all 49 reason codes. Consumer demand does not double in
    lockstep across five independent markets; a reporting or scope change does. Either way the action
    is the same: anchor on post-break months only.</p>
    <p class="sm"><strong>BASE is held flat</strong> across Jul–Sep — not a claim that demand is flat,
    but a refusal to invent a summer curve from six months containing a level shift. HIGH is the
    summer-peak case; slide 5 carries the trigger that switches to it.</p>
  </div>
  <div class="col" style="flex:0 0 27%">
    <h2>Capacity by language — BASE, per month</h2>
    <table>
      <tr><th>Language</th><th class="n">Contacts</th><th class="n">Prod h</th>
          <th class="n">Workload<br>FTE</th><th class="n">SLA<br>FTE</th></tr>
      {lang_rows}
      <tr class="tot"><td>Total</td><td class="n">{bj["contacts"]:,.0f}</td>
        <td class="n">{bj["productive_hours"]:,.0f}</td><td class="n">{bj["fte_workload_only"]:.0f}</td>
        <td class="n">{bj["fte_sla"]:.0f}</td></tr>
    </table>
    <h2 style="margin-top:16px">By BPO — the vendor brief</h2>
    <table>
      <tr><th>BPO</th><th>Languages</th><th class="n">FTE</th><th class="n">Prod h</th></tr>
      <tr><td><strong>BPO 3</strong></td><td class="mute">DE IT ES FR</td>
          <td class="n"><strong>{bp["BPO 3"]["fte"]:.0f}</strong></td><td class="n">{bp["BPO 3"]["ph"]:,.0f}</td></tr>
      <tr><td><strong>BPO 1</strong></td><td class="mute">English 50%</td>
          <td class="n"><strong>{bp["BPO 1"]["fte"]:.0f}</strong></td><td class="n">{bp["BPO 1"]["ph"]:,.0f}</td></tr>
      <tr><td><strong>BPO 2</strong></td><td class="mute">English 50%</td>
          <td class="n"><strong>{bp["BPO 2"]["fte"]:.0f}</strong></td><td class="n">{bp["BPO 2"]["ph"]:,.0f}</td></tr>
    </table>
    <p class="xs mute" style="margin-top:6px">English AHT is the BPO1/BPO2 50/50 blend, so total
    capacity does not depend on how English is split between the two vendors.</p>
  </div>
  <div class="col" style="flex:0 0 27%">
    <h2>Scenarios — paid FTE</h2>
    <table>
      <tr><th>Case</th><th class="n">Jul</th><th class="n">Aug</th><th class="n">Sep</th><th class="n">Basis</th></tr>
      {scen}
    </table>
    {chart_intervals()}
    <div class="note" style="margin-top:6px">
      <p class="sm tight"><strong>Do not hire to a point estimate.</strong> Contract a
      <strong>~490 FTE core</strong> and hold a cross-trained flex pool of <strong>60–100</strong>
      against the P90, released monthly on the re-forecast trigger.</p>
    </div>
    <p class="xs mute" style="margin-top:8px">Backfill alone runs at
    <strong>{bj["monthly_backfill_hires"]:.0f} hires/month</strong> at 36% annual attrition — with a
    4-week class and a 3-month ramp, recruitment must lead the forecast by a full quarter.</p>
  </div>
</div>"""
    return slide(3, "03 · Task 1a — Capacity forecast",
                 "Forecast, capacity and the range around it", "", body, 5)


def s4():
    d = D["deflect"]
    dfl_rows = "".join(
        f'<tr><td>{r["share_moved"]*100:.0f}%</td><td class="n">{int(r["Inbound_seats"])}</td>'
        f'<td class="n">{int(r["Chat_seats"])}</td><td class="n">{r["combined_fte"]:.1f}</td>'
        f'<td class="n {"crit" if r["delta_fte"]>0 else "mute"}">'
        f'{"+" if r["delta_fte"]>0 else ""}{r["delta_fte"]:.1f}</td></tr>' for r in d)
    body = f"""
<div class="row">
  <div class="col" style="flex:0 0 40%">
    <h2>Strategy 1 · Pool the four non-English queues <span class="accent">−{POOL:.1f} FTE (10%)</span></h2>
    {chart_occupancy()}
    <p class="sm" style="margin-top:12px"><strong>The occupancy column is the finding.</strong> Those
    queues are not idle by choice — 80/20 on a queue of 0.84 erlangs, staffed 24/7, needs 3 seats no
    matter how few calls arrive. <strong>Four small queues pay that floor four times.</strong></p>
    <table style="margin-top:10px">
      <tr><th>Queue</th><th class="n">Siloed</th><th class="n">Pooled</th><th class="n">SL</th><th class="n">Saved</th></tr>
      {"".join(f'<tr><td><strong>{p["channel"]}</strong> <span class="mute">DE IT ES FR</span></td>'
               f'<td class="n">{int(p["siloed_seats_raw"])} seats</td>'
               f'<td class="n"><strong>{int(p["pooled_seats_raw"])}</strong></td>'
               f'<td class="n good">{p["pooled_service_level"]*100:.0f}%</td>'
               f'<td class="n"><strong>{p["fte_saved"]:.1f}</strong></td></tr>' for p in D["pools"])}
      <tr class="tot"><td>Total</td><td colspan="3" class="mute" style="font-weight:400">
        ≈ 8,900 productive hours off the BPO 3 bill</td><td class="n">{POOL:.1f}</td></tr>
    </table>
  </div>
  <div class="col" style="flex:0 0 33%">
    <h2>Why it works, and what it costs</h2>
    <p class="sm">All four languages already sit in BPO 3, so this is a routing
    and skilling change, not a vendor change. Both pooled queues were <strong>re-solved through the
    same Erlang engine</strong> — the service level goes up, not down. Phase it: start with the
    overnight window, where the floors bite hardest.</p>
    <div class="note red" style="margin-top:13px">
      <h3>Tested and rejected: deflect phone → chat</h3>
      <p class="sm tight">The intuitive lever. Modelled end-to-end it <strong>costs</strong> FTE,
      because English chat consumes <strong>958 agent-seconds</strong> per contact against phone's
      <strong>458</strong>.</p>
      <table style="margin-top:6px">
        <tr><th>Shift</th><th class="n">Phone</th><th class="n">Chat</th><th class="n">FTE</th><th class="n">Δ</th></tr>
        {dfl_rows}
      </table>
    </div>
  </div>
  <div class="col" style="flex:0 0 27%">
    <h2>Strategy 2 · Chat concurrency <span class="accent">−{CONC:.1f} FTE (15%)</span></h2>
    {chart_conc()}
    <p class="sm" style="margin-top:2px">Chat is <strong>188 FTE — 39% of the entire operation</strong>,
    the largest single line in the plan. The given 1.2 sits under a column headed "Chat concurrency
    <em>English</em>" yet repeats on every BPO and every language.</p>
    <p class="sm"><strong>Ask whether it was measured.</strong> If it was, the tooling or the routing
    rules are the constraint and there is a clear case to fix them. If it is a placeholder, the plan
    carries a {CONC:.0f} FTE error. Either answer is worth having.</p>
    <div class="note grey" style="margin-top:11px">
      <p class="xs tight"><strong>Where the real prize is.</strong> The top three handling-hour drivers
      — <strong>1.1 Availability</strong> (5,026 h), <strong>3.3 Meeting point</strong> (4,712 h) and
      <strong>3.1 Voucher not received</strong> (3,844 h, CSAT 65%) — are high-volume, low-CSAT and
      automatable. That is a product ask, not a scheduling change, so it sits beside these two rather
      than among them.</p>
    </div>
  </div>
</div>"""
    return slide(4, "04 · Task 1b — Optimisation",
                 "Two strategies the arithmetic supports — and one it kills", "", body, 5)


def s5():
    body = f"""
<div class="row">
  <div class="col" style="flex:0 0 38%">
    <h2>2a · 30 / 60 / 90</h2>
    <h3>0–30 · Decide, then build</h3>
    <p class="sm tight">Four decisions gate everything downstream — none are technical:
    <strong>who owns the AHT definition</strong> (the ±78 FTE question is unresolvable without an
    owner); <strong>forecast granularity</strong> (language × channel × interval — anything coarser
    cannot produce an SLA-compliant number); <strong>who signs off assumptions</strong> and how often;
    <strong>where the model lives</strong>. Baseline the manual model's accuracy in week 1 — without
    it there is nothing to beat.</p>
    <h3 style="margin-top:9px">31–60 · Shadow, don't switch</h3>
    <p class="sm tight">New model runs in parallel on English — 59% of volume, all of the growth,
    all of the forecast risk (σ 19.5% vs under 9% elsewhere). Weekly reconciliation against the
    manual plan. The manual plan stays <em>the</em> plan.</p>
    <h3 style="margin-top:9px">61–90 · Cut over, then extend</h3>
    <p class="sm tight">English cuts over once it has beaten the baseline for six consecutive weeks.
    DE/IT/ES/FR follow. Escalation and override rules written down before, not after.</p>
    <div class="note" style="margin-top:9px">
      <p class="sm tight"><strong>"Done" at 90 days:</strong> the model produces the weekly plan
      unaided, beats the manual baseline on MAPE for six straight weeks, the three specialists run it
      without me, and every assumption is versioned and dated.</p>
    </div>
  </div>
  <div class="col" style="flex:0 0 24%">
    <h2>2b · Bringing three specialists along</h2>
    <p class="sm"><strong>Assess with an artefact, not an opinion.</strong> Give all three the same
    task on this dataset — clean it, forecast one language, document the assumptions. What comes back
    places them on forecasting depth × AI fluency far better than a conversation does.</p>
    <p class="sm"><strong>Set the expectation explicitly:</strong> AI is the tool, they own the
    judgement. The two things AI got wrong in this exercise were both plausible-sounding domain
    defaults — exactly what an expert reviewer catches and a novice ships.</p>
    <p class="sm"><strong>Protect BAU:</strong> six weeks of shadow running, paired shadowing, and a
    written prompt playbook. Capability is built <em>alongside</em> the plan, never instead of it.</p>
    <h2 style="margin-top:14px">2c · What I would measure</h2>
    <p class="sm tight"><strong>Leading</strong> — inputs with a named owner and a dated assumption ·
    time to produce a plan · % of runs reproducible from source · open data-quality items
    (<strong>starts at 12</strong>) · specialists running it solo (0 → 3).</p>
    <p class="sm tight" style="margin-top:5px"><strong>Lagging</strong> — forecast MAPE <em>and
    BIAS</em> by language · SLA attainment (baseline <strong>92%, falling</strong>) · FTE plan-vs-actual ·
    shrinkage by bucket · cost per contact.</p>
    <div class="note" style="margin-top:8px">
      <p class="sm tight"><strong>Lead with bias, not accuracy.</strong> Accuracy hides direction, and
      direction is what a workload-only model gets wrong — it is short by 34%, every single month.</p>
    </div>
  </div>
  <div class="col" style="flex:0 0 38%">
    <h2>1c · How AI was used — and where it was wrong</h2>
    <table>
      <tr><th style="width:26%">Where</th><th style="width:16%">Verdict</th><th>What happened</th></tr>
      <tr><td><strong>Sheet parsing, anomaly sweep, reconciliation</strong></td>
          <td><span class="pill pass">accepted</span></td>
          <td class="mute">Deterministic Python. I verified the cross-sheet reconciliation independently.</td></tr>
      <tr><td><strong>Erlang C implementation</strong></td>
          <td><span class="pill pass">accepted</span></td>
          <td class="mute">After checking it by hand and against a simulation. Never ship a staffing formula you have not verified.</td></tr>
      <tr><td><strong>First-pass model structure</strong></td>
          <td><span class="pill warn">rejected</span></td>
          <td class="mute">Produced workload ÷ shrinkage <em>and</em> a separate Erlang table that never met. Meets the brief only once occupancy feeds the FTE.</td></tr>
      <tr><td><strong>"Deflect phone → chat"</strong></td>
          <td><span class="pill warn">rejected</span></td>
          <td class="mute">Generic WFM instinct contradicted by this dataset's AHTs. Caught by modelling it, not by reading it.</td></tr>
      <tr><td><strong>Reason-taxonomy clustering</strong></td>
          <td><span class="pill fix">changed</span></td>
          <td class="mute">Concluded "AHT is family-level"; testing showed clusters cross families in 6 of 11 groups.</td></tr>
      <tr><td><strong>Narrative drafting</strong></td>
          <td><span class="pill fix">changed</span></td>
          <td class="mute">Defaulted to hedging. An ops audience needs a number and a recommendation.</td></tr>
    </table>
    <div class="note red" style="margin-top:11px">
      <p class="sm tight"><strong>What I would do differently.</strong> State the acceptance test
      <em>before</em> generating — "the FTE number must satisfy the SLA constraint" — rather than
      reviewing after. AI is reliable at parsing, arithmetic and structure, and unreliable at knowing
      <strong>which of two conflicting numbers in a workbook is the real one</strong>. That gap is a
      judgement call requiring the business, and no amount of prompting closes it.</p>
    </div>
    <p class="xs mute" style="margin-top:8px">Tools: Claude (Opus 5) in Claude Code for the analysis,
    the Python model and this deck. The verification suite found <strong>three real defects in my own
    model</strong> — a growth test that flagged a declining language as growing, a HIGH scenario that
    could land below BASE, and a mis-reported trend slope — all fixed at source.</p>
  </div>
</div>"""
    return slide(5, "05 · Section 2 + Task 1c", "Leading the transformation — and how AI was actually used",
                 "", body, 5)


# ================================================================ APPENDIX
def a1():
    qs = sorted(D["queues"], key=lambda r: (r["language"] != "English", r["language"], r["channel"]))
    rows = "".join(
        f'<tr><td><strong>{esc(r["language"])}</strong></td><td>{esc(r["channel"])}</td>'
        f'<td class="n">{r["contacts"]:,.0f}</td><td class="n">{r["aht"]:,.0f}</td>'
        f'<td>{"Erlang C" if r["model"]=="ErlangC" else "deferred"}</td>'
        f'<td class="n">{r["erlangs"]:.2f}' if r["model"] == "ErlangC" else
        f'<tr><td><strong>{esc(r["language"])}</strong></td><td>{esc(r["channel"])}</td>'
        f'<td class="n">{r["contacts"]:,.0f}</td><td class="n">{r["aht"]:,.0f}</td>'
        f'<td>deferred</td><td class="n mute">—' for r in qs)
    rows = ""
    for r in qs:
        rt = r["model"] == "ErlangC"
        rows += (f'<tr><td><strong>{esc(r["language"])}</strong></td><td>{esc(r["channel"])}</td>'
                 f'<td class="n">{r["contacts"]:,.0f}</td><td class="n">{r["aht"]:,.0f}</td>'
                 f'<td class="mute">{"Erlang C" if rt else "deferred"}</td>'
                 f'<td class="n">{f"{r["erlangs"]:.2f}" if rt else "—"}</td>'
                 f'<td class="n">{f"{int(r["seats_raw"])}" if rt else "—"}</td>'
                 f'<td class="n">{r["seats"]:.1f}</td>'
                 f'<td class="n">{r["occupancy"]*100:.0f}%</td>'
                 f'<td class="n">{f"{r["service_level"]*100:.1f}%" if rt else "—"}</td>'
                 f'<td class="n">{r["workload_hours"]:,.0f}</td>'
                 f'<td class="n">{r["productive_hours"]:,.0f}</td>'
                 f'<td class="n">{r["fte_workload_only"]:.1f}</td>'
                 f'<td class="n"><strong>{r["fte"]:.1f}</strong></td></tr>')
    body = f"""
<div class="row">
  <div class="col" style="flex:0 0 68%">
  <table class="dense">
    <tr><th>Language</th><th>Channel</th><th class="n">Contacts</th><th class="n">AHT s</th>
        <th>Model</th><th class="n">Erlangs</th><th class="n">Seats</th><th class="n">FTE-eq<br>seats</th>
        <th class="n">Occ</th><th class="n">Achieved<br>SL</th><th class="n">Workload<br>h</th>
        <th class="n">Productive<br>h</th><th class="n">Workload<br>FTE</th><th class="n">SLA<br>FTE</th></tr>
    {rows}
    <tr class="tot"><td>Total</td><td></td><td class="n">{bj["contacts"]:,.0f}</td><td></td><td></td>
      <td></td><td></td><td></td><td></td><td></td><td class="n">{bj["workload_hours"]:,.0f}</td>
      <td class="n">{bj["productive_hours"]:,.0f}</td><td class="n">{bj["fte_workload_only"]:.1f}</td>
      <td class="n">{bj["fte_sla"]:.1f}</td></tr>
  </table>
  </div>
  <div class="col" style="flex:0 0 32%">
    <h2>Where the 484 FTE sits</h2>{chart_channel_mix()}
    <p class="sm" style="margin-top:10px"><strong>Chat is the single largest line at 39%</strong>,
    which is why concurrency is the biggest available lever.</p>
    <p class="sm"><strong>Outbound is 4%</strong> despite carrying a quarter of all contacts — its AHT
    is 107s against email's 1,150s. That is also why the mirrored outbound column matters far less to
    capacity than it does to data credibility.</p>
    <p class="sm"><strong>Email at 159 FTE is modelled as deferred work</strong> at 85% planned
    occupancy — an explicit assumption, not from the workbook. An 80%-in-120-minute target is close to
    real-time, so if the business treats email as a live queue rather than a backlog, this line grows.</p>
    <div class="note grey" style="margin-top:10px">
      <p class="xs tight">The <strong>deferred</strong> rows carry no Erlang figures by design: a
      120-minute target is a backlog commitment, not a queue discipline, so seats are derived from
      hours and planned occupancy instead.</p>
    </div>
  </div>
</div>"""
    return slide("A1", "Appendix A1", "Every queue, end to end — BASE, July",
                 "The full working behind slide 3. Occupancy below 100% on the Erlang rows is the cost of the service level.", body, 6, True)


def a2():
    rows = "".join(
        f'<tr><td class="n mute">{i+1}</td>'
        f'<td><span class="pill {("pass" if r["status"]=="PASS" else "warn" if r["status"]=="WARN" else "fix")}">'
        f'{"pass" if r["status"]=="PASS" else "warn" if r["status"]=="WARN" else "fix"}</span></td>'
        f'<td><strong>{esc(r["check"])}</strong></td><td class="mute">{esc(r["finding"])}</td>'
        f'<td>{esc(r["decision"])}</td><td class="mute">{esc(r["impact"])}</td></tr>'
        for i, r in enumerate(D["dq"]))
    rows = rows.replace("<table>", "")
    body = f"""
<table class="dense">
  <tr><th class="n" style="width:2%">#</th><th style="width:5%">Status</th><th style="width:17%">Check</th>
      <th style="width:28%">Finding</th><th style="width:26%">Decision</th><th>Capacity impact</th></tr>
  {rows}
</table>
<p class="sm" style="margin-top:10px"><strong>Grading matters.</strong> A ±2-contact rounding residue
and a 110% SLA reading are both "wrong", but only one changes a decision. Every row above carries its
own materiality, so the reader can see which findings were acted on and which were merely noted.</p>"""
    return slide("A2", "Appendix A2", "Data-quality log — all 12 checks",
                 "Condensed to five rows on slide 2. This is the full log, including the checks that passed.", body, 6, True)


def a3():
    g = {r["language"]: r for r in D["growth"]}
    rows = "".join(
        f'<tr><td><strong>{esc(l)}</strong></td><td class="n">{g[l]["baseline"]:,.0f}</td>'
        f'<td class="n">{g[l]["post_break_change"]*100:+.1f}%</td>'
        f'<td class="n">{g[l]["trend_per_month"]:+,.0f}</td>'
        f'<td class="n">{g[l]["r2"]:.2f}</td><td class="n">{g[l]["sigma_logret"]*100:.1f}%</td>'
        f'<td>{"<strong class=\'accent\'>yes</strong>" if g[l]["growing"] else "<span class=\'mute\'>no</span>"}</td></tr>'
        for l in ["English", "German", "Spanish", "French", "Italian"])
    iv = {round(r["percentile"], 2): r for r in D["intervals"]}
    ivrows = "".join(
        f'<tr><td>P{int(p*100)}</td><td class="n">{iv[p]["multiplier"]:.3f}</td>'
        f'<td class="n">{iv[p]["contacts"]:,.0f}</td>'
        f'<td class="n{" tot" if p==0.5 else ""}">{bj["fte_paid"]*iv[p]["multiplier"]:.0f}</td></tr>'
        for p in (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95))
    body = f"""
{chart_small_multiples()}
<div class="row" style="margin-top:14px">
  <div class="col" style="flex:0 0 46%">
    <h2>Per-language growth test — post-break window</h2>
    <table>
      <tr><th>Language</th><th class="n">June</th><th class="n">Mar→Jun</th><th class="n">OLS slope<br>/month</th>
          <th class="n">R²</th><th class="n">σ</th><th>Growing?</th></tr>
      {rows}
    </table>
    <p class="sm" style="margin-top:8px">A language earns the trend extrapolation in HIGH only if its
    slope is <strong>positive</strong>, exceeds 3% of baseline, and fits at R² &gt; 0.4. Only English
    qualifies. <span class="mute">An earlier version of this test keyed off the absolute slope, which
    flagged <em>declining</em> German as growing and produced a HIGH case below BASE — caught by the
    verification suite.</span></p>
  </div>
  <div class="col" style="flex:0 0 26%">
    <h2>Confidence band — July</h2>
    <table>
      <tr><th>Pctile</th><th class="n">Mult</th><th class="n">Contacts</th><th class="n">Paid FTE</th></tr>
      {ivrows}
    </table>
    <p class="xs mute" style="margin-top:6px">Log-normal around the BASE median, σ = {D["sigma"]*100:.1f}%
    from month-over-month log returns with the March break excluded. FTE is linear in volume, so the
    same multipliers carry through.</p>
  </div>
  <div class="col" style="flex:0 0 28%">
    <h2>Monthly re-forecast trigger</h2>
    <table>
      <tr><th>Signal</th><th>Threshold</th><th>Action</th></tr>
      <tr><td>English vs BASE</td><td class="mute">&gt; +8%, 2 weeks</td><td>Switch to HIGH; release flex pool</td></tr>
      <tr><td>English vs BASE</td><td class="mute">&lt; −8%, 2 weeks</td><td>Switch to LOW; freeze pipeline</td></tr>
      <tr><td>SLA attainment</td><td class="mute">&lt; 90%, 2 weeks</td><td>Immediate re-forecast</td></tr>
      <tr><td>AHT drift</td><td class="mute">±5% vs plan</td><td>Re-baseline AHT, not volume</td></tr>
    </table>
    <div class="note red" style="margin-top:10px">
      <p class="sm tight">The SLA trigger already fired — <strong>May came in at 90%</strong>. A model
      that only produces a number, without the rule for when the number is wrong, is not operational.</p>
    </div>
  </div>
</div>"""
    return slide("A3", "Appendix A3", "Forecast detail — why only English gets a trend",
                 "", body, 6, True)


def a4():
    body = f"""
<div class="row">
  <div class="col" style="flex:0 0 34%">
    <h2>The mistake worth understanding</h2>
    <p class="sm">A workload model divides work by time and calls the result headcount. That is correct
    only if every agent is busy every second. <strong>No queue with a service-level target can run that
    way</strong> — to answer 80% of calls within 20 seconds, somebody has to be free when the call
    lands. The idle time is not waste; it is the product.</p>
    <table style="margin-top:10px">
      <tr><th>English inbound, BASE July</th><th class="n"></th></tr>
      <tr><td>Contacts</td><td class="n">{EN_IN["contacts"]:,.0f}</td></tr>
      <tr><td>AHT (BPO1/2 blend)</td><td class="n">{EN_IN["aht"]:.1f} s</td></tr>
      <tr><td>Workload hours</td><td class="n">{EN_IN["workload_hours"]:,.0f}</td></tr>
      <tr><td>Offered load</td><td class="n">{EN_IN["erlangs"]:.2f} erlangs</td></tr>
      <tr><td>Seats for 80/20</td><td class="n"><strong>{int(EN_IN["seats_raw"])}</strong></td></tr>
      <tr><td>Achieved service level</td><td class="n good">{EN_IN["service_level"]*100:.1f}%</td></tr>
      <tr><td>Occupancy at {int(EN_IN["seats_raw"])} seats</td><td class="n accent">{EN_IN["occupancy"]*100:.1f}%</td></tr>
      <tr><td class="mute">Workload FTE (÷ shrinkage only)</td><td class="n mute">{EN_IN["fte_workload_only"]:.1f}</td></tr>
      <tr class="tot"><td>FTE that actually meets SLA</td><td class="n">{EN_IN["fte"]:.1f}</td></tr>
    </table>
    <p class="sm" style="margin-top:8px"><strong>+{EN_IN["fte"]/EN_IN["fte_workload_only"]*100-100:.0f}%
    on one queue.</strong> Across all ten real-time queues it is +{SLA_UPLIFT*100:.0f}% on the total — the gap between a plan that hits SLA and one that does not.</p>
  </div>
  <div class="col" style="flex:0 0 33%">
    <h2>Why small queues cost so much more</h2>
    <p class="sm">Occupancy is not a property of the agents — it is a property of the <em>queue size</em>.
    A large queue smooths its own arrivals; a small one cannot, so it must hold spare seats against
    randomness that a bigger pool would absorb.</p>
    <table style="margin-top:9px">
      <tr><th>Queue</th><th class="n">Erlangs</th><th class="n">Seats</th><th class="n">Occupancy</th></tr>
      <tr><td>Italian inbound</td><td class="n">0.84</td><td class="n">3</td><td class="n crit">27.9%</td></tr>
      <tr><td>French inbound</td><td class="n">0.93</td><td class="n">3</td><td class="n crit">30.9%</td></tr>
      <tr><td>Spanish inbound</td><td class="n">1.14</td><td class="n">3</td><td class="n">38.1%</td></tr>
      <tr><td>German inbound</td><td class="n">1.26</td><td class="n">3</td><td class="n">41.9%</td></tr>
      <tr class="tot"><td>All four, pooled</td><td class="n">4.16</td><td class="n">7</td><td class="n good">59.5%</td></tr>
      <tr><td>English inbound</td><td class="n">{EN_IN["erlangs"]:.2f}</td><td class="n">{int(EN_IN["seats_raw"])}</td><td class="n">{EN_IN["occupancy"]*100:.1f}%</td></tr>
    </table>
    <p class="sm" style="margin-top:8px">This is the whole argument for Strategy 1, and it is invisible
    to a workload model — which would report these five queues as equally efficient per contact.</p>
    <div class="note" style="margin-top:10px">
      <p class="sm tight"><strong>Doubling volume does not double FTE.</strong> The verification suite
      checks this directly: 2× the contacts needs <strong>1.81×</strong> the FTE. Scale is a real
      economy in this model, which is exactly why pooling pays.</p>
    </div>
  </div>
  <div class="col" style="flex:0 0 33%">
    <h2>Where this model is deliberately conservative</h2>
    <ul class="sm">
      <li><strong>Monthly-average arrival rates.</strong> Erlang is run on a flat 24/7 rate. Real
      intraday peaks and overnight minimum-staffing floors make interval-level staffing
      <em>higher</em>, never lower. <strong>508 is a floor.</strong></li>
      <li><strong>Shrinkage held flat at 18%.</strong> BPO 3 carries 7% vacation and Jul–Sep is peak
      holiday. A +1–2 point summer adjustment adds 6–12 FTE (see sensitivity below).</li>
      <li><strong>Outbound kept at face value</strong> despite mirroring inbound exactly. Removing it
      would cut ~8 FTE; keeping it is the conservative call.</li>
      <li><strong>Email at 85% planned occupancy</strong> — an assumption, not from the data.</li>
    </ul>
    <h2 style="margin-top:14px">Shrinkage sensitivity</h2>
    <table>
      <tr><th>Total shrinkage</th><th class="n">SLA FTE</th><th class="n">Δ</th></tr>
      <tr><td>16%</td><td class="n">472.7</td><td class="n mute">−11.5</td></tr>
      <tr><td>17%</td><td class="n">478.4</td><td class="n mute">−5.8</td></tr>
      <tr class="tot"><td>18% <span class="mute" style="font-weight:400">— as given</span></td><td class="n">484.2</td><td class="n">—</td></tr>
      <tr><td>19%</td><td class="n">490.2</td><td class="n crit">+6.0</td></tr>
      <tr><td>20%</td><td class="n">496.3</td><td class="n crit">+12.1</td></tr>
    </table>
    <p class="sm" style="margin-top:8px">Controllable buckets (break + lunch 6%, meetings 1%,
    coaching 1%) total <strong>8 points</strong>; vacation and sick are entitlement. "Cut shrinkage"
    is generic — <strong>"reclaim 1–2 points from break scheduling and move coaching to low-demand
    hours"</strong> is worth 6–12 FTE and is actionable this quarter.</p>
    <div class="note grey" style="margin-top:11px">
      <p class="sm tight">Note the vendor difference the flat 18% hides: <strong>BPO 3 carries 7%
      vacation and 3% sick; BPO 1 and 2 carry 5% each.</strong> Same total, different labour model —
      and BPO 3's vacation line is the one that rises in the quarter being planned.</p>
    </div>
  </div>
</div>"""
    return slide("A4", "Appendix A4", "Why service level costs 34% — the Erlang mechanics",
                 "", body, 6, True)


def a5():
    body = f"""
<div class="row">
  <div class="col" style="flex:0 0 32%">
    <h2>The model</h2>
    <table style="font-size:8px">
      <tr><th style="width:38%">Module</th><th>Responsibility</th></tr>
      <tr><td><strong>config.py</strong></td><td class="mute">Every assumption in one frozen dataclass — nothing hard-coded downstream</td></tr>
      <tr><td><strong>erlang.py</strong></td><td class="mute">Erlang B/C, service level, ASA, staffing solver, normal inverse CDF</td></tr>
      <tr><td><strong>loader.py</strong></td><td class="mute">Schema-driven reader; refuses the hidden sheet; finds languages and channels by pattern, not cell address</td></tr>
      <tr><td><strong>clean.py</strong></td><td class="mute">12 data-quality checks &rarr; structured log</td></tr>
      <tr><td><strong>forecast.py</strong></td><td class="mute">Break detection, growth test, scenarios, confidence bands</td></tr>
      <tr><td><strong>capacity.py</strong></td><td class="mute">Workload &rarr; Erlang &rarr; seats &rarr; FTE &rarr; paid headcount, by BPO</td></tr>
      <tr><td><strong>optimise.py</strong></td><td class="mute">Each lever re-solved through the same engine</td></tr>
      <tr><td><strong>report.py</strong></td><td class="mute">16-sheet Excel export</td></tr>
    </table>
    <p class="sm" style="margin-top:9px"><strong>Automation was the point.</strong> Drop in next
    month's workbook and the plan regenerates: languages, channels and months are discovered from the
    sheet, and every assumption is a config value. The verification suite proves it by re-running with
    a language removed and with every constant altered.</p>
    <div class="note grey" style="margin-top:9px">
      <p class="xs tight" style="font-family:monospace">python run_model.py<br>
      python run_model.py --aht-source reason<br>
      python crosscheck.py</p>
    </div>
  </div>
  <div class="col" style="flex:0 0 36%">
    <h2>Verification — 72 checks, all passing</h2>
    <table style="font-size:8px">
      <tr><th style="width:22%">Layer</th><th>What is actually proved</th></tr>
      <tr><td><strong>Erlang B / C</strong></td><td class="mute">Recursion vs the textbook closed form (max diff <strong>1.1e-16</strong>); Erlang C vs the M/M/c stationary distribution derived independently (<strong>&lt;1e-12</strong>)</td></tr>
      <tr><td><strong>Simulation</strong></td><td class="mute">Erlang C vs a <strong>discrete-event M/M/c simulation</strong> — 5 replications × 300k arrivals per case; the analytic value sits inside a 3σ band on both service level and ASA</td></tr>
      <tr><td><strong>Solver</strong></td><td class="mute">Returns the <strong>minimal</strong> feasible seat count; service level monotone in seats</td></tr>
      <tr><td><strong>Queueing</strong></td><td class="mute">Little's Law <em>L<sub>q</sub> = λW<sub>q</sub></em> holds exactly</td></tr>
      <tr><td><strong>Raw cells</strong></td><td class="mute">The entire July chain re-derived <strong>from worksheet cells through a separate code path</strong> — matches to 1e-6</td></tr>
      <tr><td><strong>Invariants</strong></td><td class="mute">Every queue achieves ≥80% (min 80.37%); queue FTE sums exactly to the roll-up; the BPO split re-aggregates with <strong>zero</strong> FTE lost; LOW ≤ BASE ≤ HIGH</td></tr>
      <tr><td><strong>HR maths</strong></td><td class="mute">Attrition compounds to 36.00%/yr; tenure efficiency matches a 3,000-iteration cohort simulation</td></tr>
      <tr><td><strong>Levers</strong></td><td class="mute">Each 1b strategy <strong>re-solved, not asserted</strong> — including the one that came back negative</td></tr>
    </table>
  </div>
  <div class="col" style="flex:0 0 32%">
    <h2>What verification actually caught</h2>
    <p class="sm">Three real defects <strong>in my own model</strong>, all fixed at source:</p>
    <ul class="sm">
      <li>The growth test keyed off <strong>|slope|</strong>, so <em>declining</em> German qualified as
      "growing" — and HIGH came out <strong>below</strong> BASE.</li>
      <li>The reported trend was a one-step projection (6,397/mo) rather than the OLS slope
      (<strong>16,869/mo</strong>).</li>
      <li>A fourth failure surfaced the ±2-contact residue between the channel rows and their own
      totals — which became data-quality finding #1 and forced an explicit decision about which row to
      trust.</li>
    </ul>
    <div class="note" style="margin-top:10px">
      <p class="sm tight">One "failure" turned out to be wrong in the <em>test</em>, not the code: a
      reference value typed from memory. Four independent derivations — closed form, via Erlang B, the
      stationary distribution, and the simulation — agreed to <strong>1e-12</strong>. The test was
      corrected, not the model.</p>
    </div>
    <p class="sm" style="margin-top:12px"><strong>Why this belongs in the submission.</strong> A
    forecast is a number somebody staffs against. The useful question is not "is it right?" but "what
    would have to be true for it to be wrong, and did you check?" Every figure in this deck is
    generated by the model — the deck reads the model's own output, so the two cannot drift apart.</p>
    <div class="note" style="margin-top:12px">
      <p class="sm tight"><strong>The honest limit.</strong> Verification proves the model computes
      what it claims. It cannot prove the inputs are right — and two of them are not yet settled.
      That is why the two open questions carry FTE price tags on slide 2 rather than being quietly
      resolved by assumption.</p>
    </div>
  </div>
</div>"""
    return slide("A5", "Appendix A5", "The model and how it was verified",
                 "", body, 6, True)


def a6():
    a = D["assumptions"]
    rows = [("Hours per FTE per month", "173.33", "=40 × 52 ÷ 12", "'Other information' B2"),
            ("Total shrinkage", "18%", "divisor 0.82", "'Shrinkage', identical all BPOs"),
            ("Operating hours per month", "730", "24/7 → 8,760 ÷ 12", "'Other information' B7"),
            ("Phone SLA", "80% ≤ 20 s", "Erlang C", "B8"),
            ("Chat SLA", "80% ≤ 60 s", "Erlang C, ÷ concurrency", "B9"),
            ("Email SLA", "80% ≤ 120 min", "deferred model", "B10"),
            ("Chat concurrency", "1.2", "<span class='crit'>open question — worth 75 FTE</span>", "'AHT Assumptions' G column"),
            ("Deferred occupancy", "85%", "<span class='crit'>modelling assumption — not in the data</span>", "—"),
            ("Seasonal uplift", "+10%", "applied to the June baseline", "the brief"),
            ("Annual attrition", "36%", "compounds to 3.65%/month", "B12"),
            ("Learning curve", "120 / 110 / 105%", "AHT multiplier, months 1–3", "B4"),
            ("Training", "4 weeks", "non-producing, paid", "B13"),
            ("Routing", "BPO 1&amp;2 English; BPO 3 DE/IT/FR/ES", "9 of 15 AHT rows unroutable", "B5 / B6"),
            ("English BPO split", "50 / 50", "AHT blended, so capacity is split-agnostic", "<span class='mute'>assumption</span>"),
            ("English AHT source", "channel-level (709.8 s)", "<span class='crit'>vs reason-level 908.8 s — worth 78 FTE</span>", "'AHT Assumptions'")]
    trs = "".join(f'<tr><td><strong>{k}</strong></td><td class="n">{v}</td><td class="mute">{n}</td>'
                  f'<td class="mute xs">{src}</td></tr>' for k, v, n, src in rows)
    body = f"""
<div class="row">
  <div class="col" style="flex:0 0 55%">
    <h2>Every assumption, and where it comes from</h2>
    <table>
      <tr><th style="width:26%">Assumption</th><th class="n" style="width:20%">Value</th>
          <th style="width:30%">Note</th><th>Source</th></tr>
      {trs}
    </table>
  </div>
  <div class="col" style="flex:0 0 45%">
    <h2>What I would want before the next cycle</h2>
    <ul class="sm">
      <li><strong>Which English AHT is authoritative.</strong> Worth <span class="crit">78 FTE</span>.
      Needs an owner, not more analysis.</li>
      <li><strong>Whether chat concurrency was measured.</strong> Worth <span class="crit">75 FTE</span>.</li>
      <li><strong>24+ months of history.</strong> Six months containing a structural break cannot
      support a fitted seasonal model. Until then the forecast is scenario-based by necessity, not
      by preference.</li>
      <li><strong>15/30-minute arrival profiles.</strong> Monthly-average Erlang is a floor; intraday
      shape is where the real staffing lives.</li>
      <li><strong>What happened in March.</strong> A uniform 1.87× step across five languages, four
      channels and 49 reason codes is a system or scope change, not demand.</li>
      <li><strong>Cost per productive hour by BPO.</strong> Contracts are priced this way, and without
      it no lever can be ranked in €.</li>
      <li><strong>True outbound volumes.</strong> The mirrored columns cannot be real.</li>
    </ul>
    <div class="note" style="margin-top:12px">
      <h3>How I would use the team against this forecast</h3>
      <p class="sm tight">One specialist owns English — the volume, the growth and the volatility all
      sit there. One owns the pooled non-English queues, which is where Strategy 1 gets implemented.
      One owns the data contract and the re-forecast trigger, so the assumptions have a named keeper
      rather than living in a spreadsheet nobody edits. I own the two open questions, because they need
      a decision from the business rather than an analysis.</p>
    </div>
    <p class="xs mute" style="margin-top:10px">Deliverables: this deck · the source workbook with
    working shown · a 16-sheet model output workbook · the Python model and its 72-check verification
    suite.</p>
  </div>
</div>"""
    return slide("A6", "Appendix A6", "Assumptions register and open requests",
                 "", body, 6, True)


# ================================================================ BUILD
HTML = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f'<title>GYG WFM — Capacity Forecast &amp; Transformation Plan</title>'
        f'<style>{CSS}</style></head><body>'
        + "".join([s1(), s2(), s3(), s4(), s5(), a1(), a2(), a3(), a4(), a5(), a6()])
        + "</body></html>")

out = Path("GYG_WFM_Submission.html")
out.write_text(HTML, encoding="utf-8")
print(f"wrote {out} ({len(HTML):,} bytes, 11 pages)")
