#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf4llm"]
# ///
"""
Convert a large PDF (e.g. a Yamaha Data List) into small Markdown files.

Tables are kept as Markdown tables. The output is split along the PDF's
table of contents so each file covers one section and can be read on its
own without loading the whole document. Long sections are split further
into parts of at most --max-pages pages. An index.md lists every file with
its page range.

Usage:
    uv run scripts/pdf_to_markdown.py <input.pdf> <output_dir> [--max-pages N]
"""

import argparse
import re
import sys
from pathlib import Path

import pymupdf
import pymupdf4llm


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "-", text) or "section"


def plan_sections(doc: pymupdf.Document, max_pages: int) -> list[dict]:
    """Split the document into page ranges, one per leaf TOC entry.

    TOC entries that start on the same page are merged into one section.
    Pages are 0-based and the end of each range is exclusive.
    """
    toc = doc.get_toc()
    n = doc.page_count

    if not toc:
        starts = [(0, [doc.metadata.get("title") or "Document"])]
    else:
        # Leaf entries: those not immediately followed by a deeper entry.
        leaves = []
        for i, (level, title, page) in enumerate(toc):
            next_level = toc[i + 1][0] if i + 1 < len(toc) else 0
            if next_level <= level and page >= 1:
                parent = next((t for lv, t, _ in reversed(toc[:i]) if lv < level), None)
                leaves.append((page - 1, f"{parent} - {title}" if parent else title))
        # Merge entries sharing a start page.
        merged: dict[int, list[str]] = {}
        for start, title in leaves:
            merged.setdefault(start, []).append(title)
        starts = sorted(merged.items())
        if starts[0][0] > 0:
            starts.insert(0, (0, ["Front Matter"]))

    sections = []
    for i, (start, titles) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else n
        if end <= start:
            continue
        title = " / ".join(titles)
        chunks = range(start, end, max_pages)
        for part, chunk_start in enumerate(chunks, 1):
            chunk_end = min(chunk_start + max_pages, end)
            sections.append({
                "title": title + (f" (part {part})" if len(chunks) > 1 else ""),
                "start": chunk_start,
                "end": chunk_end,
            })
    return sections


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--max-pages", type=int, default=12, help="maximum pages per output file (default 12)")
    args = parser.parse_args()

    doc = pymupdf.open(args.pdf)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    sections = plan_sections(doc, args.max_pages)

    index_rows = []
    for num, sec in enumerate(sections, 1):
        pages = list(range(sec["start"], sec["end"]))
        name = f"{num:02d}-{slugify(sec['title'])[:60]}.md"
        page_label = f"{sec['start'] + 1}-{sec['end']}" if len(pages) > 1 else f"{sec['start'] + 1}"
        print(f"[{num}/{len(sections)}] pages {page_label}: {sec['title']}", file=sys.stderr)

        body = pymupdf4llm.to_markdown(doc, pages=pages, show_progress=False)
        header = f"# {sec['title']}\n\n*Source: {args.pdf.name}, PDF pages {page_label}*\n\n"
        (args.out_dir / name).write_text(header + body, encoding="utf-8")
        index_rows.append((name, sec["title"], page_label, len(header + body)))

    meta = doc.metadata
    lines = [
        f"# {meta.get('title') or args.pdf.stem}",
        "",
        f"Converted from `{args.pdf.name}` ({doc.page_count} pages). "
        "Each file covers one section; read only the ones you need.",
        "",
        "| File | Section | PDF pages | Size |",
        "|---|---|---|---|",
    ]
    lines += [f"| [{n}]({n}) | {t} | {p} | {s // 1024} KB |" for n, t, p, s in index_rows]
    (args.out_dir / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(index_rows)} files + index.md to {args.out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
