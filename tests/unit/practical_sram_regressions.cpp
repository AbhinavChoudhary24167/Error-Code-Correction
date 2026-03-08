#include <cassert>
#include <iostream>
#include <random>

#define main practical_sram_simulator_main
#include "../../PracticalSRAMSimulator.cpp"
#undef main

static void test_secded_triple_detected_uncorrectable() {
    HammingSecdedCodec codec(8);
    const uint64_t cw = codec.encode(0x5A);
    bool found = false;
    for (int i = 1; i <= codec.codewordBits() && !found; ++i) {
        for (int j = i + 1; j <= codec.codewordBits() && !found; ++j) {
            for (int k = j + 1; k <= codec.codewordBits() && !found; ++k) {
                uint64_t e = cw;
                flipBit1(e, i);
                flipBit1(e, j);
                flipBit1(e, k);
                auto r = codec.decode(e);
                if (r.status == DecodeStatus::DetectedUncorrectable) {
                    found = true;
                }
            }
        }
    }
    assert(found && "expected at least one 3-bit pattern to be detected uncorrectable");
}

class AlwaysMiscorrectCodec final : public ECCCodec {
public:
    std::string name() const override { return "AlwaysMiscorrect"; }
    int dataBits() const override { return 8; }
    int codewordBits() const override { return 8; }
    ECCMetadata metadata() const override { return {"AlwaysMiscorrect", 0, "n/a", "n/a"}; }
    uint64_t encode(uint64_t data) const override { return data & 0xFFULL; }
    DecodeResult decode(uint64_t codeword) const override {
        DecodeResult r;
        r.status = DecodeStatus::Corrected;
        r.data = (codeword ^ 0x1ULL) & 0xFFULL;
        r.corrected_codeword = r.data;
        r.corrected_bits = 1;
        return r;
    }
};

class NoopFaultModel final : public FaultModel {
public:
    std::string name() const override { return "noop"; }
    void inject(SRAMSimulator&, std::size_t, std::mt19937&, StressStats&, std::size_t) override {}
};

static void test_miscorrection_counter_path() {
    SRAMConfig cfg{64, 8};
    auto codec = std::make_unique<AlwaysMiscorrectCodec>();
    SRAMSimulator sim(cfg, std::move(codec), 1);
    NoopFaultModel fault;
    StressTestRunner::Options options;
    options.seed = 7;
    options.iterations = 200;
    options.verbose = false;
    options.run_legacy_sweeps = false;
    options.progress_interval = 0;
    auto stats = StressTestRunner::run(sim, fault, options);
    assert(stats.miscorrections > 0 && "miscorrections should increment when read was corrected then downgraded");
}

int main() {
    test_secded_triple_detected_uncorrectable();
    test_miscorrection_counter_path();
    std::cout << "practical SRAM regressions passed\n";
    return 0;
}
