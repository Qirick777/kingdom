#pragma once
// GDScript에서 시뮬레이션 핵심을 부르는 얇은 포장. 계산은 모두 core/sim_core.cpp가 한다.
#include <memory>

#include <godot_cpp/classes/ref_counted.hpp>
#include <godot_cpp/variant/dictionary.hpp>
#include <godot_cpp/variant/string.hpp>

#include "sim_core.h"

namespace godot {

class KingdomSim : public RefCounted {
    GDCLASS(KingdomSim, RefCounted)

    std::unique_ptr<kingdom::SimCore> sim;

protected:
    static void _bind_methods();

public:
    void setup(int64_t seed, int64_t people, int64_t villages);
    Dictionary run_years(int64_t years);   // 마지막 해 통계
    Dictionary stats() const;
    int64_t person_count() const;
    int64_t alive_count() const;
    String checksum() const;
};

}  // namespace godot
