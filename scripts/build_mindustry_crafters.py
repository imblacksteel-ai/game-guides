#!/usr/bin/env python3
"""
Mindustry の生産設備データ assets/data/mindustry-crafters.json を生成する。

出典: Mindustry 本体のソース（Anuken/Mindustry, GPL-3.0）の最新リリースタグの
  core/src/mindustry/content/Blocks.java（ブロック定義）と
  core/assets/bundles/bundle.properties / bundle_ja.properties（英日の表示名）。
取り込むのは数値（事実）と表示名だけ。

対象は「一定時間ごとに入力を消費して出力を出す」生産設備（GenericCrafter / AttributeCrafter /
HeatCrafter / Separator）。craftTime はティック（1秒=60ティック）。
想定外の書き方のブロックは推測で埋めず、スキップしてログに出す。

ページの <!-- MDT-CRAFTERS --> / <!-- MDT-NAMES --> マーカー間に表も書き込む（冪等）。

使い方: python3 scripts/build_mindustry_crafters.py
"""
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets/data/mindustry-crafters.json")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) Chrome/131.0"}
TYPES = ("GenericCrafter", "AttributeCrafter", "HeatCrafter", "Separator")


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read().decode("utf-8")


def latest_tag():
    data = json.loads(get("https://api.github.com/repos/Anuken/Mindustry/releases/latest"))
    return data["tag_name"]


def raw(tag, path):
    return get(f"https://raw.githubusercontent.com/Anuken/Mindustry/{tag}/{path}")


def blocks(src):
    """`name = new Type("id"){{ ... }};` を中括弧の対応で切り出す。"""
    for m in re.finditer(r"(\w+) = new (\w+)\(\"([\w-]+)\"\)\{\{", src):
        var, typ, bid = m.groups()
        i, depth = m.end(), 2
        while depth and i < len(src):
            if src[i] == "{":
                depth += 1
            elif src[i] == "}":
                depth -= 1
            i += 1
        yield var, typ, bid, src[m.end():i]


def stacks(s):
    """with(Items.copper, 30, Items.lead, 25) の中身 → [(copper, 30), ...]"""
    return [(a, float(b)) for a, b in re.findall(r"(?:Items|Liquids)\.(\w+),\s*([\d.]+)f?", s)]


def camel_to_id(s):
    return re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", s).lower()


def num(expr):
    """"60f * 2.25f/4f" のような数値だけの式を評価する。それ以外が混ざっていれば None。"""
    e = expr.replace("f", "").strip()
    if not re.fullmatch(r"[\d.\s*/+()-]+", e):
        return None
    return float(eval(e, {"__builtins__": {}}))


def parse(typ, body):
    """液体の量はソース上「1ティックあたり」なので×60で毎秒にする。アイテムは1回の生産あたり。"""
    d = {}
    m = re.search(r"craftTime = ([^;]+);", body)
    d["craft_time"] = num(m.group(1)) if m else (80.0 if typ != "Separator" else None)
    m = re.search(r"\bsize = (\d+);", body)
    d["size"] = int(m.group(1)) if m else 1
    out = []
    m = re.search(r"outputItem = new ItemStack\(Items\.(\w+), (\d+)\)", body)
    if m:
        out.append({"id": camel_to_id(m.group(1)), "kind": "item", "amount": float(m.group(2))})
    m = re.search(r"outputItems = with\(([^)]*)\)", body)
    if m:
        out += [{"id": camel_to_id(a), "kind": "item", "amount": n} for a, n in stacks(m.group(1))]
    for m in re.finditer(r"outputLiquid = new LiquidStack\(Liquids\.(\w+), ([^)]+)\)", body):
        v = num(m.group(2))
        if v is None:
            return None, "unparsed outputLiquid"
        out.append({"id": camel_to_id(m.group(1)), "kind": "liquid", "per_sec": round(v * 60, 4)})
    m = re.search(r"outputLiquids = LiquidStack\.with\(([^;]*)\);", body)
    if m:
        for liq, expr in re.findall(r"Liquids\.(\w+), ([^,]+?)(?=, Liquids|$)", m.group(1).strip()):
            v = num(expr)
            if v is None:
                return None, "unparsed outputLiquids"
            out.append({"id": camel_to_id(liq), "kind": "liquid", "per_sec": round(v * 60, 4)})
    m = re.search(r"results = with\(([^;]*)\);", body)
    if m:  # 分離機：1回の生産で重みに応じたアイテムが1個だけ出る
        pairs = stacks(m.group(1))
        total = sum(n for _, n in pairs)
        out += [{"id": camel_to_id(a), "kind": "item", "amount": round(n / total, 6), "weight": n} for a, n in pairs]
    d["outputs"] = out

    ins = []
    for m in re.finditer(r"consumeItems?\(([^;]*)\);", body):
        arg = m.group(1)
        mm = re.fullmatch(r"Items\.(\w+)(?:, (\d+))?", arg.strip())
        if mm:
            ins.append({"id": camel_to_id(mm.group(1)), "kind": "item", "amount": float(mm.group(2) or 1)})
        else:
            ins += [{"id": camel_to_id(a), "kind": "item", "amount": n} for a, n in stacks(arg)]
    for m in re.finditer(r"consumeLiquid\(Liquids\.(\w+), ([^;]+)\);", body):
        v = num(m.group(2).rstrip(")"))
        if v is None:
            return None, "unparsed consumeLiquid"
        ins.append({"id": camel_to_id(m.group(1)), "kind": "liquid", "per_sec": round(v * 60, 4)})
    if re.search(r"consumeLiquids\(|consumeItemFilter|consumeItemFlammable|consumeItemRadioactive|consumeCoolant", body):
        return None, "complex consumer"
    d["inputs"] = ins
    m = re.search(r"consumePower\(([^;]+)\);", body)
    p = num(m.group(1)) if m else 0.0
    if p is None:
        return None, "unparsed consumePower"
    d["power_per_sec"] = round(p * 60, 4)
    m = re.search(r"heatRequirement = ([\d.]+)f?;", body)
    d["heat"] = float(m.group(1)) if m else 0.0
    return d, None


def names(bundle):
    out = {}
    for line in bundle.splitlines():
        m = re.match(r"(item|liquid|block)\.([\w-]+)\.name\s*=\s*(.+)", line)
        if m:
            out[(m.group(1), m.group(2))] = m.group(3).strip()
    return out


def main():
    tag = latest_tag()
    src = raw(tag, "core/src/mindustry/content/Blocks.java")
    en = names(raw(tag, "core/assets/bundles/bundle.properties"))
    ja = names(raw(tag, "core/assets/bundles/bundle_ja.properties"))

    crafters, skipped = [], []
    planet = "serpulo"
    for var, typ, bid, body in blocks(src):
        if typ not in TYPES:
            continue
        d, why = parse(typ, body)
        if d is None or not d["craft_time"] or not d["outputs"]:
            skipped.append(f"{bid} ({typ}): {why or 'no craftTime/outputs'}")
            continue
        req = re.search(r"requirements\(Category\.\w+, (?:BuildVisibility\.(\w+), )?(with\([^;]*)\);", body)
        if req and req.group(1) in ("debugOnly", "editorOnly", "sandboxOnly"):
            skipped.append(f"{bid}: not buildable in normal play ({req.group(1)})")
            continue
        cost = stacks(req.group(2)) if req else []
        # Erekir のブロックは建設コストにベリリウム・タングステン・酸化物・カーバイドのどれかを使う
        erekir = any(i in ("beryllium", "tungsten", "oxide", "carbide") for i, _ in cost)
        d.update({
            "id": bid, "type": typ, "planet": "erekir" if erekir else "serpulo",
            "name_en": en.get(("block", bid), bid), "name_ja": ja.get(("block", bid), en.get(("block", bid), bid)),
            "cost": [{"id": camel_to_id(i), "amount": n} for i, n in cost],
        })
        crafters.append(d)

    res = set()
    for c in crafters:
        for x in c["inputs"] + c["outputs"]:
            res.add((x["kind"], x["id"]))
        for x in c["cost"]:
            res.add(("item", x["id"]))
    resources = {f"{k}:{i}": {"en": en.get((k, i), i), "ja": ja.get((k, i), en.get((k, i), i))} for k, i in sorted(res)}
    missing = [k for k, v in resources.items() if v["en"] == k.split(":")[1]]
    if missing:
        sys.exit(f"names missing from bundle: {missing}")

    data = {"version": tag, "source": "Anuken/Mindustry Blocks.java + bundles", "resources": resources, "crafters": crafters}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{tag}: wrote {len(crafters)} crafters to {os.path.relpath(OUT, ROOT)}")
    for s in skipped:
        print("  skipped:", s)



# ---- ページへの表の書き込み（main() の後に render_pages() を呼ぶ） ----
PAGES = {
    "crafters": {"en": "games/mindustry/production-calculator/index.html", "ja": "ja/games/mindustry/production-calculator/index.html"},
    "names": {"en": "games/mindustry/index.html", "ja": "ja/games/mindustry/index.html"},
}
T = {
    "en": {"crafter_head": ["Block", "Inputs /s", "Outputs /s", "Power /s", "Cycle"],
           "names_head": ["English", "Japanese", "Type"], "item": "Item", "liquid": "Liquid",
           "planet": {"serpulo": "Serpulo", "erekir": "Erekir"}, "heat": "heat {h}", "random": "one of, per cycle"},
    "ja": {"crafter_head": ["ブロック", "入力 /秒", "出力 /秒", "電力 /秒", "1サイクル"],
           "names_head": ["英語", "日本語", "種類"], "item": "アイテム", "liquid": "液体",
           "planet": {"serpulo": "セルプロ", "erekir": "エレキル"}, "heat": "熱 {h}", "random": "1サイクルごとにどれか1つ"},
}


def fmt(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def rate(x, craft_time):
    """アイテムは1サイクルあたりの個数 → 毎秒。液体はもともと毎秒。"""
    return x["per_sec"] if x["kind"] == "liquid" else x["amount"] * 60 / craft_time


def render_crafters(lang, data):
    import html as h
    t = T[lang]
    res = data["resources"]
    nm = lambda x: h.escape(res[f"{x['kind']}:{x['id']}"][lang])
    rows = []
    for planet in ("serpulo", "erekir"):
        rows.append(f'<tr class="area-row"><th colspan="5">{t["planet"][planet]}</th></tr>')
        for c in (c for c in data["crafters"] if c["planet"] == planet):
            ct = c["craft_time"]
            ins = "<br>".join(f"{nm(x)} {fmt(rate(x, ct))}" for x in c["inputs"]) or "—"
            if c["type"] == "Separator":
                total = sum(o["weight"] for o in c["outputs"])
                outs = f'<span class="build-note">{t["random"]}</span><br>' + "<br>".join(
                    f"{nm(o)} {fmt(o['weight'] / total * 60 / ct)}" for o in c["outputs"])
            else:
                outs = "<br>".join(f"{nm(x)} {fmt(rate(x, ct))}" for x in c["outputs"])
            if c["heat"]:
                outs += f'<br><span class="build-note">{t["heat"].format(h=fmt(c["heat"]))}</span>'
            name = h.escape(c["name_en"] if lang == "en" else c["name_ja"])
            sub = f'<br><span class="romaji">{h.escape(c["name_ja"] if lang == "en" else c["name_en"])}</span>'
            rows.append(f'<tr id="c-{c["id"]}"><td>{name}{sub}</td><td>{ins}</td><td>{outs}</td>'
                        f'<td class="tag-mono">{fmt(c["power_per_sec"]) if c["power_per_sec"] else "—"}</td>'
                        f'<td class="tag-mono">{fmt(ct / 60)}s</td></tr>')
    head = "".join(f"<th>{x}</th>" for x in t["crafter_head"])
    return (f'<table class="glossary mdt-table">\n<thead><tr>{head}</tr></thead>\n<tbody>\n'
            + "\n".join(rows) + "\n</tbody>\n</table>")


def render_names(lang, data):
    import html as h
    t = T[lang]
    rows = []
    for key, n in sorted(data["resources"].items(), key=lambda kv: (kv[0].split(":")[0], kv[1]["en"])):
        kind = t["item"] if key.startswith("item:") else t["liquid"]
        rows.append(f'<tr><td>{h.escape(n["en"])}</td><td class="jp">{h.escape(n["ja"])}</td><td>{kind}</td></tr>')
    head = "".join(f"<th>{x}</th>" for x in t["names_head"])
    return (f'<table class="glossary">\n<thead><tr>{head}</tr></thead>\n<tbody>\n'
            + "\n".join(rows) + "\n</tbody>\n</table>")


def render_pages():
    data = json.load(open(OUT, encoding="utf-8"))
    for key, render in (("crafters", render_crafters), ("names", render_names)):
        for lang, page in PAGES[key].items():
            path = os.path.join(ROOT, page)
            if not os.path.exists(path):
                print(f"  (page not created yet: {page})")
                continue
            s = open(path, encoding="utf-8").read()
            marker = "MDT-CRAFTERS" if key == "crafters" else "MDT-NAMES"
            new, n = re.subn(rf"(<!-- {marker}:START -->\n).*?(<!-- {marker}:END -->)",
                             lambda m: m.group(1) + render(lang, data) + "\n" + m.group(2), s, flags=re.S)
            if n != 1:
                sys.exit(f"{marker} markers not found in {page}")
            open(path, "w", encoding="utf-8").write(new)
            print(f"rendered {key} into {page}")


if __name__ == "__main__":
    main()
    render_pages()
