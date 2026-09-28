#!/usr/bin/env python
"""One-time export of the GYG WFM deck to native, fully-editable PowerPoint.

Charts are rebuilt as real PPTX chart objects (data editable in PowerPoint),
not pictures. Content is transcribed from deck_content.md as of the export
date — this script is NOT wired to deck_content.md; after this export,
PowerPoint is the place to keep editing (per the user's own choice).

Run:  pip install python-pptx   (not a repo dependency; only this script needs it)
      python3 build_pptx.py    (from inside deck/, or anywhere — paths are
                                resolved relative to this file)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

import pptx_helpers as H
import pptx_charts as CH

OUT = Path(__file__).resolve().parent.parent / "GYG_WFM_Submission.pptx"

FOOT_MAIN = "GetYourGuide · WFM take-home submission · "
FOOT_APX = ("GetYourGuide · WFM take-home · all figures reproduced by run_model.py, "
            "verified by crosscheck.py (72/72)")


def new_slide(prs, tag, title, apx=False, dek=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = H.SURF
    H.add_eyebrow(slide, tag, apx=apx)
    H.add_title(slide, title, apx=apx)
    y = H.TITLE_Y + H.TITLE_H_1LINE + 0.05
    if dek:
        H.add_dek(slide, y, dek)
        y += 0.28
    H.add_hr(slide, y)
    body_y = y + 0.15
    body_bottom = H.SLIDE_H - H.PAD_B - H.FOOT_H - 0.04
    return slide, body_y, body_bottom


def cols_for(widths, body_y, body_bottom):
    return [H.Cursor(x, y, w) for x, y, w, h in H.col_geometry(widths, body_y, body_bottom)]


def footer(slide, apx, page_no):
    H.add_footer(slide, FOOT_APX if apx else FOOT_MAIN, page_no)


# ======================================================================
# Slide 1 — Executive summary
# ======================================================================
def build_s1(prs):
    slide, by, bb = new_slide(prs, "01 · Executive summary",
                               "508 paid FTE per month to meet service level")
    c1, c2, c3 = cols_for([30, 40, 30], by, bb)

    # --- col 1
    H.h2(slide, c1, "The answer — July to September", first=True)
    H.hero(slide, c1, "508", "paid FTE<br>per month")
    H.p(slide, c1, 'To hold <strong>80% / 20s</strong> phone and <strong>80% / 60s</strong> '
                    'chat at the June run-rate <strong>+10%</strong> seasonal uplift.')
    H.tiles_row(slide, c1, [("Productive hours", "68,827", "per month — the BPO bill"),
                             ("Contacts", "294k", "all languages, all channels")])
    H.note(slide, c1, 'One number needs an owner <span class="crit">±78 FTE</span>', [
        'The workbook gives two English handle times: <strong>710s</strong> including outbound '
        'calls, <strong>909s</strong> without. That looks like drift — <strong>it isn’t:'
        '</strong> compared channel-for-channel they agree within 1%. The real question is '
        'whether outbound volume is even real — it’s nearly identical to inbound in 29 '
        'of 30 months, the signature of a copied column, not a measured one. Real or not swings '
        'the plan <strong>508 vs 585 FTE</strong>, a call for whoever owns outbound.'
    ], kind="red")
    H.p(slide, c1, "Full scenario range (LOW/HIGH) and the P10–P90 confidence band are in "
                    "the appendix (A3).", size=7.6, color=H.MUTED)

    # --- col 2
    H.h2(slide, c2, "A quarter of the requirement is service level, not workload", first=True)
    c2.advance(0.08)
    CH.waterfall(slide, c2.x, c2.y, c2.w, 2.35,
                 ["Workload", "+SLA", "SLA-met", "+Learning", "On-floor", "+Attrition", "Paid FTE"],
                 [360.2, 124.0, 484.2, 5.5, 489.7, 17.9, 507.6],
                 ["total", "delta", "total", "delta", "total", "delta", "total"],
                 [H.DEEMPH, H.ACCENT, H.DEEMPH, H.ACCENT, H.DEEMPH, H.ACCENT, H.ACCENT],
                 font_size=7.5)
    c2.advance(2.35 + 0.06)
    H.p(slide, c2, 'A workload model returns <strong>360 FTE</strong> and '
                    '<strong class="crit">misses SLA</strong> — it implicitly assumes 100% '
                    'occupancy. Erlang C says English inbound runs at <strong>70%</strong>; the '
                    'idle 30% <em>is</em> the 20-second answer time.')

    # --- col 3 — native flowchart (not a data chart)
    H.h2(slide, c3, "Model architecture — one chain, two paths in", first=True)
    c3.advance(0.06)
    draw_architecture(slide, c3.x, c3.y, c3.w, 2.55)
    c3.advance(2.55 + 0.06)
    H.p(slide, c3, "Two paths — deferred (workload) and real-time (Erlang C) — merge "
                    "before shrinkage. Same chain, every language. Full formula and constants on "
                    "slide 03.", size=7.6, color=H.MUTED)

    footer(slide, False, "1 / 5")


def draw_architecture(slide, x, y, w, h):
    def box(bx, by, bw, bh, fill, text, sub=None, text_color=None, bold=True, size=8):
        shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(bx), Inches(by),
                                      Inches(bw), Inches(bh))
        shp.adjustments[0] = 0.10
        shp.fill.solid(); shp.fill.fore_color.rgb = fill
        shp.line.fill.background()
        shp.shadow.inherit = False
        tf = shp.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = Pt(3)
        tf.margin_top = tf.margin_bottom = Pt(2)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = text
        r.font.size = Pt(size); r.font.bold = bold; r.font.name = H.FONT
        r.font.color.rgb = text_color or H.INK
        if sub:
            p2 = tf.add_paragraph(); p2.alignment = PP_ALIGN.CENTER
            r2 = p2.add_run(); r2.text = sub
            r2.font.size = Pt(size - 1.5); r2.font.bold = True; r2.font.name = H.FONT
            r2.font.color.rgb = text_color or H.MUTED
        return shp

    def arrow(x1, y1, x2, y2):
        cn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1),
                                         Inches(x2), Inches(y2))
        cn.line.color.rgb = H.RULE
        cn.line.width = Pt(1)

    half = (w - 0.06) / 2
    box(x, y, half, 0.30, H.BODY_BG, "Email + Outbound", "DEFERRED", H.MUTED, size=7.5)
    box(x + half + 0.06, y, half, 0.30, H.BODY_BG, "Inbound + Chat", "REAL-TIME", H.ACCENT, size=7.5)
    arrow(x + half / 2, y + 0.30, x + half / 2, y + 0.38)
    arrow(x + half + 0.06 + half / 2, y + 0.30, x + half + 0.06 + half / 2, y + 0.38)
    y2 = y + 0.38
    box(x, y2, half, 0.34, H.DEEMPH, "÷ occupancy (85%)", "seat-equiv. hours", size=7)
    box(x + half + 0.06, y2, half, 0.34, H.WASH, "Erlang C — 80/20s, 80/60s", "→ seats × 730h/mo", size=6.8)
    arrow(x + half / 2, y2 + 0.34, x + w / 2, y2 + 0.48)
    arrow(x + half + 0.06 + half / 2, y2 + 0.34, x + w / 2, y2 + 0.48)
    y3 = y2 + 0.48
    box(x, y3, w, 0.28, H.DEEMPH, "÷ shrinkage (18%)", size=8)
    y4 = y3 + 0.28
    arrow(x + w / 2, y4, x + w / 2, y4 + 0.08)
    y4b = y4 + 0.08
    box(x, y4b, w, 0.34, H.DEEMPH, "÷ 173.33 h per FTE", "→ 484 FTE, SLA-met", text_color=H.ACCENT, size=7.5)
    y5 = y4b + 0.34
    arrow(x + w / 2, y5, x + w / 2, y5 + 0.08)
    y5b = y5 + 0.08
    box(x, y5b, w, 0.30, H.DEEMPH, "÷ tenure-blend + training class", size=7.3)
    y6 = y5b + 0.30
    arrow(x + w / 2, y6, x + w / 2, y6 + 0.08)
    y6b = y6 + 0.08
    box(x, y6b, w, h - (y6b - y), H.ACCENT, "PAID FTE — THE BILL", "508", H.SURF, size=8)


# ======================================================================
# Slide 2 — Forecast (position 2 in the deck order)
# ======================================================================
def build_s3(prs):
    slide, by, bb = new_slide(prs, "02 · Task 1a — Capacity forecast",
                               "Forecast, capacity and the range around it")
    c1, c2, c3 = cols_for([46, 27, 27], by, bb)

    H.h2(slide, c1, "Volume — six months of actuals, three of forecast", first=True)
    c1.advance(0.06)
    CH.line_with_forecast(slide, c1.x, c1.y, c1.w, 1.55,
                           ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"],
                           [124, 121, 183, 208, 187, 227, None, None, None],
                           [None, None, None, None, None, 227, 234, 234, 234])
    c1.advance(1.55 + 0.05)
    H.p(slide, c1, 'March is a <span class="crit">structural break</span>, not seasonality — '
                    'anchor the baseline on June, post-break. <strong>BASE</strong> holds '
                    'Jul–Sep flat; <strong>HIGH</strong> carries English’s own 3-month '
                    'trend forward.', size=8.6)
    H.h2(slide, c1, "Only English is growing", gap_before=0.06)
    c1.advance(0.04)
    small_multiples(slide, c1.x, c1.y, c1.w, 0.85)
    c1.advance(0.85)

    # --- col 2 — capacity tables
    H.h2(slide, c2, "Capacity by language — BASE, per month", first=True)
    H.table(slide, c2,
            [("Language", "t"), ("Contacts", "n"), ("Prod h", "n"), ("Wkld\nFTE", "n"),
             ("SLA\nFTE", "n"), ("Paid\nFTE", "n")],
            [
                [("English", "t", "b"), ("174,128", "n"), ("40,298", "n"), ("242", "n"), ("284", "n"), ("297", "n", "b")],
                [("German", "t", "b"), ("36,135", "n"), ("8,220", "n"), ("36", "n"), ("58", "n"), ("61", "n", "b")],
                [("Spanish", "t", "b"), ("32,879", "n"), ("7,133", "n"), ("31", "n"), ("50", "n"), ("53", "n", "b")],
                [("French", "t", "b"), ("26,662", "n"), ("6,773", "n"), ("26", "n"), ("48", "n"), ("50", "n", "b")],
                [("Italian", "t", "b"), ("24,066", "n"), ("6,402", "n"), ("25", "n"), ("45", "n"), ("47", "n", "b")],
                [("Total", "t"), ("293,869", "n"), ("68,827", "n"), ("360", "n"), ("484", "n"), ("508", "n")],
            ], col_widths=[1.2, 1, 0.85, 0.85, 0.75, 0.75], total_row_idx=5, row_h=0.165, font_size=7.6)
    H.p(slide, c2, "SLA → Paid adds the same learning-curve and attrition-backfill steps as "
                    "the slide 1 waterfall, applied per language.", size=6.8, color=H.MUTED, gap_before=0.02)
    H.h2(slide, c2, "By BPO — vendor split", gap_before=0.10)
    H.table(slide, c2,
            [("BPO", "t"), ("Languages", "t"), ("FTE", "n"), ("Prod h", "n")],
            [
                [("BPO 3", "t", "b"), ("DE IT ES FR", "t", "mute"), ("201", "n", "b"), ("28,529", "n")],
                [("BPO 1", "t", "b"), ("English 50%", "t", "mute"), ("142", "n", "b"), ("20,149", "n")],
                [("BPO 2", "t", "b"), ("English 50%", "t", "mute"), ("142", "n", "b"), ("20,149", "n")],
            ], col_widths=[0.9, 1.3, 0.7, 0.9], row_h=0.19, font_size=8)
    H.p(slide, c2, 'The 50/50 English split is <span class="crit">assumed, not in the brief</span> '
                    '— English AHT is the BPO1/BPO2 blend either way, so total capacity is '
                    'split-agnostic, but the per-vendor bill above isn’t.', size=6.8, gap_before=0.04)

    # --- col 3 — scenarios
    H.h2(slide, c3, "Scenarios — paid FTE", first=True)
    H.table(slide, c3,
            [("Case", "t"), ("Jul", "n"), ("Aug", "n"), ("Sep", "n"), ("Basis", "t")],
            [
                [("BASE", "t", "b"), ("508", "n"), ("508", "n"), ("508", "n"), ("June × 1.10, held flat", "t", "mute")],
                [("HIGH", "t", "b"), ("518", "n"), ("551", "n"), ("579", "n"), ("English 3-mo trend ×1.10; rest ×1.10", "t", "mute")],
            ], col_widths=[0.7, 0.55, 0.55, 0.55, 1.65], row_h=0.30, font_size=7.8)
    H.h2(slide, c3, "Paid FTE — 80% confidence band", gap_before=0.10)
    c3.advance(0.04)
    CH.confidence_band(slide, c3.x, c3.y, c3.w, 0.62, 425, 508, 606, 380, 650)
    c3.advance(0.62)
    H.note(slide, c3, None, [
        '<strong>Do not hire to a point estimate.</strong> Contract a <strong>~490 FTE core</strong> '
        'and hold a cross-trained flex pool of <strong>60–100</strong> against the P90, '
        'released monthly on the re-forecast trigger.'
    ], p_size=8.2)
    H.p(slide, c3, "Backfill alone runs at <strong>19 hires/month</strong> at 36% annual "
                    "attrition — with a 4-week class and a 3-month ramp, recruitment must "
                    "lead the forecast by a full quarter.", size=7, color=H.MUTED, gap_before=0.05)

    footer(slide, False, "2 / 5")


def small_multiples(slide, x, y, w, h):
    langs = [
        ("English", [124, 121, 183, 208, 187, 227], H.ACCENT, "+16,870/mo"),
        ("German", [131, 128, 111, 105, 108, 103], H.INK2, "−1,904/mo"),
        ("Spanish", [119, 116, 121, 118, 122, 120], H.INK2, "+282/mo"),
        ("French", [97, 95, 98, 95, 93, 94], H.INK2, "−363/mo"),
        ("Italian", [88, 86, 92, 88, 84, 86], H.INK2, "−474/mo"),
    ]
    gap = 0.12
    cw = (w - gap * 4) / 5
    for i, (name, vals, color, rate) in enumerate(langs):
        CH.small_multiple_line(slide, x + i * (cw + gap), y, cw, h,
                                ["J", "F", "M", "A", "M", "J"], vals, color, name, rate)


# ======================================================================
# Slide 3 — Method (position 3)
# ======================================================================
def build_s2(prs):
    slide, by, bb = new_slide(prs, "03 · Method",
                               "How the number is built — and what the data would not tell us")
    c1, c2, c3 = cols_for([33, 40, 27], by, bb)

    H.h2(slide, c1, "Assumptions — what we had to decide", first=True)
    H.table(slide, c1,
            [("", "t"), ("", "t")],
            [
                [("Deferred occupancy", "t", "b"), ("85% — not in the data, industry-typical", "t", "mute")],
                [("Shrinkage", "t", "b"), ("18% flat — matches the workbook exactly", "t", "mute")],
                [("Attrition", "t", "b"), ("36%/yr → 3.65%/mo, compounded", "t", "mute")],
                [("Seasonal uplift", "t", "b"), ("+10% — mandated by the brief", "t", "mute")],
                [("Routing", "t", "b"), ("BPO 1&2 English; BPO 3 DE/IT/ES/FR", "t", "mute")],
                [("Chat concurrency", "t", "b"), ("1.2 as given — open, see Q2", "t", "crit")],
                [("English AHT engine", "t", "b"), ("channel-level, incl. outbound — open, see Q1", "t", "crit")],
            ], col_widths=[1.1, 1.9], row_h=0.235, font_size=8.5)
    H.p(slide, c1, "Erlang C runs on a flat 24/7 average arrival rate — a <em>floor</em>. "
                    "Real intraday peaks and overnight minimum-staffing push interval-level "
                    "staffing up, never down.", size=8, color=H.MUTED, gap_before=0.10)

    H.h2(slide, c2, "Data quality — 12 checks, full log in appendix", first=True)
    H.table(slide, c2,
            [("", "t"), ("", "t"), ("", "t")],
            [
                [("PASS", "t", "pill_pass"), ("English reason tickets tie to Contact Volume, all 6 months", "t", "b"), ("ratio exactly 1.000000 — safe to join", "t", "mute")],
                [("WARN", "t", "pill_warn"), ("Channel rows vs their own language total", "t", "b"), ("off by ≤2 contacts in 17/30 months", "t", "mute")],
                [("FIX", "t", "pill_fix"), ("Blank reason label, 3,729 tickets", "t", "b"), ("relabelled “UNMAPPED”, volume kept", "t", "mute")],
                [("FIX", "t", "pill_fix"), ("1 AHT outlier vs its reason median", "t", "b"), ("replaced with the reason's own median", "t", "mute")],
                [("WARN", "t", "pill_warn"), ("Inbound = Outbound, Email = Chat, most months", "t", "b"), ("synthetic mirror — kept conservatively, flagged", "t", "mute")],
                [("FIX", "t", "pill_fix"), ("SLA attainment reported at 110% in February", "t", "b"), ("impossible — excluded from the trend", "t", "mute")],
            ], col_widths=[0.5, 2.3, 2.2], row_h=0.27, font_size=7.6)
    H.p(slide, c2, "<strong>The validation that passed matters most:</strong> the per-reason "
                    "ticket counts tie to the English contact volume in all six months at a ratio "
                    "of <strong>exactly 1.000000</strong> — so the two sheets describe the "
                    "same population and the reason-mix join is safe.", size=8, gap_before=0.06)
    H.note(slide, c2, None, [
        '<strong>SLA attainment has fallen 95% → 92% while volume doubled</strong> (February '
        'reports 110%, which is impossible). That is the business case for this transformation, '
        'sitting unused in the source data.'
    ], kind="red", p_size=8, gap_before=0.06)

    H.h2(slide, c3, "Two open questions, priced", first=True)
    H.h3(slide, c3, "1 · Is outbound English volume real?", size=9.5)
    H.p(slide, c3, "AHT assumption (709.8s) and Apr–Jun actuals (908.8s) agree within 1% once "
                    "outbound is excluded from both — not AHT drift. Outbound mirrors inbound "
                    "in 29/30 months, the signature of a synthetic column. "
                    '<span class="crit">Worth 78 FTE (15%) either way.</span>', size=8)
    H.h3(slide, c3, "2 · Is chat concurrency measured or assumed?", size=9.5, gap_before=0.08)
    H.p(slide, c3, "1.2 on every BPO and every language, under a header that says “English”. "
                    '<span class="crit">Worth 75 FTE.</span>', size=8)
    H.h2(slide, c3, "Also requested", gap_before=0.10)
    H.bullets(slide, c3, [
        "24+ months of history — 6 cannot support a seasonal model",
        "15/30-minute arrival data — monthly Erlang is a floor",
        "What changed in March — system, market, or demand?",
        "Cost per productive hour by BPO — to rank levers in €",
        "True outbound volumes — the mirrored columns cannot be real",
    ], size=7.6)
    H.note(slide, c3, None, [
        '<strong>Structural finding:</strong> 45 reason codes collapse to <strong>25</strong> '
        'distinct AHT profiles, and <strong>6</strong> of those clusters cross reason families '
        '— AHT is measured on a different taxonomy than the reason codes, and neither nests '
        'inside the other.'
    ], kind="grey", p_size=7.3)

    footer(slide, False, "3 / 5")


# ======================================================================
# Slide 4 — Optimisation
# ======================================================================
def build_s4(prs):
    slide, by, bb = new_slide(prs, "04 · Task 1b — Optimisation",
                               "Two strategies the arithmetic supports — and one it kills")
    c1, c2, c3 = cols_for([40, 33, 27], by, bb)

    H.h2(slide, c1, "Strategy 1 · Pool the four non-English queues −51.4 FTE now (10%)",
         first=True)
    c1.advance(0.06)
    CH.hbar(slide, c1.x, c1.y, c1.w, 1.35,
            ["German inb 42%", "Spanish inb 38%", "French inb 31%", "Italian inb 28%"],
            [42, 38, 31, 28], [H.ACCENT] * 4, value_fmt="{:.0f}%", font_size=7.5, cat_font_size=7)
    c1.advance(1.35 + 0.06)
    H.p(slide, c1, "<strong>The occupancy column is the finding.</strong> Those queues are not "
                    "idle by choice — 80/20 on a queue of 0.84 erlangs, staffed 24/7, needs 3 "
                    "seats no matter how few calls arrive. <strong>Four small queues pay that "
                    "floor four times.</strong>", size=8.3)
    H.table(slide, c1,
            [("Queue", "t"), ("Siloed", "n"), ("Pooled", "n"), ("SL", "n"), ("Saved", "n")],
            [
                [("Inbound DE/IT/ES/FR", "t", "b"), ("12 seats", "n"), ("7", "n", "b"), ("86%", "n", "good"), ("25.7", "n", "b")],
                [("Chat DE/IT/ES/FR", "t", "b"), ("20 seats", "n"), ("14", "n", "b"), ("86%", "n", "good"), ("25.7", "n", "b")],
                [("Total", "t"), ("", "n"), ("≈ 8,900 h off BPO 3", "t", "mute"), ("", "n"), ("51.4", "n")],
            ], col_widths=[1.5, 0.8, 0.7, 0.6, 0.7], total_row_idx=2, row_h=0.22, font_size=7.8)
    y0 = H.note_open(c1)
    H.h3(slide, c1, 'Phase 2 · Pool English in too <span class="accent">+27.4 FTE more</span>', size=9.5)
    H.p(slide, c1, "Same mechanism, wider pool, re-solved the same way: <strong>Inbound</strong> "
                    "23→16 seats (+10.3 FTE), <strong>Chat</strong> 37→28 seats "
                    "(+17.1 FTE) — both still clear 80%. The catch: English sits in BPO 1/2, "
                    "the other four in BPO 3, so this is <strong>vendor consolidation</strong>, "
                    "not a routing change — a bigger lift than phase 1, worth "
                    "<strong>−78.8 FTE (15.5%)</strong> total if it clears that bar.", size=8)
    H.note_close(slide, c1, y0, kind="default")

    H.h2(slide, c2, "Why it works, and what it costs", first=True)
    H.p(slide, c2, "All four languages already sit in BPO 3, so this is a routing and skilling "
                    "change, not a vendor change. Both pooled queues were <strong>re-solved "
                    "through the same Erlang engine</strong> — the service level goes up, not "
                    "down. Phase it: start with the overnight window, where the floors bite "
                    "hardest.", size=8.6)
    y0 = H.note_open(c2, gap_before=0.13)
    H.h3(slide, c2, "Tested and rejected: deflect phone → chat", size=9.8)
    H.p(slide, c2, "The intuitive lever. Modelled end-to-end it <strong>costs</strong> FTE, "
                    "because English chat consumes <strong>958 agent-seconds</strong> per contact "
                    "against phone’s <strong>458</strong>.", size=8)
    H.table(slide, c2,
            [("Shift", "t"), ("Phone", "n"), ("Chat", "n"), ("FTE", "n"), ("Δ", "n")],
            [
                [("0%", "t"), ("11", "n"), ("24", "n"), ("159.2", "n"), ("0.0", "n", "mute")],
                [("10%", "t"), ("10", "n"), ("26", "n"), ("162.6", "n"), ("+3.4", "n", "crit")],
                [("20%", "t"), ("9", "n"), ("28", "n"), ("166.1", "n"), ("+6.8", "n", "crit")],
                [("30%", "t"), ("9", "n"), ("30", "n"), ("174.6", "n"), ("+15.4", "n", "crit")],
            ], col_widths=[0.55, 0.6, 0.6, 0.65, 0.65], row_h=0.19, font_size=7.6, gap_before=0.06)
    H.note_close(slide, c2, y0, kind="red")

    H.h2(slide, c3, "Strategy 2 · Chat concurrency −75.3 FTE (15%)", first=True)
    c3.advance(0.04)
    CH.vbar(slide, c3.x, c3.y, c3.w, 1.35,
            ["1.2", "1.5", "2", "2.5", "3"], [188, 151, 113, 90, 75],
            [H.ACCENT, H.DEEMPH, H.ACCENT, H.DEEMPH, H.DEEMPH], font_size=7.5)
    c3.advance(1.35 + 0.04)
    H.p(slide, c3, "Chat is <strong>188 FTE — 39% of the entire operation</strong>, the "
                    "largest single line in the plan. The given 1.2 sits under a column headed "
                    "“Chat concurrency <em>English</em>” yet repeats on every BPO and "
                    "every language.", size=7.8)
    H.p(slide, c3, "<strong>Ask whether it was measured.</strong> If it was, the tooling or the "
                    "routing rules are the constraint and there is a clear case to fix them. If "
                    "it is a placeholder, the plan carries a 75 FTE error. Either answer is worth "
                    "having.", size=7.8)
    H.note(slide, c3, None, [
        '<strong>Where the real prize is.</strong> The top three handling-hour drivers — '
        '<strong>1.1 Availability</strong> (5,026 h), <strong>3.3 Meeting point</strong> (4,712 h) '
        'and <strong>3.1 Voucher not received</strong> (3,844 h, CSAT 65%) — are high-volume, '
        'low-CSAT and automatable. That is a product ask, not a scheduling change, so it sits '
        'beside these two rather than among them.'
    ], kind="grey", p_size=7.2)

    footer(slide, False, "4 / 5")


# ======================================================================
# Slide 5 — Leading the transformation
# ======================================================================
def build_s5(prs):
    slide, by, bb = new_slide(prs, "05 · Section 2 + Task 1c",
                               "Leading the transformation — and how AI was actually used")
    c1, c2, c3 = cols_for([38, 24, 38], by, bb)

    H.h2(slide, c1, "2a · 30 / 60 / 90", first=True)
    H.h3(slide, c1, "0–30 · Decide, then build", size=9.5)
    H.p(slide, c1, "Four decisions gate everything downstream — none are technical: "
                    "<strong>who owns the AHT definition</strong> (the ±78 FTE question is "
                    "unresolvable without an owner); <strong>forecast granularity</strong> "
                    "(language × channel × interval); <strong>who signs off "
                    "assumptions</strong>; <strong>where the model lives</strong>. Baseline the "
                    "manual model's accuracy in week 1.", size=7.8)
    H.h3(slide, c1, "31–60 · Shadow, don't switch", size=9.5, gap_before=0.06)
    H.p(slide, c1, "New model runs in parallel on English — 59% of volume, all of the "
                    "growth, all of the forecast risk (σ 19.5% vs under 9% elsewhere). Weekly "
                    "reconciliation against the manual plan. The manual plan stays <em>the</em> "
                    "plan.", size=7.8)
    H.h3(slide, c1, "61–90 · Cut over, then extend", size=9.5, gap_before=0.06)
    H.p(slide, c1, "English cuts over once it has beaten the baseline for six consecutive weeks. "
                    "DE/IT/ES/FR follow. Escalation and override rules written down before, not "
                    "after.", size=7.8)
    H.note(slide, c1, None, [
        '<strong>"Done" at 90 days:</strong> the model produces the weekly plan unaided, beats '
        'the manual baseline on MAPE for six straight weeks, the three specialists run it without '
        'me, and every assumption is versioned and dated.'
    ], p_size=7.6)

    H.h2(slide, c2, "2b · Bringing three specialists along", first=True)
    H.p(slide, c2, "<strong>Assess with an artefact, not an opinion.</strong> Give all three the "
                    "same task on this dataset — clean it, forecast one language, document "
                    "the assumptions.", size=7.6)
    H.p(slide, c2, "<strong>Set the expectation explicitly:</strong> AI is the tool, they own the "
                    "judgement. The two things AI got wrong were both plausible-sounding domain "
                    "defaults.", size=7.6)
    H.p(slide, c2, "<strong>Protect BAU:</strong> six weeks of shadow running, paired shadowing, "
                    "and a written prompt playbook.", size=7.6)
    H.h2(slide, c2, "2c · What I would measure", gap_before=0.10)
    H.p(slide, c2, "<strong>Leading</strong> — inputs with a named owner · time to "
                    "produce a plan · open data-quality items (<strong>starts at 12</strong>) "
                    "· specialists running it solo (0→3).", size=7.3)
    H.p(slide, c2, "<strong>Lagging</strong> — forecast MAPE <em>and BIAS</em> · SLA "
                    "attainment (baseline <strong>92%, falling</strong>) · FTE plan-vs-actual "
                    "· cost per contact.", size=7.3, gap_before=0.04)
    H.note(slide, c2, None, [
        '<strong>Lead with bias, not accuracy.</strong> Accuracy hides direction — a '
        'workload-only model is short by 34%, every single month.'
    ], p_size=7.2)

    H.h2(slide, c3, "1c · How AI was used — and where it was wrong", first=True)
    H.table(slide, c3,
            [("Where", "t"), ("Verdict", "t"), ("What happened", "t")],
            [
                [("Sheet parsing, anomaly sweep", "t", "b"), ("ACCEPTED", "t", "pill_pass"), ("Deterministic Python, verified independently.", "t", "mute")],
                [("Erlang C implementation", "t", "b"), ("ACCEPTED", "t", "pill_pass"), ("Checked by hand and against a simulation.", "t", "mute")],
                [("First-pass model structure", "t", "b"), ("REJECTED", "t", "pill_warn"), ("Workload and Erlang tables that never met.", "t", "mute")],
                [("“Deflect phone→chat”", "t", "b"), ("REJECTED", "t", "pill_warn"), ("Generic WFM instinct, contradicted by the data.", "t", "mute")],
                [("Reason-taxonomy clustering", "t", "b"), ("CHANGED", "t", "pill_fix"), ("Clusters cross families in 6 of 11 groups.", "t", "mute")],
                [("Narrative drafting", "t", "b"), ("CHANGED", "t", "pill_fix"), ("Defaulted to hedging; needed a recommendation.", "t", "mute")],
            ], col_widths=[1.6, 0.85, 2.25], row_h=0.245, font_size=7.4)
    H.note(slide, c3, None, [
        '<strong>What I would do differently.</strong> State the acceptance test <em>before</em> '
        'generating — rather than reviewing after. AI is reliable at parsing, arithmetic and '
        'structure, and unreliable at knowing <strong>which of two conflicting numbers in a '
        'workbook is the real one</strong>.'
    ], kind="red", p_size=7.6)
    H.p(slide, c3, "Tools: Claude (Opus 5) in Claude Code for the analysis, the Python model and "
                    "this deck. The verification suite found <strong>three real defects in my own "
                    "model</strong> — all fixed at source.", size=6.8, color=H.MUTED, gap_before=0.05)

    footer(slide, False, "5 / 5")


# ======================================================================
# Appendix A1
# ======================================================================
A1_ROWS = [
    ("English", "Chat", "42,882", "1,150", "Erlang C", "18.77", "24", "20.0", "78%", "86.2%", "13,699", "14,600", "96.4", "102.7"),
    ("English", "Email", "42,882", "1,150", "deferred", "—", "—", "22.1", "85%", "—", "13,699", "16,116", "96.4", "113.4"),
    ("English", "Inbound", "44,182", "458", "Erlang C", "7.69", "11", "11.0", "70%", "82.6%", "5,615", "8,030", "39.5", "56.5"),
    ("English", "Outbound", "44,182", "108", "deferred", "—", "—", "2.1", "85%", "—", "1,319", "1,552", "9.3", "10.9"),
    ("French", "Chat", "6,566", "900", "Erlang C", "2.25", "5", "4.2", "45%", "92.5%", "1,641", "3,042", "11.5", "21.4"),
    ("French", "Email", "6,566", "600", "deferred", "—", "—", "1.8", "85%", "—", "1,094", "1,287", "7.7", "9.1"),
    ("French", "Inbound", "6,765", "360", "Erlang C", "0.93", "3", "3.0", "31%", "93.3%", "677", "2,190", "4.8", "15.4"),
    ("French", "Outbound", "6,765", "115", "deferred", "—", "—", "0.3", "85%", "—", "216", "254", "1.5", "1.8"),
    ("German", "Chat", "8,899", "900", "Erlang C", "3.05", "6", "5.0", "51%", "91.3%", "2,225", "3,650", "15.7", "25.7"),
    ("German", "Email", "8,899", "700", "deferred", "—", "—", "2.8", "85%", "—", "1,730", "2,036", "12.2", "14.3"),
    ("German", "Inbound", "9,168", "360", "Erlang C", "1.26", "3", "3.0", "42%", "85.7%", "917", "2,190", "6.5", "15.4"),
    ("German", "Outbound", "9,168", "115", "deferred", "—", "—", "0.5", "85%", "—", "293", "345", "2.1", "2.4"),
    ("Italian", "Chat", "5,927", "900", "Erlang C", "2.03", "4", "3.3", "51%", "84.1%", "1,482", "2,433", "10.4", "17.1"),
    ("Italian", "Email", "5,927", "800", "deferred", "—", "—", "2.1", "85%", "—", "1,317", "1,549", "9.3", "10.9"),
    ("Italian", "Inbound", "6,106", "360", "Erlang C", "0.84", "3", "3.0", "28%", "94.8%", "611", "2,190", "4.3", "15.4"),
    ("Italian", "Outbound", "6,106", "115", "deferred", "—", "—", "0.3", "85%", "—", "195", "229", "1.4", "1.6"),
    ("Spanish", "Chat", "8,097", "900", "Erlang C", "2.77", "5", "4.2", "55%", "84.2%", "2,024", "3,042", "14.2", "21.4"),
    ("Spanish", "Email", "8,097", "600", "deferred", "—", "—", "2.2", "85%", "—", "1,350", "1,588", "9.5", "11.2"),
    ("Spanish", "Inbound", "8,342", "360", "Erlang C", "1.14", "3", "3.0", "38%", "88.7%", "834", "2,190", "5.9", "15.4"),
    ("Spanish", "Outbound", "8,342", "115", "deferred", "—", "—", "0.4", "85%", "—", "266", "314", "1.9", "2.2"),
]


def build_a1(prs):
    slide, by, bb = new_slide(prs, "Appendix A1", "Every queue, end to end — BASE, July",
                               apx=True, dek="The full working behind slide 2. Occupancy below "
                               "100% on the Erlang rows is the cost of the service level.")
    c1, c2 = cols_for([68, 32], by, bb)

    header = [("Lang", "t"), ("Chan", "t"), ("Contacts", "n"), ("AHT", "n"), ("Model", "t"),
              ("Erl", "n"), ("Seats", "n"), ("Occ", "n"), ("SL", "n"), ("Wkld h", "n"),
              ("Prod h", "n"), ("Wkld FTE", "n"), ("SLA FTE", "n")]
    rows = []
    for r in A1_ROWS:
        lang, ch, contacts, aht, model, erl, seats, fte_eq, occ, sl, wh, ph, wfte, sfte = r
        rows.append([
            (lang, "t", "b"), (ch, "t"), (contacts, "n"), (aht, "n"), (model, "t", "mute"),
            (erl, "n"), (seats, "n"), (occ, "n"), (sl, "n"), (wh, "n"), (ph, "n"), (wfte, "n"),
            (sfte, "n", "b"),
        ])
    rows.append([
        ("Total", "t"), ("", "t"), ("293,869", "n"), ("", "n"), ("", "t"), ("", "n"), ("", "n"),
        ("", "n"), ("", "n"), ("51,203", "n"), ("68,827", "n"), ("360.2", "n"), ("484.2", "n"),
    ])
    H.table(slide, c1, header, rows,
            col_widths=[0.75, 0.7, 0.75, 0.55, 0.65, 0.5, 0.5, 0.5, 0.55, 0.65, 0.65, 0.7, 0.65],
            row_h=0.145, font_size=6.3, header_size=5.8, total_row_idx=20)

    H.h2(slide, c2, "Where the 484 FTE sits", first=True)
    c2.advance(0.06)
    CH.stacked_hbar_single(slide, c2.x, c2.y, c2.w, 0.55,
                            ["Chat 39%", "Email 33%", "Inbound 24%", "Outbound 4%"],
                            [188, 159, 118, 19],
                            [H.ACCENT, H.ORANGE, H.GOOD, H.C("EDA100")], font_size=8)
    c2.advance(0.55 + 0.08)
    H.p(slide, c2, "<strong>Chat is the single largest line at 39%</strong>, which is why "
                    "concurrency is the biggest available lever.", size=8)
    H.p(slide, c2, "<strong>Outbound is 4%</strong> despite carrying a quarter of all contacts "
                    "— its AHT is 107s against email's 1,150s.", size=8)
    H.p(slide, c2, "<strong>Email at 159 FTE is modelled as deferred work</strong> at 85% planned "
                    "occupancy — an explicit assumption, not from the workbook.", size=8)
    H.note(slide, c2, None, [
        'The <strong>deferred</strong> rows carry no Erlang figures by design: a 120-minute '
        'target is a backlog commitment, not a queue discipline, so seats are derived from hours '
        'and planned occupancy instead.'
    ], kind="grey", p_size=7.3)

    footer(slide, True, "A1 / 6")


# ======================================================================
# Appendix A2
# ======================================================================
A2_ROWS = [
    (1, "warn", "channel rows sum to language total", "17/30 language-months disagree; max 2 contacts (0.012%)", "rounding residue; channel rows are the source of truth"),
    (2, "pass", "EN CSAT reason tickets tie to Contact Volume", "max |ratio-1| = 0.00e+00 across 6 months", "the two sheets describe the same population — safe to join"),
    (3, "fix", "CSAT reported against zero tickets", "3 reason-months carry a CSAT score with 0 tickets", "null the CSAT; keep the row"),
    (4, "fix", "reason label missing", "blank label carrying 3,729 tickets (0.63% of EN volume)", "relabel 'UNMAPPED' and keep the volume"),
    (5, "fix", "AHT outliers vs reason median", "1 reason-month outside 0.5x–2.0x its median", "replace with the reason's own median"),
    (6, "warn", "channel pair Inbound == Outbound", "identical in 29/30 language-months", "synthetic mirror — kept conservatively, flagged"),
    (7, "warn", "channel pair Email == Chat", "identical in 23/30 language-months", "synthetic mirror — kept conservatively, flagged"),
    (8, "warn", "BPO x language routing constraint", "9 of 15 rows violate the routing brief", "drop unroutable rows before any AHT lookup"),
    (9, "pass", "shrinkage components sum to Tot Shrink", "max diff = 0.00e+00 over 15 pairs", "use Tot Shrink = 18%"),
    (10, "warn", "structural break in the volume series", "March +87% MoM; all 5 languages move together", "treat as a level shift, anchor post-break"),
    (11, "fix", "SLA attainment series within [0,1]", "February reports 110% attainment", "exclude the impossible month"),
    (12, "warn", "SLA attainment trend", "95%→92% while volume grows", "use as the business case for the transformation"),
]


def build_a2(prs):
    slide, by, bb = new_slide(prs, "Appendix A2", "Data-quality log — all 12 checks", apx=True,
                               dek="Condensed to five rows on slide 3. This is the full log, "
                               "including the checks that passed.")
    c1 = H.Cursor(H.PAD_L, by, H.CONTENT_W)
    header = [("#", "n"), ("Status", "t"), ("Check", "t"), ("Finding", "t"), ("Decision", "t")]
    rows = []
    for n, status, check, finding, decision in A2_ROWS:
        rows.append([
            (str(n), "n", "mute"), (status.upper(), "t", f"pill_{status}"),
            (check, "t", "b"), (finding, "t", "mute"), (decision, "t"),
        ])
    H.table(slide, c1, header, rows,
            col_widths=[0.3, 0.7, 2.6, 3.3, 3.2], row_h=0.29, font_size=7.6, header_size=6.5)
    H.p(slide, c1, "<strong>Grading matters.</strong> A ±2-contact rounding residue and a "
                    "110% SLA reading are both “wrong”, but only one changes a decision. "
                    "Every row above carries its own materiality.", size=8.3, gap_before=0.08)

    footer(slide, True, "A2 / 6")


# ======================================================================
# Appendix A3
# ======================================================================
def build_a3(prs):
    slide, by, bb = new_slide(prs, "Appendix A3", "Forecast detail — why only English gets a trend",
                               apx=True)
    top = H.Cursor(H.PAD_L, by, H.CONTENT_W)
    small_multiples(slide, top.x, top.y, top.w, 0.95)
    top.advance(0.95 + 0.10)
    c1, c2, c3 = cols_for([46, 26, 28], top.y, bb)

    H.h2(slide, c1, "Per-language growth test — post-break window", first=True)
    H.table(slide, c1,
            [("Language", "t"), ("June", "n"), ("Mar→Jun", "n"), ("OLS/mo", "n"), ("R²", "n"), ("σ", "n"), ("Growing?", "t")],
            [
                [("English", "t", "b"), ("158,298", "n"), ("+59.3%", "n"), ("+16,870", "n"), ("0.74", "n"), ("19.5%", "n"), ("yes", "t", "accent")],
                [("German", "t", "b"), ("32,850", "n"), ("-15.7%", "n"), ("-1,904", "n"), ("0.68", "n"), ("6.9%", "n"), ("no", "t", "mute")],
                [("Spanish", "t", "b"), ("29,890", "n"), ("+5.1%", "n"), ("+282", "n"), ("0.15", "n"), ("8.3%", "n"), ("no", "t", "mute")],
                [("French", "t", "b"), ("24,238", "n"), ("-3.2%", "n"), ("-363", "n"), ("0.19", "n"), ("5.6%", "n"), ("no", "t", "mute")],
                [("Italian", "t", "b"), ("21,878", "n"), ("+4.6%", "n"), ("-474", "n"), ("0.03", "n"), ("27.1%", "n"), ("no", "t", "mute")],
            ], col_widths=[0.9, 0.85, 0.75, 0.75, 0.5, 0.6, 0.75], row_h=0.22, font_size=7.8)
    H.p(slide, c1, "A language earns the trend extrapolation in HIGH only if its slope is "
                    "<strong>positive</strong>, exceeds 3% of baseline, and fits at R² > 0.4. "
                    "Only English qualifies.", size=8, gap_before=0.06)

    H.h2(slide, c2, "Confidence band — July", first=True)
    H.table(slide, c2,
            [("Pctile", "t"), ("Mult", "n"), ("Contacts", "n"), ("Paid FTE", "n")],
            [
                [("P5", "t"), ("0.797", "n"), ("234,264", "n"), ("405", "n")],
                [("P10", "t"), ("0.838", "n"), ("246,292", "n"), ("425", "n")],
                [("P25", "t"), ("0.911", "n"), ("267,784", "n"), ("463", "n")],
                [("P50", "t"), ("1.000", "n"), ("293,869", "n"), ("508", "n", "b")],
                [("P75", "t"), ("1.097", "n"), ("322,496", "n"), ("557", "n")],
                [("P90", "t"), ("1.193", "n"), ("350,638", "n"), ("606", "n")],
                [("P95", "t"), ("1.254", "n"), ("368,641", "n"), ("637", "n")],
            ], col_widths=[0.6, 0.6, 0.85, 0.75], row_h=0.185, font_size=7.6)
    H.p(slide, c2, "Log-normal around the BASE median, σ = 13.8% from month-over-month log "
                    "returns with the March break excluded.", size=6.8, color=H.MUTED, gap_before=0.05)

    H.h2(slide, c3, "Monthly re-forecast trigger", first=True)
    H.table(slide, c3,
            [("Signal", "t"), ("Threshold", "t"), ("Action", "t")],
            [
                [("EN vs BASE", "t"), ("> +8%, 2wk", "t", "mute"), ("Switch to HIGH", "t")],
                [("EN vs BASE", "t"), ("< −8%, 2wk", "t", "mute"), ("Switch to LOW", "t")],
                [("SLA attain.", "t"), ("< 90%, 2wk", "t", "mute"), ("Immediate re-forecast", "t")],
                [("AHT drift", "t"), ("±5% vs plan", "t", "mute"), ("Re-baseline AHT", "t")],
            ], col_widths=[0.85, 0.85, 1.35], row_h=0.24, font_size=7.6)
    H.note(slide, c3, None, [
        'The SLA trigger already fired — <strong>May came in at 90%</strong>. A model that '
        'only produces a number, without the rule for when it’s wrong, is not operational.'
    ], kind="red", p_size=7.6, gap_before=0.08)

    footer(slide, True, "A3 / 6")


# ======================================================================
# Appendix A4
# ======================================================================
def build_a4(prs):
    slide, by, bb = new_slide(prs, "Appendix A4", "Why service level costs 34% — the Erlang mechanics",
                               apx=True)
    c1, c2, c3 = cols_for([34, 33, 33], by, bb)

    H.h2(slide, c1, "The mistake worth understanding", first=True)
    H.p(slide, c1, "A workload model divides work by time and calls the result headcount. "
                    "<strong>No queue with a service-level target can run that way</strong> — "
                    "somebody has to be free when the call lands. The idle time is not waste; it "
                    "is the product.", size=8.2)
    H.table(slide, c1,
            [("English inbound, BASE July", "t"), ("", "n")],
            [
                [("Contacts", "t"), ("44,182", "n")],
                [("AHT (BPO1/2 blend)", "t"), ("457.5 s", "n")],
                [("Workload hours", "t"), ("5,615", "n")],
                [("Offered load", "t"), ("7.69 erlangs", "n")],
                [("Seats for 80/20", "t"), ("11", "n", "b")],
                [("Achieved service level", "t"), ("82.6%", "n", "good")],
                [("Occupancy at 11 seats", "t"), ("69.9%", "n", "b")],
                [("Workload FTE (÷ shrinkage only)", "t", "mute"), ("39.5", "n", "mute")],
                [("FTE that actually meets SLA", "t"), ("56.5", "n")],
            ], col_widths=[1.9, 0.75], total_row_idx=8, row_h=0.185, font_size=7.8, gap_before=0.08)
    H.p(slide, c1, "<strong>+43% on one queue.</strong> Across all ten real-time queues it is "
                    "+34% on the total.", size=8, gap_before=0.06)

    H.h2(slide, c2, "Why small queues cost so much more", first=True)
    H.p(slide, c2, "Occupancy is a property of <em>queue size</em>. A large queue smooths its own "
                    "arrivals; a small one must hold spare seats against randomness a bigger pool "
                    "would absorb.", size=8.2)
    H.table(slide, c2,
            [("Queue", "t"), ("Erlangs", "n"), ("Seats", "n"), ("Occupancy", "n")],
            [
                [("Italian inbound", "t"), ("0.84", "n"), ("3", "n"), ("27.9%", "n", "crit")],
                [("French inbound", "t"), ("0.93", "n"), ("3", "n"), ("30.9%", "n", "crit")],
                [("Spanish inbound", "t"), ("1.14", "n"), ("3", "n"), ("38.1%", "n")],
                [("German inbound", "t"), ("1.26", "n"), ("3", "n"), ("41.9%", "n")],
                [("All four, pooled", "t"), ("4.16", "n"), ("7", "n"), ("59.5%", "n", "good")],
                [("English inbound", "t"), ("7.69", "n"), ("11", "n"), ("69.9%", "n")],
            ], col_widths=[1.3, 0.7, 0.6, 0.85], total_row_idx=4, row_h=0.20, font_size=7.8, gap_before=0.08)
    H.note(slide, c2, None, [
        '<strong>Doubling volume does not double FTE.</strong> 2× the contacts needs '
        '<strong>1.81×</strong> the FTE — the real economy behind pooling.'
    ], p_size=7.6, gap_before=0.08)

    H.h2(slide, c3, "Where this model is deliberately conservative", first=True)
    H.bullets(slide, c3, [
        "<strong>Monthly-average arrival rates.</strong> Real intraday peaks push staffing "
        "<em>higher</em>, never lower. <strong>508 is a floor.</strong>",
        "<strong>Shrinkage held flat at 18%.</strong> A +1–2pt summer adjustment adds 6–12 FTE.",
        "<strong>Outbound kept at face value</strong> despite mirroring inbound exactly.",
        "<strong>Email at 85% planned occupancy</strong> — an assumption, not from the data.",
    ], size=7.6)
    H.h2(slide, c3, "Shrinkage sensitivity", gap_before=0.10)
    H.table(slide, c3,
            [("Shrinkage", "t"), ("SLA FTE", "n"), ("Δ", "n")],
            [
                [("16%", "t"), ("472.7", "n"), ("−11.5", "n", "mute")],
                [("17%", "t"), ("478.4", "n"), ("−5.8", "n", "mute")],
                [("18% — as given", "t"), ("484.2", "n"), ("—", "n")],
                [("19%", "t"), ("490.2", "n"), ("+6.0", "n", "crit")],
                [("20%", "t"), ("496.3", "n"), ("+12.1", "n", "crit")],
            ], col_widths=[1.1, 0.7, 0.7], total_row_idx=2, row_h=0.185, font_size=7.8)

    footer(slide, True, "A4 / 6")


# ======================================================================
# Appendix A5
# ======================================================================
def build_a5(prs):
    slide, by, bb = new_slide(prs, "Appendix A5", "The model and how it was verified", apx=True)
    c1, c2, c3 = cols_for([32, 36, 32], by, bb)

    H.h2(slide, c1, "The model", first=True)
    H.table(slide, c1,
            [("Module", "t"), ("Responsibility", "t")],
            [
                [("config.py", "t", "b"), ("Every assumption in one frozen dataclass", "t", "mute")],
                [("erlang.py", "t", "b"), ("Erlang B/C, service level, ASA, solver", "t", "mute")],
                [("loader.py", "t", "b"), ("Schema-driven reader; refuses the hidden sheet", "t", "mute")],
                [("clean.py", "t", "b"), ("12 data-quality checks → structured log", "t", "mute")],
                [("forecast.py", "t", "b"), ("Break detection, growth test, scenarios", "t", "mute")],
                [("capacity.py", "t", "b"), ("Workload → Erlang → seats → FTE, by BPO", "t", "mute")],
                [("optimise.py", "t", "b"), ("Each lever re-solved through the same engine", "t", "mute")],
                [("report.py", "t", "b"), ("16-sheet Excel export", "t", "mute")],
            ], col_widths=[1.0, 2.1], row_h=0.24, font_size=7.4)
    H.p(slide, c1, "<strong>Automation was the point.</strong> Drop in next month's workbook and "
                    "the plan regenerates — every assumption is a config value.", size=7.8, gap_before=0.06)
    H.note(slide, c1, None, [
        "python run_model.py<br>python run_model.py --aht-source reason<br>python crosscheck.py"
    ], kind="grey", p_size=7)

    H.h2(slide, c2, "Verification — 72 checks, all passing", first=True)
    H.table(slide, c2,
            [("Layer", "t"), ("What is actually proved", "t")],
            [
                [("Erlang B/C", "t", "b"), ("Recursion vs closed form (1.1e-16); vs stationary dist. (<1e-12)", "t", "mute")],
                [("Simulation", "t", "b"), ("vs discrete-event M/M/c — 3σ band on SL and ASA", "t", "mute")],
                [("Solver", "t", "b"), ("Minimal feasible seats; SL monotone in seats", "t", "mute")],
                [("Queueing", "t", "b"), ("Little's Law holds exactly", "t", "mute")],
                [("Raw cells", "t", "b"), ("Full July chain re-derived from cells — matches 1e-6", "t", "mute")],
                [("Invariants", "t", "b"), ("Every queue ≥80%; roll-up sums exact; LOW≤BASE≤HIGH", "t", "mute")],
                [("HR maths", "t", "b"), ("Attrition compounds to 36.00%/yr", "t", "mute")],
                [("Levers", "t", "b"), ("Each 1b strategy re-solved, not asserted", "t", "mute")],
            ], col_widths=[0.75, 2.65], row_h=0.24, font_size=7.4)

    H.h2(slide, c3, "What verification actually caught", first=True)
    H.p(slide, c3, "Three real defects <strong>in my own model</strong>, all fixed at source:", size=8)
    H.bullets(slide, c3, [
        "The growth test keyed off <strong>|slope|</strong>, so declining German qualified as "
        "“growing” — HIGH came out below BASE.",
        "The reported trend was a one-step projection rather than the OLS slope "
        "(<strong>16,869/mo</strong>).",
        "A fourth failure surfaced the ±2-contact residue — became DQ finding #1.",
    ], size=7.6)
    H.note(slide, c3, None, [
        'One "failure" was wrong in the <em>test</em>, not the code — four independent '
        'derivations agreed to <strong>1e-12</strong>. The test was corrected, not the model.'
    ], p_size=7.4, gap_before=0.07)
    H.p(slide, c3, "<strong>Why this belongs in the submission.</strong> Every figure in this "
                    "deck is generated by the model — the deck reads the model's own output, "
                    "so the two cannot drift apart.", size=7.8, gap_before=0.07)
    H.note(slide, c3, None, [
        '<strong>The honest limit.</strong> Verification proves the model computes what it '
        'claims. It cannot prove the inputs are right — two are not yet settled, which is '
        'why they carry FTE price tags on slide 3.'
    ], p_size=7.4, gap_before=0.07)

    footer(slide, True, "A5 / 6")


# ======================================================================
# Appendix A6
# ======================================================================
A6_ROWS = [
    ("Hours per FTE per month", "173.33", "=40 × 52 ÷ 12"),
    ("Total shrinkage", "18%", "divisor 0.82"),
    ("Operating hours per month", "730", "24/7 → 8,760 ÷ 12"),
    ("Phone SLA", "80% ≤ 20 s", "Erlang C"),
    ("Chat SLA", "80% ≤ 60 s", "Erlang C, ÷ concurrency"),
    ("Email SLA", "80% ≤ 120 min", "deferred model"),
    ("Chat concurrency", "1.2", "open question — worth 75 FTE"),
    ("Deferred occupancy", "85%", "modelling assumption — not in the data"),
    ("Seasonal uplift", "+10%", "applied to the June baseline"),
    ("Annual attrition", "36%", "compounds to 3.65%/month"),
    ("Learning curve", "120/110/105%", "AHT multiplier, months 1–3"),
    ("Training", "4 weeks", "non-producing, paid"),
    ("Routing", "BPO 1&2 EN; BPO 3 DE/IT/FR/ES", "9 of 15 AHT rows unroutable"),
    ("English BPO split", "50 / 50", "AHT blended — assumption"),
    ("English AHT source", "channel-level (709.8s)", "vs reason-level 908.8s — worth 78 FTE"),
]


def build_a6(prs):
    slide, by, bb = new_slide(prs, "Appendix A6", "Assumptions register and open requests", apx=True)
    c1, c2 = cols_for([55, 45], by, bb)

    H.h2(slide, c1, "Every assumption, and where it comes from", first=True)
    header = [("Assumption", "t"), ("Value", "n"), ("Note", "t")]
    rows = []
    for name, val, note in A6_ROWS:
        mod = "crit" if "worth" in note or "assumption" in note.lower() or "open question" in note else "mute"
        rows.append([(name, "t", "b"), (val, "n"), (note, "t", mod)])
    H.table(slide, c1, header, rows, col_widths=[1.7, 1.3, 2.6], row_h=0.225, font_size=7.2)

    H.h2(slide, c2, "What I would want before the next cycle", first=True)
    H.bullets(slide, c2, [
        '<strong>Which English AHT is authoritative.</strong> Worth <span class="crit">78 FTE</span>. Needs an owner.',
        '<strong>Whether chat concurrency was measured.</strong> Worth <span class="crit">75 FTE</span>.',
        "<strong>24+ months of history.</strong> Six months with a structural break can't support a fitted seasonal model.",
        "<strong>15/30-minute arrival profiles.</strong> Monthly-average Erlang is a floor.",
        "<strong>What happened in March.</strong> A uniform step is a system change, not demand.",
        "<strong>Cost per productive hour by BPO.</strong> Needed to rank levers in €.",
        "<strong>True outbound volumes.</strong> The mirrored columns cannot be real.",
    ], size=7.6)
    H.note(slide, c2, "How I would use the team against this forecast", [
        "One specialist owns English. One owns the pooled non-English queues. One owns the data "
        "contract and re-forecast trigger. I own the two open questions — they need a "
        "business decision, not more analysis."
    ], p_size=7.6, gap_before=0.10)
    H.p(slide, c2, "Deliverables: this deck · the source workbook with working shown · a "
                    "16-sheet model output workbook · the Python model and its 72-check "
                    "verification suite.", size=6.8, color=H.MUTED, gap_before=0.08)

    footer(slide, True, "A6 / 6")


# ======================================================================
def main():
    prs = Presentation()
    prs.slide_width = Inches(H.SLIDE_W)
    prs.slide_height = Inches(H.SLIDE_H)

    build_s1(prs)
    build_s3(prs)
    build_s2(prs)
    build_s4(prs)
    build_s5(prs)
    build_a1(prs)
    build_a2(prs)
    build_a3(prs)
    build_a4(prs)
    build_a5(prs)
    build_a6(prs)

    prs.save(str(OUT))
    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes, {len(prs.slides)} slides)")


if __name__ == "__main__":
    main()
