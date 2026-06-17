#!/usr/bin/env python3
"""Regenerate the self-contained Chapter 3 HTML preview from its sources.

`ch3_methodology.html` (at the repo root) embeds two kinds of source copies
that the page JS renders at load time:

  * the chapter markdown, inside
    `<script type="text/markdown" id="chapter-md"> ... </script>`, and
  * one diagram per
    `<script type="text/x-mermaid" data-slug="SLUG"> ... </script>`.

The HTML never reads the source files at runtime, so those embedded copies
drift whenever the sources change. This script re-syncs them in place from
the canonical sources:

  * chapter markdown  <- drafts/ch3_methodology.md
  * each diagram body <- wiki/diagrams/<rest>.md  (for slug
    `diagrams/<rest>`), taking the inner content of that file's first
    ```mermaid fenced code block.

Only the bodies of those script blocks are rewritten; the surrounding
CSS/JS/banner shell is left byte-for-byte intact. The operation is
idempotent: a second run reports no changes.

Stdlib only. All paths are resolved relative to the repo root (the parent of
this `tools/` directory), so it works in any checkout.

Re-run command (from the repo root):

    python tools/sync_chapter_html.py
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HTML_PATH = REPO_ROOT / "ch3_methodology.html"
CHAPTER_MD_PATH = REPO_ROOT / "drafts" / "ch3_methodology.md"

CHAPTER_OPEN_TAG = '<script type="text/markdown" id="chapter-md">'
SCRIPT_CLOSE = "</script>"

# Matches one x-mermaid block, capturing the slug (group "slug") and the
# current body (group "body"). The body is non-greedy up to the first
# closing </script>; the embedded markdown is assumed to never contain the
# literal "</script>".
XMERMAID_RE = re.compile(
    r'(?P<open><script type="text/x-mermaid" data-slug="(?P<slug>[^"]+)">)'
    r"(?P<body>.*?)"
    r"(?P<close></script>)",
    re.DOTALL,
)

# Extracts the inner content of the first ```mermaid fenced code block.
MERMAID_FENCE_RE = re.compile(
    r"```mermaid[^\n]*\n(?P<inner>.*?)\n```",
    re.DOTALL,
)


def replace_chapter_md(html, chapter_md):
    """Return (new_html, changed) with the chapter-md block body replaced.

    Splices `chapter_md` between the opening chapter-md tag and its matching
    closing </script>, preserving both tags and everything else verbatim.
    """
    open_idx = html.find(CHAPTER_OPEN_TAG)
    if open_idx == -1:
        raise SystemExit(
            "ERROR: opening tag not found: " + CHAPTER_OPEN_TAG
        )
    body_start = open_idx + len(CHAPTER_OPEN_TAG)
    close_idx = html.find(SCRIPT_CLOSE, body_start)
    if close_idx == -1:
        raise SystemExit(
            "ERROR: no closing </script> found for chapter-md block"
        )

    old_body = html[body_start:close_idx]
    # The page JS renders the markdown via marked, which tolerates leading
    # whitespace; the original places the first line immediately after the
    # opening tag, so we keep that convention by inserting the raw draft.
    new_body = chapter_md
    if old_body == new_body:
        return html, False
    new_html = html[:body_start] + new_body + html[close_idx:]
    return new_html, True


def extract_mermaid(source_text):
    """Return the inner mermaid content, or None if there is no fence."""
    m = MERMAID_FENCE_RE.search(source_text)
    if not m:
        return None
    return m.group("inner").strip()


def replace_xmermaid_blocks(html, newline):
    """Replace each x-mermaid block body from its mapped wiki source.

    `newline` is the line-ending style of the surrounding HTML ("\\r\\n" or
    "\\n"); inserted bodies adopt it so the rewrite stays byte-consistent and
    idempotent in either kind of checkout.

    Returns (new_html, summary) where summary is a list of dicts describing
    each block: slug, status ("updated" | "unchanged" | "warn-missing" |
    "warn-no-fence"), old_len, new_len.
    """
    summary = []

    def _sub(match):
        slug = match.group("slug")
        old_body = match.group("body")

        # slug "diagrams/<rest>" -> wiki/diagrams/<rest>.md
        rel = slug + ".md"
        source_path = REPO_ROOT / "wiki" / Path(rel)

        record = {
            "slug": slug,
            "old_len": len(old_body),
            "new_len": len(old_body),
        }

        if not source_path.exists():
            record["status"] = "warn-missing"
            record["detail"] = str(source_path)
            summary.append(record)
            return match.group(0)  # leave block unchanged

        source_text = source_path.read_text(encoding="utf-8")
        inner = extract_mermaid(source_text)
        if inner is None:
            record["status"] = "warn-no-fence"
            record["detail"] = str(source_path)
            summary.append(record)
            return match.group(0)  # leave block unchanged

        # extract_mermaid returns content with translated "\n" newlines;
        # rewrap to the surrounding HTML's newline style. Match the page-JS
        # contract (it reads textContent.trim()): body on its own lines.
        inner = inner.replace("\n", newline)
        new_body = newline + inner + newline
        record["new_len"] = len(new_body)
        record["status"] = "updated" if new_body != old_body else "unchanged"
        summary.append(record)
        return match.group("open") + new_body + match.group("close")

    new_html = XMERMAID_RE.sub(_sub, html)
    return new_html, summary


def main():
    if not HTML_PATH.exists():
        raise SystemExit("ERROR: HTML not found: " + str(HTML_PATH))
    if not CHAPTER_MD_PATH.exists():
        raise SystemExit("ERROR: chapter markdown not found: " + str(CHAPTER_MD_PATH))

    # Read with newline="" (no newline translation) so CRLF/LF line endings
    # survive round-trip unchanged, keeping the rest of the file byte-for-byte
    # identical on rewrite.
    original = HTML_PATH.read_text(encoding="utf-8", newline="")
    chapter_md = CHAPTER_MD_PATH.read_text(encoding="utf-8", newline="")

    # Detect the HTML's newline style so inserted diagram bodies match it.
    html_newline = "\r\n" if "\r\n" in original else "\n"

    html, md_changed = replace_chapter_md(original, chapter_md)
    html, diagram_summary = replace_xmermaid_blocks(html, html_newline)

    will_write = html != original
    if will_write:
        HTML_PATH.write_text(html, encoding="utf-8", newline="")

    # --- summary report ---
    print("sync_chapter_html.py")
    print("  repo root : " + str(REPO_ROOT))
    print("  html      : " + str(HTML_PATH))
    print()
    print("chapter-md block:")
    print(
        "  source    : %s (%d bytes)"
        % (CHAPTER_MD_PATH.relative_to(REPO_ROOT), len(chapter_md))
    )
    print("  status    : " + ("updated" if md_changed else "unchanged"))
    print()
    print("x-mermaid blocks (%d):" % len(diagram_summary))
    warnings = []
    for rec in diagram_summary:
        status = rec["status"]
        if status == "updated":
            print(
                "  [updated]   %s  (%d -> %d bytes)"
                % (rec["slug"], rec["old_len"], rec["new_len"])
            )
        elif status == "unchanged":
            print("  [unchanged] %s  (%d bytes)" % (rec["slug"], rec["new_len"]))
        elif status == "warn-missing":
            msg = "WARNING: source file missing for slug '%s': %s (block left unchanged)" % (
                rec["slug"],
                rec["detail"],
            )
            print("  " + msg)
            warnings.append(msg)
        elif status == "warn-no-fence":
            msg = "WARNING: no ```mermaid fence in source for slug '%s': %s (block left unchanged)" % (
                rec["slug"],
                rec["detail"],
            )
            print("  " + msg)
            warnings.append(msg)
    print()
    if will_write:
        print("RESULT: ch3_methodology.html rewritten.")
    else:
        print("RESULT: no changes (already in sync).")
    if warnings:
        print("RESULT: %d warning(s) emitted." % len(warnings))

    # Non-zero exit only on hard errors; warnings do not fail the run.
    return 0


if __name__ == "__main__":
    sys.exit(main())
