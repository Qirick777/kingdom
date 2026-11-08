// 요약 상세도 인구 벤치마크 (19번 문서 8절 1단계).
// 사용: sim_bench [인구] [마을] [년] [시드]
#include "../core/sim_core.h"
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>

using namespace kingdom;

static long rss_kb() {
    std::ifstream f("/proc/self/status");
    std::string line;
    while (std::getline(f, line))
        if (line.rfind("VmRSS:", 0) == 0) return std::atol(line.c_str() + 6);
    return -1;
}

int main(int argc, char** argv) {
    Config c;
    c.people = argc > 1 ? std::atoi(argv[1]) : 300000;
    c.villages = argc > 2 ? std::atoi(argv[2]) : 1600;
    int years = argc > 3 ? std::atoi(argv[3]) : 300;
    c.seed = argc > 4 ? std::strtoull(argv[4], nullptr, 10) : 1;

    auto t0 = std::chrono::steady_clock::now();
    SimCore sim(c);
    double init_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
    std::printf("시작: 인구 %d, 마을 %d, %d년, 시드 %llu. 초기화 %.0fms\n", c.people, c.villages, years,
                (unsigned long long)c.seed, init_ms);
    std::printf("%5s %8s %9s %7s %7s %6s %6s %6s %8s %8s %7s\n", "년", "산사람", "누적", "출생", "사망", "혼인",
                "평균나이", "식량", "혈통인원", "혈통합", "ms/년");
    std::vector<YearStats> st;
    st.reserve(years);
    auto t1 = std::chrono::steady_clock::now();
    sim.run_years(years, &st);
    double run_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t1).count();
    for (auto& s : st) {
        if (s.year % 25 != 0 && s.year != years) continue;
        std::printf("%5d %8d %9lld %7d %7d %6d %8.1f %6.2f %8d %8.2f %7.1f\n", s.year, s.alive, (long long)s.ever,
                    s.births, s.deaths, s.marriages, s.mean_age, s.mean_food, s.player_alive, s.player_r_sum, s.ms);
    }
    double per_year = run_ms / years;
    double worst = 0;
    for (auto& s : st) worst = std::max(worst, s.ms);
    const double YEAR_AT_32X_MS = 1008 * 4000.0 / 32.0;   // 1008시간대 × 4초 / 32
    std::printf("\n합계 %.1f초, 1년 평균 %.1fms (가장 느린 해 %.1fms)\n", run_ms / 1000, per_year, worst);
    std::printf("32x에서 1년 = %.0f초 → 요약 인구 계산이 차지하는 몫 %.3f%%\n", YEAR_AT_32X_MS / 1000,
                per_year / YEAR_AT_32X_MS * 100);
    std::printf("누적 인물 %lld명, 인물 배열 %.1fMB (1명 %.1f바이트), 프로세스 RSS %.1fMB\n",
                (long long)sim.person_count(), sim.bytes() / 1048576.0,
                (double)sim.bytes() / std::max<int64_t>(1, sim.person_count()), rss_kb() / 1024.0);
    std::printf("검사합 %016llx\n", (unsigned long long)sim.checksum());
    return 0;
}
