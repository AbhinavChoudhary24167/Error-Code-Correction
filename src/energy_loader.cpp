#include "energy_loader.hpp"
#include "../gate_energy.hpp"

GateEnergies load_gate_energies(int node_nm, double vdd,
                                 const std::string& path) {
    return {
        gate_energy(node_nm, vdd, "xor", path),
        gate_energy(node_nm, vdd, "and", path),
        gate_energy(node_nm, vdd, "adder_stage", path)
    };
}

