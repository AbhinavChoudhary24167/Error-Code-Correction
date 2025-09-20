#include <iostream>
#include <string>

#include "src/energy_loader.hpp"
#include "src/hamming_simulator.hpp"
#include "src/hamming_sim_configs.hpp"

int main(int argc, char* argv[]) {
    try {
        int node_nm = 28;
        double vdd = 0.8;
        std::string pcm_path;
        for (int i = 1; i < argc; ++i) {
            std::string arg = argv[i];
            if (arg == "--node" && i + 1 < argc) {
                node_nm = std::stoi(argv[++i]);
            } else if (arg == "--vdd" && i + 1 < argc) {
                vdd = std::stod(argv[++i]);
            } else if (arg == "--pcm" && i + 1 < argc) {
                pcm_path = argv[++i];
            }
        }

        std::cout << "Advanced Hamming SEC-DED Memory Simulator (64-bit)" << std::endl;
        std::cout << "Data bits: 64, Parity bits: 7, Overall parity: 1, Total bits: 72" << std::endl;
        std::cout << "Memory size: 128GB (16G 64-bit words)" << std::endl;
        std::cout << "Features: Single Error Correction, Double Error Detection" << std::endl;
        std::cout << "Using node " << node_nm << " nm at VDD=" << vdd << " V" << std::endl;

        GateEnergies energies{};
        try {
            energies = load_gate_energies(node_nm, vdd);
        } catch (const std::exception& e) {
            std::cerr << "Warning: " << e.what() << ". Using default gate energies." << std::endl;
        }

        using WordTraits = ecc::Hamming64WordTraits;
        using Workload = ecc::Hamming64Workload;

        auto params = Workload::fromGateEnergies(energies);
        ecc::AdvancedMemorySimulator<WordTraits, Workload> memory(params);
        if (!pcm_path.empty() && !memory.loadParityCheckMatrix(pcm_path)) {
            std::cerr << "Warning: failed to load parity-check matrix from '" << pcm_path
                      << "'. Using default." << std::endl;
        }

        ecc::AdvancedTestSuite<WordTraits, Workload> tests(memory);
        tests.runAllTests();

        memory.printStatistics();
        memory.printFinalSummary("ADVANCED 64-BIT SIMULATION COMPLETE");

        ecc::printArchetypeReport(Workload::archetype_config_path);
        ecc::runEccSchemeDemo();
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}

