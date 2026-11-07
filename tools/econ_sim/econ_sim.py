#!/usr/bin/env python3
"""경제 시뮬레이터 (밸런스 검증용).

docs/design/14_property_and_class.md, 15_house_tax_inheritance.md 의 규칙을
연 단위로 돌려서 계층이 생기는지, 수치가 맞물리는지 확인한다.
게임 코드가 아니다. 표준 라이브러리만 쓴다.

사용 예:
    python3 econ_sim.py --scenario A
    python3 econ_sim.py --scenario all
"""
import argparse
import math
import random
from collections import Counter, defaultdict

# ---------------------------------------------------------------- 상수

ADULT_FOOD = 48
CHILD_FOOD = 24
ELDER_FOOD = 40
WEATHER = [(0.20, 1.3, "풍년"), (0.55, 1.0, "평년"), (0.20, 0.6, "흉년"), (0.05, 0.3, "대흉년")]
E_WEATHER = sum(p * m for p, m, _ in WEATHER)

# 지형: (수확 배수, 개간 노동(주), 경작 가능 비율, 채집 산출/년)
TERRAIN = {
    "평야": (1.5, 8, 0.9, 1.0),
    "강변": (1.69, 8, 0.8, 1.0),   # 강변 1.3 x 비옥함 1.3
    "숲": (1.3, 24, 0.9, 3.0),     # 개간 뒤 배수
    "구릉": (0.8, 16, 0.6, 1.0),
}

# 집: 등급 -> (이름, 재료비(곡식 환산), 노동(인·주, 장인 포함), 수용, 곡식 연 손실률, 위신, 연 유지비)
# 15_house_tax_inheritance.md 1절. 저택 = 지주 소작료 약 1.5년치, 왕궁 = 나라 세수 몇 년치
HOUSES = {
    0: ("노숙", 0, 0, 0, 0.30, -20, 0),
    1: ("움막", 10, 2, 4, 0.10, -5, 1),
    2: ("가옥", 40, 8, 6, 0.05, 5, 2),
    3: ("저택", 1000, 290, 12, 0.02, 20, 26),
    4: ("왕궁", 14800, 4350, 40, 0.01, 60, 380),
}
COLD = {0: 4.0, 1: 1.0, 2: 0.0, 3: 0.0, 4: 0.0}   # 1인당 연 추위 비용(곡식 환산)
PAYBACK = {"탐욕": 6, "야심": 15}                  # 회수 한도(년). 나머지 10
FACE = {"야심": 1.5, "만족": 0.7}                   # 체면 계수. 나머지 1.0

PERSONALITIES = ["탐욕", "관대", "근면", "야심", "만족", "독실"]
CLASS_TIER = {"무산": 0, "소작농": 1, "자영농": 2, "지주": 3}


DEFAULT = dict(
    years=150,
    households=30,
    start_plots=4,
    start_grain=60,
    start_house=1,
    region={"평야": 256, "강변": 64, "숲": 192, "구릉": 64},
    cap_per_adult=2,        # 하급 도구 1인 2필지
    base_yield=40,
    seed_per_plot=8,
    tithe=0.0,
    tax=0.0,
    inherit="균분",          # 균분, 장자, 장자우대
    interest=0.30,
    rent_cap=0.5,           # 관습 반타작. 농노제면 0.7
    flight_floor=0.3,       # 도주, 이주, 도적질로 얻는 바깥 선택지(순수확 대비)
    pre_gift=True,          # 혼인 때 생전 분재
    usury_ban=False,
    birth_p=0.32,           # 연간 임신 확률 (수유 중 제외)
    emigrate_p=0.3,         # 땅 없이 2년 연속 굶은 가구가 지역을 떠날 확률
    hire_share=0.25,        # 잉여 중 물건과 일손(의류, 품팔이, 머슴)에 쓰는 비율
    infant_survival=0.85,
    forage_cap=72,
    tool_upkeep=6,
    plague_year=None,
    plague_frac=0.4,
    rng_seed=1,
    report_every=10,
)


# ---------------------------------------------------------------- 자료형

class Person:
    __slots__ = ("id", "sex", "born", "alive", "father", "mother", "spouse",
                 "hh", "pers", "r", "class15", "birth_class", "nursing")

    def __init__(self, pid, sex, born, pers):
        self.id = pid
        self.sex = sex
        self.born = born
        self.alive = True
        self.father = None
        self.mother = None
        self.spouse = None
        self.hh = None
        self.pers = pers
        self.r = {}
        self.class15 = None
        self.birth_class = None
        self.nursing = -10


class Household:
    __slots__ = ("id", "head", "members", "plots", "grain", "house", "loans",
                 "alive", "labor", "cap", "farm", "rented_out", "forage_labor",
                 "hunger", "food_ratio", "bonded", "clients", "cls", "spare", "hunger_years",
                 "upkeep_miss", "keep_bad")

    def __init__(self, hid):
        self.id = hid
        self.head = None
        self.members = set()
        self.plots = set()
        self.grain = 0.0
        self.house = 1
        self.loans = []          # [lender_hid, principal, rate, missed]
        self.alive = True
        self.labor = 0.0
        self.cap = 0.0
        self.farm = []           # 이번 해 경작 필지(자기 땅 + 빌린 땅)
        self.rented_out = 0
        self.forage_labor = 0.0
        self.hunger = False
        self.food_ratio = 1.0
        self.bonded = 0
        self.clients = 0
        self.cls = "자영농"
        self.spare = 0.0
        self.hunger_years = 0
        self.upkeep_miss = 0
        self.keep_bad = 0


class Plot:
    __slots__ = ("id", "terrain", "arable", "state", "owner", "operator", "rent")

    def __init__(self, pid, terrain, arable):
        self.id = pid
        self.terrain = terrain
        self.arable = arable
        self.state = "숲" if terrain == "숲" else "황무지"
        if not arable:
            self.state = "불모"
        self.owner = None
        self.operator = None
        self.rent = 0.0


# ---------------------------------------------------------------- 세계

class World:
    def __init__(self, **kw):
        self.p = dict(DEFAULT)
        self.p.update(kw)
        self.rng = random.Random(self.p["rng_seed"])
        self.year = 0
        self.persons = {}
        self.hhs = {}
        self.plots = []
        self.next_pid = 0
        self.next_hid = 0
        self.rent_frac = 0.3
        self.forage_rate = self.p["forage_cap"]
        self.weather_log = []
        self.tax_total = 0.0
        self.tithe_total = 0.0
        self.church_gifts = 0.0
        self.births_by_class = Counter()
        self.surv_by_class = Counter()
        self.child_track = {}    # pid -> 출생 계층
        self.mobility = []       # (class15, class30)
        self.seizures = 0
        self.emigrants = 0
        self.wages_paid = 0.0
        self.house_downs = 0
        self.house_sales = 0
        self.sales = 0
        self.houses_built = Counter()
        self.reports = []
        self._init_world()

    # ---------------- 초기화

    def _new_person(self, sex, born, pers=None):
        pid = self.next_pid
        self.next_pid += 1
        p = Person(pid, sex, born, pers or self.rng.choice(PERSONALITIES))
        self.persons[pid] = p
        return p

    def _new_hh(self):
        hid = self.next_hid
        self.next_hid += 1
        h = Household(hid)
        self.hhs[hid] = h
        return h

    def _init_world(self):
        rng = self.rng
        for terrain, n in self.p["region"].items():
            frac = TERRAIN[terrain][2]
            for _ in range(n):
                self.plots.append(Plot(len(self.plots), terrain, rng.random() < frac))
        plains = [pl for pl in self.plots if pl.terrain == "평야" and pl.arable]
        rng.shuffle(plains)
        for k in range(self.p["households"]):
            h = self._new_hh()
            h.grain = self.p["start_grain"]
            h.house = self.p["start_house"]
            m = self._new_person("M", -rng.randint(22, 40))
            f = self._new_person("F", -rng.randint(18, 34))
            m.spouse, f.spouse = f.id, m.id
            m.r = {k: 1.0}
            f.r = {k: 1.0}
            for p in (m, f):
                p.hh = h.id
                h.members.add(p.id)
            h.head = m.id
            for _ in range(rng.randint(0, 3)):
                c = self._new_person(rng.choice("MF"), -rng.randint(0, 8))
                c.father, c.mother = m.id, f.id
                c.r = {k: 1.0}
                c.hh = h.id
                h.members.add(c.id)
            for _ in range(self.p["start_plots"]):
                pl = plains.pop()
                pl.state = "경작지"
                pl.owner = h.id
                h.plots.add(pl.id)

    # ---------------- 보조 계산

    def age(self, p):
        return self.year - p.born

    def net_expected(self, pl):
        return self.p["base_yield"] * TERRAIN[pl.terrain][0] * E_WEATHER - self.p["seed_per_plot"]

    def plot_price(self, pl):
        return max(0.2, self.rent_frac) * self.net_expected(pl) * 15

    def house_value(self, h):
        return HOUSES[h.house][1] + HOUSES[h.house][2]

    def wealth(self, h):
        return (sum(self.plot_price(self.plots[i]) for i in h.plots)
                + h.grain + self.house_value(h)
                - sum(l[1] for l in h.loans))

    def living(self, h):
        return [self.persons[i] for i in h.members if self.persons[i].alive]

    def labor_of(self, h):
        tot = 0.0
        for p in self.living(h):
            a = self.age(p)
            if 16 <= a < 60:
                tot += 1.0
            elif 10 <= a < 16:
                tot += 0.5
            elif a >= 60:
                tot += 0.3
        if h.bonded > 0:
            tot *= 0.7     # 채무 노역: 노동 30%를 채권자에게
        return tot

    def need_of(self, h):
        n = 0.0
        for p in self.living(h):
            a = self.age(p)
            n += CHILD_FOOD if a < 16 else (ELDER_FOOD if a >= 60 else ADULT_FOOD)
        return n

    def seed_target(self, h):
        """다음 해 종자로 남겨 둘 곡식: 지금 가진 땅과 노동으로 경작할 수 있는 만큼."""
        own = sum(1 for i in h.plots if self.plots[i].state == "경작지")
        plots = max(own, len(h.farm))
        return min(plots, int(self.labor_of(h) * self.p["cap_per_adult"])) * self.p["seed_per_plot"]

    def house_cost(self, t):
        return HOUSES[t][1] + HOUSES[t][2]

    def house_gain(self, h, frm, to, stock):
        """H1: 집을 frm에서 to로 바꿀 때 연 이득(곡식 환산)."""
        members = self.living(h)
        m = len(members)
        storage = stock * (HOUSES[frm][4] - HOUSES[to][4])
        crowd = (max(0, m - HOUSES[frm][3]) - max(0, m - HOUSES[to][3])) * 10
        cold = m * (COLD[frm] - COLD[to])
        head = self.persons.get(h.head)
        marriageable = sum(1 for x in members if 14 <= self.age(x) <= 25 and x.spouse is None
                           and head and (x.father == head.id or x.mother == head.id))
        face = FACE.get(self.head_pers(h), 1.0)
        stage = CLASS_TIER.get(h.cls, 1)
        prestige = (HOUSES[to][5] - HOUSES[frm][5]) * 2 * face * (1 + stage / 3) * (1 + 0.5 * min(2, marriageable))
        upkeep = HOUSES[to][6] - HOUSES[frm][6]
        return storage + crowd + cold + prestige - upkeep

    def house_decision(self, h, reserve):
        """H1: 한 등급 위를 따져 회수 기간 안에 들면 짓는다. 쓴 곡식(품삯과 재료비)을 돌려준다."""
        frm = h.house
        to = frm + 1
        if to > 3:
            return 0.0
        cost = self.house_cost(to) - 0.3 * self.house_cost(frm)
        liquid = h.grain - reserve - self.need_of(h)   # 흉년 대비로 2년치 식량을 남긴다
        if liquid < cost:
            return 0.0
        gain = self.house_gain(h, frm, to, h.grain - cost)
        limit = PAYBACK.get(self.head_pers(h), 10)
        if gain <= 0 or cost / gain > limit:
            return 0.0
        h.grain -= cost
        h.house = to
        self.houses_built[HOUSES[to][0]] += 1
        return cost

    def house_keep_ok(self, h):
        """H2: 지금 집이 한 등급 아래보다 주는 연 이득이 보유 비용(팔면 받을 돈의 10%)을 넘는가."""
        frm = h.house
        if frm < 2:
            return True
        proceeds = 0.5 * (self.house_cost(frm) - self.house_cost(frm - 1))
        return self.house_gain(h, frm - 1, frm, h.grain) >= 0.10 * proceeds

    def head_pers(self, h):
        hp = self.persons.get(h.head)
        return hp.pers if hp else "만족"

    def alive_hhs(self):
        return [h for h in self.hhs.values() if h.alive]

    # ---------------- 봄: 경작 배분, 소작 시장, 개간

    def spring(self):
        p = self.p
        cap_pa = p["cap_per_adult"]
        offered = []
        for h in self.alive_hhs():
            h.labor = self.labor_of(h)
            h.cap = h.labor * cap_pa
            h.farm = []
            h.rented_out = 0
            own = sorted((self.plots[i] for i in h.plots if self.plots[i].state == "경작지"),
                         key=self.net_expected, reverse=True)
            k = min(len(own), int(h.cap + 1e-9))
            for pl in own[:k]:
                pl.operator = h.id
                pl.rent = 0.0
                h.farm.append(pl.id)
            for pl in own[k:]:
                pl.operator = None
                offered.append(pl)
            h.spare = h.cap - k

        # 개간: 무주지가 있으면 소작보다 먼저 자기 땅을 연다
        free = [pl for pl in self.plots if pl.state in ("황무지", "숲")]
        free.sort(key=lambda pl: self.net_expected(pl) / TERRAIN[pl.terrain][1], reverse=True)
        fi = 0
        for h in self.alive_hhs():
            h.forage_labor = 0.0
            spare_labor = h.labor - len(h.farm) / cap_pa
            extra = 2 if self.head_pers(h) in ("탐욕", "야심", "근면") else 0
            target = math.ceil(h.cap) + extra
            while spare_labor > 0 and len(h.plots) < target and fi < len(free):
                pl = free[fi]
                cost = TERRAIN[pl.terrain][1] / 48
                if cost > spare_labor:
                    break
                fi += 1
                spare_labor -= cost
                pl.state = "경작지"
                pl.owner = h.id
                h.plots.add(pl.id)
            h.spare = spare_labor * cap_pa

        # 소작 협상 (14_property_and_class.md 7-4)
        demand = [h for h in self.alive_hhs() if h.spare >= 1]
        total_demand = sum(int(h.spare) for h in demand)
        ref = self.plots[0]
        n_ref = self.net_expected(ref) if ref.terrain == "평야" else 48
        free_open = [pl for pl in self.plots if pl.state == "황무지"]
        free_forest = [pl for pl in self.plots if pl.state == "숲"]
        if free_open:
            clear_alt = 0.6 * max(self.net_expected(pl) for pl in free_open)
        elif free_forest:
            clear_alt = 0.35 * self.net_expected(free_forest[0])
        else:
            clear_alt = 0.0
        o_t = max(clear_alt, self.forage_rate / cap_pa, p["flight_floor"] * n_ref)
        p_find = min(1.0, total_demand / max(1, len(offered)))
        o_l = p_find * 0.5 * n_ref
        share = o_t + (n_ref - o_t - o_l) * 0.5
        rent = min(p["rent_cap"] * n_ref, max(0.1 * n_ref, n_ref - share))
        if offered:
            self.rent_frac = rent / n_ref

        offered.sort(key=self.net_expected, reverse=True)
        self.rng.shuffle(demand)
        demand.sort(key=lambda h: (not h.hunger, len(h.plots)))
        it = iter(offered)
        for h in demand:
            want = int(h.spare)
            while want > 0:
                pl = next(it, None)
                if pl is None:
                    break
                pl.operator = h.id
                pl.rent = self.rent_frac
                h.farm.append(pl.id)
                self.hhs[pl.owner].rented_out += 1
                want -= 1
                h.spare -= 1
        for pl in it:
            pl.operator = None

        for h in self.alive_hhs():
            h.forage_labor = max(0.0, h.spare / cap_pa)   # 남은 노동은 채집

        pool = sum(TERRAIN[pl.terrain][3] for pl in self.plots if pl.state in ("황무지", "숲", "불모"))
        flabor = sum(h.forage_labor for h in self.alive_hhs())
        self.forage_rate = min(p["forage_cap"], pool * 2.0 / max(1e-6, flabor))

        # 종자
        for h in self.alive_hhs():
            need_seed = len(h.farm) * p["seed_per_plot"]
            if h.grain < need_seed:
                self.borrow(h, need_seed - h.grain)
            while h.farm and h.grain < len(h.farm) * p["seed_per_plot"]:
                pid = h.farm.pop()           # 종자가 없으면 휴경
                pl = self.plots[pid]
                if pl.owner != h.id:
                    self.hhs[pl.owner].rented_out -= 1
                pl.operator = None
                h.forage_labor += 1 / cap_pa  # 남는 노동은 채집으로
            h.grain -= len(h.farm) * p["seed_per_plot"]

        for h in self.alive_hhs():
            self.classify(h)

    def classify(self, h):
        own_farmed = sum(1 for i in h.farm if self.plots[i].owner == h.id)
        rented_in = len(h.farm) - own_farmed
        if h.rented_out >= 2 and h.rented_out >= own_farmed:
            h.cls = "지주"
        elif len(h.plots) >= 1 and rented_in <= len(h.plots):
            h.cls = "자영농"
        elif rented_in >= 1:
            h.cls = "소작농"
        else:
            h.cls = "무산"

    # ---------------- 대여

    def lenders(self):
        out = []
        for h in self.alive_hhs():
            lendable = h.grain - 1.5 * self.need_of(h)
            if lendable <= 5:
                continue
            pers = self.head_pers(h)
            if self.p["usury_ban"]:
                if pers in ("관대", "독실"):
                    out.append((h, lendable))
            elif pers == "탐욕" or self.rng.random() < 0.5:
                out.append((h, lendable))
        out.sort(key=lambda x: -x[1])
        return out

    def credit_limit(self, h):
        coll = sum(self.plot_price(self.plots[i]) for i in h.plots) * 0.5 + self.house_value(h) * 0.5 + 40
        return coll - sum(l[1] for l in h.loans)

    def borrow(self, h, amount):
        amount = min(amount, max(0.0, self.credit_limit(h)))
        got = 0.0
        if amount <= 0:
            return 0.0
        rate = 0.0 if self.p["usury_ban"] else self.p["interest"]
        for lh, lendable in self.lenders():
            if lh.id == h.id:
                continue
            x = min(lendable, amount - got)
            if x <= 0:
                break
            lh.grain -= x
            h.grain += x
            h.loans.append([lh.id, x, rate, 0])
            got += x
            if got >= amount - 1e-6:
                break
        return got

    def settle_loans(self, h):
        keep = []
        for loan in h.loans:
            lid, principal, rate, missed = loan
            lender = self.hhs.get(lid)
            due = principal * (1 + rate)
            pay = min(due, max(0.0, h.grain))
            h.grain -= pay
            if lender and lender.alive:
                lender.grain += pay
            rest = due - pay
            if rest <= 0.5:
                continue
            missed += 1
            if missed >= 2:
                rest = self.seize(h, lender, rest)
                if rest <= 0.5:
                    continue
                if self.p["usury_ban"]:
                    if lender:
                        lender.clients += 1   # 땅 대신 사람이 넘어간다
                    continue
                h.bonded = 5                    # 채무 노역
                continue
            keep.append([lid, rest, rate, missed])
        h.loans = keep

    def seize(self, h, lender, rest):
        if lender is None or not lender.alive or self.p["usury_ban"]:
            return rest
        plots = sorted((self.plots[i] for i in h.plots), key=self.net_expected, reverse=True)
        for pl in plots:
            if rest <= 0.5:
                break
            price = self.plot_price(pl)
            self.transfer_plot(pl, lender)
            rest -= price
            self.seizures += 1
        if rest > 0.5 and h.house >= 2:
            rest -= self.house_value(h) * 0.6
            h.house = 1
        return max(0.0, rest)

    def transfer_plot(self, pl, new_h):
        old = self.hhs.get(pl.owner)
        if old:
            old.plots.discard(pl.id)
        pl.owner = new_h.id if new_h else None
        if new_h:
            new_h.plots.add(pl.id)
        else:
            pl.state = "황무지" if pl.terrain != "숲" else "황무지"

    # ---------------- 가을: 수확, 청구, 빚, 소비

    def autumn(self):
        p = self.p
        r = self.rng.random()
        acc = 0.0
        for prob, mult, name in WEATHER:
            acc += prob
            if r <= acc:
                break
        self.weather_log.append(name)
        for h in self.alive_hhs():
            for pid in h.farm:
                pl = self.plots[pid]
                gross = p["base_yield"] * TERRAIN[pl.terrain][0] * mult
                net = max(0.0, gross - p["seed_per_plot"])
                tithe = p["tithe"] * net
                tax = p["tax"] * net
                rent = pl.rent * net if pl.owner != h.id else 0.0
                h.grain += gross - tithe - tax - rent
                self.tithe_total += tithe
                self.tax_total += tax
                if rent:
                    self.hhs[pl.owner].grain += rent
            # 채집(육류는 저장 불가, 이번 해에 먹는다)
        for h in self.alive_hhs():
            self.settle_loans(h)
        for h in self.alive_hhs():
            meat = h.forage_labor * self.forage_rate
            need = self.need_of(h) + p["tool_upkeep"] * min(h.labor, len(h.farm) / p["cap_per_adult"])
            need_after_meat = max(0.0, need - meat)
            seed_keep = min(h.grain, self.seed_target(h))
            if h.grain - seed_keep < need_after_meat:
                self.borrow(h, need_after_meat - (h.grain - seed_keep))
            eat = min(max(0.0, h.grain - seed_keep), need_after_meat)
            if (meat + eat) / max(1.0, need) < 0.7:
                # 허기가 심하면 종자에 손을 댄다
                extra = min(h.grain - eat, 0.7 * need - meat - eat)
                eat += max(0.0, extra)
            h.grain -= eat
            h.food_ratio = (meat + eat) / need if need > 0 else 1.0
            h.food_ratio = min(1.0, h.food_ratio)
            h.hunger = h.food_ratio < 0.95
            h.hunger_years = h.hunger_years + 1 if h.hunger else 0
            if h.bonded > 0:
                h.bonded -= 1

    # ---------------- 잉여 사용, 집, 땅 시장, 손실

    def spend(self):
        p = self.p
        sellers = []
        buyers = []
        build_pool = 0.0
        distress_house = []
        for h in self.alive_hhs():
            need = self.need_of(h)
            reserve = need + len(h.farm) * p["seed_per_plot"]
            surplus = h.grain - reserve
            pers = self.head_pers(h)
            members = len(self.living(h))
            # 집 (H1, H2): 유지비 → 몰락 매각 → 한 등급 위 판단
            up = HOUSES[h.house][6]
            if h.grain >= up:
                h.grain -= up
                build_pool += up
                h.upkeep_miss = 0
            else:
                h.upkeep_miss += 1
                if h.upkeep_miss >= 2 and h.house > 0:
                    h.house -= 1          # 낡아서 한 등급 내려앉음
                    h.upkeep_miss = 0
                    self.house_downs += 1
            if h.house >= 2 and not self.house_keep_ok(h):
                h.keep_bad += 1
            else:
                h.keep_bad = 0
            if h.house >= 2 and (h.hunger or h.keep_bad >= 3):
                distress_house.append(h)
                h.keep_bad = 0
            else:
                build_pool += self.house_decision(h, reserve)
            surplus = h.grain - reserve
            if surplus > 0:
                if pers == "관대":
                    gift = surplus * 0.3
                    poor = [x for x in self.alive_hhs() if x.hunger and x.id != h.id]
                    if poor:
                        each = gift / len(poor)
                        for x in poor:
                            x.grain += each
                        h.grain -= gift
                        h.clients += len(poor)
                elif pers == "독실":
                    h.grain -= surplus * 0.3
                    self.church_gifts += surplus * 0.3
                if pers in ("탐욕", "근면", "야심") or self.rng.random() < 0.3:
                    buyers.append(h)
            if (h.hunger or any(l[3] >= 1 for l in h.loans)) and h.plots and h not in distress_house:
                sellers.append(h)
            if members > HOUSES[h.house][3]:
                pass  # 과밀은 사망률에서 처리

        # H2: 굶는 집은 땅보다 집을 먼저 판다. 값은 (지금 집 - 한 등급 아래) 가치의 50%, 부유한 집이 낸다
        rich = sorted(self.alive_hhs(), key=lambda x: -(x.grain - self.need_of(x)))
        for h in distress_house:
            frm = h.house
            proceeds = 0.5 * (self.house_cost(frm) - self.house_cost(frm - 1))
            for b in rich:
                if b.id != h.id and b.grain - self.need_of(b) * 1.5 >= proceeds:
                    b.grain -= proceeds
                    h.grain += proceeds
                    h.house = frm - 1
                    self.house_sales += 1
                    break

        # 부업과 품팔이: 잉여 있는 집이 물건과 일손을 산다. 받는 쪽은 노동이 남거나 굶는 집
        # 집 짓기와 유지비도 품삯과 재료값으로 같은 곳에 흘러간다
        pool = build_pool
        for h in self.alive_hhs():
            surplus = h.grain - self.need_of(h) - len(h.farm) * p["seed_per_plot"]
            if surplus > 0:
                x = surplus * p["hire_share"]
                h.grain -= x
                pool += x
        workers = [(h, h.forage_labor + (0.5 if h.hunger else 0.0)) for h in self.alive_hhs()]
        tot = sum(wt for _, wt in workers)
        if tot > 0:
            for h, wt in workers:
                h.grain += pool * wt / tot
        self.wages_paid += pool

        self.rng.shuffle(sellers)
        buyers.sort(key=lambda h: -h.grain)
        for s in sellers:
            pl = min((self.plots[i] for i in s.plots), key=self.net_expected)
            price = self.plot_price(pl) * 0.7
            for b in buyers:
                if b.id == s.id or not b.alive:
                    continue
                if b.grain - self.need_of(b) * 1.5 >= price:
                    b.grain -= price
                    s.grain += price
                    self.transfer_plot(pl, b)
                    self.sales += 1
                    break

        for h in self.alive_hhs():
            h.grain *= (1 - HOUSES[h.house][4])
            for i in h.plots:
                pl = self.plots[i]
                if pl.operator is None and pl.state == "경작지":
                    pass

    # ---------------- 인구: 사망, 출생, 혼인, 상속

    def demography(self):
        p = self.p
        rng = self.rng
        deaths = []
        for h in self.alive_hhs():
            members = self.living(h)
            crowd = max(0, len(members) - HOUSES[h.house][3]) * 0.005
            fr = h.food_ratio
            for per in members:
                a = self.age(per)
                if a < 16:
                    base, hung = 0.01, 0.25
                elif a < 45:
                    base, hung = 0.01, 0.10
                elif a < 60:
                    base, hung = 0.025, 0.10
                elif a < 70:
                    base, hung = 0.06, 0.20
                else:
                    base, hung = 0.15, 0.20
                if h.house == 0:
                    base += 0.02
                if rng.random() < base + hung * (1 - fr) + crowd:
                    deaths.append(per)
        if p["plague_year"] is not None and self.year == p["plague_year"]:
            for per in list(self.persons.values()):
                if per.alive and rng.random() < p["plague_frac"]:
                    deaths.append(per)
        for per in deaths:
            if per.alive:
                self.kill(per)

        # 출생
        for h in self.alive_hhs():
            for per in self.living(h):
                if per.sex != "F" or per.spouse is None:
                    continue
                a = self.age(per)
                if not (16 <= a <= 45) or self.year - per.nursing < 2:
                    continue
                sp = self.persons.get(per.spouse)
                if not sp or not sp.alive:
                    continue
                if rng.random() < p["birth_p"] * h.food_ratio ** 2:
                    per.nursing = self.year
                    if rng.random() < 0.02:
                        self.kill(per)          # 출산 사망
                    if rng.random() < p["infant_survival"] * (0.6 + 0.4 * h.food_ratio):
                        c = self._new_person(rng.choice("MF"), self.year,
                                             rng.choice([sp.pers, per.pers]) if rng.random() < 0.4 else None)
                        c.father, c.mother = sp.id, per.id
                        r = defaultdict(float)
                        for k, v in sp.r.items():
                            r[k] += v / 2
                        for k, v in per.r.items():
                            r[k] += v / 2
                        c.r = dict(r)
                        c.hh = h.id
                        c.birth_class = h.cls
                        h.members.add(c.id)
                        self.births_by_class[h.cls] += 1
                        self.child_track[c.id] = h.cls

        # 15세, 30세 계층 기록
        for per in self.persons.values():
            if not per.alive:
                continue
            a = self.age(per)
            h = self.hhs.get(per.hh)
            if h is None:
                continue
            if a == 15:
                per.class15 = h.cls
                if per.id in self.child_track:
                    self.surv_by_class[self.child_track.pop(per.id)] += 1
            elif a == 30 and per.class15:
                self.mobility.append((per.class15, h.cls))

        self.marriages()
        self.emigrate()

    def emigrate(self):
        """땅 없이 굶는 가구는 변경, 도시, 도적단으로 떠난다 (14_property_and_class.md 7-6)."""
        for h in self.alive_hhs():
            if h.plots or h.hunger_years < 2:
                continue
            if self.rng.random() < self.p["emigrate_p"]:
                for per in self.living(h):
                    per.alive = False      # 지역 밖으로 나감 (사망 아님)
                    self.emigrants += 1
                    bc = self.child_track.pop(per.id, None)
                    if bc:
                        self.births_by_class[bc] -= 1   # 생존율 계산에서 뺀다
                    if per.spouse is not None:
                        sp = self.persons.get(per.spouse)
                        if sp and sp.hh != h.id:
                            sp.spouse = None
                h.members.clear()
                self.dissolve(h)

    def kill(self, per):
        per.alive = False
        self.child_track.pop(per.id, None)
        if per.spouse is not None:
            sp = self.persons.get(per.spouse)
            if sp:
                sp.spouse = None
        h = self.hhs.get(per.hh)
        if h is None:
            return
        h.members.discard(per.id)
        if h.head == per.id:
            self.inherit(per, h)

    def heirs_of(self, dead):
        kids = [x for x in self.persons.values()
                if x.alive and (x.father == dead.id or x.mother == dead.id)]
        sons = sorted((k for k in kids if k.sex == "M"), key=lambda k: k.born)
        if sons:
            return sons
        return sorted((k for k in kids if k.sex == "F"), key=lambda k: k.born)

    def inherit(self, dead, h):
        heirs = self.heirs_of(dead)
        rule = self.p["inherit"]
        plots = sorted((self.plots[i] for i in h.plots), key=self.net_expected, reverse=True)
        shares = []
        if heirs:
            n = len(heirs)
            if rule == "장자" or n == 1:
                shares = [1.0] + [0.0] * (n - 1)
            elif rule == "장자우대":
                shares = [0.5] + [0.5 / (n - 1)] * (n - 1)
            else:
                shares = [1.0 / n] * n
        # 필지 배분 (필지는 쪼개지 않는다)
        if heirs:
            counts = [int(s * len(plots)) for s in shares]
            left = len(plots) - sum(counts)
            for i in range(left):
                counts[i % len(counts)] += 1
            idx = 0
            for heir, c in zip(heirs, counts):
                target = self.hhs.get(heir.hh)
                for _ in range(c):
                    pl = plots[idx]
                    idx += 1
                    if target and target.alive and target.id != h.id:
                        self.transfer_plot(pl, target)
            grain = h.grain
            for heir, s in zip(heirs, shares):
                target = self.hhs.get(heir.hh)
                if target and target.alive and target.id != h.id:
                    target.grain += grain * s
                    h.grain -= grain * s
        # 새 가구주
        members = self.living(h)
        if not members:
            if not heirs:
                for pl in plots:
                    self.transfer_plot(pl, None)
            self.dissolve(h)
            return
        in_house_sons = [x for x in heirs if x.hh == h.id and self.age(x) >= 16]
        if in_house_sons:
            h.head = in_house_sons[0].id
        else:
            adults = sorted((x for x in members if self.age(x) >= 16), key=lambda x: x.born)
            h.head = adults[0].id if adults else min(members, key=lambda x: x.born).id
        if not heirs and h.plots:
            pass   # 상속인이 없으면 가구에 남은 사람이 그대로 쓴다

    def dissolve(self, h):
        h.alive = False
        for i in list(h.plots):
            self.transfer_plot(self.plots[i], None)
        for lid, *_ in h.loans:
            pass
        h.loans = []

    def marriages(self):
        rng = self.rng
        men, women = [], []
        for per in self.persons.values():
            if not per.alive or per.spouse is not None:
                continue
            a = self.age(per)
            if per.sex == "M" and 20 <= a <= 45:
                men.append(per)
            elif per.sex == "F" and 17 <= a <= 40:
                women.append(per)
        rng.shuffle(men)
        rng.shuffle(women)
        if not men or not women:
            return
        wk = lambda x: self.wealth(self.hhs[x.hh]) if x.hh in self.hhs else 0
        def prospect(m):
            h = self.hhs.get(m.hh)
            if h is None:
                return 0.0
            if h.hunger:
                return 0.1
            if not h.plots and not h.farm:
                return 0.2
            return 0.6
        men = [m for m in men if rng.random() < prospect(m)]
        men.sort(key=wk)
        women.sort(key=wk)
        used = set()
        n = min(len(men), len(women))
        # 비슷한 재산끼리 짝 (상위 백분위 맞추기)
        for i, m in enumerate(men[:n]):
            j = int(i * len(women) / max(1, len(men)))
            for d in range(0, len(women)):
                for jj in (j + d, j - d):
                    if 0 <= jj < len(women) and jj not in used:
                        w = women[jj]
                        if w.father is not None and w.father == m.father:
                            continue
                        if w.hh == m.hh:
                            continue
                        used.add(jj)
                        self.wed(m, w)
                        break
                else:
                    continue
                break

    def wed(self, m, w):
        m.spouse, w.spouse = w.id, m.id
        mh = self.hhs[m.hh]
        wh = self.hhs.get(w.hh)
        dowry = 0.0
        if wh and wh.alive:
            dowry = min(30.0, max(0.0, wh.grain * 0.1))
            wh.grain -= dowry
            wh.members.discard(w.id)
            if wh.head == w.id:
                rest = self.living(wh)
                if rest:
                    wh.head = min(rest, key=lambda x: x.born).id
                else:
                    self.dissolve(wh)
        heir = mh.head == m.id
        if not heir:
            head = self.persons.get(mh.head)
            sons = [x for x in self.living(mh) if x.sex == "M" and head
                    and (x.father == head.id or x.mother == head.id)]
            sons.sort(key=lambda x: x.born)
            heir = bool(sons) and sons[0].id == m.id
        if heir:
            w.hh = mh.id
            mh.members.add(w.id)
            mh.grain += dowry
            return
        nh = self._new_hh()
        nh.head = m.id
        mh.members.discard(m.id)
        m.hh = nh.id
        w.hh = nh.id
        nh.members.update([m.id, w.id])
        if self.p["pre_gift"] and self.p["inherit"] != "장자":
            self.pre_gift(mh, nh, m)
        nh.grain = dowry + min(20.0, max(0.0, mh.grain * 0.05))
        mh.grain -= nh.grain - dowry
        if mh.grain >= self.house_cost(1):
            mh.grain -= self.house_cost(1)
            nh.house = 1
        else:
            nh.house = 0

    def pre_gift(self, mh, nh, son):
        """생전 분재: 아들이 분가할 때 몫을 미리 떼어 준다 (15_house_tax_inheritance.md 3-3)."""
        head = self.persons.get(mh.head)
        if head is None:
            return
        sons = [x for x in self.persons.values() if x.alive and x.sex == "M"
                and (x.father == head.id or x.mother == head.id)]
        n = max(1, len(sons))
        share = len(mh.plots) / n
        if self.p["inherit"] == "장자우대":
            share = len(mh.plots) * 0.5 / max(1, n - 1)
        keep = int(self.labor_of(mh) * self.p["cap_per_adult"])   # 부모가 계속 부칠 만큼은 남긴다
        give = int(min(share, max(0, len(mh.plots) - keep)))
        plots = sorted((self.plots[i] for i in mh.plots), key=self.net_expected)
        for pl in plots[:give]:
            self.transfer_plot(pl, nh)

    # ---------------- 기록

    def gini(self, xs):
        xs = sorted(max(0.0, x) for x in xs)
        n = len(xs)
        if n == 0 or sum(xs) == 0:
            return 0.0
        cum = sum((i + 1) * x for i, x in enumerate(xs))
        return (2 * cum) / (n * sum(xs)) - (n + 1) / n

    def report(self):
        hs = self.alive_hhs()
        pop = sum(len(self.living(h)) for h in hs)
        cls = Counter(h.cls for h in hs)
        n = max(1, len(hs))
        free = sum(1 for pl in self.plots if pl.state in ("황무지", "숲"))
        farmed = sum(len(h.farm) for h in hs)
        tenanted = sum(1 for h in hs for i in h.farm if self.plots[i].owner != h.id)
        houses = Counter(HOUSES[h.house][0] for h in hs)
        hungry = sum(1 for h in hs if h.hunger) / n
        top = sorted(hs, key=lambda h: -len(h.plots))
        top10 = sum(len(h.plots) for h in top[: max(1, len(hs) // 10)])
        owned = sum(len(h.plots) for h in hs)
        row = dict(
            year=self.year, pop=pop, hh=len(hs),
            자영농=cls["자영농"] / n, 소작농=cls["소작농"] / n, 지주=cls["지주"] / n, 무산=cls["무산"] / n,
            gini=self.gini([self.wealth(h) for h in hs]),
            rent=self.rent_frac, tenancy=tenanted / max(1, farmed),
            free=free, hungry=hungry, top10_land=top10 / max(1, owned),
            houses=dict(houses), weather="".join(w[0] for w in self.weather_log[-10:]),
        )
        self.reports.append(row)
        return row

    # ---------------- 실행

    def step(self):
        self.spring()
        self.autumn()
        self.spend()
        self.demography()
        self.year += 1

    def run(self, verbose=True):
        if verbose:
            print(f"{'년':>4} {'인구':>5} {'가구':>4} {'자영':>5} {'소작':>5} {'지주':>5} {'무산':>5} "
                  f"{'지니':>5} {'소작료':>5} {'소작비':>5} {'무주지':>5} {'굶주림':>5} {'상위10%땅':>7}  작황(최근10년)")
        for _ in range(self.p["years"] + 1):
            if self.year % self.p["report_every"] == 0:
                r = self.report()
                if verbose:
                    print(f"{r['year']:>4} {r['pop']:>5} {r['hh']:>4} {r['자영농']:>5.0%} {r['소작농']:>5.0%} "
                          f"{r['지주']:>5.0%} {r['무산']:>5.0%} {r['gini']:>5.2f} {r['rent']:>5.0%} "
                          f"{r['tenancy']:>5.0%} {r['free']:>5} {r['hungry']:>5.0%} {r['top10_land']:>7.0%}  {r['weather']}")
            if self.year == self.p["years"]:
                break
            self.step()
        return self.reports

    def summary(self):
        mob = self.mobility
        moved = sum(1 for a, b in mob if CLASS_TIER[a] != CLASS_TIER[b])
        up = sum(1 for a, b in mob if CLASS_TIER[b] > CLASS_TIER[a])
        down = sum(1 for a, b in mob if CLASS_TIER[b] < CLASS_TIER[a])
        print(f"\n세대 간 계층 이동률: {moved / max(1, len(mob)):.0%} (상승 {up}, 하락 {down}, 표본 {len(mob)})")
        print("출생 계층별 15세 생존율:")
        for c in ("지주", "자영농", "소작농", "무산"):
            b = self.births_by_class[c]
            s = self.surv_by_class[c]
            if b:
                print(f"  {c}: 출생 {b}, 15세 도달 {s} ({s / b:.0%})")
        print(f"담보 집행 필지: {self.seizures}, 땅 매매: {self.sales}, 이주 {self.emigrants}명, 지은 집: {dict(self.houses_built)}, "
              f"집 매각 {self.house_sales}, 낡아 내려앉음 {self.house_downs}")
        tab = defaultdict(Counter)
        for h in self.alive_hhs():
            tab[h.cls][HOUSES[h.house][0]] += 1
        for c in ("지주", "자영농", "소작농", "무산"):
            n = sum(tab[c].values())
            if n:
                print(f"  {c} 집: " + ", ".join(f"{k} {v / n:.0%}" for k, v in sorted(tab[c].items())))
        print(f"누적 세금 {self.tax_total:.0f}, 헌물 {self.tithe_total:.0f}")
        hs = self.alive_hhs()
        clients = sorted((h.clients for h in hs), reverse=True)[:3]
        if self.p["usury_ban"]:
            print(f"후견 관계 상위 3가구: {clients}")
        # 시조별 혈통 점수
        score = defaultdict(float)
        for per in self.persons.values():
            if per.alive:
                for k, v in per.r.items():
                    score[k] += v * 100
        vals = sorted(score.values(), reverse=True)
        if vals:
            print(f"시조 30쌍 혈통 점수: 최고 {vals[0]:.0f}, 중앙 {vals[len(vals) // 2]:.0f}, "
                  f"최저 {vals[-1]:.0f}, 단절 {self.p['households'] - len(vals)}")


SCENARIOS = {
    "A": dict(desc="개척: 평등 30가구, 하급 도구, 세금 없음", years=150),
    "A_tax": dict(desc="개척 + 영주 세금 10%, 헌물 10%", years=150, tax=0.10, tithe=0.10),
    "D": dict(desc="역병: A를 150년 돌린 뒤 인구 40% 사망, 30년 더", years=180, plague_year=150),
    "장자": dict(desc="A와 같고 장자 상속", years=150, inherit="장자"),
    "장자우대": dict(desc="A와 같고 장자 절반, 나머지 균분", years=150, inherit="장자우대"),
    "분재없음": dict(desc="A와 같고 생전 분재 없음(사후 상속만)", years=150, pre_gift=False),
    "고리금지": dict(desc="A와 같고 고리대금 금지 교리", years=150, usury_ban=True),
    "상급": dict(desc="A와 같고 상급 도구(1인 3필지)", years=150, cap_per_adult=3),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="A")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    names = list(SCENARIOS) if args.scenario == "all" else [args.scenario]
    for name in names:
        cfg = dict(SCENARIOS[name])
        desc = cfg.pop("desc")
        print(f"\n=== 시나리오 {name}: {desc} (시드 {args.seed}) ===")
        w = World(rng_seed=args.seed, **cfg)
        w.run()
        w.summary()


if __name__ == "__main__":
    main()
