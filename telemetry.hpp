#ifndef TELEMETRY_HPP
#define TELEMETRY_HPP
#include <cstdint>
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
inline double estimate_energy(const Telemetry& t) {
    constexpr double E_XOR = 2e-12;
    constexpr double E_AND = 1e-12;
    return t.xor_ops * E_XOR + t.and_ops * E_AND;
}
#endif // TELEMETRY_HPP
