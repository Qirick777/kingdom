#pragma once
// 결정적 난수: (시드, 대상 id, 용도, 시각)을 해시해 바로 값을 뽑는다.
// 상태를 들고 다니지 않으므로 계산 순서, 스레드 수, 상세도 전환과 상관없이 같은 결과가 나온다.
#include <cstdint>

namespace kingdom {

inline uint64_t mix64(uint64_t z) {
    z += 0x9E3779B97F4A7C15ull;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
    return z ^ (z >> 31);
}

inline uint64_t hash4(uint64_t seed, uint64_t a, uint64_t b, uint64_t c) {
    return mix64(mix64(mix64(mix64(seed) ^ a) ^ b) ^ c);
}

// [0, 1)
inline double u01(uint64_t h) { return (h >> 11) * (1.0 / 9007199254740992.0); }

// 용도 상수
enum Purpose : uint64_t {
    P_DEATH = 1, P_CONCEIVE, P_SEX, P_GENOME, P_TRAITS, P_INFANT, P_MATERNAL,
    P_PROSPECT, P_SHUFFLE, P_HARVEST, P_INIT, P_CHILDBIRTH_WEEK,
};

}  // namespace kingdom
