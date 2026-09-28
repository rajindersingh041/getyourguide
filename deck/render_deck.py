#!/usr/bin/env python3
"""Builds GYG_WFM_Submission.html (and optionally its PDF) from deck_content.md.

deck_content.md is the single file you edit: wording, which slides exist, and
what order they're in. Layout (CSS grid, column widths, chart SVGs) lives in
deck/style.css and figures/deck/*.svg and isn't touched by this script.

Usage:
    python3 deck/render_deck.py            # writes GYG_WFM_Submission.html
    python3 deck/render_deck.py --pdf       # also writes GYG_WFM_Submission.pdf
"""
from __future__ import annotations
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MD_PATH = ROOT / "deck_content.md"
CSS_PATH = ROOT / "deck" / "style.css"
OUT_HTML = ROOT / "GYG_WFM_Submission.html"
OUT_PDF = ROOT / "GYG_WFM_Submission.pdf"

SLIDE_RE = re.compile(r"^===([A-Za-z0-9]+)===\s*\n(.*?)\n===end===\s*$", re.S | re.M)
FIELD_RE = re.compile(r"^(tag|title|dek|apx):[ \t]*(.*)$")
SECTION_RE = re.compile(r"^---(col:(\d+)%|full)---\s*$")

FOOT_MAIN = "GetYourGuide &middot; WFM take-home submission &middot; "
FOOT_APX = (
    'GetYourGuide &middot; WFM take-home &middot; all figures reproduced by '
    '<span style="font-family:monospace">run_model.py</span>, verified by '
    '<span style="font-family:monospace">crosscheck.py</span> (72/72)'
)


def strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def parse_md(text: str) -> tuple[list[str], dict]:
    text = strip_comments(text)
    order_m = re.search(r"^order:\s*(.+)$", text, re.M)
    if not order_m:
        raise SystemExit("deck_content.md: missing top-level `order:` line")
    order = [s.strip() for s in order_m.group(1).split(",") if s.strip()]

    slides = {}
    for m in SLIDE_RE.finditer(text):
        sid, block = m.group(1), m.group(2)
        lines = block.split("\n")
        fields = {"tag": "", "title": "", "dek": "", "apx": "false"}
        i = 0
        while i < len(lines):
            fm = FIELD_RE.match(lines[i])
            if fm:
                fields[fm.group(1)] = fm.group(2).strip()
                i += 1
            elif lines[i].strip() == "":
                i += 1
            else:
                break
        body_lines = lines[i:]
        sections = []  # list of ("full"|width_pct, html)
        cur_kind, cur_lines = None, []

        def flush():
            if cur_kind is not None:
                sections.append((cur_kind, "\n".join(cur_lines).strip()))

        for line in body_lines:
            sm = SECTION_RE.match(line)
            if sm:
                flush()
                cur_kind = "full" if sm.group(1) == "full" else sm.group(2)
                cur_lines = []
            else:
                cur_lines.append(line)
        flush()

        if sid in slides:
            raise SystemExit(f"deck_content.md: duplicate slide id '{sid}'")
        slides[sid] = dict(
            tag=fields["tag"], title=fields["title"], dek=fields["dek"],
            apx=fields["apx"].strip().lower() == "true", sections=sections,
        )
    return order, slides


def render_slide(sid: str, sl: dict, page_no: str, total: str) -> str:
    full_html = "".join(html for kind, html in sl["sections"] if kind == "full")
    col_sections = [(kind, html) for kind, html in sl["sections"] if kind != "full"]
    row_html = ""
    if col_sections:
        cols = "".join(
            f'<div class="col" style="flex:0 0 {width}%">\n{html}\n</div>'
            for width, html in col_sections
        )
        row_html = f'<div class="row">\n{cols}\n</div>'
    body = full_html + row_html
    dek_html = f'<p class="dek">{sl["dek"]}</p>' if sl["dek"] else ""
    foot_left = FOOT_APX if sl["apx"] else FOOT_MAIN
    cls = "slide apx" if sl["apx"] else "slide"
    return f"""<section class="{cls}">
  <div class="eyebrow"><span class="tag">{sl["tag"]}</span><span>Manager, Workforce Management &middot; Care Experience &amp; Strategy</span></div>
  <h1>{sl["title"]}</h1>
  {dek_html}
  <div class="hr"></div>
  <div class="body">{body}</div>
  <div class="foot"><span>{foot_left}</span><span class="pg">{page_no} / {total}</span></div>
</section>"""


def build_html() -> str:
    order, slides = parse_md(MD_PATH.read_text(encoding="utf-8"))
    missing = [sid for sid in order if sid not in slides]
    if missing:
        raise SystemExit(f"deck_content.md: order references undefined slide(s): {missing}")

    main_ids = [sid for sid in order if not slides[sid]["apx"]]
    apx_ids = [sid for sid in order if slides[sid]["apx"]]
    total_main = str(len(main_ids))
    total_apx = str(len(apx_ids))

    main_n = 0
    apx_n = 0
    rendered = []
    for sid in order:
        sl = slides[sid]
        if sl["apx"]:
            apx_n += 1
            page_no = f"A{apx_n}"
            total = total_apx
        else:
            main_n += 1
            page_no = str(main_n)
            total = total_main
        rendered.append(render_slide(sid, sl, page_no, total))

    css = CSS_PATH.read_text(encoding="utf-8")
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<title>GYG WFM — Capacity Forecast &amp; Transformation Plan</title>'
        f"<style>{css}</style></head><body>"
        + "".join(rendered)
        + "</body></html>"
    )


def main():
    html = build_html()
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"wrote {OUT_HTML} ({len(html):,} bytes)")

    if "--pdf" in sys.argv:
        subprocess.run(
            ["chromium", "--headless", "--disable-gpu", "--no-sandbox",
             "--virtual-time-budget=8000",
             f"--print-to-pdf={OUT_PDF}",
             "--no-pdf-header-footer",
             str(OUT_HTML)],
            check=True,
        )
        print(f"wrote {OUT_PDF}")


if __name__ == "__main__":
    main()
