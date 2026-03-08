#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>
#include <random>

#define main practical_sram_simulator_main
#include "../../PracticalSRAMSimulator.cpp"
#undef main

static void require(bool cond, const std::string& msg) {
    if (!cond) {
        throw std::runtime_error(msg);
    }
}

static void runForWidth(int bits) {
    HammingSecdedCodec codec(bits);
    const int n = codec.codewordBits();
    std::vector<uint64_t> values;
    if (bits <= 16) {
        const uint64_t max_data = (1ULL << bits) - 1ULL;
        for (uint64_t d = 0; d <= max_data; ++d) {
            values.push_back(d);
        }
    } else {
        values = {0ULL, 1ULL, 0xFFFFFFFFULL, 0xAAAAAAAAULL, 0x55555555ULL, 0x80000000ULL};
        std::mt19937 rng(12345);
        for (int i = 0; i < 2048; ++i) {
            values.push_back(rng());
        }
    }

    for (uint64_t d : values) {
        const uint64_t cw = codec.encode(d);

        for (int i = 1; i <= n; ++i) {
            uint64_t e = cw;
            flipBit1(e, i);
            DecodeResult r = codec.decode(e);
            require(r.status == DecodeStatus::Corrected,
                    "single-bit error not corrected for bits=" + std::to_string(bits));
            require(r.data == d, "single-bit correction returned wrong data");
        }

        for (int i = 1; i <= n; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                uint64_t e = cw;
                flipBit1(e, i);
                flipBit1(e, j);
                DecodeResult r = codec.decode(e);
                require(r.status == DecodeStatus::DetectedUncorrectable,
                        "double-bit error not flagged uncorrectable");
            }
        }

        bool saw_triple_corrected = false;
        for (int i = 1; i <= n; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                for (int k = j + 1; k <= n; ++k) {
                    uint64_t e = cw;
                    flipBit1(e, i);
                    flipBit1(e, j);
                    flipBit1(e, k);
                    DecodeResult r = codec.decode(e);
                    if (r.status == DecodeStatus::Corrected) {
                        saw_triple_corrected = true;
                    }
                }
            }
        }

        if (saw_triple_corrected) {
            std::cout << "[info] bits=" << bits << " data=0x" << std::hex << d << std::dec
                      << " had triple-error aliases to corrected (expected SEC-DED limitation)\n";
            break;
        }
    }
}

int main() {
    runForWidth(8);
    runForWidth(16);
    runForWidth(32);
    std::cout << "secded brute-force checks passed\n";
    return 0;
}
