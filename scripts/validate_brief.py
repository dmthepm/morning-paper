#!/usr/bin/env python3
"""
Morning Brief validation and regression testing.

Validates structural correctness, content minimums, and compares against golden fixtures.
Run after assemble_brief.py, before sending digest.

Usage:
  python3 validate_brief.py <brief.md> [--previous <prev_brief.md>] [--golden <golden_dir>] [--fail-on-warn] [--disable-diff]
"""

import sys
import os
import json
import difflib
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

# Import the existing QA linter
sys.path.insert(0, str(Path(__file__).parent))
try:
    import qa_linter
except ImportError as e:
    print(f"ERROR: Could not import qa_linter: {e}")
    sys.exit(1)


def structural_validation(brief_path: Path) -> Dict:
    """Run QA linter and additional structural checks."""
    # Run existing linter
    result = qa_linter.lint(str(brief_path), fix=False, verbose=False)
    
    # Additional checks beyond linter
    content = brief_path.read_text()
    
    # 1. Signals count: 10-20 items (not 5)
    # Count tweet blocks (including tweet-pair)
    tweet_blocks = len(re.findall(r'<div class=[\"\']tweet[\"\'][^>]*>', content))
    tweet_blocks += len(re.findall(r'<div class=[\"\']tweet-pair[\"\'][^>]*>', content))
    if tweet_blocks < 10:
        result['warnings'].append({
            'code': 'SIGNALS_TOO_FEW',
            'message': f'Only {tweet_blocks} tweet blocks found — expected 10-20.',
            'context': '',
            'line': 0
        })
    elif tweet_blocks > 20:
        result['warnings'].append({
            'code': 'SIGNALS_TOO_MANY',
            'message': f'{tweet_blocks} tweet blocks found — expected 10-20.',
            'context': '',
            'line': 0
        })
    
    # 2. Full Read I + II: both populated with real content
    full_reads = len(re.findall(r'<div class=[\"\']full-read[\"\'][^>]*>', content))
    if full_reads < 2:
        result['errors'].append({
            'code': 'FULL_READ_MISSING',
            'message': f'Only {full_reads} full-read blocks found — expected 2.',
            'context': '',
            'line': 0
        })
    
    # 3. HN: 20 cards with HN-specific data
    hn_cards = len(re.findall(r'<div class=[\"\']hn-card[\"\'][^>]*>', content))
    if hn_cards < 20:
        result['warnings'].append({
            'code': 'HN_CARDS_INSUFFICIENT',
            'message': f'Only {hn_cards} HN cards found — expected 20.',
            'context': '',
            'line': 0
        })
    
    # 4. Weather: present in info row
    # Look for info-row containing weather or temperature
    if '°F' not in content and '°C' not in content:
        result['warnings'].append({
            'code': 'WEATHER_MISSING',
            'message': 'Weather information (temperature) not found in info row.',
            'context': '',
            'line': 0
        })
    
    # 5. Skool: TBD or real content (not context summary placeholder)
    # Check for Skool section and ensure it's not placeholder
    skool_section = re.search(r'## V\. MAIN BRANCH.*SKOOL COMMUNITY.*?(?=##|$)', content, re.DOTALL | re.IGNORECASE)
    if skool_section:
        skool_text = skool_section.group(0)
        if 'TBD' in skool_text or 'placeholder' in skool_text.lower():
            result['warnings'].append({
                'code': 'SKOOL_PLACEHOLDER',
                'message': 'Skool section contains placeholder content.',
                'context': '',
                'line': 0
            })
    
    # 6. Agency: TBD or real content
    agency_section = re.search(r'## VI\. HIGH-TICKET AGENCY.*?(?=##|$)', content, re.DOTALL | re.IGNORECASE)
    if agency_section:
        agency_text = agency_section.group(0)
        if 'TBD' in agency_text or 'placeholder' in agency_text.lower():
            result['warnings'].append({
                'code': 'AGENCY_PLACEHOLDER',
                'message': 'High-ticket agency section contains placeholder content.',
                'context': '',
                'line': 0
            })
    
    # 7. Operations: markdown parsed to HTML (not raw text)
    # Check for <ul> tags inside operations section (should be HTML, not markdown list)
    ops_section = re.search(r'## VII\. OPERATIONS.*?(?=##|$)', content, re.DOTALL | re.IGNORECASE)
    if ops_section:
        ops_text = ops_section.group(0)
        # If there's a markdown list pattern (- item) that's not converted
        if re.search(r'^\s*-\s+', ops_text, re.MULTILINE):
            result['errors'].append({
                'code': 'OPS_MARKDOWN_RAW',
                'message': 'Operations section contains raw markdown list (not converted to HTML).',
                'context': '',
                'line': 0
            })
    
    # 8. Page count: >= 10 pages (estimate)
    lines = content.count('\n')
    estimated_pages = max(1, round(lines / 90))
    if estimated_pages < 10:
        result['warnings'].append({
            'code': 'PAGE_COUNT_LOW',
            'message': f'Estimated page count is {estimated_pages} — expected >= 10.',
            'context': '',
            'line': 0
        })

    return result


def diff_against_previous(current_path: Path, previous_path: Path) -> Dict:
    """Compute diff between current and previous brief."""
    current = current_path.read_text().splitlines()
    previous = previous_path.read_text().splitlines()
    
    diff = list(difflib.unified_diff(previous, current, lineterm='', fromfile='previous', tofile='current', n=3))
    
    # Count added/removed lines (simplistic)
    added = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
    removed = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
    
    # Identify major sections changed
    sections_changed = []
    for line in diff:
        if line.startswith('+') and re.match(r'^\+#+\s+[I-X]', line):
            sections_changed.append(line.strip())
        elif line.startswith('-') and re.match(r'^-#+\s+[I-X]', line):
            sections_changed.append(line.strip())
    
    return {
        'diff': diff[:100],  # limit size
        'added_lines': added,
        'removed_lines': removed,
        'sections_changed': list(set(sections_changed)),
        'has_changes': added > 0 or removed > 0
    }


def find_previous_brief(current_brief: Path) -> Optional[Path]:
    """Find previous day's brief in same directory based on date pattern."""
    # Pattern: YYYY-MM-DD-brief-review.md
    pattern = re.compile(r'(\d{4}-\d{2}-\d{2})-brief-review\.md$')
    match = pattern.search(str(current_brief.name))
    if not match:
        return None
    current_date_str = match.group(1)
    try:
        current_date = datetime.strptime(current_date_str, '%Y-%m-%d')
        prev_date = current_date - timedelta(days=1)
        prev_date_str = prev_date.strftime('%Y-%m-%d')
        # Replace date in filename
        prev_name = pattern.sub(f'{prev_date_str}-brief-review.md', current_brief.name)
        prev_path = current_brief.parent / prev_name
        if prev_path.exists():
            return prev_path
    except Exception:
        pass
    return None


def validate_telegram_digest(digest_text: str) -> List[Dict]:
    """Validate Telegram digest format."""
    issues = []
    # 1. Single message (not multiple) - we can't validate here, but we can check if digest contains multiple message separators
    # For now, assume caller passes the digest text.
    # 2. Contains PDF link
    if not re.search(r'\[.*?\]\(.*?\.pdf\)', digest_text):
        issues.append({
            'code': 'DIGEST_NO_PDF_LINK',
            'message': 'Telegram digest missing PDF link with markdown formatting.',
            'severity': 'ERROR'
        })
    # 3. No 'Additional Reading' repeated noise
    if 'Additional Reading' in digest_text:
        issues.append({
            'code': 'DIGEST_ADDITIONAL_READING_NOISE',
            'message': 'Telegram digest contains "Additional Reading" noise.',
            'severity': 'WARN'
        })
    return issues


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Validate Morning Brief')
    parser.add_argument('brief', help='Path to assembled brief markdown file')
    parser.add_argument('--previous', help='Path to previous brief for diff')
    parser.add_argument('--golden', help='Directory with golden fixtures')
    parser.add_argument('--fail-on-warn', action='store_true', help='Treat warnings as errors')
    parser.add_argument('--disable-diff', action='store_true', help='Skip diff against previous brief')
    parser.add_argument('--output', default='-', help='Output JSON report file')
    parser.add_argument('--quiet', action='store_true', help='Suppress non-error output')
    args = parser.parse_args()
    
    brief_path = Path(args.brief)
    if not brief_path.exists():
        print(f"Error: brief file not found: {brief_path}")
        sys.exit(1)
    
    report = {
        'brief': str(brief_path),
        'structural': structural_validation(brief_path),
        'diff': None,
        'telegram_digest_issues': [],
        'pass': True
    }
    
    # Diff against previous brief (auto-detected or provided)
    if not args.disable_diff:
        previous_path = None
        if args.previous:
            previous_path = Path(args.previous)
        else:
            previous_path = find_previous_brief(brief_path)
        
        if previous_path and previous_path.exists():
            report['diff'] = diff_against_previous(brief_path, previous_path)
        elif not args.quiet:
            print(f"Info: no previous brief found for diff", file=sys.stderr)
    
    # Diff against golden fixture (if provided)
    if args.golden:
        golden_dir = Path(args.golden)
        # Look for latest golden brief
        # For simplicity, assume golden_dir contains assembled-brief.md
        golden_path = golden_dir / 'assembled-brief.md'
        if golden_path.exists():
            report['diff_golden'] = diff_against_previous(brief_path, golden_path)
    
    # Determine pass/fail
    errors = len(report['structural']['errors'])
    warnings = len(report['structural']['warnings'])
    if errors > 0:
        report['pass'] = False
    if args.fail_on_warn and warnings > 0:
        report['pass'] = False
    
    # Output report
    if args.output == '-':
        if not args.quiet:
            print(json.dumps(report, indent=2))
    else:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
    
    # Print summary to stderr
    if not args.quiet:
        if errors:
            print(f"Validation failed with {errors} error(s), {warnings} warning(s)", file=sys.stderr)
        elif warnings:
            print(f"Validation passed with {warnings} warning(s)", file=sys.stderr)
        else:
            print(f"Validation passed", file=sys.stderr)
    
    # Exit code
    sys.exit(0 if report['pass'] else 1)


if __name__ == '__main__':
    main()