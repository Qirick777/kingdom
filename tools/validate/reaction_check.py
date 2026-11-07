#!/usr/bin/env python3
"""16_trait_effects.md 3-2 반응 공식을 실제 특성 데이터로 계산한다.

예: 일부일처 교단에서 교주가 아내 4명을 둘 때, 교단이 가진 교리 조합별로
독실한 신도와 냉소적 신도의 반응량을 낸다.
"""
import glob
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
T = {}
for p in glob.glob(os.path.join(ROOT, "data", "traits", "*.json")):
    for t in json.load(open(p, encoding="utf-8"))["traits"]:
        T[t["id"]] = t

INTERNAL = {"독실": 0.4, "정직": 0.2, "냉소": -0.4, "기만": -0.2}


def internalization(pers):
    return max(0.0, min(1.4, 0.6 + sum(INTERNAL.get(x, 0) for x in pers)))


def severity(traits, behavior):
    sev = 0
    for tid in traits:
        for e in T[tid]["effects"]:
            if e["type"] == "norm" and e["behavior"] == behavior and e["status"] == "forbidden":
                sev = max(sev, e["severity"])
    return sev


def justification(traits, behavior, holder, pers):
    keep = 1.0
    for tid in traits:
        for e in T[tid]["effects"]:
            if e["type"] != "justify" or e["holder"] != holder:
                continue
            if e["behavior"] not in ("*", behavior):
                continue
            j = e["value"]
            if "독실" in pers:
                j = min(0.95, j * 1.25)
            if "냉소" in pers:
                j *= 0.5
            keep *= 1 - j
    return 1 - keep


def reaction(traits, behavior, holder, pers, evidence=1.0):
    return severity(traits, behavior) * internalization(pers) * (1 - justification(traits, behavior, holder, pers)) * evidence


def main():
    cases = [
        ("위선(정당화 없음)", ["doctrine.monogamy"]),
        ("+ 기적 숭배", ["doctrine.monogamy", "doctrine.miracle_worship"]),
        ("+ 성혼", ["doctrine.monogamy", "doctrine.sacred_union"]),
        ("+ 성혼 + 교주 무오류", ["doctrine.monogamy", "doctrine.sacred_union", "doctrine.infallible_leader"]),
    ]
    print("일부일처 교단, 교주가 아내 4명 (행위: multiple_wives, 증거: 목격)")
    print(f"{'교리 조합':<22}{'독실 신도':>10}{'충성 변화':>10}{'냉소 신도':>10}")
    for name, traits in cases:
        a = reaction(traits, "multiple_wives", "head", ["독실"])
        b = reaction(traits, "multiple_wives", "head", ["냉소"])
        print(f"{name:<22}{a:>10.1f}{-a / 2:>10.1f}{b:>10.1f}")


if __name__ == "__main__":
    main()
