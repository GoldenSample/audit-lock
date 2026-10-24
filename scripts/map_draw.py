#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Чертёж контура ИЗ ДАННЫХ карты BRANCH_MAP.json: по дорожке на каждый путь (flows[].path), узлы слева направо по порядку связей.

  python map_draw.py BRANCH_MAP.json --out img/

Пишет img/map_<путь>.svg на каждый путь и img/map.html со всеми чертежами и легендой. Цвет рамки = статус станции
(ok, weak, broken, dead), массивы пунктиром, под именем строка замков: «замков: N» или «ВНЕ ЗАМКОВ» красным.
Чертёж не рисуется руками: что не попало в карту, того нет и на чертеже, и это видно сразу.
"""
from __future__ import annotations

import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

C = {"bg": "#0f1419", "panel": "#18202b", "line": "#3a4a5e", "text": "#e8eef5", "grey": "#8b98ac",
     "ok": "#3fb27f", "weak": "#e0a43a", "broken": "#e5534b", "dead": "#6b7785", "array": "#58a6ff", "ext": "#8b98ac"}
BW, BH, GX, GY, PAD = 210, 74, 70, 26, 30


def wrap(s: str, n: int = 26) -> list[str]:
    words, lines, cur = str(s).split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > n and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines[:2] or [""]


def ranks(nodes: list[str], edges: list[tuple[str, str]]) -> dict[str, int]:
    r = {n: 0 for n in nodes}
    for _ in range(len(nodes)):
        changed = False
        for a, b in edges:
            if r[b] < r[a] + 1 and r[a] + 1 < len(nodes):
                r[b] = r[a] + 1
                changed = True
        if not changed:
            break
    return r


def lane_svg(title: str, flows: list[dict], nodes: dict[str, dict]) -> str:
    order: list[str] = []
    for f in flows:
        for k in (f["from"], f["to"]):
            if k not in order:
                order.append(k)
    edges = [(f["from"], f["to"]) for f in flows if f["from"] in nodes and f["to"] in nodes]
    rk = ranks(order, edges)
    cols: dict[int, list[str]] = defaultdict(list)
    for n in order:
        cols[rk[n]].append(n)
    pos = {}
    for c, ns in cols.items():
        for i, n in enumerate(ns):
            pos[n] = (PAD + c * (BW + GX), PAD + 40 + i * (BH + GY))
    w = PAD * 2 + (max(cols) + 1) * (BW + GX) - GX if cols else 400
    h = PAD * 2 + 70 + max(len(v) for v in cols.values()) * (BH + GY) - GY if cols else 200
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
           f'font-family="system-ui, Segoe UI, Arial, sans-serif">',
           f'<rect width="100%" height="100%" fill="{C["bg"]}"/>',
           '<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
           f'<path d="M0,0 L10,5 L0,10 z" fill="{C["grey"]}"/></marker></defs>',
           f'<text x="{PAD}" y="{PAD + 8}" fill="{C["text"]}" font-size="18" font-weight="600">{html.escape(title)}</text>']
    for f in flows:
        a, b = f["from"], f["to"]
        if a not in pos or b not in pos:
            continue
        (x1, y1), (x2, y2) = pos[a], pos[b]
        sx, sy, ex, ey = x1 + BW, y1 + BH / 2, x2, y2 + BH / 2
        if x2 <= x1:
            sx, ex = x1 + BW / 2, x2 + BW / 2
            sy, ey = (y1 + BH, y2) if y2 > y1 else (y1, y2 + BH)
        mx = (sx + ex) / 2
        if y1 == y2 and rk.get(b, 0) - rk.get(a, 0) > 1:     # через голову соседей: дугой под рядом, чтобы не лечь на узлы
            sx, sy, ex, ey = x1 + BW / 2, y1 + BH, x2 + BW / 2, y2 + BH
            dip = sy + 34
            d_attr, ly = f"M{sx},{sy} C{sx},{dip} {ex},{dip} {ex},{ey}", dip - 2
        else:
            d_attr, ly = f"M{sx},{sy} C{mx},{sy} {mx},{ey} {ex},{ey}", (sy + ey) / 2 - 5
        out.append(f'<path d="{d_attr}" fill="none" stroke="{C["line"]}" '
                   f'stroke-width="1.6" marker-end="url(#ar)"><title>{html.escape(str(f.get("what", "")))}</title></path>')
        if f.get("what"):
            out.append(f'<text x="{mx}" y="{ly}" fill="{C["grey"]}" font-size="10" text-anchor="middle">'
                       f'{html.escape(str(f["what"])[:28])}</text>')
    for n, (x, y) in pos.items():
        d = nodes.get(n, {"id": n, "name": n, "status": "broken", "_missing": True})
        is_arr = d.get("_kind") == "array"
        stroke = C["array"] if is_arr else C["ext"] if d.get("external") else C.get(d.get("status"), C["broken"])
        dash = ' stroke-dasharray="6 4"' if is_arr else ""
        out.append(f'<rect x="{x}" y="{y}" width="{BW}" height="{BH}" rx="8" fill="{C["panel"]}" stroke="{stroke}" '
                   f'stroke-width="2"{dash}><title>{html.escape(n + ": " + str(d.get("evidence") or d.get("path") or ""))}</title></rect>')
        for i, line in enumerate(wrap(d.get("name") or n)):
            out.append(f'<text x="{x + 12}" y="{y + 22 + i * 16}" fill="{C["text"]}" font-size="13">{html.escape(line)}</text>')
        if is_arr:
            sub, col = "массив" + ("" if d.get("in_product", True) else ", мимо продукта"), C["array"]
        elif d.get("external"):
            sub, col = "внешний мир", C["grey"]
        elif d.get("_missing"):
            sub, col = "НЕТ В КАРТЕ", C["broken"]
        else:
            nl = len(d.get("locks") or [])
            sub, col = (f"замков: {nl} · {d.get('status')}", C["grey"]) if nl else (f"ВНЕ ЗАМКОВ · {d.get('status')}", C["broken"])
        out.append(f'<text x="{x + 12}" y="{y + BH - 12}" fill="{col}" font-size="11" font-weight="600">{html.escape(sub)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return 2
    out = Path(a[a.index("--out") + 1]) if "--out" in a else Path("img")
    out.mkdir(parents=True, exist_ok=True)
    d = json.loads(Path(a[0]).read_text(encoding="utf-8"))
    nodes = {s["id"]: dict(s, _kind="station") for s in d.get("stations", [])}
    nodes.update({x["id"]: dict(x, _kind="array", name=x.get("name") or x.get("what") or x["id"]) for x in d.get("arrays", [])})
    lanes: dict[str, list[dict]] = defaultdict(list)
    for f in d.get("flows", []):
        lanes[f.get("path") or "main"].append(f)
    parts = []
    for lane, fl in lanes.items():
        svg = lane_svg(f"{d.get('name', 'контур')}: путь «{lane}»", fl, nodes)
        fn = out / ("map_" + (re.sub(r"[^\w-]+", "_", lane).strip("_") or "main") + ".svg")
        fn.write_text(svg, encoding="utf-8")
        parts.append(svg)
        print(f"{fn}: связей {len(fl)}")
    legend = ("<p>Рамка: <b style='color:#3fb27f'>ok</b>, <b style='color:#e0a43a'>weak</b> (держится текстом или с дырой), "
              "<b style='color:#e5534b'>broken</b>, <b style='color:#6b7785'>dead</b>; пунктир = массив. "
              "«ВНЕ ЗАМКОВ» = у станции нет ни одного замка на пути. Наведи на узел: опора путь:строка.</p>")
    page = ("<!doctype html><meta charset='utf-8'><title>Карта контура</title>"
            f"<body style='background:{C['bg']};color:{C['text']};color-scheme:dark;font-family:system-ui,sans-serif;padding:16px'>"
            f"<h1 style='font-size:20px'>{html.escape(d.get('name', 'контур'))}</h1>{legend}"
            + "".join(f"<div style='overflow-x:auto;margin:16px 0'>{p}</div>" for p in parts) + "</body>")
    (out / "map.html").write_text(page, encoding="utf-8")
    print(f"{out / 'map.html'}: чертежей {len(parts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
