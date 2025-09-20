#include <gtest/gtest.h>

#include <string>

#include "src/hamming_sim_configs.hpp"
#include "src/hamming_simulator.hpp"

namespace {

TEST(HammingSimulator32, SingleBitCorrection) {
    using WordTraits = ecc::Hamming32WordTraits;
    using Workload = ecc::Hamming32Workload;
    ecc::AdvancedMemorySimulator<WordTraits, Workload> memory({0.0, 0.0});

    auto address = static_cast<Workload::AddressType>(42);
    auto data = static_cast<WordTraits::DataType>(0x12345678u);
    memory.write(address, data);
    memory.injectError(address, 5);
    auto result = memory.read(address);

    EXPECT_EQ(result.error_type, ecc::HammingCodeSECDED<WordTraits>::SINGLE_ERROR_CORRECTABLE);
    EXPECT_EQ(result.corrected_data, data);
    EXPECT_TRUE(result.data_corrected);
}

TEST(HammingSimulator64, DoubleErrorDetection) {
    using WordTraits = ecc::Hamming64WordTraits;
    using Workload = ecc::Hamming64Workload;
    ecc::AdvancedMemorySimulator<WordTraits, Workload> memory({0.0, 0.0});

    auto address = static_cast<Workload::AddressType>(1024);
    auto data = static_cast<WordTraits::DataType>(0xFEDCBA9876543210ULL);
    memory.write(address, data);
    memory.injectError(address, 5);
    memory.injectError(address, 12);
    auto result = memory.read(address);

    EXPECT_EQ(result.error_type, ecc::HammingCodeSECDED<WordTraits>::DOUBLE_ERROR_DETECTABLE);
    EXPECT_FALSE(result.data_corrected);
}

TEST(HammingSimulatorShared, StatisticsCountsReadsAndWrites) {
    using WordTraits = ecc::Hamming32WordTraits;
    using Workload = ecc::Hamming32Workload;
    ecc::AdvancedMemorySimulator<WordTraits, Workload> memory({0.0, 0.0});

    auto address = static_cast<Workload::AddressType>(7);
    auto data = static_cast<WordTraits::DataType>(0xCAFEBABEu);
    memory.write(address, data);
    auto result = memory.read(address);
    ASSERT_EQ(result.error_type, ecc::HammingCodeSECDED<WordTraits>::NO_ERROR);

    testing::internal::CaptureStdout();
    memory.printStatistics();
    std::string output = testing::internal::GetCapturedStdout();

    EXPECT_NE(output.find("Total Memory Operations"), std::string::npos);
    EXPECT_NE(output.find("Reads"), std::string::npos);
    EXPECT_NE(output.find("Writes"), std::string::npos);
}

}  // namespace

