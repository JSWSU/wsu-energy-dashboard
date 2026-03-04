#!/usr/bin/env python3
"""
JSON repair utility for Claude discipline scan output.
Fixes common malformations before declaring a scan failed.

Usage:
    python repair_json.py <path-to-raw-output.txt> <path-to-output.json>

Exit codes:
    0 = repaired successfully, valid JSON written
    1 = unrepairable, no output written
"""

import json
import re
import sys


def repair(raw):
    """Attempt to repair malformed JSON from Claude output.

    Returns (parsed_obj, None) on success or (None, error_msg) on failure.
    """
    text = raw.strip()

    # Step 1: Strip any text before the first [ or {
    # Claude sometimes prefixes JSON with explanation text
    first_bracket = len(text)
    for ch in ('[', '{'):
        idx = text.find(ch)
        if idx >= 0 and idx < first_bracket:
            first_bracket = idx
    if first_bracket < len(text):
        text = text[first_bracket:]
    else:
        return None, "No JSON array or object found in output"

    # Step 2: Fix UTF-8 issues (smart quotes, em dashes)
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    text = text.replace('\u2013', '-').replace('\u2014', '-')

    # Step 3: Remove trailing commas before ] or }
    text = re.sub(r',\s*([\]}])', r'\1', text)

    # Step 4: Try parsing as-is
    try:
        obj = json.loads(text)
        return obj, None
    except json.JSONDecodeError:
        pass

    # Step 5: Fix truncated JSON by closing open brackets/braces
    # Use a stack to track nesting order so closings are in correct reverse order
    stack = []
    in_string = False
    escape_next = False
    for ch in text:
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in ('[', '{'):
            stack.append(ch)
        elif ch == ']' and stack and stack[-1] == '[':
            stack.pop()
        elif ch == '}' and stack and stack[-1] == '{':
            stack.pop()

    # Close any open string
    if in_string:
        text += '"'

    # Remove trailing comma after closing string
    text = re.sub(r',\s*$', '', text)

    # Close open brackets/braces in correct reverse nesting order
    closing = {'[': ']', '{': '}'}
    text += ''.join(closing[ch] for ch in reversed(stack))

    # Remove trailing commas again after additions
    text = re.sub(r',\s*([\]}])', r'\1', text)

    # Step 6: Try parsing repaired text
    try:
        obj = json.loads(text)
        return obj, None
    except json.JSONDecodeError as e:
        return None, f"Repair failed: {e}"


def validate_structure(obj):
    """Check that repaired JSON has expected discipline output structure."""
    if isinstance(obj, dict):
        # Accept dict with 'requirements' or 'findings' key
        if 'requirements' in obj or 'findings' in obj:
            return True, None
        # Accept dict with 'summary' key (alternate Claude format)
        if 'summary' in obj:
            return True, None
        return False, f"Dict missing 'requirements' or 'findings' key. Keys: {list(obj.keys())[:10]}"
    if isinstance(obj, list):
        # Accept list of requirement items
        if len(obj) == 0:
            return False, "Empty list"
        if isinstance(obj[0], dict):
            return True, None
        return False, f"List items are not dicts: {type(obj[0])}"
    return False, f"Unexpected top-level type: {type(obj)}"


def main():
    if len(sys.argv) < 3:
        print("Usage: python repair_json.py <input-raw> <output-json>", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    with open(input_path, 'r', encoding='utf-8', errors='replace') as f:
        raw = f.read()

    obj, err = repair(raw)
    if err:
        print(f"REPAIR FAILED: {err}", file=sys.stderr)
        sys.exit(1)

    ok, verr = validate_structure(obj)
    if not ok:
        print(f"STRUCTURE INVALID: {verr}", file=sys.stderr)
        sys.exit(1)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

    print(f"REPAIRED: {output_path}")
    sys.exit(0)


if __name__ == '__main__':
    main()
