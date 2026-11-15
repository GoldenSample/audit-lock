#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check of the pipeline map BRANCH_MAP.json (schema: references/audit-method.md, section 4).

  python map_check.py BRANCH_MAP.json [--strict]

Prints: how many stations, datasets and links; stations outside the locks (locks is empty); broken and dead stations; datasets
that nobody reads or that do not go into the product; errors: a repeated id, a link to a missing node, an unknown status,
a station without support. Exit code 0 = no errors (a station outside the locks is not an error, it is an audit finding);
with --strict a station outside the locks is an error too.
"""
from __future__ import annotations

import json
import sys
from collections import Counter

STATUS = {"ok", "weak", "broken", "dead"}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    strict = "--strict" in sys.argv
    if not args:
        print(__doc__)
        return 2
    with open(args[0], encoding="utf-8") as f:
        d = json.load(f)
    st, ar, fl = d.get("stations") or [], d.get("arrays") or [], d.get("flows") or []
    errs: list[str] = []
    ids = Counter([s.get("id") for s in st] + [a.get("id") for a in ar])
    for i, n in ids.items():
        if not i:
            errs.append("a node without an id")
        elif n > 1:
            errs.append(f"id \"{i}\" is repeated {n} times")
    known = set(ids)
    for k, x in enumerate(fl):
        for end in ("from", "to"):
            if x.get(end) not in known:
                errs.append(f"link {k} ({x.get('from')} -> {x.get('to')}): node \"{x.get(end)}\" is not in stations or arrays")
    outside, bad = [], []
    for s in st:
        if s.get("status") not in STATUS:
            errs.append(f"station \"{s.get('id')}\": status \"{s.get('status')}\" is not one of {sorted(STATUS)}")
        if not s.get("external") and not s.get("evidence"):
            errs.append(f"station \"{s.get('id')}\" has no support (evidence path:line)")
        if not s.get("external") and not s.get("locks"):
            outside.append(s)
        if s.get("status") in ("broken", "dead"):
            bad.append(s)
    readers = {r for a in ar for r in (a.get("readers") or [])}
    unread = [a for a in ar if not a.get("readers")]
    not_in_product = [a for a in ar if a.get("in_product") is False]
    used = {x.get("from") for x in fl} | {x.get("to") for x in fl} | readers
    lonely = [s for s in st if s.get("id") not in used]
    paths = Counter(x.get("path") or "main" for x in fl)
    print(f"map \"{d.get('name', '?')}\": stations {len(st)}, datasets {len(ar)}, links {len(fl)}, paths {len(paths)} "
          f"({', '.join(f'{k} {v}' for k, v in paths.items())})")
    print(f"outside the locks {len(outside)}: " + (", ".join(f"{s['id']} ({s.get('status')})" for s in outside) or "none"))
    print(f"broken or dead {len(bad)}: " + (", ".join(f"{s['id']} {s['status']}" for s in bad) or "none"))
    if unread:
        print("datasets that nobody reads: " + ", ".join(a["id"] for a in unread))
    if not_in_product:
        print("datasets that do not go into the product: " + ", ".join(a["id"] for a in not_in_product))
    if lonely:
        print("stations without links: " + ", ".join(s["id"] for s in lonely))
    if strict and outside:
        errs.append(f"strict mode: {len(outside)} stations outside the locks")
    if errs:
        print(f"ERRORS {len(errs)}:\n  " + "\n  ".join(errs))
        return 1
    print("no errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
