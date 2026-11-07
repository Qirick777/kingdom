#!/usr/bin/env python3
"""특성 데이터 검증기. docs/design/16_trait_effects.md 8절.

data/registry.json 과 data/traits/*.json 을 읽어 형식과 참조를 검사한다.
오류가 있으면 종료 코드 1.
"""
import glob
import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REG = os.path.join(ROOT, "data", "registry.json")
TRAITS = os.path.join(ROOT, "data", "traits", "*.json")

EFFECT_FIELDS = {
    "mod": ({"var", "op", "value"}, {"who", "if", "arg"}),
    "norm": ({"behavior", "status", "severity"}, {"who", "exempt", "if"}),
    "justify": ({"behavior", "holder", "value"}, {"who", "if"}),
    "opinion": ({"from", "to", "value"}, {"if"}),
    "enable": ({"action"}, {"who", "if"}),
    "disable": ({"action"}, {"who", "if"}),
    "ai": ({"action", "weight"}, {"who", "if"}),
    "event": ({"event", "chance_per_year"}, {"who", "if"}),
    "slot": ({"slot", "value"}, set()),
}


def main():
    reg = json.load(open(REG, encoding="utf-8"))
    errors, warns = [], []
    known = {k: set(reg[k]) for k in ("vars", "behaviors", "actions", "metrics", "predicates", "events", "scopes")}
    pers = set(reg["personalities"])
    kinds = reg["kinds"]
    traits = []
    for path in sorted(glob.glob(TRAITS)):
        name = os.path.basename(path)
        try:
            data = json.load(open(path, encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"{name}: JSON 오류 {e}")
            continue
        prop = data.get("proposed", {}) or {}
        for k, v in prop.items():
            if k not in known:
                errors.append(f"{name}: proposed 의 알 수 없는 구역 {k}")
                continue
            for key in v:
                if key in known[k]:
                    warns.append(f"{name}: proposed {k}.{key} 는 이미 레지스트리에 있음")
                else:
                    warns.append(f"{name}: 제안 {k}.{key} = {v[key]}")
                known[k].add(key)
        for t in data.get("traits", []):
            traits.append((name, t))

    ids = Counter(t.get("id") for _, t in traits)
    for i, n in ids.items():
        if n > 1:
            errors.append(f"id 중복: {i} ({n}번)")
    all_ids = set(ids)

    def chk_scope(where, v):
        if v is not None and v not in known["scopes"]:
            errors.append(f"{where}: 범위 '{v}' 없음")

    def chk_if(where, conds):
        if conds is None:
            return
        if not isinstance(conds, list):
            errors.append(f"{where}: if 는 목록이어야 함")
            return
        for c in conds:
            base = c.split(":", 1)[0].lstrip("!")
            if base not in known["predicates"]:
                errors.append(f"{where}: 조건 '{c}' 없음")

    for fname, t in traits:
        tid = t.get("id", "?")
        w = f"{fname}:{tid}"
        for f in ("id", "name", "kind", "tier", "effects"):
            if f not in t:
                errors.append(f"{w}: 필드 {f} 없음")
        kind = t.get("kind")
        if kind not in kinds:
            errors.append(f"{w}: kind '{kind}' 없음")
        if t.get("tier") not in ("기본", "해금", "없음"):
            errors.append(f"{w}: tier '{t.get('tier')}'")
        if t.get("tier") == "해금" and not t.get("unlock"):
            errors.append(f"{w}: 해금인데 unlock 없음")
        for u in t.get("unlock", []) or []:
            if u.get("metric") not in known["metrics"]:
                errors.append(f"{w}: 해금 지표 '{u.get('metric')}' 없음")
            if u.get("op") not in (">=", "<=", "==", ">", "<"):
                errors.append(f"{w}: 해금 op '{u.get('op')}'")
            if not isinstance(u.get("value"), (int, float)):
                errors.append(f"{w}: 해금 value 가 숫자가 아님")
            if u.get("metric") == "group.has_trait" and u.get("arg") not in all_ids:
                errors.append(f"{w}: 해금 조건의 특성 '{u.get('arg')}' 없음")
        for ex in t.get("exclusive", []) or []:
            if ex not in all_ids:
                errors.append(f"{w}: 배타 대상 '{ex}' 없음")
        for p in (t.get("likes", []) or []) + (t.get("dislikes", []) or []):
            if p not in pers:
                errors.append(f"{w}: 성격 '{p}' 없음")
        if kind == "성격" and t.get("pair") not in pers:
            errors.append(f"{w}: pair 없음 또는 잘못됨")
        if kind == "형질":
            g = t.get("genetics") or {}
            if g.get("dominance") not in ("우성", "열성", "X열성") or not (0 <= g.get("carrier_freq", -1) <= 1):
                errors.append(f"{w}: genetics 형식 오류")
        if kind == "재능":
            if "skill" not in t or "genius_effects" not in t:
                errors.append(f"{w}: 재능은 skill, genius_effects 필요")
            elif t["skill"] is not None and t["skill"] not in reg["skills"]:
                errors.append(f"{w}: 기술 '{t['skill']}' 없음")
        if kind == "숙련":
            if t.get("skill") not in reg["skills"] or t.get("threshold") not in (50, 80):
                errors.append(f"{w}: 숙련은 skill, threshold(50/80) 필요")
        if kind == "이력":
            if t.get("visibility") not in ("공개", "비밀", "둘 다") or not t.get("trigger"):
                errors.append(f"{w}: 이력은 visibility, trigger 필요")
        effs = list(t.get("effects", []) or [])
        if not effs:
            errors.append(f"{w}: effects 비어 있음")
        if kind == "재능":
            effs += list(t.get("genius_effects", []) or [])
        for k, e in enumerate(effs):
            ew = f"{w}#{k}"
            typ = e.get("type")
            if typ not in EFFECT_FIELDS:
                errors.append(f"{ew}: type '{typ}' 없음")
                continue
            req, opt = EFFECT_FIELDS[typ]
            keys = set(e) - {"type"}
            for r in req - keys:
                errors.append(f"{ew}: 필드 {r} 없음")
            for x in keys - req - opt:
                errors.append(f"{ew}: 알 수 없는 필드 {x}")
            chk_if(ew, e.get("if"))
            if typ == "mod":
                if e.get("var") not in known["vars"]:
                    errors.append(f"{ew}: 변수 '{e.get('var')}' 없음")
                if e.get("op") not in ("add", "mul", "set"):
                    errors.append(f"{ew}: op '{e.get('op')}'")
                if e.get("op") == "mul" and not (isinstance(e.get("value"), (int, float)) and e["value"] > 0):
                    errors.append(f"{ew}: mul 값은 양수")
                chk_scope(ew, e.get("who"))
            elif typ == "norm":
                if e.get("behavior") not in known["behaviors"]:
                    errors.append(f"{ew}: 행위 '{e.get('behavior')}' 없음")
                if e.get("status") not in ("forbidden", "allowed", "required"):
                    errors.append(f"{ew}: status '{e.get('status')}'")
                if not (0 <= e.get("severity", -1) <= 100):
                    errors.append(f"{ew}: severity 0~100")
                chk_scope(ew, e.get("who"))
                chk_scope(ew, e.get("exempt"))
            elif typ == "justify":
                if e.get("behavior") != "*" and e.get("behavior") not in known["behaviors"]:
                    errors.append(f"{ew}: 행위 '{e.get('behavior')}' 없음")
                if not (0 <= e.get("value", -1) <= 1):
                    errors.append(f"{ew}: justify 값 0~1")
                chk_scope(ew, e.get("holder"))
                chk_scope(ew, e.get("who"))
            elif typ == "opinion":
                chk_scope(ew, e.get("from"))
                chk_scope(ew, e.get("to"))
                if not isinstance(e.get("value"), (int, float)):
                    errors.append(f"{ew}: opinion 값이 숫자가 아님")
            elif typ in ("enable", "disable"):
                if e.get("action") not in known["actions"]:
                    errors.append(f"{ew}: 행동 '{e.get('action')}' 없음")
                chk_scope(ew, e.get("who"))
            elif typ == "ai":
                if e.get("action") not in known["actions"] and e.get("action") not in known["behaviors"]:
                    errors.append(f"{ew}: ai 대상 '{e.get('action')}' 이 행동, 행위 어디에도 없음")
                if not (isinstance(e.get("weight"), (int, float)) and e["weight"] > 0):
                    errors.append(f"{ew}: ai weight 는 양수")
                chk_scope(ew, e.get("who"))
            elif typ == "event":
                if e.get("event") not in known["events"]:
                    errors.append(f"{ew}: 사건 '{e.get('event')}' 없음")
                if not (0 <= e.get("chance_per_year", -1) <= 1):
                    errors.append(f"{ew}: 확률 0~1")
            elif typ == "slot":
                if e.get("slot") not in ("trait", "succession"):
                    errors.append(f"{ew}: slot '{e.get('slot')}'")

    # 문자열 어디에든 들어 있는 특성 id 참조가 실제로 있는지
    id_pat = re.compile(r"(law|doctrine|family|band|custom|tribe|city|league|merc|order|revolt|trade|guild|crime|cabal|cabal_goal|school|faction|pers|gene|talent|hist|mastery)\.[a-z_0-9]+")

    def walk(o, where):
        if isinstance(o, dict):
            for k, v in o.items():
                if k != "id":
                    walk(v, where)
        elif isinstance(o, list):
            for v in o:
                walk(v, where)
        elif isinstance(o, str) and id_pat.fullmatch(o) and o not in all_ids:
            errors.append(f"{where}: 없는 특성 id '{o}' 참조")

    for fname, t in traits:
        walk(t, f"{fname}:{t.get('id')}")
        for u in t.get("unlock", []) or []:
            if u.get("metric") == "cond.any":
                for sub in u.get("arg", []) or []:
                    if sub.get("metric") not in known["metrics"]:
                        errors.append(f"{fname}:{t.get('id')}: cond.any 안의 지표 '{sub.get('metric')}' 없음")

    # 배타 대칭
    ex = {t["id"]: set(t.get("exclusive", []) or []) for _, t in traits if "id" in t}
    for a, bs in ex.items():
        for b in bs:
            if b in ex and a not in ex[b]:
                errors.append(f"배타 비대칭: {a} → {b}")

    by_kind = Counter(t.get("kind") for _, t in traits)
    print("특성 수:", sum(by_kind.values()))
    for k, n in sorted(by_kind.items(), key=lambda x: -x[1]):
        print(f"  {k}: {n}")
    for wmsg in warns:
        print("경고:", wmsg)
    for e in errors:
        print("오류:", e)
    print(f"오류 {len(errors)}개, 경고 {len(warns)}개")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
