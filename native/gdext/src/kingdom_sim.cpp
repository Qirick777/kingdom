#include "kingdom_sim.h"

#include <cstdio>
#include <godot_cpp/core/class_db.hpp>

using namespace godot;

static Dictionary to_dict(const kingdom::YearStats& s) {
    Dictionary d;
    d["year"] = s.year;
    d["alive"] = s.alive;
    d["ever"] = (int64_t)s.ever;
    d["births"] = s.births;
    d["deaths"] = s.deaths;
    d["marriages"] = s.marriages;
    d["mean_age"] = s.mean_age;
    d["mean_food"] = s.mean_food;
    d["player_alive"] = s.player_alive;
    d["player_r_sum"] = s.player_r_sum;
    d["ms"] = s.ms;
    return d;
}

void KingdomSim::_bind_methods() {
    ClassDB::bind_method(D_METHOD("setup", "seed", "people", "villages"), &KingdomSim::setup);
    ClassDB::bind_method(D_METHOD("run_years", "years"), &KingdomSim::run_years);
    ClassDB::bind_method(D_METHOD("stats"), &KingdomSim::stats);
    ClassDB::bind_method(D_METHOD("person_count"), &KingdomSim::person_count);
    ClassDB::bind_method(D_METHOD("alive_count"), &KingdomSim::alive_count);
    ClassDB::bind_method(D_METHOD("checksum"), &KingdomSim::checksum);
}

void KingdomSim::setup(int64_t seed, int64_t people, int64_t villages) {
    kingdom::Config c;
    c.seed = (uint64_t)seed;
    c.people = (int)people;
    c.villages = (int)villages;
    sim = std::make_unique<kingdom::SimCore>(c);
}

Dictionary KingdomSim::run_years(int64_t years) {
    if (!sim) return Dictionary();
    std::vector<kingdom::YearStats> st;
    sim->run_years((int)years, &st);
    return st.empty() ? Dictionary() : to_dict(st.back());
}

Dictionary KingdomSim::stats() const { return sim ? to_dict(sim->snapshot()) : Dictionary(); }
int64_t KingdomSim::person_count() const { return sim ? sim->person_count() : 0; }
int64_t KingdomSim::alive_count() const { return sim ? sim->alive_count() : 0; }

String KingdomSim::checksum() const {
    if (!sim) return String();
    char buf[24];
    std::snprintf(buf, sizeof(buf), "%016llx", (unsigned long long)sim->checksum());
    return String(buf);
}
