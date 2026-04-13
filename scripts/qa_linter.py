#!/usr/bin/env python3
"""
Morning Brief QA Linter
========================
Runs after brief assembly, before PDF generation.
Checks structural correctness, content minimums, and page target.
Optional visual screenshot pass catches rendering bugs markdown can't reveal.

Usage:
  python3 qa_linter.py <brief.md> [--fix] [--screenshot] [--verbose]
"""

import re
import sys
import yaml
import json
import subprocess
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional

TRY_YAML = True
try:
    import yaml
except ImportError:
    TRY_YAML = False

TRY_PYMUPDF = True
try:
    import fitz
except ImportError:
    TRY_PYMUPDF = False


# ─── Issue Severities ────────────────────────────────────────────────────────

@dataclass
class Issue:
    severity: str  # ERROR, WARN, INFO
    code: str
    message: str
    context: str = ""
    line: int = 0
    auto_fix: str = ""

ERRORS = []
WARNINGS = []
INFOS = []

def error(code, message, context="", line=0, auto_fix=""):
    ISSUES.append(Issue("ERROR", code, message, context, line, auto_fix))

def warn(code, message, context="", line=0):
    WARNINGS.append(Issue("WARN", code, message, context, line))

def info(code, message, context="", line=0):
    INFOS.append(Issue("INFO", code, message, context, line))

ISSUES: List[Issue] = []


# ─── Markdown HTML Block Parser ──────────────────────────────────────────────
# Tracks whether we are inside an HTML block and what tag we're in.
# HTML block = line starting with <tag...> (not indented with 4+ spaces)
# Block ends when a line starts with </tag> or a matching closing tag.

def find_html_blocks(content: str):
    """
    Returns list of (start_line, end_line, tag_name) for each HTML block.
    Lines are 1-indexed.
    Skips YAML frontmatter automatically.
    """
    lines = content.split('\n')
    blocks = []
    i = 0
    n = len(lines)

    # Skip frontmatter
    if n > 0 and lines[0].strip() == '---':
        for j in range(1, n):
            if lines[j].strip() == '---':
                i = j + 1
                break
                # Skip rest of frontmatter

    while i < n:
        line = lines[i]
        # Skip frontmatter
        if i == 0 and line.strip() == '---':
            while i < n and not (lines[i].strip() == '---' and i > 0):
                i += 1
            i += 1
            continue

        # Check for opening HTML tag (not indented, starts with <)
        m = re.match(r'^(\s*)(<([a-zA-Z][a-zA-Z0-9-]*))', line)
        if m and not m.group(1):
            tag = m.group(3)
            # Self-closing or void tag — single line
            if tag in ('area', 'base', 'br', 'col', 'embed', 'hr', 'img',
                       'input', 'link', 'meta', 'param', 'source', 'track', 'wbr',
                       'img', 'br', 'hr'):
                i += 1
                continue
            # Check if self-closing with />
            rest = line[m.end():]
            if '/>' in rest:
                i += 1
                continue

            start = i
            depth = 1
            i += 1
            while i < n:
                cline = lines[i]
                # Closing tag
                cm = re.match(r'^(\s*)(</([a-zA-Z][a-zA-Z0-9-]*)\s*>)', cline)
                if cm and not cm.group(1):
                    ctag = cm.group(3)
                    if ctag == tag:
                        blocks.append((start + 1, i + 1, tag))  # 1-indexed
                        i += 1
                        break
                    else:
                        # Nested different tag — skip
                        i += 1
                        continue
                # Another opening tag at same level
                om = re.match(r'^(\s*)(<([a-zA-Z][a-zA-Z0-9-]*))', cline)
                if om and not om.group(1):
                    otag = om.group(3)
                    if otag not in ('area', 'base', 'br', 'col', 'embed', 'hr',
                                    'img', 'input', 'link', 'meta', 'param',
                                    'source', 'track', 'wbr', 'img', 'br', 'hr'):
                        # Check not self-closing
                        rest = cline[om.end():]
                        if '/>' not in rest:
                            depth += 1
                i += 1
        else:
            i += 1

    return blocks


def md_header_lines_in_block(lines: List[str], start: int, end: int) -> List[int]:
    """Return 1-indexed line numbers of markdown headers (# ## etc) inside [start, end)."""
    results = []
    for i in range(start - 1, min(end, len(lines))):
        line = lines[i]
        # Markdown headers: start of line, optional leading whitespace, #+
        m = re.match(r'^(\s+)?(#{1,6})\s+', line)
        if m:
            results.append(i + 1)
    return results


# ─── YAML Frontmatter Parser ──────────────────────────────────────────────────

def parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter. Returns dict of the yaml block."""
    if not TRY_YAML:
        return {}
    lines = content.split('\n')
    # Frontmatter must start at line 0
    if len(lines) < 3 or lines[0].strip() != '---':
        return {}
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            end = i
            break
    if end is None:
        return {}
    try:
        data = yaml.safe_load('\n'.join(lines[1:end]))
        return data if isinstance(data, dict) else {}
    except:
        return {}


# ─── Section Tracker ─────────────────────────────────────────────────────────

SECTION_PATTERNS = [
    (r'#+\s*I\.\s*SIGNALS',                          'I. Signals'),
    (r'#+\s*II\.\s*FULL READ',                        'II. Full Read'),
    (r'#+\s*III\.\s*FULL READ',                       'III. Full Read'),
    (r'#+\s*IV\.\s*HACKER NEWS',                      'IV. Hacker News'),
    (r'#+\s*V\.\s*MAIN BRANCH.*SKOOL',                'V. Skool Community'),
    (r'#+\s*V-A?\.\s*CONTENT DRAFTS',                 'V-A. Content Drafts'),
    (r'#+\s*VI\.\s*HIGH-TICKET AGENCY',               'VI. High-Ticket Agency'),
    (r'#+\s*VII\.\s*OPERATIONS',                      'VII. Operations'),
    (r'#+\s*VIII\.\s*OVERNIGHT PIPELINE',              'VIII. Overnight Pipeline'),
    (r'#+\s*(?:VIII|IX|X)\.\s*ACTION REQUIRED',        'Action Required'),
    (r'#+\s*(?:IX|X)\.\s*REFERENCES',                 'X. References'),
    # HTML variants (h1, h2, h3)
    (r'<h[1-6][^>]*>\s*I\.\s*SIGNALS',               'I. Signals'),
    (r'<h[1-6][^>]*>\s*IV\.\s*HACKER NEWS',          'IV. Hacker News'),
    (r'<h[1-6][^>]*>\s*(?:VIII|IX|X)\.\s*ACTION',  'Action Required'),
]

REQUIRED_SECTIONS = ['I. Signals', 'II. Full Read', 'IV. Hacker News',
                     'V. Skool Community', 'Action Required']


# ─── Content Counters ─────────────────────────────────────────────────────────

def count_words(text: str) -> int:
    return len(re.findall(r'\b\w+\b', text))

def count_elements(content: str, tag_pattern: str) -> int:
    return len(re.findall(tag_pattern, content, re.IGNORECASE))


# ─── Main Lint Logic ─────────────────────────────────────────────────────────

def lint(brief_path: str, fix: bool = False, verbose: bool = False) -> dict:
    global ISSUES, ERRORS, WARNINGS, INFOS
    ISSUES = []
    ERRORS = []
    WARNINGS = []
    INFOS = []

    path = Path(brief_path)
    if not path.exists():
        error("FILE_NOT_FOUND", f"File not found: {brief_path}")
        return result()

    content = path.read_text()
    raw_lines = content.split('\n')

    # ── 1. HTML Block / Markdown Collision ──────────────────────────────
    blocks = find_html_blocks(content)
    lines = raw_lines  # already split

    for (bstart, bend, tag) in blocks:
        offending = md_header_lines_in_block(lines, bstart, bend)
        if offending:
            ctx = '\n'.join(f"  L{ln}: {lines[ln-1]}" for ln in offending[:3])
            error(
                "MD_INSIDE_HTML_BLOCK",
                f"Markdown header(s) found inside <{tag}> HTML block — renders as raw text. "
                f"Move header outside the div or use HTML (<h1>) inside.",
                ctx,
                line=offending[0],
                auto_fix=(
                    f"Convert markdown '## Header' to HTML '<h1>Header</h1>' "
                    f"inside the <div class='hn-section'> block."
                )
            )

    # ── 2. HN Section Structure ───────────────────────────────────────────
    # Correct: <div class="hn-section"> followed by <h1>IV. HACKER NEWS</h1>
    # Wrong: <div class="hn-section"> followed by ## IV. HACKER NEWS (markdown in block)
    hn_section = re.search(
        r'<div class=["\']hn-section["\']>(.*?)</div>\s*(?=<div class=["\']hn-cards["\']|'
        r'<div class=["\']hn-cards["\'])',
        content, re.DOTALL
    )
    if hn_section:
        inner = hn_section.group(1)
        if re.search(r'^#{1,6}\s+IV\.\s+HACKER NEWS', inner, re.MULTILINE):
            error(
                "HN_MD_HEADER_IN_BLOCK",
                "HN section has markdown '## IV. HACKER NEWS' inside HTML block — "
                "will render as raw text instead of styled heading. "
                "Use <h1>IV. HACKER NEWS</h1> inside .hn-section.",
                context=inner[:200],
                auto_fix="Replace '## IV. HACKER NEWS' with '<h1>IV. HACKER NEWS</h1>' inside .hn-section"
            )
        if not re.search(r'<h1\b|<h[1-6][^>]*>.*?IV\..*?HACKER NEWS', inner, re.DOTALL | re.IGNORECASE):
            warn(
                "HN_MISSING_HTML_HEADER",
                "HN section found but no <h1>IV. HACKER NEWS</h1> header detected inside .hn-section."
            )

    # Check .hn-cards has columns: 2
    hn_cards = re.search(
        r'<div class=["\']hn-cards["\'][^>]*>(.*?)</div>',
        content, re.DOTALL
    )
    if hn_cards:
        hn_cards_open = re.search(r'<div class=["\']hn-cards["\'][^>]*>', content)
        if hn_cards_open and 'columns:' not in hn_cards_open.group(0) and 'column-count' not in hn_cards_open.group(0):
            warn(
                "HN_CARDS_NO_COLUMNS",
                ".hn-cards div found but 'columns: 2' style is missing. "
                "Add 'style=\"columns: 2; column-gap: 0.08in;\"' to the opening tag.",
                context=hn_cards_open.group(0)
            )

    # Check for flex-wrap on HN cards (old broken pattern)
    if re.search(r'<div class=["\']hn-cards["\'][^>]*flex-wrap', content):
        warn(
            "HN_CARDS_FLEX_WRAP",
            ".hn-cards uses flex/flex-wrap — this causes Chromium to treat the entire "
            "block as one unit, leading to poor page breaks. Use 'columns: 2' instead."
        )

    # ── 3. YAML Frontmatter ───────────────────────────────────────────────
    fm = parse_frontmatter(content)

    if not fm:
        error("YAML_MISSING", "No YAML frontmatter found — header/footer/page settings may be wrong.")
    else:
        # headerTemplate/footerTemplate may be at top level OR inside pdf_options
        opts = fm.get('pdf_options', {}) or {}
        if isinstance(opts, dict):
            htf = opts.get('headerTemplate', fm.get('headerTemplate', None))
            ft = opts.get('footerTemplate', fm.get('footerTemplate', None))
            bg = opts.get('printBackground', None)
            dhf = opts.get('displayHeaderFooter', None)
        else:
            htf = fm.get('headerTemplate', None)
            ft = fm.get('footerTemplate', None)
            bg = None
            dhf = None

        if htf is None:
            error("YAML_NO_HEADER_TEMPLATE",
                  "headerTemplate missing from YAML frontmatter (checked top-level and pdf_options).")
        elif htf == '':
            error(
                "YAML_EMPTY_HEADER_TEMPLATE",
                "headerTemplate is empty string — Chrome will render its own default "
                "timestamp, creating ghost text. Use '<span></span>' instead.",
                auto_fix="Set headerTemplate: \"<span></span>\" in YAML frontmatter"
            )

        if ft is None or ft == '':
            error("YAML_NO_FOOTER_TEMPLATE",
                  "footerTemplate missing or empty — no page numbers.")

        if bg is None:
            warn("YAML_NO_PRINT_BG", "printBackground not set — colors/backgrounds may not print.")
        if dhf is None:
            warn("YAML_NO_DISPLAY_HF", "displayHeaderFooter not set — no page numbers.")

    # ── 4. Required Sections ──────────────────────────────────────────────
    found_sections = {}
    for pat, label in SECTION_PATTERNS:
        if re.search(pat, content, re.IGNORECASE | re.MULTILINE):
            found_sections[label] = True

    for req in REQUIRED_SECTIONS:
        if not any(req.lower() in s.lower() for s in found_sections):
            warn("SECTION_MISSING", f"Required section '{req}' not found in brief.", context=req)

    # Check for empty sections (header with no content until next header or end)
    section_headers = [(m.start(), m.group(0)) for m in
                       re.finditer(r'(?:^|\n)(#{1,6}\s+[A-Z][A-Z0-9 .\-]+|'
                                   r'<h[1-6][^>]*>.*?</h[1-6]>)',
                                   content, re.MULTILINE)]
    for idx, (pos, header) in enumerate(section_headers):
        next_pos = section_headers[idx + 1][0] if idx + 1 < len(section_headers) else len(content)
        section_content = content[pos:next_pos].strip()
        # Remove the header line itself from content check
        content_without_header = re.sub(r'^#{1,6}\s+[^\n]+', '', section_content, flags=re.MULTILINE).strip()
        content_without_header = re.sub(r'<h[1-6][^>]*>.*?</h[1-6]>', '', content_without_header,
                                         flags=re.DOTALL).strip()
        if not content_without_header or len(content_without_header) < 5:
            warn("SECTION_EMPTY", f"Section appears empty or near-empty: {header.strip()}",
                 context=header.strip()[:100])

    # ── 5. Content Minimums ────────────────────────────────────────────────
    hn_card_count = count_elements(content, r'<div class=["\']hn-card["\']')
    if hn_card_count < 10:
        warn("HN_FEW_CARDS", f"Only {hn_card_count} HN cards found — expected 10-20.")
    else:
        info("HN_CARD_COUNT", f"{hn_card_count} HN cards found.", f"{hn_card_count} cards")

    tweet_blocks = (count_elements(content, r'<div class=["\']tweet["\']') +
                     count_elements(content, r'<div class=["\']tweet-pair["\']'))
    if tweet_blocks < 3:
        warn("SIGNALS_FEW_TWEETS", f"Only {tweet_blocks} tweet blocks found — expected 4-6.")

    full_reads = count_elements(content, r'<div class=["\']full-read["\']')
    if full_reads < 1:
        warn("FULL_READ_MISSING", "No full-read blocks found — Section II/III appears empty.")

    # Word count for page estimation
    # Strip frontmatter, CSS, HTML tags for word count
    text_only = content
    text_only = re.sub(r'^---.*?---\s*', '', text_only, flags=re.DOTALL)  # frontmatter
    text_only = re.sub(r'<style[^>]*>.*?</style>', '', text_only, flags=re.DOTALL)  # CSS
    text_only = re.sub(r'<[^>]+>', ' ', text_only)  # HTML tags
    text_only = re.sub(r'\{[^{}]*\}', ' ', text_only)  # variables
    word_count = count_words(text_only)

    # Rough page estimate: ~350 words/page at 9pt Courier with current density
    # This is a rough gauge, not exact
    page_estimate = max(1, round(word_count / 350))
    if page_estimate < 6:
        warn("PAGE_COUNT_LOW", f"Page estimate ~{page_estimate} pages — brief may be too short. Target: 10 pages.")
    elif page_estimate > 14:
        warn("PAGE_COUNT_HIGH", f"Page estimate ~{page_estimate} pages — brief may be too long. Target: 10 pages.")
    else:
        info("PAGE_COUNT", f"Page estimate ~{page_estimate} pages. Word count: {word_count}.", f"{word_count} words")

    # ── 6. Break-inside checks ─────────────────────────────────────────────
    # CSS can be in YAML frontmatter (css: |) or in <style> HTML tags
    css_text = ""
    css_block = re.search(r'<style[^>]*>(.*?)</style>', content, re.DOTALL)
    if css_block:
        css_text += css_block.group(1) + "\n"
    # Also check YAML frontmatter css: field
    fm = parse_frontmatter(content)
    yaml_css = fm.get('css', '')
    if yaml_css:
        css_text += yaml_css + "\n"

    card_classes = ['tweet', 'tweet-pair', 'hn-card', 'full-read']
    for cls in card_classes:
        blocks_found = count_elements(content, rf'<div class=["\'].*{cls}.*["\']>')
        if blocks_found > 0:
            # Check if CSS has break-inside for this class
            # Handles multi-line: .tweet {\n   break-inside: avoid;
            has_break_css = re.search(
                rf'\.{re.escape(cls)}\s*\{{[^}}]*\}}',
                css_text, re.DOTALL
            )
            if has_break_css:
                block_text = has_break_css.group(0)
                if 'break-inside' not in block_text and 'page-break-inside' not in block_text:
                    has_break_css = None
            if not has_break_css:
                warn(f"CARD_NO_BREAK_AVOID",
                     f".{cls} blocks found ({blocks_found}) but no 'break-inside: avoid' "
                     f"found in CSS for .{cls}. Cards may be cut across page breaks.")

    # ── 7. CSS Class Coverage ──────────────────────────────────────────────
    # Verify classes used in HTML are defined in CSS
    html_classes = set(re.findall(r'<div class=["\']([^"\']+)["\']', content))
    css_class_defs = set(re.findall(r'\.([a-zA-Z][a-zA-Z0-9_-]*)\s*\{', content))
    css_class_defs |= set(re.findall(r'\.([a-zA-Z][a-zA-Z0-9_-]*)\s*:', content))

    for cls in html_classes:
        for part in cls.split():
            # Skip inline styles
            if part.startswith('style=') or part.startswith('onclick'):
                continue
            # Check if this specific class (possibly compound) has a definition
            if part not in css_class_defs:
                # Check for partial match (e.g., 'hn-card-header' should match .hn-card-header)
                if not any(part == d or part.endswith(d) or d.endswith(part)
                           for d in css_class_defs):
                    if verbose:
                        info("CSS_CLASS_NO_DEF", f"Class '.{part}' used in HTML but not defined in CSS.",
                             f"Used in: {cls}")

    # ── 8. HN Specific Checks ─────────────────────────────────────────────
    hn_cards_all = re.findall(r'<div class=["\']hn-card["\']>(.*?)</div>\s*(?=<div class="hn-card"|$)',
                              content, re.DOTALL)
    for idx, card in enumerate(hn_cards_all[:5], 1):  # Check first 5
        if not re.search(r'hn-rank|hn-title', card, re.DOTALL):
            warn("HN_CARD_STRUCTURE", f"HN card #{idx} may be missing .hn-rank or .hn-title.",
                 context=card[:100])
        if not re.search(r'hn-rank', card):
            warn("HN_CARD_NO_RANK", f"HN card #{idx} has no rank number.", context=card[:80])

    # ── 9. Tweet Specific Checks ───────────────────────────────────────────
    tweet_blocks_found = re.findall(
        r'<div class=["\'](?:tweet|tweet-pair)["\'][^>]*>(.*?)</div>',
        content, re.DOTALL
    )
    for idx, tweet in enumerate(tweet_blocks_found[:5], 1):
        if not re.search(r'tweet-author|tweet-text', tweet):
            warn("TWEET_STRUCTURE", f"Tweet #{idx} may be missing .tweet-author or .tweet-text.",
                 context=tweet[:80])

    return result()


def result() -> dict:
    total = len(ERRORS) + len(WARNINGS) + len(INFOS)
    return {
        "errors": [vars(i) for i in ISSUES if i.severity == "ERROR"],
        "warnings": [vars(i) for i in WARNINGS],
        "infos": [vars(i) for i in INFOS],
        "total": total,
        "pass": len(ERRORS) == 0,
    }


def print_report(r: dict, verbose: bool = False):
    print(f"\n{'='*60}")
    print(f"  MORNING BRIEF QA REPORT")
    print(f"{'='*60}")
    print(f"  {'✓ PASS' if r['pass'] else '✗ FAIL'} — {r['errors']} error(s), "
          f"{len(r['warnings'])} warning(s), {len(r['infos'])} info(s)\n")

    if r['errors']:
        print(f"  [ERROR] Fix before printing:\n")
        for e in r['errors']:
            fix_note = f"\n       ↳ AUTO-FIX: {e['auto_fix']}" if e.get('auto_fix') else ""
            print(f"       ✗ {e['code']}: {e['message']}{fix_note}")
            if e.get('context'):
                print(f"         Context:\n{e['context']}")
            if e.get('line'):
                print(f"         Line {e['line']}")
        print()

    if r['warnings']:
        print(f"  [WARN] Review:\n")
        for w in r['warnings']:
            print(f"       ⚠ {w['code']}: {w['message']}")
            if w.get('context'):
                print(f"         Context: {w['context'][:80]}")
        print()

    if verbose and r['infos']:
        print(f"  [INFO]")
        for i in r['infos']:
            print(f"       • {i['code']}: {i['message']}")
        print()

    return r['pass']


# ─── Auto-Fix Logic ───────────────────────────────────────────────────────────

def auto_fix(brief_path: str, r: dict) -> bool:
    """Apply known safe auto-fixes. Returns True if changes were made."""
    content = Path(brief_path).read_text()
    changed = False

    # Fix 1: YAML empty headerTemplate
    fm_lines = content.split('\n')
    fm_start = None
    fm_end = None
    for i, line in enumerate(fm_lines):
        if line.strip() == '---':
            if fm_start is None:
                fm_start = i
            else:
                fm_end = i
                break

    if fm_start is not None and fm_end is not None:
        fm_block = '\n'.join(fm_lines[fm_start:fm_end + 1])

        if re.search(r'headerTemplate:\s*["\']?["\']?\s*$', fm_block):
            # It's empty — fix it
            fixed = re.sub(
                r'(headerTemplate:\s*)["\']?["\']?\s*$',
                r'\1"<span></span>"',
                fm_block,
                flags=re.MULTILINE
            )
            fixed_content = '\n'.join(fm_lines[:fm_start]) + '\n' + fixed + '\n' + '\n'.join(fm_lines[fm_end + 1:])
            Path(brief_path).write_text(fixed_content)
            content = fixed_content
            changed = True
            print("  [AUTO-FIX] Set headerTemplate to '<span></span>' in YAML frontmatter.")

        # Fix 2: HN section — convert markdown header inside HTML block to HTML h1
        # This is complex — mark as needing manual fix
        if re.search(r'<div class=["\']hn-section["\']>.*?##\s+IV\.\s+HACKER NEWS',
                     content, re.DOTALL):
            print("  [MANUAL-FIX NEEDED] HN section has markdown ## inside HTML block.")
            print("                    Convert '## IV. HACKER NEWS' to '<h1>IV. HACKER NEWS</h1>' inside .hn-section.")

    if changed:
        print(f"\n  Auto-fixes applied. Re-run linter to verify.")

    return changed


# ─── Visual Screenshot Pass ───────────────────────────────────────────────────

def screenshot_pass(brief_md_path: str, tmp_dir: str = "/tmp/brief-qa") -> dict:
    """Generate PDF from markdown, screenshot key pages, return paths."""
    if not TRY_PYMUPDF:
        return {"available": False, "reason": "PyMuPDF not available"}

    os.makedirs(tmp_dir, exist_ok=True)
    pdf_path = f"{tmp_dir}/preview.pdf"

    # Generate PDF
    import subprocess
    result = subprocess.run(
        ['md-to-pdf', brief_md_path, '--pdf-options',
         '{"format":"Letter","margin":{"top":"0.6in","right":"0.55in","bottom":"0.6in","left":"0.55in"},'
         '"printBackground":true,"displayHeaderFooter":true}'],
        capture_output=True, text=True, timeout=60,
        cwd=os.path.dirname(brief_md_path) or '.'
    )
    if result.returncode != 0:
        return {"available": False, "reason": f"md-to-pdf failed: {result.stderr[:200]}"}

    # Find the generated PDF (md-to-pdf outputs alongside the .md file)
    expected_pdf = brief_md_path.replace('.md', '.pdf')
    if os.path.exists(expected_pdf):
        pdf_path = expected_pdf
    else:
        # Search for most recent PDF in common locations
        candidates = [
            os.path.join(os.path.dirname(brief_md_path), 'preview.pdf'),
            os.path.join(tmp_dir, 'preview.pdf'),
        ]
        for c in candidates:
            if os.path.exists(c):
                pdf_path = c
                break

    if not os.path.exists(pdf_path):
        return {"available": False, "reason": f"PDF not found at {expected_pdf}"}

    # Screenshot pages 1, 2, and last page
    pages_of_interest = []
    try:
        doc = fitz.open(pdf_path)
        total = len(doc)

        # Always: page 1, page 2, last page
        pages_of_interest = [1, 2, total]
        # Also: whichever page contains HN section
        for i in range(total):
            text = doc[i].get_text()
            if 'HACKER NEWS' in text or 'HN Algolia' in text:
                pages_of_interest.append(i + 1)
                break

        pages_of_interest = sorted(set(pages_of_interest))
        screenshot_paths = []

        for pg in pages_of_interest:
            if pg > total:
                continue
            page = doc[pg - 1]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom = 144dpi
            out_path = f"{tmp_dir}/page{pg}.png"
            pix.save(out_path)
            screenshot_paths.append({"page": pg, "path": out_path})

        doc.close()
        return {
            "available": True,
            "pdf_path": pdf_path,
            "total_pages": total,
            "screenshots": screenshot_paths
        }
    except Exception as e:
        return {"available": False, "reason": str(e)[:200]}


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Morning Brief QA Linter")
    parser.add_argument("brief", help="Path to assembled brief (.md)")
    parser.add_argument("--fix", action="store_true", help="Apply auto-fixes")
    parser.add_argument("--screenshot", action="store_true", help="Generate visual screenshot pass")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show info-level issues")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    r = lint(args.brief, fix=args.fix, verbose=args.verbose)

    if not args.json:
        passed = print_report(r, verbose=args.verbose)

        if args.fix:
            auto_fixed = auto_fix(args.brief, r)
            if auto_fixed:
                r = lint(args.brief, fix=False, verbose=args.verbose)
                print_report(r, verbose=args.verbose)

        if args.screenshot:
            print(f"\n  [SCREENSHOT PASS]")
            sp = screenshot_pass(args.brief)
            if sp.get('available'):
                print(f"       PDF: {sp['pdf_path']} ({sp['total_pages']} pages)")
                for ss in sp['screenshots']:
                    print(f"       Page {ss['page']}: {ss['path']}")
            else:
                print(f"       Skipped: {sp.get('reason', 'unknown error')}")

        if not passed:
            print(f"\n  ⚠ BRIEF HAS ERRORS — DO NOT PRINT")
            sys.exit(1)
        else:
            print(f"\n  ✓ No errors — safe to print")
            sys.exit(0)
    else:
        print(json.dumps(r, indent=2))
        sys.exit(0 if r['pass'] else 1)


if __name__ == "__main__":
    main()
