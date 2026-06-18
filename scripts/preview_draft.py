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

Figure discovery (a caption is a paragraph beginning ``**Figure N.M``):
- Result plots come from a ``Source: `results/.../slug.pdf` `` line in the
  caption; the sibling ``slug.png`` is embedded right after it.
- Figures cited inline with no Source line are supplied by the per-file
  OVERRIDES table below. Chapter 4's baseline figures (4.1-4.6) are inline-only,
  and 4.7's PNG lives under ``explain/`` rather than beside its PDF, so they are
  listed there explicitly. Extend OVERRIDES when a new chapter needs it.
- Diagrams come from a wiki page wikilink in the caption, e.g.
  ``**Figure 3.1 ([[diagrams/runtime/architecture]])``. The page's Mermaid
  block is rendered live in-browser by mermaid.js (see MERMAID_JS) — no raster
  is embedded, so these figures need network to view (or a vendored mermaid.js).

Requires pandoc (https://pandoc.org). PNGs (gitignored screen renders) must
exist on disk — run the relevant ``output.*plots`` generator first if not.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile

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
    "pre.mermaid{background:none;border:none;text-align:center}"
    "</style>\n"
)

# Loader for diagrams rendered live in-browser from their Mermaid source. The
# preview embeds figures as <pre class="mermaid"> blocks (see build()); this
# script turns them into SVG. Loaded from a CDN, so viewing needs network —
# to make the preview fully offline, vendor mermaid.esm.min.mjs and point the
# import at the local copy. securityLevel 'loose' lets the diagrams' HTML
# labels (<b>, <br/>) render instead of being sanitized away.
MERMAID_JS = (
    '<script type="module">\n'
    "import mermaid from "
    "'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';\n"
    "mermaid.initialize({startOnLoad:true, securityLevel:'loose'});\n"
    "</script>\n"
)

_CAP = re.compile(r"\*\*Figure\s+(\d+\.\d+)")
_REF = re.compile(r"Figure\s+(\d+\.\d+)")
_SRC = re.compile(r"Source:\s*`?([^\s`]+)\.pdf`?")
# A caption may instead cite a wiki diagram page, e.g. [[diagrams/runtime/macro]];
# that page holds the figure's Mermaid source rather than a rendered raster.
_DIAG = re.compile(r"\[\[(diagrams/[^\]#|]+)")
_MERMAID = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)


def _png_for(num: str, para: str, overrides: dict) -> str | None:
    if num in overrides:
        return overrides[num]
    m = _SRC.search(para)
    return m.group(1) + ".png" if m else None


def _mermaid_for(diag: str) -> str | None:
    """Return the first Mermaid block from wiki/<diag>.md, or None."""
    path = os.path.join(ROOT, "wiki", diag + ".md")
    if not os.path.exists(path):
        return None
    m = _MERMAID.search(open(path, encoding="utf-8").read())
    return m.group(1).rstrip() if m else None


def build(draft: str, out: str) -> tuple[str, list[str]]:
    base = os.path.basename(draft)
    overrides = OVERRIDES.get(base, {})
    md = open(os.path.join(ROOT, draft), encoding="utf-8").read()
    paras = re.split(r"\n\s*\n", md.strip())
    caption_figs = {m.group(1) for p in paras if (m := _CAP.match(p.lstrip()))}

    emitted: list[str] = []
    chunks: list[str] = []
    missing: list[str] = []
    mermaids: dict[str, str] = {}              # fig num -> Mermaid source

    def emit(num: str, png: str | None, alt: str = "") -> None:
        if not png or num in emitted:
            return
        abs_png = os.path.join(ROOT, png)
        if not os.path.exists(abs_png):
            missing.append(f"Figure {num} -> {png} (not on disk)")
            return
        chunks.append(f"![{alt}]({abs_png})")
        emitted.append(num)

    def emit_diagram(num: str, diag: str) -> None:
        if num in emitted:
            return
        src = _mermaid_for(diag)
        if src is None:
            missing.append(f"Figure {num} -> {diag} (no Mermaid block found)")
            return
        mermaids[num] = src
        # Placeholder; the real <pre class="mermaid"> is spliced in after pandoc
        # so pandoc never touches the diagram source.
        chunks.append(f'<div class="mermaid-slot" data-fig="{num}"></div>')
        emitted.append(num)

    for p in paras:
        chunks.append(p)
        cap = _CAP.match(p.lstrip())
        if cap:                                    # caption block -> after caption
            num = cap.group(1)
            png = _png_for(num, p, overrides)
            if png:
                emit(num, png)
            elif (dm := _DIAG.search(p)):          # caption cites a diagram page
                emit_diagram(num, dm.group(1))
        else:                                      # inline-only figs -> at first mention
            for num in _REF.findall(p):
                if num in overrides and num not in caption_figs:
                    emit(num, overrides[num], alt=f"Figure {num}")

    body = re.sub(r"\[\[([^\]]+)\]\]", r'<span class="cite">[\1]</span>',
                  "\n\n".join(chunks))
    note = (f'<p style="color:#888;font-style:italic">Preview of {draft} — '
            "figures inline. Generated for reading; not a committed artifact.</p>\n\n")
    md_path = out.rsplit(".", 1)[0] + ".md"
    with open(md_path, "w", encoding="utf-8") as f:
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
        except FileNotFoundError:
            raise SystemExit(
                "pandoc not found on PATH. Install it from https://pandoc.org "
                "(Windows: `winget install --id JohnMacFarlane.Pandoc`)."
            )
        except subprocess.CalledProcessError:
            continue
    else:
        raise SystemExit("pandoc failed (is it installed?)")

    if mermaids:                                   # splice diagrams into the HTML
        html = open(out, encoding="utf-8").read()
        for num, src in mermaids.items():
            esc = src.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            fig = (f'<figure><pre class="mermaid">\n{esc}\n</pre>'
                   f'<figcaption>Figure {num}</figcaption></figure>')
            html = re.sub(
                rf'<div class="mermaid-slot" data-fig="{re.escape(num)}"\s*>\s*</div>',
                lambda _m, f=fig: f, html)
        html = (html.replace("</body>", MERMAID_JS + "</body>", 1)
                if "</body>" in html else html + MERMAID_JS)
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
    return out, missing


def main() -> None:
    draft = sys.argv[1] if len(sys.argv) > 1 else "drafts/ch4_results.md"
    stem = os.path.basename(draft).rsplit(".", 1)[0]
    default_out = os.path.join(tempfile.gettempdir(), f"{stem}_preview.html")
    out = sys.argv[2] if len(sys.argv) > 2 else default_out
    out, missing = build(draft, out)
    print(f"wrote {out}")
    for m in missing:
        print(f"  WARNING missing: {m}")
    if sys.platform == "darwin":
        subprocess.run(["open", out], check=False)
    elif sys.platform == "win32":
        os.startfile(out)  # noqa: in-script Windows-only call
    elif sys.platform.startswith("linux"):
        subprocess.run(["xdg-open", out], check=False)


if __name__ == "__main__":
    main()
