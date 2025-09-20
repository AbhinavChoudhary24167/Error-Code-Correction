#include <iostream>
#include <string>

#include "src/hamming_simulator.hpp"
#include "src/hamming_sim_configs.hpp"

int main(int argc, char* argv[]) {
    try {
        std::string pcm_path;
        for (int i = 1; i < argc; ++i) {
            std::string arg = argv[i];
            if (arg == "--pcm" && i + 1 < argc) {
                pcm_path = argv[++i];
            }
        }

        std::cout << "Advanced Hamming SEC-DED Memory Simulator" << std::endl;
        std::cout << "Data bits: 32, Parity bits: 6, Overall parity: 1, Total bits: 39" << std::endl;
        std::cout << "Memory size: 1GB (256M 32-bit words)" << std::endl;
        std::cout << "Features: Single Error Correction, Double Error Detection" << std::endl;

        using WordTraits = ecc::Hamming32WordTraits;
        using Workload = ecc::Hamming32Workload;

        auto params = Workload::defaultParams();
        ecc::AdvancedMemorySimulator<WordTraits, Workload> memory(params);
        if (!pcm_path.empty() && !memory.loadParityCheckMatrix(pcm_path)) {
            std::cerr << "Warning: failed to load parity-check matrix from '" << pcm_path
                      << "'. Using default." << std::endl;
        }

        ecc::AdvancedTestSuite<WordTraits, Workload> tests(memory);
        tests.runAllTests();

        memory.printStatistics();
        memory.printFinalSummary("ADVANCED SIMULATION COMPLETE");

        ecc::printArchetypeReport(Workload::archetype_config_path);
        ecc::runEccSchemeDemo();
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}

