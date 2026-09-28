"""Generate static waterfall SVGs for understanding_numbers.md (stdlib only)."""
import sys
from pathlib import Path

SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8983", "#e6e5e0"
TOTAL = "#6b6a66"
BLUE, ORANGE = "#2a78d6", "#eb6834"


def waterfall(steps, title, subtitle, legend, out, ymax, tick):
    """steps: list of (label, sublabel, value, kind, color); kind = 'total' | 'delta'."""
    W, H = 860, 440
    L, R, T, B = 64, 24, 92, 70
    pw, ph = W - L - R, H - T - B
    n = len(steps)
    slot = pw / n
    bw = slot * 0.56
    y = lambda v: T + ph - v / ymax * ph

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
         f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif">',
         f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>',
         f'<text x="{L}" y="34" font-size="18" font-weight="600" fill="{INK}">{title}</text>',
         f'<text x="{L}" y="56" font-size="13" fill="{INK2}">{subtitle}</text>']
    # legend
    lx = L
    for name, col in legend:
        s.append(f'<rect x="{lx}" y="68" width="12" height="12" rx="2" fill="{col}"/>')
        s.append(f'<text x="{lx + 18}" y="78.5" font-size="12" fill="{INK2}">{name}</text>')
        lx += 26 + 6.4 * len(name)
    # grid + axis ticks
    v = 0
    while v <= ymax + 1e-9:
        s.append(f'<line x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{GRID}" stroke-width="1"/>')
        s.append(f'<text x="{L - 8}" y="{y(v) + 4:.1f}" font-size="11" fill="{MUTED}" text-anchor="end">{v:g}</text>')
        v += tick
    s.append(f'<line x1="{L}" x2="{W - R}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="{MUTED}" stroke-width="1"/>')

    running = 0.0
    prev_top = None
    for i, (label, sub, val, kind, col) in enumerate(steps):
        cx = L + slot * i + slot / 2
        x0 = cx - bw / 2
        if kind == "total":
            lo, hi = 0.0, val
            running = val
            text = f"{val:,.1f}"
        else:
            lo, hi = running, running + val
            running = hi
            text = f"+{val:,.1f}"
        ytop, ybot = y(hi), y(lo)
        h = max(ybot - ytop, 1.5)
        s.append(f'<rect x="{x0:.1f}" y="{ytop:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="3" fill="{col}"/>')
        # connector from previous bar's running level
        if prev_top is not None:
            s.append(f'<line x1="{x0 - (slot - bw):.1f}" x2="{x0:.1f}" y1="{y(prev_top):.1f}" y2="{y(prev_top):.1f}" '
                     f'stroke="{MUTED}" stroke-width="1" stroke-dasharray="3 3"/>')
        prev_top = running
        weight = "600" if kind == "total" else "500"
        s.append(f'<text x="{cx:.1f}" y="{ytop - 7:.1f}" font-size="13" font-weight="{weight}" fill="{INK}" '
                 f'text-anchor="middle">{text}</text>')
        s.append(f'<text x="{cx:.1f}" y="{H - B + 20:.1f}" font-size="12" font-weight="{weight}" fill="{INK}" '
                 f'text-anchor="middle">{label}</text>')
        if sub:
            s.append(f'<text x="{cx:.1f}" y="{H - B + 36:.1f}" font-size="11" fill="{INK2}" '
                     f'text-anchor="middle">{sub}</text>')
    s.append("</svg>")
    Path(out).write_text("\n".join(s))


outdir = Path(sys.argv[1])
outdir.mkdir(exist_ok=True)

# 1. Headcount build-up, BASE July (run_model.py output)
waterfall(
    [("Workload only", "100% busy", 360.2, "total", TOTAL),
     ("+ SLA (Erlang C)", "idle time for SLA", 124.0, "delta", BLUE),
     ("SLA-met FTE", "", 484.2, "total", TOTAL),
     ("+ Learning curve", "÷ 0.9889 tenure blend", 5.5, "delta", BLUE),
     ("On-floor FTE", "", 489.7, "total", TOTAL),
     ("+ In training", "4-week class, 3.65%/mo", 17.9, "delta", BLUE),
     ("Paid FTE", "the bill", 507.6, "total", TOTAL)],
    "From workload to paid headcount: 360 → 508 FTE",
    "BASE scenario, July (Aug and Sep identical). All 5 languages.",
    [("Subtotal", TOTAL), ("Added requirement", BLUE)],
    outdir / "waterfall_fte_buildup.svg", ymax=600, tick=100)

# 2. English row of the B.4 table, by channel
waterfall(
    [("Email", "42,882 × 1,150 s", 113.4, "delta", BLUE),
     ("Inbound phone", "11 seats, 70% occ", 56.5, "delta", ORANGE),
     ("Outbound phone", "44,182 × 107.5 s", 10.9, "delta", BLUE),
     ("Chat", "24 slots ÷ 1.2", 102.7, "delta", ORANGE),
     ("English FTE", "SLA-met", 283.5, "total", TOTAL)],
    "English: how the 283.5 FTE row in B.4 adds up",
    "BASE July, 174,128 contacts. Deferred channels use workload math; real-time use Erlang C.",
    [("Deferred: hours ÷ 0.85 ÷ 0.82 ÷ 173.33", BLUE),
     ("Real-time: seats × 730 ÷ 0.82 ÷ 173.33", ORANGE),
     ("Total", TOTAL)],
    outdir / "waterfall_english_channels.svg", ymax=300, tick=50)
print("ok")
