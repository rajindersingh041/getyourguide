#!/usr/bin/env python
"""Measures every slide in a real browser and reports content overflow.

Eyeballing 11 pages misses clipped rows. This injects a probe, runs Chromium
headless, and reads the measurements back out of the serialised DOM.
"""
import re, subprocess, sys, tempfile
from pathlib import Path

src = Path(sys.argv[1] if len(sys.argv) > 1 else "GYG_WFM_Submission.html")
html = src.read_text(encoding="utf-8")

PROBE = """
<script>
window.addEventListener('load', function () {
  var out = [];
  document.querySelectorAll('.slide').forEach(function (s, i) {
    var pg   = s.querySelector('.pg');
    var foot = s.querySelector('.foot');
    var sr   = s.getBoundingClientRect();
    var fr   = foot.getBoundingClientRect();
    // deepest element bottom inside the slide body
    var deep = 0, culprit = '';
    s.querySelectorAll('.body *').forEach(function (el) {
      var r = el.getBoundingClientRect();
      if (r.height && r.bottom > deep) {
        deep = r.bottom;
        culprit = el.tagName.toLowerCase() + (el.className ? '.' + String(el.className).split(' ')[0] : '');
      }
    });
    var overflow = deep - fr.top;                       // >0 means it hits the footer
    var slack    = fr.top - deep;                       // unused vertical space
    out.push([pg ? pg.textContent.trim() : i + 1,
              Math.round(overflow), Math.round(slack),
              Math.round(sr.height), culprit].join('|'));
  });
  var d = document.createElement('div');
  d.id = 'probe-report';
  d.textContent = 'REPORT' + '::' + out.join('~~');
  document.body.appendChild(d);
});
</script>
"""
tmp = Path(tempfile.mkdtemp()) / "probe.html"
tmp.write_text(html.replace("</body>", PROBE + "</body>"), encoding="utf-8")

dom = subprocess.run(
    ["chromium", "--headless", "--disable-gpu", "--no-sandbox", "--dump-dom",
     "--virtual-time-budget=8000", str(tmp)],
    capture_output=True, text=True, timeout=180).stdout

m = re.search(r'<div id="probe-report">REPORT::(.*?)</div>', dom, re.S)
if not m:
    print("probe did not report — check the page for a script error")
    sys.exit(2)

print(f"{'page':>6}  {'overflow':>9}  {'slack':>7}   deepest element")
print("-" * 64)
bad = thin = 0
for rec in m.group(1).split("~~"):
    pg, ov, sl, h, culprit = rec.split("|")
    ov, sl = int(ov), int(sl)
    if ov > 0:
        flag, bad = "  OVERFLOW", bad + 1
    elif sl > 130:
        flag, thin = "  under-filled", thin + 1
    else:
        flag = ""
    print(f"{pg:>6}  {ov:>+9}  {sl:>7}   {culprit}{flag}")
print("-" * 64)
print(f"{bad} overflowing, {thin} under-filled (>130pt slack)")
sys.exit(1 if bad else 0)
