#!/usr/bin/env python3
"""Render a draft chapter to a self-contained HTML preview with figures inline.

A draft (``drafts/ch*.md``) cites figures as text and keeps the plots in
separate files, so reviewing one means flipping between the prose and a handful
of PDFs. This helper stitches them into a single scrollable HTML page — each
figure embedded (base64) at the point the prose first references it — so a
chapter reads top to bottom without opening anything else.

Usage:
    python3 scripts/preview_draft.py [draft.md] [out.html]
    make preview                                  # Chapter 4 (default)
    make preview FILE=drafts/ch3_methodology.md   # any chapter

Figure discovery:
- Most figures come from their caption block — a paragraph beginning
  ``**Figure N.M — ...`` that carries ``Source: `results/.../slug.pdf` ``; the
  sibling ``slug.png`` is embedded right after the caption.
- Figures cited inline with no Source line are supplied by the per-file
  OVERRIDES table below. Chapter 4's baseline figures (4.1-4.6) are inline-only,
  and 4.7's PNG lives under ``explain/`` rather than beside its PDF, so they are
  listed there explicitly. Extend OVERRIDES when a new chapter needs it.

Requires pandoc (https://pandoc.org). PNGs (gitignored screen renders) must
exist on disk — run the relevant ``output.*plots`` generator first if not.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Per-draft figure -> PNG for figures cited inline without a Source line.
OVERRIDES = {
    "ch4_results.md": {
        "4.1": "results/baseline/plots/latency_vs_n.png",
        "4.2": "results/baseline/plots/throughput_vs_n.png",
        "4.3": "results/baseline/plots/msgs_vs_n.png",
        "4.4": "results/baseline/plots/decision_rate_vs_n.png",
        "4.5": "results/baseline/plots/goodput_ci_vs_n.png",
        "4.6": "results/baseline/plots/success_rate_vs_n.png",
        "4.7": "results/baseline/explain/theory_vs_measured.png",
    },
}

STYLE = (
    "<style>"
    "body{max-width:860px;margin:2rem auto;padding:0 1.2rem;"
    "font-family:Georgia,'Times New Roman',serif;line-height:1.65;color:#1a1a1a}"
    "h1{font-size:2rem}h2{border-bottom:2px solid #ccc;padding-bottom:.2rem;margin-top:2.2rem}"
    "h3{color:#333;margin-top:1.8rem}"
    "figure{margin:1.4rem 0;text-align:center}"
    "figcaption{font-size:.85em;color:#666;margin-top:.3rem}"
    "img{max-width:100%;border:1px solid #ddd;border-radius:4px;"
    "box-shadow:0 1px 4px rgba(0,0,0,.08)}"
    "code{background:#f4f4f4;padding:.1em .3em;border-radius:3px;font-size:.9em}"
    "table{border-collapse:collapse;margin:1rem 0}td,th{border:1px solid #ccc;padding:.3em .6em}"
    ".cite{color:#9a9a9a;font-size:.78em}"
    "</style>\n"
)

_CAP = re.compile(r"\*\*Figure\s+(\d+\.\d+)")
_REF = re.compile(r"Figure\s+(\d+\.\d+)")
_SRC = re.compile(r"Source:\s*`?([^\s`]+)\.pdf`?")


def _png_for(num: str, para: str, overrides: dict) -> str | None:
    if num in overrides:
        return overrides[num]
    m = _SRC.search(para)
    return m.group(1) + ".png" if m else None


def build(draft: str, out: str) -> tuple[str, list[str]]:
    base = os.path.basename(draft)
    overrides = OVERRIDES.get(base, {})
    md = open(os.path.join(ROOT, draft)).read()
    paras = re.split(r"\n\s*\n", md.strip())
    caption_figs = {m.group(1) for p in paras if (m := _CAP.match(p.lstrip()))}

    emitted: list[str] = []
    chunks: list[str] = []
    missing: list[str] = []

    def emit(num: str, png: str | None, alt: str = "") -> None:
        if not png or num in emitted:
            return
        abs_png = os.path.join(ROOT, png)
        if not os.path.exists(abs_png):
            missing.append(f"Figure {num} -> {png} (not on disk)")
            return
        chunks.append(f"![{alt}]({abs_png})")
        emitted.append(num)

    for p in paras:
        chunks.append(p)
        cap = _CAP.match(p.lstrip())
        if cap:                                    # caption block -> after caption
            num = cap.group(1)
            emit(num, _png_for(num, p, overrides))
        else:                                      # inline-only figs -> at first mention
            for num in _REF.findall(p):
                if num in overrides and num not in caption_figs:
                    emit(num, overrides[num], alt=f"Figure {num}")

    body = re.sub(r"\[\[([^\]]+)\]\]", r'<span class="cite">[\1]</span>',
                  "\n\n".join(chunks))
    note = (f'<p style="color:#888;font-style:italic">Preview of {draft} — '
            "figures inline. Generated for reading; not a committed artifact.</p>\n\n")
    md_path = out.rsplit(".", 1)[0] + ".md"
    with open(md_path, "w") as f:
        f.write(STYLE + note + body)

    title = f"{base} — review preview"
    attempts = (
        ["--standalone", "--embed-resources"],
        ["--self-contained"],
        ["--standalone"],
    )
    for flags in attempts:
        try:
            subprocess.run(["pandoc", md_path, "-o", out, *flags,
                            "--metadata", f"title={title}"], check=True)
            break
        except subprocess.CalledProcessError:
            continue
    else:
        raise SystemExit("pandoc failed (is it installed?)")
    return out, missing


def main() -> None:
    draft = sys.argv[1] if len(sys.argv) > 1 else "drafts/ch4_results.md"
    stem = os.path.basename(draft).rsplit(".", 1)[0]
    out = sys.argv[2] if len(sys.argv) > 2 else f"/tmp/{stem}_preview.html"
    out, missing = build(draft, out)
    print(f"wrote {out}")
    for m in missing:
        print(f"  WARNING missing: {m}")
    if sys.platform == "darwin":
        subprocess.run(["open", out], check=False)


if __name__ == "__main__":
    main()
