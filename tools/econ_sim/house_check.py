"""계층별 집 분포를 시드 5개로 잰다."""
from collections import Counter, defaultdict
from econ_sim import World, SCENARIOS, HOUSES
import sys
name = sys.argv[1] if len(sys.argv) > 1 else "A"
cfg = dict(SCENARIOS[name]); cfg.pop("desc")
tab = defaultdict(Counter); built = Counter(); downs = sales = 0; rows = []
for sd in range(1, 6):
    w = World(rng_seed=sd, **cfg); w.run(verbose=False)
    for h in w.alive_hhs():
        tab[h.cls][HOUSES[h.house][0]] += 1
    built.update(w.houses_built); downs += w.house_downs; sales += w.house_sales
    rows.append(w.reports[-1])
print(f"시나리오 {name}, 150년 뒤 계층별 집 (시드 5개 합)")
for c in ("지주", "자영농", "소작농", "무산"):
    n = sum(tab[c].values()) or 1
    print(f"  {c:4} n={n:4}  " + "  ".join(f"{k} {tab[c][k] / n:4.0%}" for k in ("노숙", "움막", "가옥", "저택")))
print("지은 집", dict(built), "| 집 매각", sales, "| 낡아 내려앉음", downs)
avg = lambda k: sum(r[k] for r in rows) / len(rows)
print(f"인구 {avg('pop'):.0f}, 지니 {avg('gini'):.2f}, 자영 {avg('자영농'):.0%}, 소작 {avg('소작농'):.0%}, 지주 {avg('지주'):.0%}, 무산 {avg('무산'):.0%}, 굶주림 {avg('hungry'):.0%}")

# 재산 5분위별
q = defaultdict(Counter)
for sd in range(1, 6):
    w = World(rng_seed=sd, **cfg); w.run(verbose=False)
    hs = sorted(w.alive_hhs(), key=lambda h: w.wealth(h) - w.house_value(h))
    n = len(hs)
    for i, h in enumerate(hs):
        q[min(4, i * 5 // n)][HOUSES[h.house][0]] += 1
print("재산 5분위(집 값 제외)별 집")
for k, label in enumerate(["하위 20%", "20~40%", "40~60%", "60~80%", "상위 20%"]):
    n = sum(q[k].values()) or 1
    print(f"  {label:8} " + "  ".join(f"{t} {q[k][t] / n:4.0%}" for t in ("노숙", "움막", "가옥", "저택")))
