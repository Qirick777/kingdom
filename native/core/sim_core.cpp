#include "sim_core.h"
#include "rng.h"

#include <algorithm>
#include <cmath>
#include <cstring>

namespace kingdom {

// ---------------------------------------------------------------- 유전 (01번 1절, 3절)
// 외형: 머리색 2비트, 눈색 2, 피부 3, 키 4, 얼굴형 3, 골격 2 = 한 벌 16비트. 대립유전자 두 벌 = 32비트
static const int G_WIDTH[6] = {2, 2, 3, 4, 3, 2};
static const int G_RANGE[6] = {4, 3, 5, 10, 6, 3};
// 형질 14개: 한 벌 14비트(있음/없음). 우성이면 하나만 있어도, 열성이면 둘 다 있어야 발현
enum Trait { T_GIANT, T_BEAUTY, T_GENIUS, T_STRONG, T_LONGLIFE, T_FERTILE, T_SENSES, T_SMALL, T_UGLY,
             T_DULL, T_SICKLY, T_INFERTILE, T_HEMOPHILIA, T_MADNESS, T_COUNT };
static const bool T_DOMINANT[T_COUNT] = {true, true, false, false, false, true, false, false, false,
                                         false, false, false, false, false};
// 기본 보유율(대립유전자 하나 이상을 가진 비율)
static const double T_RATE[T_COUNT] = {0.03, 0.04, 0.06, 0.06, 0.05, 0.05, 0.05, 0.06, 0.04,
                                       0.05, 0.06, 0.04, 0.02, 0.03};

static inline bool expressed(uint32_t t, int i) {
    bool a = (t >> i) & 1u, b = (t >> (T_COUNT + i)) & 1u;
    return T_DOMINANT[i] ? (a || b) : (a && b);
}

// 부모 한 명의 두 벌에서 유전자마다 한쪽을 골라 생식세포 한 벌을 만든다
static uint32_t gamete(uint32_t word, const int* widths, int genes, int hap_bits, uint64_t h) {
    uint32_t out = 0;
    int off = 0;
    for (int g = 0; g < genes; ++g) {
        int w = widths ? widths[g] : 1;
        uint32_t mask = (1u << w) - 1u;
        int from = (h >> g) & 1u ? hap_bits : 0;
        out |= ((word >> (from + off)) & mask) << off;
        off += w;
    }
    return out;
}

// ---------------------------------------------------------------- 사망률 (econ_sim.py demography)
// 연간 기본 사망률, 굶주림 가산(1 - 식량 충족률에 곱함)
static const int AGE_BANDS = 5;
static const double D_BASE[AGE_BANDS] = {0.01, 0.01, 0.025, 0.06, 0.15};
static const double D_HUNG[AGE_BANDS] = {0.25, 0.10, 0.10, 0.20, 0.20};
static inline int age_band(int age) {
    return age < 16 ? 0 : age < 45 ? 1 : age < 60 ? 2 : age < 70 ? 3 : 4;
}
static inline double annual_to_season(double p) {
    p = std::min(0.999, std::max(0.0, p));
    return 1.0 - std::pow(1.0 - p, 0.25);
}

// ---------------------------------------------------------------- 기본

SimCore::SimCore(const Config& c) : cfg(c) {
    wheel.resize(64);
    init_population();
}

double SimCore::rnd(uint64_t id, uint64_t purpose, uint64_t t) const {
    return u01(hash4(cfg.seed, id, purpose, t));
}

int32_t SimCore::add_person(uint8_t sx, int32_t born, int32_t vil, uint8_t soc, int32_t fa, int32_t mo) {
    int32_t id = (int32_t)birth.size();
    sex.push_back(sx);
    social.push_back(soc);
    birth.push_back(born);
    death.push_back(-1);
    father.push_back(fa);
    mother.push_back(mo);
    spouse.push_back(-1);
    village.push_back(vil);
    dynasty.push_back(-1);
    fertile_from.push_back(0);
    pregnant.push_back(0);
    genome.push_back(0);
    traits.push_back(0);
    r.push_back(0.0f);
    alive_ids.push_back(id);
    villages[vil].alive++;
    return id;
}

void SimCore::init_population() {
    // 마을을 정사각 격자에 놓고, 3×3 묶음을 혼인 시장 하나로 본다
    int side = (int)std::ceil(std::sqrt((double)cfg.villages));
    villages.resize(cfg.villages);
    int rs = cfg.region_size;
    int rside = (side + rs - 1) / rs;
    for (int v = 0; v < cfg.villages; ++v) {
        int x = v % side, y = v / side;
        villages[v].region = (y / rs) * rside + (x / rs);
    }
    // 시작 나이 분포: 대략 안정 인구(나이마다 e^(-나이/28)), 0~79세
    std::vector<double> cdf(80);
    double s = 0;
    for (int a = 0; a < 80; ++a) { s += std::exp(-a / 28.0); cdf[a] = s; }
    for (double& c : cdf) c /= s;
    const double SOC_W[5] = {0.10, 0.50, 0.15, 0.15, 0.10};

    size_t reserve = (size_t)cfg.people * 12;   // 300년 동안 태어날 사람까지
    for (auto* v : {&birth, &death, &father, &mother, &spouse, &village, &dynasty, &fertile_from})
        v->reserve(reserve);
    sex.reserve(reserve); social.reserve(reserve); pregnant.reserve(reserve);
    genome.reserve(reserve); traits.reserve(reserve); r.reserve(reserve);

    int per = cfg.people / cfg.villages;
    int64_t made = 0;
    for (int v = 0; v < cfg.villages; ++v) {
        int n = (int)(per * (0.7 + 0.6 * rnd(v, P_INIT, 0)));
        if (v == cfg.villages - 1) n = std::max(1, (int)(cfg.people - made));
        villages[v].cap = (int)(n * cfg.cap_slack);
        for (int i = 0; i < n; ++i, ++made) {
            uint64_t key = (uint64_t)v * 100000 + i;
            double ua = rnd(key, P_INIT, 1);
            int age = (int)(std::lower_bound(cdf.begin(), cdf.end(), ua) - cdf.begin());
            uint8_t sx = rnd(key, P_SEX, 0) < 0.5 ? 1 : 0;
            double us = rnd(key, P_INIT, 2), acc = 0;
            uint8_t soc = 4;
            for (int k = 0; k < 5; ++k) { acc += SOC_W[k]; if (us < acc) { soc = (uint8_t)k; break; } }
            int32_t born = -age * WEEKS_PER_YEAR - (int)(rnd(key, P_INIT, 3) * WEEKS_PER_YEAR);
            int32_t id = add_person(sx, born, v, soc, -1, -1);
            dynasty[id] = next_dynasty++;
            // 외형: 유전자마다 대립유전자 둘을 무작위로
            uint32_t g = 0;
            int off = 0;
            for (int k = 0; k < 6; ++k) {
                uint32_t a = (uint32_t)(rnd(id, P_GENOME, k) * G_RANGE[k]);
                uint32_t b = (uint32_t)(rnd(id, P_GENOME, k + 10) * G_RANGE[k]);
                g |= a << off;
                g |= b << (16 + off);
                off += G_WIDTH[k];
            }
            genome[id] = g;
            // 형질: 대립유전자 하나를 가질 확률 q, 1-(1-q)^2 = 보유율
            uint32_t t = 0;
            for (int k = 0; k < T_COUNT; ++k) {
                double q = 1.0 - std::sqrt(1.0 - T_RATE[k]);
                if (rnd(id, P_TRAITS, k) < q) t |= 1u << k;
                if (rnd(id, P_TRAITS, k + 20) < q) t |= 1u << (T_COUNT + k);
            }
            traits[id] = t;
        }
    }
    // 시작 혼인: 혼인 시장을 몇 번 돌려 기혼 비율을 안정 상태 근처로 맞춘다
    for (int k = 0; k < 8; ++k) marriages(k + 1);   // 라운드마다 다른 난수
    for (int32_t id : alive_ids)
        if (sex[id] == 0 && spouse[id] >= 0)
            fertile_from[id] = (int32_t)(rnd(id, P_INIT, 4) * 2 * WEEKS_PER_YEAR);
    // 플레이어 가문 시조: 0번 마을의 25~35세 기혼 남성 하나. r = 1
    for (int32_t id : alive_ids) {
        int age = (now - birth[id]) / WEEKS_PER_YEAR;
        if (village[id] == 0 && sex[id] == 1 && spouse[id] >= 0 && age >= 25 && age <= 35) {
            r[id] = 1.0f;
            break;
        }
    }
    acc = YearStats();
}

// ---------------------------------------------------------------- 계절 진행

void SimCore::harvest_and_food() {
    int year = now / WEEKS_PER_YEAR;
    for (int v = 0; v < (int)villages.size(); ++v) {
        Village& vl = villages[v];
        // 해마다 수확 변동(정규분포 근사: 균등 4개 합)
        double z = 0;
        for (int k = 0; k < 4; ++k) z += rnd(v, P_HARVEST, (uint64_t)year * 4 + k);
        z = (z - 2.0) * std::sqrt(3.0);
        double harvest = std::max(0.3, 1.0 + cfg.harvest_sd * z);
        double f = vl.alive > 0 ? vl.cap * harvest / vl.alive : 1.0;
        vl.food = (float)std::min(1.0, f);
    }
}

void SimCore::kill(int32_t p, int32_t week) {
    if (death[p] >= 0) return;
    death[p] = week;
    villages[village[p]].alive--;
    int32_t sp = spouse[p];
    if (sp >= 0 && death[sp] < 0) spouse[sp] = -1;   // 남은 배우자는 재혼할 수 있다
    acc.deaths++;
}

void SimCore::deaths_sweep() {
    // 마을, 나이 구간마다 계절 사망률을 한 번 계산해 두고 사람은 표를 읽는다
    const int V = (int)villages.size();
    static thread_local std::vector<float> tab;
    tab.resize((size_t)V * AGE_BANDS);
    for (int v = 0; v < V; ++v)
        for (int b = 0; b < AGE_BANDS; ++b)
            tab[(size_t)v * AGE_BANDS + b] =
                (float)annual_to_season(D_BASE[b] + D_HUNG[b] * (1.0 - villages[v].food));
    uint64_t season = now / WEEKS_PER_SEASON;
    for (int32_t id : alive_ids) {
        if (death[id] >= 0) continue;
        int age = (now - birth[id]) / WEEKS_PER_YEAR;
        uint32_t t = traits[id];
        if (expressed(t, T_LONGLIFE) && age >= 45) age = std::max(45 - 1, age - 15);   // 장수: 노화 15년 늦게
        double p = tab[(size_t)village[id] * AGE_BANDS + age_band(age)];
        if (expressed(t, T_STRONG)) p *= 0.8;
        if (expressed(t, T_SICKLY)) p *= 1.3;
        if (expressed(t, T_HEMOPHILIA) && sex[id] == 1) p *= 1.5;
        if (rnd(id, P_DEATH, season) < p) kill(id, now);
    }
}

void SimCore::conceptions() {
    const int V = (int)villages.size();
    static thread_local std::vector<float> tab;
    tab.resize(V);
    for (int v = 0; v < V; ++v) {
        double f = villages[v].food;
        tab[v] = (float)annual_to_season(cfg.birth_p * f * f);
    }
    uint64_t season = now / WEEKS_PER_SEASON;
    for (int32_t id : alive_ids) {
        if (sex[id] != 0 || death[id] >= 0 || pregnant[id]) continue;
        int32_t sp = spouse[id];
        if (sp < 0 || death[sp] >= 0) continue;
        int age = (now - birth[id]) / WEEKS_PER_YEAR;
        if (age < 16 || age > 45 || now < fertile_from[id]) continue;
        double p = tab[village[id]];
        if (expressed(traits[id], T_FERTILE)) p *= 1.5;
        if (expressed(traits[id], T_INFERTILE) || expressed(traits[sp], T_INFERTILE)) p *= 0.3;
        if (rnd(id, P_CONCEIVE, season) < p) {
            pregnant[id] = 1;
            int wk = now + (int)(rnd(id, P_CHILDBIRTH_WEEK, season) * WEEKS_PER_SEASON) + PREGNANCY_WEEKS;
            wheel[wk % 64].push_back(Event{wk, 0, id, sp});
        }
    }
}

void SimCore::process_week(int w) {
    auto& bucket = wheel[w % 64];
    if (bucket.empty()) return;
    std::vector<Event> due;
    due.swap(bucket);
    for (const Event& e : due) {
        if (e.week != w) { bucket.push_back(e); continue; }
        int32_t m = e.person;
        if (death[m] >= 0) continue;              // 임신 중 사망
        pregnant[m] = 0;
        fertile_from[m] = w + NURSING_WEEKS;
        float food = villages[village[m]].food;
        bool mother_dies = rnd(m, P_MATERNAL, w) < cfg.maternal_death;
        if (rnd(m, P_INFANT, w) < cfg.infant_survival * (0.6 + 0.4 * food)) {
            int32_t f = e.father;
            uint64_t key = ((uint64_t)m << 20) ^ (uint64_t)w;
            uint8_t sx = rnd(key, P_SEX, 1) < 0.5 ? 1 : 0;
            uint8_t soc = f >= 0 ? social[f] : social[m];
            int32_t c = add_person(sx, w, village[m], soc, f, m);
            dynasty[c] = f >= 0 ? dynasty[f] : dynasty[m];
            uint64_t h = hash4(cfg.seed, (uint64_t)c, P_GENOME, 99);
            genome[c] = gamete(genome[f >= 0 ? f : m], G_WIDTH, 6, 16, h) |
                        (gamete(genome[m], G_WIDTH, 6, 16, h >> 8) << 16);
            uint64_t ht = hash4(cfg.seed, (uint64_t)c, P_TRAITS, 99);
            traits[c] = gamete(traits[f >= 0 ? f : m], nullptr, T_COUNT, T_COUNT, ht) |
                        (gamete(traits[m], nullptr, T_COUNT, T_COUNT, ht >> 20) << T_COUNT);
            r[c] = 0.5f * ((f >= 0 ? r[f] : 0.0f) + r[m]);
            acc.births++;
        }
        if (mother_dies) kill(m, w);
    }
}

void SimCore::marriages(int salt) {
    // 혼인 시장(지역)마다 미혼 남녀를 모아 계층, 무작위 순으로 짝짓는다(econ_sim.py marriages)
    int regions = 0;
    for (auto& v : villages) regions = std::max(regions, v.region + 1);
    static thread_local std::vector<std::vector<int32_t>> men, women;
    men.assign(regions, {});
    women.assign(regions, {});
    uint64_t season = (uint64_t)(now / WEEKS_PER_SEASON) * 64 + (uint64_t)salt;
    const double P_NORMAL = annual_to_season(0.6), P_POOR = annual_to_season(0.2), P_HUNGRY = annual_to_season(0.1);
    for (int32_t id : alive_ids) {
        if (death[id] >= 0 || spouse[id] >= 0) continue;
        int age = (now - birth[id]) / WEEKS_PER_YEAR;
        int reg = villages[village[id]].region;
        if (sex[id] == 1) {
            if (age < 20 || age > 45) continue;
            double pr = villages[village[id]].food < 0.8 ? P_HUNGRY : social[id] == 0 ? P_POOR : P_NORMAL;
            if (rnd(id, P_PROSPECT, season) < pr) men[reg].push_back(id);
        } else if (age >= 17 && age <= 40) {
            women[reg].push_back(id);
        }
    }
    auto key = [&](int32_t id) {
        return ((uint64_t)social[id] << 56) | (hash4(cfg.seed, id, P_SHUFFLE, season) >> 8);
    };
    for (int g = 0; g < regions; ++g) {
        auto& M = men[g];
        auto& W = women[g];
        if (M.empty() || W.empty()) continue;
        std::sort(M.begin(), M.end(), [&](int32_t a, int32_t b) { return key(a) < key(b); });
        std::sort(W.begin(), W.end(), [&](int32_t a, int32_t b) { return key(a) < key(b); });
        std::vector<uint8_t> used(W.size(), 0);
        size_t n = std::min(M.size(), W.size());
        for (size_t i = 0; i < n; ++i) {
            int32_t m = M[i];
            long j0 = (long)(i * W.size() / M.size());
            for (long d = 0; d < 8; ++d) {
                bool done = false;
                for (long j : {j0 + d, j0 - d}) {
                    if (j < 0 || j >= (long)W.size() || used[j]) continue;
                    int32_t w = W[j];
                    bool sib = (father[w] >= 0 && father[w] == father[m]) || (mother[w] >= 0 && mother[w] == mother[m]);
                    if (sib) continue;
                    used[j] = 1;
                    spouse[m] = w;
                    spouse[w] = m;
                    if (village[w] != village[m]) {       // 아내가 남편 마을로 옮긴다
                        villages[village[w]].alive--;
                        village[w] = village[m];
                        villages[village[m]].alive++;
                    }
                    acc.marriages++;
                    done = true;
                    break;
                }
                if (done) break;
            }
        }
    }
}

void SimCore::compact_alive() {
    size_t k = 0;
    for (int32_t id : alive_ids)
        if (death[id] < 0) alive_ids[k++] = id;
    alive_ids.resize(k);
}

void SimCore::step_season() {
    if (now % WEEKS_PER_YEAR == 0 || now % WEEKS_PER_SEASON == 0) harvest_and_food();
    deaths_sweep();
    conceptions();
    for (int w = now; w < now + WEEKS_PER_SEASON; ++w) process_week(w);
    marriages();
    compact_alive();
    now += WEEKS_PER_SEASON;
}

// ---------------------------------------------------------------- 실행, 통계

YearStats SimCore::snapshot() const {
    YearStats s = acc;
    s.year = now / WEEKS_PER_YEAR;
    s.alive = (int)alive_ids.size();
    s.ever = (int64_t)birth.size();
    double age = 0, food = 0;
    for (int32_t id : alive_ids) {
        age += (now - birth[id]) / (double)WEEKS_PER_YEAR;
        if (r[id] > 0) { s.player_alive++; s.player_r_sum += r[id]; }
    }
    for (auto& v : villages) food += v.food;
    s.mean_age = alive_ids.empty() ? 0 : age / alive_ids.size();
    s.mean_food = food / villages.size();
    return s;
}

}  // namespace kingdom

#include <chrono>

namespace kingdom {

void SimCore::run_years(int years, std::vector<YearStats>* out) {
    for (int y = 0; y < years; ++y) {
        auto t0 = std::chrono::steady_clock::now();
        acc = YearStats();
        for (int s = 0; s < WEEKS_PER_YEAR / WEEKS_PER_SEASON; ++s) step_season();
        auto t1 = std::chrono::steady_clock::now();
        if (out) {
            YearStats st = snapshot();
            st.ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
            out->push_back(st);
        }
    }
}

uint64_t SimCore::checksum() const {
    uint64_t h = 1469598103934665603ull;
    auto add = [&](const void* p, size_t n) {
        const uint8_t* b = (const uint8_t*)p;
        for (size_t i = 0; i < n; ++i) { h ^= b[i]; h *= 1099511628211ull; }
    };
    add(birth.data(), birth.size() * 4);
    add(death.data(), death.size() * 4);
    add(father.data(), father.size() * 4);
    add(mother.data(), mother.size() * 4);
    add(spouse.data(), spouse.size() * 4);
    add(village.data(), village.size() * 4);
    add(genome.data(), genome.size() * 4);
    add(traits.data(), traits.size() * 4);
    add(r.data(), r.size() * 4);
    return h;
}

size_t SimCore::bytes() const {
    // 실제로 쓰는 크기(예약해 둔 여유 용량은 빼고)
    size_t n = birth.size();
    size_t b = n * (3 * 1 + 8 * 4 + 3 * 4);   // uint8 3열, int32 8열, genome·traits·r 3열
    b += villages.size() * sizeof(Village) + alive_ids.size() * 4;
    for (auto& w : wheel) b += w.size() * sizeof(Event);
    return b;
}

}  // namespace kingdom
