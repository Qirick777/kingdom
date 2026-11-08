#pragma once
// 시뮬레이션 핵심 1단계: 요약 상세도의 인구 (19번 문서 4절, 8절 1단계).
// Godot에 기대지 않는 순수 C++. GDExtension(native/gdext)과 벤치마크(native/tools)가 이 코드를 쓴다.
//
// 시간: 주 단위 정수. 1년 = 48주, 1계절 = 12주(12번 4절).
// 인물은 열 단위 배열(SoA)로 둔다. 죽은 사람도 지우지 않는다(혈통 점수, 계보).
// 규칙 수치는 tools/econ_sim/econ_sim.py의 인구 부분과 01번 8절을 따른다.
#include <cstdint>
#include <vector>
#include <string>

namespace kingdom {

constexpr int WEEKS_PER_YEAR = 48;
constexpr int WEEKS_PER_SEASON = 12;
constexpr int PREGNANCY_WEEKS = 36;
constexpr int NURSING_WEEKS = 48;

struct Config {
    uint64_t seed = 1;
    int villages = 1600;          // 대 맵
    int people = 300000;          // 시작 인구
    int region_size = 3;          // 혼인 시장 = 마을 격자 3×3
    double cap_slack = 1.15;      // 마을 부양 한계 = 시작 인구 × 이 값
    double birth_p = 0.32;        // 연간 임신 확률(부부, 수유 중 제외) × 식량 충족률²
    double infant_survival = 0.85;
    double maternal_death = 0.02;
    double harvest_sd = 0.15;     // 마을별 해마다 수확 변동
};

struct Village {
    int region = 0;
    int cap = 0;                  // 부양 가능 인원
    int alive = 0;
    float food = 1.0f;            // 식량 충족률 0~1
};

struct Event {                    // 사건 예약 바퀴의 항목
    int32_t week;
    int32_t kind;                 // 0 = 출산
    int32_t person;               // 산모
    int32_t father;
};

struct YearStats {
    int year = 0;
    int alive = 0;
    int64_t ever = 0;
    int births = 0;
    int deaths = 0;
    int marriages = 0;
    double mean_age = 0;
    double mean_food = 0;
    int player_alive = 0;         // 플레이어 혈통(r > 0) 산 사람 수
    double player_r_sum = 0;      // 산 사람의 r 합(07번 점수의 재료)
    double ms = 0;                // 그 해 계산에 든 시간
};

class SimCore {
public:
    explicit SimCore(const Config& c);
    void step_season();           // 12주 진행
    void run_years(int years, std::vector<YearStats>* out = nullptr);
    YearStats snapshot() const;
    uint64_t checksum() const;
    size_t bytes() const;         // 인물, 마을, 사건 배열이 쓰는 메모리

    int64_t person_count() const { return (int64_t)birth.size(); }
    int alive_count() const { return (int)alive_ids.size(); }
    int week() const { return now; }

    // ---- 인물 열 배열 (공개: 바인딩과 시험이 읽는다)
    std::vector<uint8_t> sex;         // 0 여, 1 남
    std::vector<uint8_t> social;      // 0 노예 1 평민 2 장인상인 3 지주기사 4 귀족
    std::vector<int32_t> birth, death;   // 주. death = -1이면 살아 있다
    std::vector<int32_t> father, mother, spouse;
    std::vector<int32_t> village;
    std::vector<int32_t> dynasty;     // 가문 id(부계)
    std::vector<int32_t> fertile_from;   // 이 주부터 임신 가능(수유 끝)
    std::vector<uint8_t> pregnant;
    std::vector<uint32_t> genome;     // 외형 유전자 6개 × 대립유전자 2 (01번 1절)
    std::vector<uint32_t> traits;     // 형질 14개 × 대립유전자 2 (01번 3절)
    std::vector<float> r;             // 플레이어 혈통 비율(07번)

    std::vector<Village> villages;

private:
    Config cfg;
    int now = 0;
    int next_dynasty = 0;
    std::vector<int32_t> alive_ids;
    std::vector<std::vector<Event>> wheel;   // 주 단위 바퀴(64주). 출산은 36주 뒤라 넘치지 않는다
    YearStats acc;                            // 올해 누적

    double rnd(uint64_t id, uint64_t purpose, uint64_t t) const;
    int32_t add_person(uint8_t sx, int32_t born, int32_t vil, uint8_t soc, int32_t fa, int32_t mo);
    void init_population();
    void harvest_and_food();
    void deaths_sweep();
    void conceptions();
    void process_week(int w);
    void marriages(int salt = 0);
    void kill(int32_t p, int32_t week);
    void compact_alive();
};

}  // namespace kingdom
