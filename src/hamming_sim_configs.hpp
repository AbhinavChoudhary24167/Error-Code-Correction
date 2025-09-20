#pragma once

#include <array>
#include <cstdint>
#include <map>
#include <unordered_map>
#include <utility>

#include "gate_energy.hpp"
#include "src/energy_loader.hpp"

namespace ecc {

struct Hamming32WordTraits {
    using DataType = uint32_t;
    static constexpr int DATA_BITS = 32;
    static constexpr std::array<int, 6> parity_positions{{1, 2, 4, 8, 16, 32}};
};

struct Hamming64WordTraits {
    using DataType = uint64_t;
    static constexpr int DATA_BITS = 64;
    static constexpr std::array<int, 7> parity_positions{{1, 2, 4, 8, 16, 32, 64}};
};

struct Hamming32Workload {
    using WordTraits = Hamming32WordTraits;
    using DataType = WordTraits::DataType;
    using AddressType = uint32_t;

    template <typename CodeWord>
    using MemoryContainer = std::unordered_map<AddressType, CodeWord>;

    static constexpr AddressType memory_size_words = 1024u * 1024u * 256u;  // 1GB / 4 bytes
    static constexpr bool include_known_vectors = true;
    static constexpr bool include_batch_fault_injection = true;
    static constexpr bool include_large_address_test = false;
    static constexpr bool include_million_dataset = false;
    static constexpr bool include_stress_test = false;

    struct KnownVector {
        DataType data;
        std::array<uint64_t, 2> encoded;
    };

    static inline constexpr std::array<KnownVector, 3> known_vectors{{
        KnownVector{0x00000000u, {0x0ULL, 0x0ULL}},
        KnownVector{0xFFFFFFFFu, {0x3F7FFFFFF4ULL, 0x0ULL}},
        KnownVector{0x12345678u, {0x44C68A67C9ULL, 0x0ULL}}
    }};

    static inline constexpr std::array<DataType, 5> no_error_data{{
        0x00000000u, 0xFFFFFFFFu, 0x12345678u, 0xA5A5A5A5u, 0x5A5A5A5Au
    }};
    static constexpr AddressType no_error_base = 0;

    static constexpr DataType single_error_data = 0x12345678u;
    static constexpr AddressType single_error_base = 1000;
    static inline constexpr std::array<int, 12> single_error_positions{{
        1, 2, 3, 4, 5, 8, 15, 16, 20, 32, 35, 39
    }};

    static constexpr DataType double_error_data = 0xAAAAAAAAu;
    static constexpr AddressType double_error_base = 2000;
    static inline constexpr std::array<std::pair<int, int>, 5> double_error_pairs{{
        std::pair<int, int>{1, 3},
        std::pair<int, int>{2, 5},
        std::pair<int, int>{10, 15},
        std::pair<int, int>{20, 25},
        std::pair<int, int>{30, 35}
    }};

    static constexpr DataType overall_parity_data = 0x55555555u;
    static constexpr AddressType overall_parity_address = 3000;

    static constexpr DataType burst_data = 0x87654321u;
    static constexpr AddressType burst_base = 4000;
    static inline constexpr std::array<std::pair<int, int>, 5> burst_configs{{
        std::pair<int, int>{1, 2},
        std::pair<int, int>{5, 3},
        std::pair<int, int>{10, 4},
        std::pair<int, int>{20, 5},
        std::pair<int, int>{30, 6}
    }};

    static constexpr DataType random_multiple_data = 0xDEADBEEFu;
    static constexpr AddressType random_multiple_base = 5000;
    static inline constexpr std::array<int, 6> random_error_counts{{3, 4, 5, 6, 7, 8}};

    static constexpr AddressType mixed_workload_base = 6000;
    static constexpr int mixed_workload_iterations = 20;
    static constexpr unsigned mixed_workload_seed = 12345u;

    static constexpr unsigned batch_fault_trials = 1000u;
    static constexpr unsigned batch_seed = 42u;
    static constexpr unsigned batch_min_errors = 1u;
    static constexpr unsigned batch_max_errors = 3u;

    static constexpr const char* archetype_config_path = "configs/archetypes.json";
    static constexpr const char* summary_capacity_label = "1GB capacity";

    static inline constexpr std::array<AddressType, 0> large_addresses{};
    static inline constexpr std::array<DataType, 0> large_address_patterns{};
    static constexpr uint64_t million_dataset_size = 0ULL;
    static constexpr AddressType million_dataset_base = 0;
    static constexpr unsigned million_dataset_seed = 0u;
    static constexpr unsigned million_dataset_error_upper = 0u;
    static constexpr AddressType stress_test_base = 0;
    static constexpr uint64_t stress_test_count = 0ULL;
    static constexpr unsigned stress_test_seed = 0u;
    static constexpr const char* stress_env_var = "RUN_STRESS_TEST";

    struct Params {
        double energy_per_xor;
        double energy_per_and;
    };

    static Params defaultParams() {
        return {
            gate_energy(28, 0.8, "xor"),
            gate_energy(28, 0.8, "and")
        };
    }
};

struct Hamming64Workload {
    using WordTraits = Hamming64WordTraits;
    using DataType = WordTraits::DataType;
    using AddressType = uint64_t;

    template <typename CodeWord>
    using MemoryContainer = std::map<AddressType, CodeWord>;

    static constexpr AddressType memory_size_words = 16ULL * 1024ULL * 1024ULL * 1024ULL;  // 128GB / 8 bytes
    static constexpr bool include_known_vectors = false;
    static constexpr bool include_batch_fault_injection = false;
    static constexpr bool include_large_address_test = true;
    static constexpr bool include_million_dataset = true;
    static constexpr bool include_stress_test = true;

    struct KnownVector {
        DataType data;
        std::array<uint64_t, 2> encoded;
    };

    static inline constexpr std::array<KnownVector, 0> known_vectors{};

    static inline constexpr std::array<DataType, 5> no_error_data{{
        0x0000000000000000ULL,
        0xFFFFFFFFFFFFFFFFULL,
        0x123456789ABCDEF0ULL,
        0xA5A5A5A5A5A5A5A5ULL,
        0x5A5A5A5A5A5A5A5AULL
    }};
    static constexpr AddressType no_error_base = 0;

    static constexpr DataType single_error_data = 0x123456789ABCDEF0ULL;
    static constexpr AddressType single_error_base = 1000;
    static inline constexpr std::array<int, 14> single_error_positions{{
        1, 2, 3, 4, 5, 8, 15, 16, 20, 32, 40, 64, 70, 72
    }};

    static constexpr DataType double_error_data = 0xAAAAAAAAAAAAAAAAULL;
    static constexpr AddressType double_error_base = 2000;
    static inline constexpr std::array<std::pair<int, int>, 6> double_error_pairs{{
        std::pair<int, int>{1, 3},
        std::pair<int, int>{2, 5},
        std::pair<int, int>{10, 15},
        std::pair<int, int>{20, 25},
        std::pair<int, int>{30, 35},
        std::pair<int, int>{50, 60}
    }};

    static constexpr DataType overall_parity_data = 0x5555555555555555ULL;
    static constexpr AddressType overall_parity_address = 3000;

    static constexpr DataType burst_data = 0x87654321ABCDEF09ULL;
    static constexpr AddressType burst_base = 4000;
    static inline constexpr std::array<std::pair<int, int>, 6> burst_configs{{
        std::pair<int, int>{1, 2},
        std::pair<int, int>{5, 3},
        std::pair<int, int>{10, 4},
        std::pair<int, int>{20, 5},
        std::pair<int, int>{30, 6},
        std::pair<int, int>{50, 8}
    }};

    static constexpr DataType random_multiple_data = 0xDEADBEEFCAFEBABEULL;
    static constexpr AddressType random_multiple_base = 5000;
    static inline constexpr std::array<int, 8> random_error_counts{{3, 4, 5, 6, 7, 8, 10, 12}};

    static constexpr AddressType mixed_workload_base = 6000;
    static constexpr int mixed_workload_iterations = 20;
    static constexpr unsigned mixed_workload_seed = 12345u;

    static inline constexpr std::array<AddressType, 6> large_addresses{{
        0x0ULL,
        0x100000ULL,
        0x40000000ULL,
        0x100000000ULL,
        0x200000000ULL,
        0x300000000ULL
    }};
    static inline constexpr std::array<DataType, 6> large_address_patterns{{
        0x0123456789ABCDEFULL,
        0xFEDCBA9876543210ULL,
        0xAAAAAAAAAAAAAAAAULL,
        0x5555555555555555ULL,
        0xF0F0F0F0F0F0F0F0ULL,
        0x0F0F0F0F0F0F0F0FULL
    }};

    static constexpr uint64_t million_dataset_size = 1000000ULL;
    static constexpr AddressType million_dataset_base = 10000000ULL;
    static constexpr unsigned million_dataset_seed = 42u;
    static constexpr unsigned million_dataset_error_upper = 999u;

    static constexpr AddressType stress_test_base = 50000000ULL;
    static constexpr uint64_t stress_test_count = 1000000ULL;
    static constexpr unsigned stress_test_seed = 1337u;
    static constexpr const char* stress_env_var = "RUN_STRESS_TEST";

    static constexpr const char* archetype_config_path = "configs/archetypes.json";
    static constexpr const char* summary_capacity_label = "128GB capacity";

    struct Params {
        double energy_per_xor;
        double energy_per_and;
    };

    static Params defaultParams() {
        return {0.0, 0.0};
    }

    static Params fromGateEnergies(const GateEnergies& energies) {
        return {energies.xor_energy, energies.and_energy};
    }
};

}  // namespace ecc

