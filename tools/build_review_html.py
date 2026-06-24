#!/usr/bin/env python3
"""Build a single self-contained HTML review document from the thesis drafts.

Reads every chapter in drafts/, renders markdown -> HTML with pandoc, resolves
each figure caption to its real plot/diagram asset, base64-embeds the images so
the output is one portable file, and wraps everything in a reader-friendly shell
(auto table of contents, scroll-spy, reading-time estimates, citation/TODO
toggles, figure lightbox, light/sepia/dark themes, print-to-PDF).

Usage:  python3 tools/build_review_html.py
Output: review/thesis-review.html   (open in any browser; no network needed)

Re-run after editing any draft to regenerate. Pure stdlib + pandoc on PATH.
"""

import base64
import html
import mimetypes
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFTS = os.path.join(ROOT, "drafts")
RESULTS = os.path.join(ROOT, "results")
DIAGRAMS = os.path.join(ROOT, "wiki", "diagrams")
OUT_DIR = os.path.join(ROOT, "review")
OUT = os.path.join(OUT_DIR, "thesis-review.html")

# Chapter order + display metadata. `deliver` feeds the sidebar reading guide.
CHAPTERS = [
    ("front_acknowledgments.md", "Acknowledgments", "front",
     "Front matter. Contains TODO(human) placeholders to fill before submission."),
    ("ch1_intro.md", "Chapter 1 — Introduction", "ch1",
     "Problem, scope, and the five research questions (RQ1–RQ5). Read §1.5 first."),
    ("ch2_litreview.md", "Chapter 2 — Literature Review", "ch2",
     "The three families and why published numbers do not compare (the gap)."),
    ("ch3_methodology.md", "Chapter 3 — Methodology", "ch3",
     "Simulator, the three implemented protocols, metric schema, experiment matrix."),
    ("ch4_results.md", "Chapter 4 — Results", "ch4",
     "The core. Baseline + delay + adversarial sweeps; answers RQ1–RQ4."),
    ("ch5_synthesis.md", "Chapter 5 — Synthesis", "ch5",
     "Collates Ch4 into one Pareto frontier; answers RQ5 (no family dominates)."),
    ("ch6_conclusion.md", "Chapter 6 — Conclusions", "ch6",
     "Findings (§6.1), limitations (§6.2), further work (§6.3), closing (§6.4)."),
]

# RQ -> where-answered map for the guide (grounded in ch1 §1.5 + roadmap).
RQ_MAP = [
    ("RQ1", "Commit-latency scaling as network-delay variance grows", "Ch4 §4.3 (delay sweep)"),
    ("RQ2", "Throughput degradation as Byzantine fraction → fault bound", "Ch4 §4.4 (adversarial sweep)"),
    ("RQ3", "Relative communication overhead (msgs/bytes per unit)", "Ch4 §4.2.4 (baseline overhead)"),
    ("RQ4", "Which adversary breaks liveness vs safety vs neither", "Ch4 §4.4 (adversarial sweep)"),
    ("RQ5", "Cross-family Pareto frontier / does any family dominate", "Ch5 §5.4 (synthesis)"),
]


def pandoc(md_text):
    """Render GFM markdown to an HTML fragment via pandoc."""
    proc = subprocess.run(
        ["pandoc", "-f", "gfm", "-t", "html"],
        input=md_text.encode("utf-8"),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        sys.exit("pandoc failed: " + proc.stderr.decode("utf-8", "replace"))
    return proc.stdout.decode("utf-8")


def build_png_index():
    """basename(without .png) -> absolute path, skipping macOS ' 2.png' dupes."""
    idx = {}
    for dirpath, _dirs, files in os.walk(RESULTS):
        for f in files:
            if not f.endswith(".png") or f.endswith(" 2.png"):
                continue
            idx.setdefault(f[:-4], os.path.join(dirpath, f))
    return idx


PNG_INDEX = build_png_index()


def data_uri(path):
    mime, _ = mimetypes.guess_type(path)
    if mime is None:
        mime = "application/octet-stream"
    with open(path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("ascii")
    return "data:%s;base64,%s" % (mime, b64)


def resolve_pdf_source(path):
    """`results/.../foo.pdf` reference -> embedded PNG <img>, matched by basename."""
    base = os.path.splitext(os.path.basename(path.strip()))[0]
    p = PNG_INDEX.get(base)
    if not p:
        return None
    return '<img class="figimg" loading="lazy" alt="%s" src="%s">' % (
        html.escape(base), data_uri(p))


def resolve_diagram_slug(slug):
    """`diagrams/runtime/macro` -> embedded SVG <img>, or None if not exported."""
    p = os.path.join(DIAGRAMS, slug + ".svg")
    if not os.path.exists(p):
        return None
    return '<img class="figimg svgimg" loading="lazy" alt="%s" src="%s">' % (
        html.escape(slug), data_uri(p))


FIG_P = re.compile(r"<p>\s*<strong>\s*Figure\s+([0-9]+(?:\.[0-9]+)?)", re.S)
PARA = re.compile(r"<p>.*?</p>", re.S)
PDF_REF = re.compile(r"results/[A-Za-z0-9_./ -]+?\.pdf")
DIAG_REF = re.compile(r"\[\[diagrams/([^\]#]+?)\]\]")

# Figures whose caption cites an experiment page (the draft-style data-plot
# convention) instead of an inline results/*.pdf path, so the path/slug resolvers
# above cannot reach them. Map figure number -> PNG basename in results/.
FIG_FALLBACK = {"5.1": "frontier_radar"}


def inject_figures(frag):
    """Replace each bold 'Figure N.M' caption paragraph with a <figure>."""
    def repl(m):
        para = m.group(0)
        fm = FIG_P.match(para)
        if not fm:
            return para
        fignum = fm.group(1)
        imgs, missing = [], []

        for ref in PDF_REF.findall(para):
            tag = resolve_pdf_source(ref)
            if tag:
                imgs.append(tag)
            else:
                missing.append(os.path.basename(ref))
        if not imgs:
            for slug in DIAG_REF.findall(para):
                tag = resolve_diagram_slug(slug)
                if tag:
                    imgs.append(tag)
                else:
                    missing.append("diagrams/" + slug)
        if not imgs:
            base = FIG_FALLBACK.get(fignum)
            if base and base in PNG_INDEX:
                imgs.append('<img class="figimg" loading="lazy" alt="%s" src="%s">'
                            % (html.escape(base), data_uri(PNG_INDEX[base])))

        # Caption text = paragraph inner HTML, with the diagram parenthetical removed.
        caption = para[3:-4]  # strip <p> ... </p>
        caption = re.sub(r"\s*\(\s*\[\[diagrams/[^\]]+\]\]\s*\)", "", caption)

        if not imgs:
            body = ('<div class="fig-missing">Figure asset not yet exported'
                    + (": <code>%s</code>" % html.escape(", ".join(missing)) if missing else "")
                    + "</div>")
        else:
            body = "".join('<div class="figimg-wrap">%s</div>' % t for t in imgs)

        anchor = "fig-" + fignum.replace(".", "-")
        return ('<figure class="fig" id="%s">%s<figcaption>%s</figcaption></figure>'
                % (anchor, body, caption))

    return PARA.sub(repl, frag)


CITE = re.compile(r"\[\[([^\]]+?)\]\]")
TODO = re.compile(r"TODO\([^)]*\)")
HEAD_ID = re.compile(r"(<h[1-6])\s+id=\"[^\"]*\"")


def style_citations(frag):
    def repl(m):
        ref = m.group(1)
        short = ref.split("/")[-1].split("#")[0]
        return ('<span class="cite" title="%s">%s</span>'
                % (html.escape(ref), html.escape(short)))
    return CITE.sub(repl, frag)


def style_todos(frag):
    return TODO.sub(lambda m: '<mark class="todo">%s</mark>' % html.escape(m.group(0)), frag)


def word_count(md_text):
    txt = re.sub(r"`[^`]*`", " ", md_text)
    txt = re.sub(r"[#>*_\-|\[\]]", " ", txt)
    return len(txt.split())


def process_chapter(fname, title, anchor):
    with open(os.path.join(DRAFTS, fname), encoding="utf-8") as fh:
        md = fh.read()
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)  # drop build-instruction comments
    words = word_count(md)
    frag = pandoc(md)
    frag = HEAD_ID.sub(r"\1", frag)      # let JS own heading ids
    if "<h1" not in frag:                # front matter has no heading of its own
        frag = "<h1>%s</h1>\n%s" % (html.escape(title), frag)
    frag = inject_figures(frag)
    frag = style_citations(frag)
    frag = style_todos(frag)
    rt = max(1, round(words / 200))
    section = ('<section class="chapter" id="%s" data-title="%s" data-rt="%d" data-wc="%d">\n%s\n</section>'
               % (anchor, html.escape(title), rt, words, frag))
    return section, rt, words


def main():
    sections, metas = [], []
    for fname, title, anchor, deliver in CHAPTERS:
        sec, rt, wc = process_chapter(fname, title, anchor)
        sections.append(sec)
        metas.append((title, anchor, rt, wc, deliver))
    body = "\n".join(sections)

    # Sidebar reading-guide pieces (static HTML).
    total_rt = sum(m[2] for m in metas)
    total_wc = sum(m[3] for m in metas)
    guide_rows = "".join(
        '<li><a href="#%s"><span class="g-title">%s</span>'
        '<span class="g-rt">~%d min</span></a>'
        '<span class="g-deliver">%s</span></li>'
        % (anchor, html.escape(title), rt, html.escape(deliver))
        for (title, anchor, rt, _wc, deliver) in metas)
    rq_rows = "".join(
        '<tr><td class="rq-id">%s</td><td>%s</td><td class="rq-where">%s</td></tr>'
        % (rid, html.escape(q), html.escape(where))
        for (rid, q, where) in RQ_MAP)

    out = (TEMPLATE
           .replace("__BODY__", body)
           .replace("__GUIDE_ROWS__", guide_rows)
           .replace("__RQ_ROWS__", rq_rows)
           .replace("__TOTAL_RT__", str(total_rt))
           .replace("__TOTAL_WC__", format(total_wc, ",")))

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(out)
    size_mb = os.path.getsize(OUT) / 1e6
    print("Wrote %s  (%.1f MB, %d chapters, ~%d min total read)"
          % (os.path.relpath(OUT, ROOT), size_mb, len(metas), total_rt))


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Thesis Review — L1 Consensus Evaluation</title>
<style>
:root{
  --bg:#ffffff; --fg:#1d2026; --muted:#6b7280; --rule:#e5e7eb; --rule2:#eef0f3;
  --side:#f7f8fa; --side-fg:#2b2f36; --accent:#2563eb; --accent-soft:#dbeafe;
  --cite:#7c8499; --todo-bg:#fff3cd; --todo-fg:#7a5b00; --code-bg:#f3f4f6;
  --fig-bg:#fafbfc; --shadow:0 1px 3px rgba(0,0,0,.08); --content:780px;
}
html[data-theme="sepia"]{
  --bg:#f6efe2; --fg:#3a3226; --muted:#7d7058; --rule:#e2d7c1; --rule2:#ece3d2;
  --side:#efe6d4; --side-fg:#4a4030; --accent:#9a5b2c; --accent-soft:#ecdcc6;
  --code-bg:#ece3d2; --fig-bg:#f1e9d9; --cite:#8d7d60; --todo-bg:#efe0b8; --todo-fg:#6b4e00;
}
html[data-theme="dark"]{
  --bg:#15171c; --fg:#dfe3ea; --muted:#9aa3b2; --rule:#2b2f38; --rule2:#23262e;
  --side:#1b1e25; --side-fg:#c7cdd8; --accent:#6ea8fe; --accent-soft:#22324d;
  --code-bg:#242832; --fig-bg:#1c1f27; --cite:#7f8aa0; --todo-bg:#473b16; --todo-fg:#f1d98a;
  --shadow:0 1px 3px rgba(0,0,0,.4);
}
*{box-sizing:border-box}
html{font-size:var(--fs,18px);scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--fg);
  font-family:Georgia,"Iowan Old Style","Source Serif Pro",serif;line-height:1.7;
  -webkit-font-smoothing:antialiased}
#progress{position:fixed;top:0;left:0;height:3px;width:0;background:var(--accent);z-index:50;transition:width .1s}

/* layout */
#shell{display:grid;grid-template-columns:320px 1fr}
#side{position:sticky;top:0;align-self:start;height:100vh;overflow-y:auto;
  background:var(--side);color:var(--side-fg);border-right:1px solid var(--rule);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
  font-size:.82rem;line-height:1.5;padding:0}
#main{min-width:0;display:flex;justify-content:center;padding:48px 40px 160px}
#doc{width:100%;max-width:var(--content)}

/* sidebar blocks */
.s-pad{padding:14px 16px;border-bottom:1px solid var(--rule)}
.s-title{font-weight:700;font-size:.95rem;margin:0 0 2px}
.s-sub{color:var(--muted);font-size:.74rem}
.controls{display:flex;flex-wrap:wrap;gap:6px}
.controls button{font:inherit;font-size:.74rem;cursor:pointer;border:1px solid var(--rule);
  background:var(--bg);color:var(--side-fg);border-radius:7px;padding:5px 9px;line-height:1}
.controls button:hover{border-color:var(--accent);color:var(--accent)}
.controls button.on{background:var(--accent-soft);border-color:var(--accent);color:var(--accent)}
.seg{display:inline-flex;border:1px solid var(--rule);border-radius:7px;overflow:hidden}
.seg button{border:0;border-radius:0;border-right:1px solid var(--rule)}
.seg button:last-child{border-right:0}

details.guide{border-bottom:1px solid var(--rule)}
details.guide>summary{cursor:pointer;padding:11px 16px;font-weight:700;font-size:.82rem;list-style:none;
  display:flex;justify-content:space-between;align-items:center;user-select:none}
details.guide>summary::-webkit-details-marker{display:none}
details.guide>summary::after{content:"▾";color:var(--muted);transition:transform .2s}
details.guide:not([open])>summary::after{transform:rotate(-90deg)}
.guide-body{padding:0 16px 14px}
.guide-body p{margin:.5em 0;color:var(--side-fg)}
.guide-body ol{margin:.4em 0 .4em 1.1em;padding:0}
.guide-body ol li{margin:.28em 0}
ul.chlist{list-style:none;margin:.2em 0;padding:0}
ul.chlist li{padding:7px 0;border-bottom:1px dashed var(--rule)}
ul.chlist li:last-child{border-bottom:0}
ul.chlist a{display:flex;justify-content:space-between;gap:8px;text-decoration:none;color:var(--side-fg);font-weight:600}
ul.chlist a:hover .g-title{color:var(--accent)}
.g-rt{color:var(--muted);font-weight:400;white-space:nowrap}
.g-deliver{display:block;color:var(--muted);font-weight:400;margin-top:2px;font-size:.76rem}
table.rq{width:100%;border-collapse:collapse;margin:.3em 0;font-size:.76rem}
table.rq td{border-bottom:1px solid var(--rule);padding:5px 4px;vertical-align:top}
.rq-id{font-weight:700;color:var(--accent);white-space:nowrap}
.rq-where{color:var(--muted);white-space:nowrap}
.legend{font-size:.76rem;color:var(--side-fg)}
.legend div{margin:5px 0;display:flex;gap:7px;align-items:baseline}

/* TOC */
#toc-wrap{padding:10px 8px 40px}
#toc-wrap .toc-h{padding:4px 8px;color:var(--muted);font-size:.7rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700}
#toc a{display:block;text-decoration:none;color:var(--side-fg);padding:4px 8px;border-radius:6px;
  border-left:2px solid transparent}
#toc a:hover{background:var(--bg)}
#toc a.lvl1{font-weight:700;margin-top:8px}
#toc a.lvl2{padding-left:18px;font-size:.8rem}
#toc a.lvl3{padding-left:30px;font-size:.76rem;color:var(--muted)}
#toc a.active{color:var(--accent);border-left-color:var(--accent);background:var(--accent-soft)}

/* document prose */
#doc h1{font-size:1.95rem;line-height:1.2;margin:0 0 .2em;padding-bottom:.3em;border-bottom:2px solid var(--rule)}
#doc h2{font-size:1.4rem;margin:1.8em 0 .5em;padding-top:.2em}
#doc h3{font-size:1.12rem;margin:1.5em 0 .4em;color:var(--fg)}
#doc h4{font-size:1rem;margin:1.3em 0 .3em;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
#doc p{margin:0 0 1.05em}
#doc a{color:var(--accent)}
#doc code{background:var(--code-bg);border-radius:4px;padding:.08em .35em;font-size:.86em;
  font-family:"SF Mono",Menlo,Consolas,monospace}
#doc pre{background:var(--code-bg);border-radius:8px;padding:14px 16px;overflow-x:auto;font-size:.82rem}
#doc pre code{background:none;padding:0}
#doc blockquote{margin:1em 0;padding:.3em 1.1em;border-left:3px solid var(--rule);color:var(--muted)}
#doc ul,#doc ol{margin:0 0 1.05em;padding-left:1.4em}
#doc li{margin:.3em 0}
#doc table{border-collapse:collapse;width:100%;margin:1.2em 0;font-size:.84rem;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
#doc th,#doc td{border:1px solid var(--rule);padding:7px 10px;text-align:left;vertical-align:top}
#doc thead th{background:var(--side);font-weight:700}
#doc tbody tr:nth-child(even){background:var(--rule2)}

.chapter{padding-top:24px;scroll-margin-top:16px}
.chapter+.chapter{margin-top:36px}
.chmeta{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:.74rem;
  color:var(--muted);margin:.2em 0 1.6em;display:flex;gap:14px;flex-wrap:wrap}
.chmeta span{display:inline-flex;align-items:center;gap:4px}

/* figures */
figure.fig{margin:1.8em 0;padding:16px;background:var(--fig-bg);border:1px solid var(--rule);
  border-radius:10px;box-shadow:var(--shadow);scroll-margin-top:16px}
.figimg-wrap{text-align:center}
figure.fig .figimg{max-width:100%;height:auto;cursor:zoom-in;border-radius:4px;
  background:#fff}
figure.fig .svgimg{background:#fff;padding:6px}
figure.fig figcaption{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  font-size:.8rem;line-height:1.5;color:var(--muted);margin-top:12px;padding-top:10px;
  border-top:1px solid var(--rule)}
figure.fig figcaption strong{color:var(--fg)}
.fig-missing{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:.82rem;
  color:var(--todo-fg);background:var(--todo-bg);border-radius:6px;padding:18px;text-align:center}

/* citation chips + todo */
.cite{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:.66em;
  vertical-align:.25em;color:var(--cite);background:var(--code-bg);border-radius:4px;
  padding:.05em .4em;margin:0 .12em;cursor:help;white-space:nowrap;font-weight:600}
.cite::before{content:"§ "}
body.hide-cites .cite{display:none}
mark.todo{background:var(--todo-bg);color:var(--todo-fg);border-radius:4px;padding:.02em .3em;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:.82em;font-weight:600}
body.hide-todos mark.todo{background:none;color:inherit;font-weight:inherit;padding:0}

/* lightbox */
#lb{position:fixed;inset:0;background:rgba(0,0,0,.86);display:none;z-index:100;
  cursor:zoom-out;padding:30px}
#lb.open{display:flex;align-items:center;justify-content:center}
#lb img{max-width:96%;max-height:96%;background:#fff;border-radius:6px;box-shadow:0 10px 40px rgba(0,0,0,.5)}

#totop{position:fixed;right:22px;bottom:22px;z-index:40;border:1px solid var(--rule);
  background:var(--side);color:var(--side-fg);border-radius:50%;width:42px;height:42px;
  cursor:pointer;font-size:1.1rem;display:none;box-shadow:var(--shadow)}
#totop.show{display:block}

#sidetoggle{display:none}

@media (max-width:900px){
  #shell{grid-template-columns:1fr}
  #side{position:fixed;left:0;top:0;width:300px;z-index:60;transform:translateX(-100%);transition:transform .25s}
  body.side-open #side{transform:translateX(0)}
  #sidetoggle{display:block;position:fixed;left:14px;top:12px;z-index:70;border:1px solid var(--rule);
    background:var(--side);color:var(--side-fg);border-radius:8px;padding:8px 11px;cursor:pointer;box-shadow:var(--shadow)}
  #main{padding:64px 20px 140px}
}

@media print{
  #side,#progress,#totop,#sidetoggle,#lb{display:none!important}
  #shell{grid-template-columns:1fr}
  #main{padding:0}
  body{font-size:11pt}
  .cite{display:none}
  figure.fig{break-inside:avoid;box-shadow:none}
  .chapter{break-before:page}
  .chapter:first-of-type{break-before:auto}
}
</style>
</head>
<body>
<div id="progress"></div>
<button id="sidetoggle" aria-label="Toggle sidebar">☰ Contents</button>

<div id="shell">
<aside id="side">
  <div class="s-pad">
    <p class="s-title">Thesis — Review build</p>
    <p class="s-sub">L1 consensus evaluation · ~__TOTAL_RT__ min · __TOTAL_WC__ words</p>
  </div>

  <div class="s-pad">
    <div class="controls">
      <span class="seg" role="group" aria-label="Theme">
        <button data-theme="light" title="Light">☀</button>
        <button data-theme="sepia" title="Sepia">◐</button>
        <button data-theme="dark" title="Dark">☾</button>
      </span>
      <span class="seg" role="group" aria-label="Font size">
        <button id="fs-down" title="Smaller text">A−</button>
        <button id="fs-up" title="Larger text">A+</button>
      </span>
      <button id="t-cites" title="Toggle citation chips">§ refs</button>
      <button id="t-todos" class="on" title="Toggle TODO highlight">TODO</button>
      <button id="t-print" title="Print / Save as PDF">⎙ PDF</button>
    </div>
  </div>

  <details class="guide" open>
    <summary>How to read this efficiently</summary>
    <div class="guide-body">
      <p>This is a <strong>review build</strong> of the drafted chapters, regenerated from
      <code>drafts/</code>. Figures are the real plots/diagrams, embedded inline.</p>
      <p><strong>Suggested order</strong></p>
      <ol>
        <li>Read <strong>Ch1 §1.5</strong> (the five RQs) — they frame everything below.</li>
        <li>Skim <strong>Ch2</strong> for the three families and "the gap" (§2.5).</li>
        <li><strong>Ch3</strong>: read §3.2 system model + §3.5 metric schema closely; skim the per-protocol subsections.</li>
        <li><strong>Ch4</strong> is the payload — go sweep by sweep (§4.2 → §4.3 → §4.4). Every figure caption is self-contained.</li>
        <li><strong>Ch5</strong> collates Ch4 into one Pareto frontier and settles RQ5 (§5.4).</li>
        <li><strong>Ch6</strong> for findings, limitations, and further work.</li>
      </ol>
      <p><strong>Scope note:</strong> the thesis evaluates three protocols
      (PBFT, Casper FFG, Snowman); a DAG-based family (Narwhal+Tusk) is noted only
      as further work (Ch6 §6.3.2).</p>
    </div>
  </details>

  <details class="guide" open>
    <summary>Chapters at a glance</summary>
    <div class="guide-body">
      <ul class="chlist">__GUIDE_ROWS__</ul>
    </div>
  </details>

  <details class="guide">
    <summary>Where each RQ is answered</summary>
    <div class="guide-body">
      <table class="rq"><tbody>__RQ_ROWS__</tbody></table>
    </div>
  </details>

  <details class="guide">
    <summary>Legend</summary>
    <div class="guide-body legend">
      <div><span class="cite" title="example/path">slug</span><span>citation to a wiki page (hover for full path; toggle with "§ refs")</span></div>
      <div><mark class="todo">TODO(...)</mark><span>an unresolved authoring gap (toggle highlight with "TODO")</span></div>
      <div><code>code</code><span>a metric, symbol, or config key</span></div>
      <div><span>🔍</span><span>click any figure to enlarge</span></div>
    </div>
  </details>

  <nav id="toc-wrap">
    <div class="toc-h">Contents</div>
    <div id="toc"></div>
  </nav>
</aside>

<div id="main"><article id="doc">
__BODY__
</article></div>
</div>

<div id="lb"><img alt="enlarged figure"></div>
<button id="totop" title="Back to top">↑</button>

<script>
(function(){
  var root=document.documentElement, body=document.body;
  function save(k,v){try{localStorage.setItem(k,v)}catch(e){}}
  function load(k){try{return localStorage.getItem(k)}catch(e){return null}}

  // theme
  function setTheme(t){root.setAttribute("data-theme",t);save("rv-theme",t);
    document.querySelectorAll(".seg [data-theme]").forEach(function(b){b.classList.toggle("on",b.dataset.theme===t)});}
  setTheme(load("rv-theme")||"light");
  document.querySelectorAll(".seg [data-theme]").forEach(function(b){
    b.addEventListener("click",function(){setTheme(b.dataset.theme)});});

  // font size
  var fs=parseInt(load("rv-fs")||"18",10);
  function setFs(v){fs=Math.max(14,Math.min(24,v));root.style.setProperty("--fs",fs+"px");save("rv-fs",fs);}
  setFs(fs);
  document.getElementById("fs-up").onclick=function(){setFs(fs+1)};
  document.getElementById("fs-down").onclick=function(){setFs(fs-1)};

  // toggles
  var tc=document.getElementById("t-cites"), tt=document.getElementById("t-todos");
  function applyCites(){var h=load("rv-hidecite")==="1";body.classList.toggle("hide-cites",h);tc.classList.toggle("on",!h);}
  function applyTodos(){var h=load("rv-hidetodo")==="1";body.classList.toggle("hide-todos",h);tt.classList.toggle("on",!h);}
  applyCites();applyTodos();
  tc.onclick=function(){save("rv-hidecite",load("rv-hidecite")==="1"?"0":"1");applyCites();};
  tt.onclick=function(){save("rv-hidetodo",load("rv-hidetodo")==="1"?"0":"1");applyTodos();};
  document.getElementById("t-print").onclick=function(){window.print();};

  // per-chapter meta line + heading ids
  var slugCount={};
  function slug(s){var b=s.toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"");
    if(slugCount[b]!=null){slugCount[b]++;b=b+"-"+slugCount[b];}else{slugCount[b]=0;}return b;}
  var chapters=document.querySelectorAll(".chapter");
  chapters.forEach(function(ch){
    var rt=ch.dataset.rt, wc=ch.dataset.wc;
    var h1=ch.querySelector("h1");
    if(h1){
      var meta=document.createElement("div");meta.className="chmeta";
      meta.innerHTML='<span>⏱ ~'+rt+' min read</span><span>📝 '+Number(wc).toLocaleString()+' words</span>';
      h1.insertAdjacentElement("afterend",meta);
    }
  });

  // build TOC
  var toc=document.getElementById("toc"), heads=[];
  document.querySelectorAll("#doc h1,#doc h2,#doc h3").forEach(function(h){
    if(!h.id) h.id=slug(h.textContent);
    var lvl=h.tagName==="H1"?1:(h.tagName==="H2"?2:3);
    var a=document.createElement("a");a.href="#"+h.id;a.className="lvl"+lvl;a.textContent=h.textContent;
    toc.appendChild(a);heads.push(h);
    h.style.scrollMarginTop="16px";
  });

  // scroll-spy
  var links={};toc.querySelectorAll("a").forEach(function(a){links[a.getAttribute("href").slice(1)]=a;});
  var spy=new IntersectionObserver(function(ents){
    ents.forEach(function(e){
      if(e.isIntersecting){
        toc.querySelectorAll("a.active").forEach(function(a){a.classList.remove("active");});
        var a=links[e.target.id];
        if(a){a.classList.add("active");a.scrollIntoView({block:"nearest"});}
      }
    });
  },{rootMargin:"-10% 0px -78% 0px",threshold:0});
  heads.forEach(function(h){spy.observe(h);});

  // reading progress
  var prog=document.getElementById("progress"), totop=document.getElementById("totop");
  function onScroll(){
    var st=window.scrollY||document.documentElement.scrollTop;
    var h=document.documentElement.scrollHeight-window.innerHeight;
    prog.style.width=(h>0?(st/h*100):0)+"%";
    totop.classList.toggle("show",st>600);
  }
  window.addEventListener("scroll",onScroll,{passive:true});onScroll();
  totop.onclick=function(){window.scrollTo({top:0,behavior:"smooth"});};

  // lightbox
  var lb=document.getElementById("lb"), lbimg=lb.querySelector("img");
  document.querySelectorAll("figure.fig .figimg").forEach(function(img){
    img.addEventListener("click",function(){lbimg.src=img.src;lb.classList.add("open");});
  });
  lb.addEventListener("click",function(){lb.classList.remove("open");lbimg.src="";});

  // mobile sidebar
  var st=document.getElementById("sidetoggle");
  st.onclick=function(){body.classList.toggle("side-open");};
  document.getElementById("toc").addEventListener("click",function(){body.classList.remove("side-open");});
})();
</script>
</body>
</html>"""


if __name__ == "__main__":
    main()
