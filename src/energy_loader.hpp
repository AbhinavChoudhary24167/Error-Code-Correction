#pragma once

#include <string>

struct GateEnergies {
    double xor_energy;
    double and_energy;
    double adder_stage_energy;
};

GateEnergies load_gate_energies(int node_nm, double vdd,
                                 const std::string& path = "tech_calib.json");

