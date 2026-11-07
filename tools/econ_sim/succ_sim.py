#!/usr/bin/env python3
"""집단 수장 승계 시뮬레이터 (밸런스 검증용).

15_house_tax_inheritance.md 4절의 승계 규칙별 장단점이
별도 페널티 없이 공통 메커니즘에서 나오는지 확인한다.

공통 메커니즘
  1. 승계 확률 p_i : 규칙이 "지금 수장이 죽으면 i가 이을 확률"을 정한다.
  2. 직위 가치 V_i : 수장 수입 x 남은 재위 기대 연수.
  3. 행동 효용   : 각 행동이 p_i를 얼마나 바꾸는지(Δp) x V_i - 비용 - 위험 - 도덕 비용.
  4. 기대와 원한 : 관습이 정한 기대 몫과 실제 받은 몫의 차이가 원한이 된다.
  5. 충성과 이탈 : 정통성, 호감, 불안기가 봉신 충성을 정하고, 충성이 낮고 힘이 크면 독립한다.

사용 예:
    python3 succ_sim.py                 # 규칙 9종, 각 200회
    python3 succ_sim.py --runs 50 --rule 장자
"""
import argparse
import math
import random

RULES = ["장자", "말자", "분할", "연장자", "가문내선출", "공개선출", "지명", "실력", "신탁"]
PERS = ["야심", "탐욕", "관대", "만족", "잔인", "정직", "독실", "기만"]

# ---------------------------------------------------------------- 수치 (문서 4-5절과 같다)

C = dict(
    years=200,
    vassals=8,
    ruler_domain=40.0,
    vassal_domain=(5.0, 15.0),
    tribute=0.2,              # 봉신 공납 비율
    birth_p=0.25,             # 혼인한 여성 연 출산 확률
    cadet_birth=0.7,          # 땅 없는 방계의 출산 배수
    tenure_cap=25,            # 직위 가치 계산의 최대 재위 연수
    # 암살
    murder_success=0.30,
    detect_if_success=0.35,
    detect_if_fail=0.60,
    executed_if_detected=0.70,
    murder_try=0.15,          # 효용이 양수일 때 그해 실제로 시도할 확률
    # 도덕 비용 (V 단위 = 수장 연수입 x 10 의 백분율)
    moral={"부": 120, "자": 100, "형제": 80, "숙질": 40, "사촌": 20, "남": 5},
    pers_moral={"잔인": 0.3, "야심": 0.7, "기만": 0.8, "탐욕": 0.9, "만족": 1.2,
                "관대": 2.0, "독실": 1.5, "정직": 2.5},
    pers_gain={"야심": 1.5, "탐욕": 1.2, "만족": 0.5},
    # 원한
    grievance_scale=60,       # (기대 몫 - 받은 몫) x 60
    merit_gap=10,             # 능력이 승계자보다 이만큼 높으면 야심가는 몫을 주장
    grievance_decay=5,
    revolt_grievance=40,
    revolt_min_pwin=0.35,
    revolt_try=0.3,
    # 충성과 독립
    indep_loyalty=25,
    indep_power=0.25,
    indep_try=0.3,
    unrest_years=1,
    unrest_loyalty=10,
    # 분쟁
    dispute_ratio=1.5,
    custom_bonus=20,
    devastation=0.92,         # 내전 1회마다 모든 영지 가치 x 0.92
    # 정통성 시작값
    legit={"관습": 60, "선출": 65, "신탁": 80, "실력": 35, "찬탈": 25, "분쟁승리": -15},
    # 기타
    designate_age=50,
    overmighty=40,            # 봉신 힘 / 수장 힘 이 1이면 충성 -40
    personal_share=0.4,       # 직위가 가문을 떠나면 직할령 중 개인 재산으로 남는 몫
    rule_bonus={"장자": 20, "말자": 10, "분할": 20, "연장자": 10, "신탁": 30},
    softmax_T=8.0,
    bribe_like=1.0 / 1.5,     # 뇌물 1.5당 호감 +1
    emigrate_value=0.15,      # 개척지 기대 가치 (V 단위)
)


class P:
    __slots__ = ("id", "male", "born", "alive", "father", "dyn", "pers", "ability", "spirit",
                 "gold", "griev", "favor", "r", "domain", "in_realm", "wife_born", "strength",
                 "rigged", "rig_exposed")

    def __init__(self, pid, male, born, dyn, pers, ability):
        self.id = pid
        self.male = male
        self.born = born
        self.alive = True
        self.father = None
        self.dyn = dyn
        self.pers = pers
        self.ability = ability
        self.spirit = 0.0
        self.gold = 0.0
        self.griev = 0.0
        self.favor = 0.0
        self.r = 0.0
        self.domain = 0.0
        self.in_realm = True
        self.wife_born = None
        self.strength = 0.0
        self.rigged = False
        self.rig_exposed = False


class Sim:
    def __init__(self, rule, seed, **kw):
        self.c = dict(C)
        self.c.update(kw)
        self.rule = rule
        self.rng = random.Random(seed)
        self.year = 0
        self.ps = {}
        self.nid = 0
        self.like = {}            # (봉신 id, 인물 id) -> 호감
        self.vassals = []
        self.ruler = None
        self.D = self.c["ruler_domain"]
        self.legit = 60.0
        self.unrest = 0
        self.designated = None
        self.regent = None
        self.live = []
        self._resolving = False
        self.m = dict(succ=0, acc_age=0.0, no_designation=0, disputed=0, murders=0, attempts=0, executed=0, regency=0,
                      minor_years=0, regent_usurp=0, revolts=0, revolt_win=0, indep=0,
                      emigr=0, ability=0.0, dyn_years=0, bribes=0.0, rigged=0, rig_exposed=0,
                      patricide=0, fratricide=0, war_dead=0)
        self._init()
        self.live = list(self.ps.values())
        self.init_total = self.realm_total()

    # ------------------------------------------------ 초기화

    def new(self, male, born, dyn, father=None, pers=None, ability=None):
        rng = self.rng
        if ability is None:
            base = self.ps[father].ability if father is not None else 50
            ability = max(5, min(95, 0.5 * base + 0.5 * rng.gauss(50, 15)))
        if pers is None:
            if father is not None and rng.random() < 0.4:
                pers = self.ps[father].pers
            else:
                pers = rng.choice(PERS)
        p = P(self.nid, male, born, dyn, pers, ability)
        p.spirit = rng.random()
        p.father = father
        self.ps[p.id] = p
        self.nid += 1
        self.live.append(p)
        return p

    def _init(self):
        rng = self.rng
        founder = self.new(True, -30, 0)
        founder.r = 1.0
        founder.wife_born = -25
        self.ruler = founder.id
        for _ in range(rng.randint(0, 2)):
            k = self.new(rng.random() < 0.5, -rng.randint(0, 4), 0, founder.id)
            k.r = 0.5
        for _ in range(2):   # 수장의 형제
            b = self.new(True, -rng.randint(24, 29), 0)
            b.wife_born = b.born + 4
        for d in range(1, self.c["vassals"] + 1):
            v = self.new(True, -rng.randint(30, 50), d)
            v.domain = rng.uniform(*self.c["vassal_domain"])
            v.wife_born = v.born + 4
            self.vassals.append(v.id)

    # ------------------------------------------------ 보조

    def age(self, p):
        return self.year - p.born

    def R(self):
        return self.ps[self.ruler]

    def realm_total(self):
        return self.D + sum(self.ps[v].domain for v in self.vassals)

    def ruler_income(self):
        trib = sum(self.ps[v].domain * self.loyalty(self.ps[v]) / 100 for v in self.vassals)
        return self.D + self.c["tribute"] * trib

    def V(self, p):
        """직위 가치: 수장 수입 x 남은 재위 기대 연수."""
        yrs = min(self.c["tenure_cap"], max(3, 65 - self.age(p)))
        return self.ruler_income() * yrs

    def Vunit(self):
        return self.ruler_income() * 10

    def power(self, p):
        if p.id == self.ruler:
            return self.D + p.gold / 10 + p.strength
        return p.domain + p.gold / 10 + p.strength

    def lk(self, v, p):
        key = (v, p)
        if key not in self.like:
            base = 15 if self.ps[v].dyn == self.ps[p].dyn else 0
            self.like[key] = base + self.rng.uniform(-20, 20)
        return self.like[key]

    def loyalty(self, v):
        L = 50 + 0.5 * (self.legit - 50) + 0.5 * self.lk(v.id, self.ruler) - v.griev / 2
        # 힘이 수장에 가까운 봉신일수록 덜 굽힌다
        rp = self.power(self.R())
        L -= self.c["overmighty"] * min(1.0, self.power(v) / rp if rp > 0 else 1.0)
        if self.unrest > 0:
            L -= self.c["unrest_loyalty"]
        return max(0.0, min(100.0, L))

    def ruling_dyn(self):
        return self.R().dyn

    def kin_close(self):
        """수장 할아버지의 부계 남성 후손(3대까지) 중 왕국 안에 사는 성인 직전 남성."""
        r = self.R()
        anc = r
        for _ in range(2):
            if anc.father is not None and anc.father in self.ps:
                anc = self.ps[anc.father]
        out = []
        for p in self.live:
            if not (p.alive and p.male and p.in_realm and p.dyn == r.dyn):
                continue
            q, d = p, 0
            while q is not None and d <= 3:
                if q.id == anc.id:
                    out.append(p)
                    break
                q = self.ps.get(q.father)
                d += 1
        if r.dyn == 0 and not out:
            out = [p for p in self.live if p.alive and p.male and p.in_realm and p.dyn == 0]
        return out

    def sons(self, pid):
        return [p for p in self.live if p.alive and p.male and p.in_realm and p.father == pid]

    def relation(self, a, b):
        if a.father == b.id:
            return "부"
        if b.father == a.id:
            return "자"
        if a.father is not None and a.father == b.father:
            return "형제"
        fa = self.ps.get(a.father)
        fb = self.ps.get(b.father)
        if (fa and fa.father is not None and fa.father == b.father) or (fb and fb.father is not None and fb.father == a.father):
            return "숙질"
        if fa and fb and fa.father is not None and fa.father == fb.father:
            return "사촌"
        if a.dyn == b.dyn:
            return "사촌"
        return "남"

    # ------------------------------------------------ 승계 확률

    def softmax(self, items, T=None):
        T = T or self.c["softmax_T"]
        if not items:
            return {}
        mx = max(s for _, s in items)
        ws = [(i, math.exp((s - mx) / T)) for i, s in items]
        tot = sum(w for _, w in ws)
        return {i: w / tot for i, w in ws}

    def order_primo(self, youngest=False, exclude=None):
        """장자/말자 순위: 수장의 아들 → 형제 → 조카 → 가문 성인 남성."""
        ex = exclude or set()
        r = self.R()
        sons = sorted((p for p in self.sons(r.id) if p.id not in ex), key=lambda p: p.born, reverse=youngest)
        if sons:
            return sons
        kin = [p for p in self.kin_close() if p.id != r.id and p.id not in ex]
        kin.sort(key=lambda p: (self.relation(p, r) != "형제", p.born))
        return kin

    def probs(self, exclude=None):
        """지금 수장이 죽으면 각자 이을 확률."""
        ex = set(exclude or ())
        r = self.R()
        rule = self.rule
        if rule in ("장자", "분할"):
            o = self.order_primo(False, ex)
            return {o[0].id: 1.0} if o else {}
        if rule == "말자":
            o = self.order_primo(True, ex)
            return {o[0].id: 1.0} if o else {}
        if rule == "연장자":
            o = [p for p in self.kin_close() if p.id != r.id and p.id not in ex and self.age(p) >= 16]
            if not o:
                o = self.order_primo(False, ex)
            o.sort(key=lambda p: p.born)
            return {o[0].id: 1.0} if o else {}
        if rule == "지명":
            cands = [p for p in self.sons(r.id) if p.id not in ex] or \
                    [p for p in self.kin_close() if p.id != r.id and p.id not in ex]
            if not cands:
                return {}
            if self.designated is None and self._resolving:
                # 지명 없이 급사: 성인 친족 사이 실력 승계
                adults = [p for p in self.kin_close() if p.id != r.id and p.id not in ex and self.age(p) >= 16]
                if adults:
                    st = {p.id: max(0.1, self.power(p) + self.supporters(p)) ** 2 for p in adults}
                    tot = sum(st.values())
                    return {k: v / tot for k, v in st.items()}
            if self.designated in [p.id for p in cands]:
                d = 0.85 if self.legit >= 50 else 0.5
                rest = self.softmax([(p.id, 0.6 * p.ability + 0.4 * p.favor) for p in cands if p.id != self.designated])
                out = {k: v * (1 - d) for k, v in rest.items()}
                out[self.designated] = d if rest else 1.0
                return out
            return self.softmax([(p.id, 0.6 * p.ability + 0.4 * p.favor) for p in cands])
        if rule in ("가문내선출", "공개선출"):
            cands = [p for p in self.kin_close() if p.id != r.id and p.id not in ex and self.age(p) >= 16]
            if rule == "공개선출":
                cands += [self.ps[v] for v in self.vassals if v not in ex and self.ps[v].pers in ("야심", "탐욕")]
            if not cands:
                o = self.order_primo(False, ex)
                return {o[0].id: 1.0} if o else {}
            share = {p.id: 0.0 for p in cands}
            totw = 0.0
            for v in self.vassals:
                vp = self.ps[v]
                w = vp.domain + vp.gold / 10
                totw += w
                items = []
                for p in cands:
                    s = 0.5 * p.ability + 0.3 * self.lk(v, p.id)
                    if p.id == v:
                        s += 30
                    items.append((p.id, s))
                for k, pr in self.softmax(items).items():
                    share[k] += w * pr
            # 득표율을 승리 확률로: 득표율^3 정규화
            if totw <= 0:
                return {k: 1.0 / len(share) for k in share}
            tot = sum(s ** 3 for s in share.values()) or 1
            return {k: (s ** 3) / tot for k, s in share.items()}
        if rule == "실력":
            cands = [p for p in self.kin_close() if p.id != r.id and p.id not in ex and self.age(p) >= 16]
            cands += [self.ps[v] for v in self.vassals if v not in ex and self.ps[v].pers == "야심"]
            if not cands:
                o = self.order_primo(False, ex)
                return {o[0].id: 1.0} if o else {}
            st = {p.id: max(0.1, self.power(p) + self.supporters(p)) ** 2 for p in cands}
            tot = sum(st.values())
            return {k: s / tot for k, s in st.items()}
        if rule == "신탁":
            cands = [p for p in self.sons(r.id) if p.id not in ex] or \
                    [p for p in self.kin_close() if p.id != r.id and p.id not in ex]
            if not cands:
                return {}
            w = {p.id: (1 + 2 * p.spirit) * (3 if p.rigged and not p.rig_exposed else 1) for p in cands}
            tot = sum(w.values())
            return {k: x / tot for k, x in w.items()}
        return {}

    def supporters(self, p):
        """p를 수장보다 좋아하는 봉신의 힘 x 0.5."""
        s = 0.0
        for v in self.vassals:
            if v == p.id:
                continue
            if self.lk(v, p.id) > self.lk(v, self.ruler) + 10:
                s += self.ps[v].domain * 0.5
        return s

    # ------------------------------------------------ 해마다

    def step(self):
        self.live = [p for p in self.ps.values() if p.alive]
        self._kin = None
        self.natural_deaths()
        self.births()
        self.vassal_heirs()
        self.actions()
        self.designate()
        self.economy()
        if self.R().alive is False:
            self.succession()
        r = self.R()
        if self.age(r) < 16:
            self.m["minor_years"] += 1
        if r.dyn == 0:
            self.m["dyn_years"] += 1
        self.year += 1

    def mortality(self, a):
        if a < 5:
            return 0.04
        if a < 16:
            return 0.01
        if a < 40:
            return 0.012
        if a < 55:
            return 0.02
        if a < 65:
            return 0.04
        if a < 75:
            return 0.08
        return 0.18

    def kill(self, p):
        if not p.alive:
            return
        p.alive = False
        if p.id in self.vassals:
            self.vassals.remove(p.id)
            heir = self.new(True, self.year - self.rng.randint(18, 35), p.dyn, None)
            heir.domain = p.domain
            heir.r = p.r / 2
            heir.wife_born = heir.born + 3
            for v in self.vassals:
                pass
            self.vassals.append(heir.id)
        if p.id == self.ruler:
            self.succession()

    def natural_deaths(self):
        for p in list(self.live):
            if p.alive and self.rng.random() < self.mortality(self.age(p)):
                self.kill(p)
        if self.regent is not None:
            rg = self.ps.get(self.regent)
            if rg is None or not rg.alive or self.age(self.R()) >= 16:
                self.regent = None

    def births(self):
        rng = self.rng
        for p in list(self.live):
            if not (p.alive and p.male):
                continue
            a = self.age(p)
            if p.wife_born is None:
                if 20 <= a <= 40 and rng.random() < 0.5:
                    p.wife_born = self.year - rng.randint(17, 22)
                continue
            wa = self.year - p.wife_born
            if not (18 <= wa <= 42):
                continue
            bp = self.c["birth_p"]
            if p.domain == 0 and p.id != self.ruler:
                bp *= self.c["cadet_birth"]
            if rng.random() < bp:
                k = self.new(rng.random() < 0.5, self.year, p.dyn, p.id)
                k.r = p.r / 2
                k.in_realm = p.in_realm

    def vassal_heirs(self):
        pass   # kill()에서 처리

    # ------------------------------------------------ 행동

    def actions(self):
        rng = self.rng
        r = self.R()
        actors = [p for p in self.kin_close() if p.id != r.id and self.age(p) >= 14]
        actors += [self.ps[v] for v in self.vassals]
        rng.shuffle(actors)
        base = self.probs()
        for a in actors:
            if not a.alive or not self.R().alive:
                continue
            self.try_murder(a, base)
            if not self.R().alive:
                break
            base = self.probs()
            self.try_spend(a, base)
            self.try_emigrate(a, base)
            self.try_revolt(a, base)
            if not self.R().alive:
                break
            base = self.probs()
        for v in list(self.vassals):
            vp = self.ps[v]
            if vp.alive and self.loyalty(vp) < self.c["indep_loyalty"] and \
                    self.power(vp) >= self.c["indep_power"] * self.power(self.R()) and rng.random() < self.c["indep_try"]:
                self.vassals.remove(v)
                vp.in_realm = False
                self.m["indep"] += 1

    def try_murder(self, a, base):
        """암살 효용 = 성공률 x 이득 - 발각 위험 x 손실 - 도덕 비용."""
        c = self.c
        r = self.R()
        Vu = self.Vunit()
        Va = self.V(a) * c["pers_gain"].get(a.pers, 1.0)
        pa = base.get(a.id, 0.0)
        own_life = (a.domain + 2) * 20 + 0.5 * Vu
        p_det = c["murder_success"] * c["detect_if_success"] + (1 - c["murder_success"]) * c["detect_if_fail"]
        loss = p_det * c["executed_if_detected"] * own_life
        best = None
        targets = [r] + [self.ps[k] for k in base if k != a.id]
        for t in targets:
            if not t.alive or t.id == a.id:
                continue
            if t.id == r.id:
                remain = max(0, 65 - self.age(r))
                gain = pa * Va * min(1.0, remain / 20)
            else:
                pa2 = self.probs(exclude={t.id}).get(a.id, 0.0)
                gain = (pa2 - pa) * Va
            rel = self.relation(a, t)
            moral = c["moral"][rel] / 100 * Vu * c["pers_moral"].get(a.pers, 1.0)
            U = c["murder_success"] * gain - loss - moral
            if U > 0 and (best is None or U > best[0]):
                best = (U, t, rel)
        if best is None or self.rng.random() >= c["murder_try"]:
            return
        U, t, rel = best
        self.m["attempts"] += 1
        ok = self.rng.random() < c["murder_success"]
        det = self.rng.random() < (c["detect_if_success"] if ok else c["detect_if_fail"])
        if ok:
            self.m["murders"] += 1
            if rel == "부":
                self.m["patricide"] += 1
            if rel == "형제":
                self.m["fratricide"] += 1
            if t.id == r.id and self.regent == a.id:
                self.m["regent_usurp"] += 1
            if t.id == self.regent:
                self.regent = None
            self.kill(t)
        if det and a.alive and self.R().alive and self.R().id != a.id:
            if self.rng.random() < c["executed_if_detected"]:
                self.m["executed"] += 1
                self.kill(a)
            else:
                a.in_realm = False

    def try_spend(self, a, base):
        """규칙이 돈으로 p를 올릴 길을 열어 두면 쓴다: 총애(지명), 매수(선출), 병력(실력), 신탁 조작."""
        rule = self.rule
        if a.gold <= 1 or a.id in self.vassals and rule not in ("공개선출", "실력"):
            return
        Va = self.V(a) * self.c["pers_gain"].get(a.pers, 1.0)
        pa = base.get(a.id, 0.0)
        if pa <= 0 and rule not in ("공개선출", "실력"):
            return
        g = a.gold * 0.3
        if rule == "지명" and self.designated is None:
            T = self.c["softmax_T"]
            dp = pa * (1 - pa) * 0.4 / T * (g * 0.5)
            if dp * Va > g:
                a.gold -= g
                a.favor += g * 0.5
                self.R().gold += g
        elif rule in ("가문내선출", "공개선출"):
            if not self.vassals:
                return
            e = max(self.vassals, key=lambda v: self.ps[v].domain)
            if e == a.id:
                return
            old = self.lk(e, a.id)
            self.like[(e, a.id)] = old + g * self.c["bribe_like"]
            pa2 = self.probs().get(a.id, 0.0)
            if (pa2 - pa) * Va > g:
                a.gold -= g
                self.ps[e].gold += g
                self.m["bribes"] += g
            else:
                self.like[(e, a.id)] = old
        elif rule == "실력":
            old = a.strength
            a.strength += g / 5
            pa2 = self.probs().get(a.id, 0.0)
            if (pa2 - pa) * Va > g:
                a.gold -= g
            else:
                a.strength = old
        elif rule == "신탁" and not a.rigged and a.pers in ("야심", "기만", "탐욕") and a.gold >= 30:
            a.rigged = True
            a.gold -= 30
            self.m["rigged"] += 1

    def try_emigrate(self, a, base):
        """이을 가망이 없는 성인 남성은 개척지 가치와 남을 가치를 비교한다."""
        if a.id in self.vassals or a.domain > 0 or not (18 <= self.age(a) <= 35):
            return
        pa = base.get(a.id, 0.0)
        stay = pa * self.V(a) + 2 * 20
        go = self.c["emigrate_value"] * self.Vunit() * (a.ability / 50)
        if a.pers in ("야심", "탐욕"):
            go *= 1.3
        if go > stay and self.rng.random() < 0.2:
            a.in_realm = False
            self.m["emigr"] += 1

    def try_revolt(self, a, base):
        c = self.c
        if a.griev < c["revolt_grievance"]:
            return
        r = self.R()
        pw = self.power(a) + self.supporters(a)
        pr = self.power(r)
        pwin = pw / (pw + pr) if pw + pr > 0 else 0
        if pwin < c["revolt_min_pwin"]:
            return
        Va = self.V(a)
        loss = (a.domain + 2) * 20 + 0.5 * self.Vunit()
        if pwin * Va - (1 - pwin) * loss <= 0 or self.rng.random() >= c["revolt_try"]:
            return
        self.m["revolts"] += 1
        self.devastate()
        if self.rng.random() < pwin:
            self.m["revolt_win"] += 1
            old = r
            self.install(a, "찬탈")
            if self.rng.random() < 0.5:
                old.alive = False
            else:
                old.in_realm = False
        else:
            self.m["war_dead"] += 1
            if self.rng.random() < 0.6:
                self.kill(a)
            else:
                a.in_realm = False

    def devastate(self):
        k = self.c["devastation"]
        self.D *= k
        for v in self.vassals:
            self.ps[v].domain *= k

    def designate(self):
        if self.rule != "지명" or self.designated is not None:
            return
        r = self.R()
        sons = [p for p in self.sons(r.id) if self.age(p) >= 16]
        if sons and (self.age(r) >= self.c["designate_age"] or self.rng.random() < 0.05):
            best = max(sons, key=lambda p: 0.6 * p.ability + 0.4 * p.favor + self.rng.gauss(0, 5))
            self.designated = best.id

    def economy(self):
        r = self.R()
        inc = self.ruler_income()
        r.gold += inc * 0.3
        kin = [p for p in self.kin_close() if p.id != r.id]
        for p in kin:
            p.gold += 2
        for v in self.vassals:
            vp = self.ps[v]
            vp.gold += vp.domain * 0.3
        for p in self.ps.values():
            if p.alive:
                p.griev = max(0.0, p.griev - self.c["grievance_decay"])
        self.legit = min(100.0, self.legit + 1)
        if self.unrest > 0:
            self.unrest -= 1
        if self.rule == "신탁":
            for p in kin:
                if p.rigged and not p.rig_exposed and self.rng.random() < 0.08:
                    p.rig_exposed = True
                    self.m["rig_exposed"] += 1

    # ------------------------------------------------ 승계

    def install(self, p, how):
        c = self.c
        prev = self.R() if self.ruler is not None else None
        self.ruler = p.id
        if p.id in self.vassals:
            self.vassals.remove(p.id)
            self.D += p.domain
            p.domain = 0.0
        self.legit = c["legit"]["관습"] if how == "관습" else c["legit"].get(how, 50)
        if how == "신탁" and p.rig_exposed:
            self.legit -= 40
        self.unrest = c["unrest_years"]
        self.designated = None
        self.m["succ"] += 1
        self.m["ability"] += p.ability
        self.m["acc_age"] += self.age(p)
        for q in self.ps.values():
            q.favor = 0.0
        if self.age(p) < 16:
            self.m["regency"] += 1
            kin = [q for q in self.kin_close() if q.id != p.id and self.age(q) >= 16]
            kin.sort(key=lambda q: (self.relation(q, p) not in ("숙질", "형제"), q.born))
            self.regent = kin[0].id if kin else None

    def succession(self):
        c = self.c
        rng = self.rng
        dead = self.R()
        designated_win_id = self.designated
        if self.rule == "지명" and self.designated is None:
            self.m["no_designation"] += 1
        self._resolving = True
        pr = self.probs()
        self._resolving = False
        if not pr:
            # 가문 단절: 가장 강한 봉신이 차지
            if not self.vassals:
                return
            v = max((self.ps[v] for v in self.vassals), key=self.power)
            self.install(v, "실력")
            return
        keys = list(pr)
        ws = [pr[k] for k in keys]
        if sum(ws) <= 0:
            ws = [1.0] * len(keys)
        winner = self.ps[rng.choices(keys, weights=ws)[0]]
        designated_win = designated_win_id == winner.id
        how = {"가문내선출": "선출", "공개선출": "선출", "신탁": "신탁", "실력": "실력"}.get(self.rule, "관습")
        # 기대와 원한: 관습상 기대 몫(=승계 전 확률, 야심가는 능력 차로 몫 주장) - 받은 몫
        sons = self.sons(dead.id)
        for k, p0 in pr.items():
            q = self.ps[k]
            if q.id == winner.id:
                continue
            expect = p0
            if self.rule == "분할" and q in sons:
                expect = 0.0   # 분할에서는 몫을 받는다
            if q.pers == "야심" and q.ability > winner.ability + c["merit_gap"]:
                expect = max(expect, 0.5)
            if self.rule == "신탁" and q.pers == "독실":
                expect *= 0.3
            q.griev += c["grievance_scale"] * expect
        # 계승 분쟁: 1위 주장 강도가 2위의 1.5배 미만이면 내전
        ranked = sorted(pr.items(), key=lambda kv: -kv[1])
        runner = next((self.ps[k] for k, _ in ranked if k != winner.id), None)
        if runner is not None:
            def claim(p, is_winner):
                s = 50 if is_winner else 30
                if is_winner and how == "관습":
                    s += c["custom_bonus"]
                if is_winner:
                    s += c["rule_bonus"].get(self.rule, 0)
                    if self.rule == "지명" and designated_win:
                        s += 40 + self.legit / 2
                    if self.rule == "신탁" and p.rig_exposed:
                        s -= 40
                if self.rule in ("가문내선출", "공개선출", "실력") or (self.rule == "지명" and not designated_win):
                    s += 100 * pr.get(p.id, 0)
                tot = sum(self.ps[v].domain for v in self.vassals) or 1
                s += 100 * self.supporters(p) * 2 / tot
                s += p.ability / 10
                return s
            cw, cr = claim(winner, True), claim(runner, False)
            if runner.pers in ("야심", "잔인") and cw < c["dispute_ratio"] * cr:
                self.m["disputed"] += 1
                self.devastate()
                pw = self.power(winner) + self.supporters(winner)
                prr = self.power(runner) + self.supporters(runner)
                if rng.random() < prr / (pw + prr + 1e-9):
                    winner, runner = runner, winner
                self.m["war_dead"] += 1
                if rng.random() < 0.6:
                    runner.alive = False
                else:
                    runner.in_realm = False
                self.install(winner, how)
                self.legit += c["legit"]["분쟁승리"]
                self.personal_split(dead, winner)
                self.split_if_needed(dead, winner)
                return
        self.install(winner, how)
        self.personal_split(dead, winner)
        self.split_if_needed(dead, winner)

    def personal_split(self, dead, winner):
        """직위가 죽은 수장의 자식 밖으로 가면, 직할령 일부는 자식의 개인 재산으로 남는다(4-1)."""
        if self.rule == "분할":
            return
        sons = sorted(self.sons(dead.id), key=lambda p: p.born)
        if not sons or winner in sons:
            return
        heir = sons[0]
        share = self.D * self.c["personal_share"]
        self.D -= share
        heir.domain += share
        if heir.id not in self.vassals:
            self.vassals.append(heir.id)

    def split_if_needed(self, dead, winner):
        """분할: 수장의 아들들이 직할령을 똑같이 나누고, 맏이 아닌 아들은 봉신이 된다."""
        if self.rule != "분할":
            return
        sons = [p for p in self.sons(dead.id)]
        if len(sons) <= 1 or winner not in sons:
            return
        share = self.D / len(sons)
        self.D = share
        for s in sons:
            if s.id == winner.id:
                continue
            s.domain = share
            self.vassals.append(s.id)
            self.like[(s.id, winner.id)] = 30 + self.rng.uniform(-10, 10)

    # ------------------------------------------------ 실행

    def run(self):
        for _ in range(self.c["years"]):
            self.step()
        m = dict(self.m)
        m["retention"] = self.realm_total() / self.init_total
        rp = self.power(self.R())
        m["conc"] = rp / max(1e-9, rp + sum(self.power(self.ps[v]) for v in self.vassals))
        m["acc_age"] = m["acc_age"] / max(1, m["succ"])
        m["blood"] = sum(p.r for p in self.ps.values() if p.alive) * 100
        m["ability"] = m["ability"] / max(1, m["succ"])
        m["dyn_years"] = m["dyn_years"] / self.c["years"]
        return m


def compare(runs, rules, years):
    keys = [("succ", "승계 수", "{:.1f}"), ("disputed", "내전 승계", "{:.2f}"),
            ("attempts", "암살 시도", "{:.2f}"), ("murders", "암살 성공", "{:.2f}"),
            ("fratricide", "형제 살해", "{:.2f}"), ("patricide", "부친 살해", "{:.2f}"),
            ("regency", "미성년 승계", "{:.2f}"), ("regent_usurp", "섭정 찬탈", "{:.2f}"),
            ("revolts", "반란", "{:.2f}"), ("indep", "봉신 독립", "{:.2f}"),
            ("emigr", "개척 이주", "{:.2f}"), ("ability", "수장 능력", "{:.1f}"),
            ("acc_age", "즉위 나이", "{:.1f}"), ("no_designation", "지명 없이 사망", "{:.2f}"),
            ("conc", "권력 집중도", "{:.0%}"), ("retention", "영토 유지", "{:.0%}"),
            ("dyn_years", "시조 가문 집권", "{:.0%}"), ("blood", "혈통 점수", "{:.0f}"),
            ("bribes", "뇌물 총액", "{:.0f}"), ("rigged", "신탁 조작", "{:.2f}")]
    res = {}
    for rule in rules:
        acc = {}
        for sd in range(runs):
            m = Sim(rule, sd, years=years).run()
            for k, _, _ in keys:
                acc[k] = acc.get(k, 0) + m[k]
        res[rule] = {k: v / runs for k, v in acc.items()}
    head = f"{'':<14}" + "".join(f"{r:>9}" for r in rules)
    print(head)
    for k, name, fmt in keys:
        print(f"{name:<12}" + "".join(f"{fmt.format(res[r][k]):>9}" for r in rules))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=200)
    ap.add_argument("--years", type=int, default=200)
    ap.add_argument("--rule", default=None)
    a = ap.parse_args()
    rules = [a.rule] if a.rule else RULES
    print(f"규칙별 평균 ({a.runs}회 x {a.years}년)")
    compare(a.runs, rules, a.years)


if __name__ == "__main__":
    main()
