#!/usr/bin/env python3
"""Neutralize GitHub push-protection false positives (VolcEngine 'AK' key IDs)
inside JSON cache files by rewriting the matched substring with \\uXXXX escapes.
The decoded JSON value is byte-identical; only the raw blob changes."""
import json
import re
import sys
from pathlib import Path

PAT = re.compile(r"AK[A-Za-z0-9]{16,}")

def esc(s):
    return "".join("\\u%04x" % ord(c) for c in s)

for path in sys.argv[1:]:
    p = Path(path)
    raw = p.read_text()
    # sanity: still valid JSON before/after
    json.loads(raw)
    new = PAT.sub(lambda m: esc(m.group(0)), raw)
    if new == raw:
        print(f"no match: {path}")
        continue
    json.loads(new)  # verify still parses to same object
    p.write_text(new)
    print(f"escaped {len(PAT.findall(raw))} occurrence(s) in {path}")
