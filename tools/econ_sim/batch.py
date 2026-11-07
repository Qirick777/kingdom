"""여러 시드로 시나리오를 돌려 주요 지표를 모은다."""
import sys
from collections import Counter
from econ_sim import World, SCENARIOS, CLASS_TIER

def run(name, seeds=range(1, 6), at=(50, 100, 150)):
    cfg = dict(SCENARIOS[name]); cfg.pop("desc")
    rows = []
    for sd in seeds:
        w = World(rng_seed=sd, **cfg)
        w.run(verbose=False)
        by = {r["year"]: r for r in w.reports}
        mob = w.mobility
        moved = sum(1 for a, b in mob if CLASS_TIER[a] != CLASS_TIER[b]) / max(1, len(mob))
        surv = {c: w.surv_by_class[c] / max(1, w.births_by_class[c]) for c in ("지주", "자영농", "소작농", "무산")}
        rows.append((sd, by, moved, surv, w))
    return rows

if __name__ == "__main__":
    names = sys.argv[1:] or ["A"]
    for name in names:
        print(f"\n=== {name}: {SCENARIOS[name]['desc']} ===")
        rows = run(name, at=None)
        years = sorted(rows[0][1])
        pick = [y for y in years if y in (30, 50, 80, 100, 150, 160, 170, 180)]
        for y in pick:
            vals = [r[1][y] for r in rows if y in r[1]]
            avg = lambda k: sum(v[k] for v in vals) / len(vals)
            print(f"{y:>4}년 인구 {avg('pop'):5.0f} 자영 {avg('자영농'):4.0%} 소작 {avg('소작농'):4.0%} 지주 {avg('지주'):4.0%} "
                  f"무산 {avg('무산'):4.0%} 지니 {avg('gini'):.2f} 소작료 {avg('rent'):4.0%} 굶주림 {avg('hungry'):4.0%} 상위10%땅 {avg('top10_land'):4.0%}")
        print(f"이동률 평균 {sum(r[2] for r in rows)/len(rows):.0%}  |  15세 생존율 " +
              ", ".join(f"{c} {sum(r[3][c] for r in rows)/len(rows):.0%}" for c in ("지주", "자영농", "소작농", "무산")))
