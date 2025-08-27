#ifndef TELEMETRY_HPP
#define TELEMETRY_HPP
#include <cstdint>
#include "src/energy_loader.hpp"

struct Telemetry {
    uint32_t xor_ops = 0;
    uint32_t and_ops = 0;
};

inline bool XOR(bool a, bool b, Telemetry &t) {
    t.xor_ops++;
    return a ^ b;
}

inline bool AND(bool a, bool b, Telemetry &t) {
    t.and_ops++;
    return a & b;
}

inline double estimate_energy(const Telemetry& t,
                              int node_nm, double vdd,
                              const std::string& path = "tech_calib.json") {
    const auto energies = load_gate_energies(node_nm, vdd, path);
    return t.xor_ops * energies.xor_energy +
           t.and_ops * energies.and_energy;
}
#endif // TELEMETRY_HPP
