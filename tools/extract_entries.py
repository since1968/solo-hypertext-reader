#!/usr/bin/env python3
"""Extract a numbered-entry gamebook PDF into a Solo Hypertext Reader entries JSON.

Two ways to get page text:

  1. Default: renders each page with `pdftoppm` and OCRs it with `tesseract`
     (both must be installed and on PATH). Works standalone, no AI assistant
     needed, but stylized "drop-cap" entry numbers are a known weak spot for
     generic OCR -- see the "known limitations" note in the README.

  2. --text-dir DIR: ingests pre-transcribed per-page text files instead
     (e.g. produced by an AI assistant reading page images directly, which
     is far more accurate for this kind of book). Use --render-only first
     to produce page images in the naming convention this expects.

Usage:
    python3 tools/extract_entries.py PDF [options]
    python3 tools/extract_entries.py PDF --render-only [--pages START-END]
    python3 tools/extract_entries.py PDF --text-dir DIR [--pages START-END]

Exit codes:
    0  extraction completed, no validation errors
    1  extraction completed, but validation errors found (e.g. broken links)
    2  fatal error (bad PDF, missing tools, bad arguments)
"""

import argparse
import glob
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import namedtuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_entries  # noqa: E402  (path insert must happen first)

DEFAULT_DPI = 200
DEFAULT_MARGIN_TOP = 0.06
DEFAULT_MARGIN_BOTTOM = 0.06
# Empirically calibrated against real page renders (SJG6204 p.7): the true
# column gutter sits noticeably right of page-center, and margins are much
# tighter than a naive guess -- a naive 0.5/0.04/0.02 setup truncated real
# words on both columns. Tuned to this one publisher template; a different
# book will likely need --column-split/--margin-*/--gutter recalibrated the
# same way (bisect page-image crop widths until OCR stops truncating words).
DEFAULT_MARGIN_SIDE = 0.02
DEFAULT_COLUMN_SPLIT = 0.529
DEFAULT_GUTTER = 0.012
DEFAULT_PSM = 6
DEFAULT_LANG = "eng"
DEFAULT_FIRST_ID = 1
DEFAULT_INTRO_HEADING = "introduction"
DEFAULT_RESYNC_LOOKAHEAD = 3
DEFAULT_MAX_ENTRY_CHARS = 8000

QA_KEYWORDS = ["roll", "Plot Word", "Morale", "Combat Map"]

PageText = namedtuple("PageText", ["page_num", "text"])
PageSpan = namedtuple("PageSpan", ["page_num", "char_start", "char_end"])


# --------------------------------------------------------------------------
# PDF inspection
# --------------------------------------------------------------------------


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def require_tool(name):
    if shutil.which(name) is None:
        raise SystemExit(
            f"Required tool '{name}' not found on PATH. Install it "
            f"(e.g. 'brew install poppler tesseract' or the equivalent for "
            f"your OS), or use --text-dir to skip OCR entirely."
        )


def get_pdf_page_count(pdf_path):
    require_tool("pdfinfo")
    result = run(["pdfinfo", str(pdf_path)])
    if result.returncode != 0:
        raise SystemExit(f"pdfinfo failed on '{pdf_path}': {result.stderr.strip()}")
    m = re.search(r"^Pages:\s*(\d+)", result.stdout, re.MULTILINE)
    if not m:
        raise SystemExit(f"Could not determine page count for '{pdf_path}'")
    return int(m.group(1))


def get_page_size_pts(pdf_path, page_num):
    require_tool("pdfinfo")
    result = run(["pdfinfo", "-f", str(page_num), "-l", str(page_num), str(pdf_path)])
    if result.returncode != 0:
        raise SystemExit(f"pdfinfo failed on '{pdf_path}' page {page_num}")
    m = re.search(r"^Page\s+\d+\s+size:\s*([\d.]+)\s*x\s*([\d.]+)", result.stdout, re.MULTILINE)
    if not m:
        raise SystemExit(f"Could not determine page size for '{pdf_path}' page {page_num}")
    return float(m.group(1)), float(m.group(2))


def resolve_page_range(pages_arg, page_count):
    if not pages_arg:
        return 1, page_count
    m = re.match(r"^(\d+)-(\d+)$", pages_arg.strip())
    if not m:
        raise SystemExit(f"--pages must look like START-END, got '{pages_arg}'")
    start, end = int(m.group(1)), int(m.group(2))
    if start < 1 or end > page_count or start > end:
        raise SystemExit(
            f"--pages {pages_arg} is out of range for a {page_count}-page document"
        )
    return start, end


# --------------------------------------------------------------------------
# Rendering / cropping / OCR (Tesseract path)
# --------------------------------------------------------------------------


def compute_crop_boxes(
    page_w_pts,
    page_h_pts,
    dpi,
    margin_top,
    margin_bottom,
    margin_side,
    column_split,
    gutter,
    single_column,
):
    px_w = round(page_w_pts / 72 * dpi)
    px_h = round(page_h_pts / 72 * dpi)

    top = round(px_h * margin_top)
    bottom = round(px_h * (1 - margin_bottom))
    height = bottom - top
    side = round(px_w * margin_side)

    if single_column:
        width = px_w - 2 * side
        return {"full": (side, top, width, height)}

    split_x = px_w * column_split
    gutter_px = px_w * gutter

    left_x = side
    left_w = round((split_x - gutter_px / 2) - left_x)
    right_x = round(split_x + gutter_px / 2)
    right_w = round((px_w - side) - right_x)

    return {
        "left": (left_x, top, left_w, height),
        "right": (right_x, top, right_w, height),
    }


def _pdftoppm_render(pdf_path, page_num, dpi, box, prefix, gray):
    x, y, w, h = box
    cmd = [
        "pdftoppm",
        "-png",
        "-f",
        str(page_num),
        "-l",
        str(page_num),
        "-r",
        str(dpi),
        "-x",
        str(x),
        "-y",
        str(y),
        "-W",
        str(w),
        "-H",
        str(h),
    ]
    if gray:
        cmd.append("-gray")
    cmd += [str(pdf_path), str(prefix)]
    result = run(cmd)
    if result.returncode != 0:
        raise SystemExit(f"pdftoppm failed on page {page_num}: {result.stderr.strip()}")
    matches = glob.glob(f"{prefix}*.png")
    if not matches:
        raise SystemExit(f"pdftoppm produced no output for page {page_num} (prefix {prefix})")
    return Path(matches[0])


def render_page_images(pdf_path, page_num, dpi, crop_boxes, work_dir, gray=True):
    require_tool("pdftoppm")
    images = {}
    for name, box in crop_boxes.items():
        prefix = work_dir / f"page-{page_num:04d}-{name}"
        images[name] = _pdftoppm_render(pdf_path, page_num, dpi, box, prefix, gray)
    return images


def render_full_page(pdf_path, page_num, dpi, work_dir):
    """Render a full, uncropped page image -- used by --render-only for the
    AI-vision-transcription workflow (matches the manual process this tool
    replaces: no cropping needed, a human/AI just reads the whole page)."""
    require_tool("pdftoppm")
    prefix = work_dir / f"page-{page_num:04d}"
    cmd = ["pdftoppm", "-png", "-f", str(page_num), "-l", str(page_num), "-r", str(dpi), str(pdf_path), str(prefix)]
    result = run(cmd)
    if result.returncode != 0:
        raise SystemExit(f"pdftoppm failed on page {page_num}: {result.stderr.strip()}")
    matches = glob.glob(f"{prefix}*.png")
    if not matches:
        raise SystemExit(f"pdftoppm produced no output for page {page_num}")
    src = Path(matches[0])
    dest = work_dir / f"page-{page_num:04d}.png"
    if src != dest:
        src.rename(dest)
    return dest


def ocr_image(image_path, psm, lang):
    require_tool("tesseract")
    cmd = ["tesseract", str(image_path), "stdout", "--psm", str(psm), "-l", lang]
    result = run(cmd)
    if result.returncode != 0:
        raise SystemExit(f"tesseract failed on '{image_path}': {result.stderr.strip()}")
    return result.stdout


def get_page_text_tesseract(pdf_path, page_num, dpi, crop_boxes, psm, lang, work_dir):
    images = render_page_images(pdf_path, page_num, dpi, crop_boxes, work_dir)
    order = ["full"] if "full" in images else ["left", "right"]
    parts = [ocr_image(images[name], psm, lang) for name in order]
    return "\n".join(parts)


# --------------------------------------------------------------------------
# Pre-transcribed text ingestion
# --------------------------------------------------------------------------


def get_page_text_from_dir(text_dir, page_num):
    path = Path(text_dir) / f"page-{page_num:04d}.txt"
    if not path.exists():
        raise SystemExit(
            f"Expected transcript '{path}' not found. --text-dir expects one "
            f"'page-NNNN.txt' file per page in the requested range, matching "
            f"the 'page-NNNN.png' naming --render-only produces."
        )
    return path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# Book text assembly
# --------------------------------------------------------------------------


def get_book_text(pdf_path, start_page, end_page, args, work_dir):
    pages = []
    if args.text_dir:
        for page_num in range(start_page, end_page + 1):
            text = get_page_text_from_dir(args.text_dir, page_num)
            pages.append(PageText(page_num, text))
    else:
        for page_num in range(start_page, end_page + 1):
            w_pts, h_pts = get_page_size_pts(pdf_path, page_num)
            crop_boxes = compute_crop_boxes(
                w_pts,
                h_pts,
                args.dpi,
                args.margin_top,
                args.margin_bottom,
                args.margin_side,
                args.column_split,
                args.gutter,
                args.single_column,
            )
            text = get_page_text_tesseract(
                pdf_path, page_num, args.dpi, crop_boxes, args.tesseract_psm, args.tesseract_lang, work_dir
            )
            pages.append(PageText(page_num, text))
    return pages


FOOTER_LINE_RE = re.compile(
    r"^\s*("
    r"[-–—]\s*\d{1,4}\s*[-–—]"  # bare "— 6 —" / "-8-"
    r"|.{0,60}[-–—]\s*\d{1,4}\s*[-–—]"  # "Title —8—"
    r")\s*$"
)


def strip_footer_header_lines(text):
    """Secondary defense against running footers leaking into body text.
    The primary defense is cropping the header/footer band out of the page
    image before OCR ever sees it; this just catches anything that slips
    through (or anything present in --text-dir input)."""
    lines = text.split("\n")
    kept = [line for line in lines if not FOOTER_LINE_RE.match(line)]
    return "\n".join(kept)


def build_stream(pages):
    cleaned = []
    spans = []
    pos = 0
    for page in pages:
        text = strip_footer_header_lines(page.text)
        if cleaned:
            cleaned.append("\n")
            pos += 1
        start = pos
        cleaned.append(text)
        pos += len(text)
        spans.append(PageSpan(page.page_num, start, pos))
    return "".join(cleaned), spans


# --------------------------------------------------------------------------
# Sequential entry-boundary segmentation
# --------------------------------------------------------------------------


# A real entry can open with dialogue (a quote mark) instead of a capital
# letter directly -- confirmed in the trusted SJG6204 data, ~7% of entries
# (e.g. entry 35: '"Are you addled?" Belit shouts...'). The lookahead below
# accepts an uppercase letter or a straight/curly quote/apostrophe.
_ENTRY_START_CHAR = "A-Z\"'‘’“”"


def id_boundary_pattern(entry_id):
    # Line start (tolerant of stray leading OCR whitespace), the literal id
    # digits, an optional short run of whitespace/period, then a REQUIRED
    # lookahead for a plausible entry-opening character. That lookahead is
    # what rejects ordinary prose numbers (dice rolls, stat blocks, page
    # refs) -- confirmed against a real false-positive candidate (a title
    # page's print-run line "1 2 3 4 5 6 7 8 9 10", where no candidate digit
    # run is followed by a capital letter or quote).
    return re.compile(rf"(?m)^[ \t]*{entry_id}[ \t]{{0,2}}\.?[ \t]{{0,2}}(?=[{_ENTRY_START_CHAR}])")


def find_intro_span(stream, heading):
    if not heading:
        return None
    m = re.search(re.escape(heading), stream, re.IGNORECASE)
    if not m:
        return None
    return m.end()


def segment_entries(stream, first_id, max_id, resync_lookahead, max_entry_chars, intro_start):
    markers = []  # (entry_id, marker_start, body_start)
    anomalies = []

    search_pos = intro_start if intro_start is not None else 0
    expected_id = first_id
    # Bound how far ahead a marker search is allowed to look. Without this,
    # a misread marker (e.g. a drop-cap digit OCR'd wrong) leaves the exact
    # search unbounded -- re.search() will happily accept a *coincidental*
    # match of the same digit pattern anywhere later in the whole book
    # (confirmed in testing: a stray "1" + capital letter deep in later
    # pages got accepted as "entry 1", silently swallowing ~15 pages into
    # one bogus entry). A real next entry is never more than one very-long
    # entry's worth of text away, so max_entry_chars doubles as a sane
    # search-window bound too.
    search_window = max(max_entry_chars * 2, 2000)

    while max_id is None or expected_id <= max_id:
        window_end = min(len(stream), search_pos + search_window)
        pat = id_boundary_pattern(expected_id)
        m = pat.search(stream, search_pos, window_end)
        if m:
            markers.append((expected_id, m.start(), m.end()))
            search_pos = m.end()
            expected_id += 1
            continue

        resynced = False
        for k in range(1, resync_lookahead + 1):
            candidate_id = expected_id + k
            if max_id is not None and candidate_id > max_id:
                break
            m2 = id_boundary_pattern(candidate_id).search(stream, search_pos, window_end)
            if m2:
                missing = ", ".join(str(i) for i in range(expected_id, candidate_id))
                anomalies.append(
                    f"entry marker(s) {missing} not found; resumed at entry {candidate_id}"
                )
                markers.append((candidate_id, m2.start(), m2.end()))
                search_pos = m2.end()
                expected_id = candidate_id + 1
                resynced = True
                break
        if not resynced:
            break

    stopped_at_id = expected_id

    entries = {}
    entry_spans = {}

    if intro_start is not None:
        intro_end = markers[0][1] if markers else len(stream)
        intro_body = stream[intro_start:intro_end].strip()
        if intro_body:
            entries["0"] = {"id": 0, "body": intro_body}
            entry_spans["0"] = (intro_start, intro_end)
        if not markers:
            anomalies.append("intro heading found but no numbered entries were found afterward")

    for i, (entry_id, marker_start, body_start) in enumerate(markers):
        body_end = markers[i + 1][1] if i + 1 < len(markers) else len(stream)
        body = stream[body_start:body_end].strip()
        key = str(entry_id)
        entries[key] = {"id": entry_id, "body": body}
        entry_spans[key] = (marker_start, body_end)
        if len(body) > max_entry_chars:
            anomalies.append(
                f"entry {entry_id}: body is {len(body)} chars, unusually long "
                f"-- possible missed boundary/OCR overrun"
            )

    return entries, entry_spans, anomalies, stopped_at_id


def compute_zero_coverage_pages(page_spans, entry_spans):
    zero_pages = []
    for ps in page_spans:
        covered = any(
            not (e_end <= ps.char_start or e_start >= ps.char_end)
            for (e_start, e_end) in entry_spans.values()
        )
        if not covered:
            zero_pages.append(ps.page_num)
    return zero_pages


# --------------------------------------------------------------------------
# QA report
# --------------------------------------------------------------------------


def keyword_scan(entries):
    counts = {}
    for keyword in QA_KEYWORDS:
        pat = re.compile(re.escape(keyword), re.IGNORECASE)
        counts[keyword] = sum(len(pat.findall(e["body"])) for e in entries.values())
    return counts


def build_qa_report(entries, entry_spans, anomalies, page_spans, stopped_at_id, pages_processed):
    val_report = validate_entries.validate(entries)
    zero_coverage_pages = compute_zero_coverage_pages(page_spans, entry_spans)
    numeric_ids = sorted(int(k) for k in entries.keys() if k.lstrip("-").isdigit())

    return {
        "entry_count": len(entries),
        "id_range_found": [numeric_ids[0], numeric_ids[-1]] if numeric_ids else None,
        "stopped_at_id": stopped_at_id,
        "pages_processed": pages_processed,
        "pages_with_zero_entry_coverage": zero_coverage_pages,
        "anomalies": anomalies,
        "keyword_counts": keyword_scan(entries),
        "errors": val_report.errors,
        "warnings": val_report.warnings,
        "endings": sorted(val_report.endings, key=int),
        "passed": val_report.passed,
    }


def format_qa_text(report, pdf_path):
    lines = []
    lines.append(f"Solo Hypertext Reader extraction report: {pdf_path}")
    lines.append(f"  {report['entry_count']} entries extracted, id range {report['id_range_found']}")
    lines.append(f"  sequential search stopped looking at id {report['stopped_at_id']}")
    lines.append(f"  {report['pages_processed']} pages processed")
    lines.append("")

    lines.append(f"PAGES WITH ZERO ENTRY COVERAGE ({len(report['pages_with_zero_entry_coverage'])})")
    lines.append("  (expected for front/back matter; unexpected here means OCR likely failed)")
    for p in report["pages_with_zero_entry_coverage"]:
        lines.append(f"  - page {p}")
    lines.append("")

    lines.append(f"ANOMALIES ({len(report['anomalies'])})")
    for a in report["anomalies"]:
        lines.append(f"  - {a}")
    lines.append("")

    lines.append(f"ERRORS ({len(report['errors'])})")
    for e in report["errors"]:
        lines.append(f"  - {e}")
    lines.append("")

    lines.append(f"WARNINGS ({len(report['warnings'])})")
    for w in report["warnings"]:
        lines.append(f"  - {w}")
    lines.append("")

    lines.append(f"ENDINGS ({len(report['endings'])})")
    for key in report["endings"]:
        lines.append(f"  - {key}")
    lines.append("")

    lines.append("KEYWORD MENTIONS (proofreading aid, not linked)")
    for keyword, count in report["keyword_counts"].items():
        lines.append(f"  - {keyword}: {count}")
    lines.append("")

    lines.append(f"SUMMARY: {'PASS' if report['passed'] else 'FAIL'}")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def write_entries_json(entries, out_path):
    numeric_ids = sorted(int(k) for k in entries.keys())
    ordered = {str(i): entries[str(i)] for i in numeric_ids}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(ordered, f, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def build_arg_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pdf_path", help="source PDF")
    parser.add_argument("--pages", default=None, help="1-based inclusive page range, e.g. 7-29 (default: all pages)")
    parser.add_argument("--text-dir", default=None, help="ingest pre-transcribed page-NNNN.txt files instead of running Tesseract")
    parser.add_argument("--render-only", action="store_true", help="just rasterize full page images and exit (for an AI-vision transcription pass)")
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI)
    parser.add_argument("--single-column", action="store_true")
    parser.add_argument("--column-split", type=float, default=DEFAULT_COLUMN_SPLIT)
    parser.add_argument("--margin-top", type=float, default=DEFAULT_MARGIN_TOP)
    parser.add_argument("--margin-bottom", type=float, default=DEFAULT_MARGIN_BOTTOM)
    parser.add_argument("--margin-side", type=float, default=DEFAULT_MARGIN_SIDE)
    parser.add_argument("--gutter", type=float, default=DEFAULT_GUTTER)
    parser.add_argument("--tesseract-psm", type=int, default=DEFAULT_PSM)
    parser.add_argument("--tesseract-lang", default=DEFAULT_LANG)
    parser.add_argument("--first-id", type=int, default=DEFAULT_FIRST_ID)
    parser.add_argument("--intro-heading", default=DEFAULT_INTRO_HEADING, help='case-insensitive anchor for entry 0; pass "" to disable')
    parser.add_argument("--max-id", type=int, default=None)
    parser.add_argument("--resync-lookahead", type=int, default=DEFAULT_RESYNC_LOOKAHEAD)
    parser.add_argument("--max-entry-chars", type=int, default=DEFAULT_MAX_ENTRY_CHARS)
    parser.add_argument("--out", default=None, help="output entries JSON path (default: <pdf_stem>_entries.json next to the PDF)")
    parser.add_argument("--qa-report", default=None, help="QA report path (default: <pdf_stem>_extract_report.json next to the PDF)")
    parser.add_argument("--work-dir", default=None, help="where rendered images are written (default: temp dir, or <pdf_stem>_pages/ for --render-only/--keep-images)")
    parser.add_argument("--keep-images", action="store_true", help="don't delete rendered images after the run")
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"'{pdf_path}' does not exist", file=sys.stderr)
        return 2

    stem = pdf_path.stem
    out_path = Path(args.out) if args.out else pdf_path.with_name(f"{stem}_entries.json")
    qa_path = Path(args.qa_report) if args.qa_report else pdf_path.with_name(f"{stem}_extract_report.json")

    needs_persistent_work_dir = args.render_only or args.keep_images
    if args.work_dir:
        work_dir = Path(args.work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
        cleanup_work_dir = False
    elif needs_persistent_work_dir:
        work_dir = pdf_path.with_name(f"{stem}_pages")
        work_dir.mkdir(parents=True, exist_ok=True)
        cleanup_work_dir = False
    else:
        # Created next to the PDF rather than via the system temp dir:
        # some sandboxed/restricted environments (seen in testing) block
        # external tools like `tesseract` from reading paths under the
        # system temp dir even when Python itself can write there, and a
        # workspace-local scratch dir is a safe default in general anyway.
        work_dir = Path(tempfile.mkdtemp(prefix=f".{stem}_work_", dir=str(pdf_path.parent)))
        cleanup_work_dir = True

    try:
        page_count = get_pdf_page_count(pdf_path) if not args.text_dir or args.render_only else None
        if page_count is None:
            # --text-dir without needing pdfinfo: only required if --pages
            # wasn't given, since we need *some* count to default the range.
            if not args.pages:
                raise SystemExit("--text-dir requires --pages START-END (no PDF inspection is done to infer a default range)")
            start_page, end_page = resolve_page_range(args.pages, 10**9)
        else:
            start_page, end_page = resolve_page_range(args.pages, page_count)

        if args.render_only:
            for page_num in range(start_page, end_page + 1):
                render_full_page(pdf_path, page_num, args.dpi, work_dir)
            print(f"Rendered pages {start_page}-{end_page} to {work_dir}/")
            return 0

        pages = get_book_text(pdf_path, start_page, end_page, args, work_dir)
        stream, page_spans = build_stream(pages)
        intro_start = find_intro_span(stream, args.intro_heading)

        entries, entry_spans, anomalies, stopped_at_id = segment_entries(
            stream, args.first_id, args.max_id, args.resync_lookahead, args.max_entry_chars, intro_start
        )

        if not entries:
            print("No entries could be segmented from the given pages.", file=sys.stderr)
            return 2

        report = build_qa_report(
            entries, entry_spans, anomalies, page_spans, stopped_at_id, end_page - start_page + 1
        )

        write_entries_json(entries, out_path)
        with open(qa_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        print(format_qa_text(report, pdf_path))
        print(f"\nWrote {out_path}")
        print(f"Wrote {qa_path}")

        return 0 if report["passed"] else 1
    finally:
        if cleanup_work_dir:
            shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
