#include "src/bch63.hpp"

#include <algorithm>
#include <vector>

#include <gtest/gtest.h>

namespace {
std::vector<bool> makeMessage(int length) {
    std::vector<bool> msg(length, false);
    for (int i = 0; i < length; ++i) {
        msg[static_cast<std::size_t>(i)] = ((i * 37 + 5) & 1) != 0;
    }
    return msg;
}
}

class BCH63Test : public ::testing::Test {
protected:
    BCH63 bch;
    std::vector<bool> message;
    BCH63::Codeword baseline;

    BCH63Test()
        : message(makeMessage(bch.dataLength())),
          baseline(bch.encode(message)) {}
};

TEST_F(BCH63Test, NoErrorRoundTrip) {
    auto result = bch.decode(baseline);
    EXPECT_FALSE(result.detected);
    EXPECT_TRUE(result.success);
    EXPECT_EQ(result.data, message);
    EXPECT_EQ(result.corrected.countErrors(baseline), 0);
}

TEST_F(BCH63Test, CorrectsSingleBitErrors) {
    for (int pos = 0; pos < BCH63::N; ++pos) {
        auto corrupted = baseline;
        corrupted.flipBit(pos);
        auto result = bch.decode(corrupted);
        EXPECT_TRUE(result.detected) << "Position " << pos;
        EXPECT_TRUE(result.success) << "Position " << pos;
        ASSERT_EQ(result.error_locations.size(), 1u);
        EXPECT_EQ(result.error_locations.front(), pos);
        EXPECT_EQ(result.corrected.countErrors(baseline), 0);
        EXPECT_EQ(result.data, message);
    }
}

TEST_F(BCH63Test, CorrectsDoubleBitErrors) {
    for (int i = 0; i < BCH63::N; ++i) {
        for (int j = i + 1; j < BCH63::N; ++j) {
            auto corrupted = baseline;
            corrupted.flipBit(i);
            corrupted.flipBit(j);
            auto result = bch.decode(corrupted);
            EXPECT_TRUE(result.detected) << "Pair " << i << "," << j;
            EXPECT_TRUE(result.success) << "Pair " << i << "," << j;
            ASSERT_EQ(result.error_locations.size(), 2u);
            auto locations = result.error_locations;
            std::sort(locations.begin(), locations.end());
            std::vector<int> expected{i, j};
            EXPECT_EQ(locations, expected);
            EXPECT_EQ(result.corrected.countErrors(baseline), 0);
            EXPECT_EQ(result.data, message);
        }
    }
}

TEST_F(BCH63Test, DetectsAllTripleBitPatterns) {
    for (int i = 0; i < BCH63::N; ++i) {
        for (int j = i + 1; j < BCH63::N; ++j) {
            for (int k = j + 1; k < BCH63::N; ++k) {
                auto corrupted = baseline;
                corrupted.flipBit(i);
                corrupted.flipBit(j);
                corrupted.flipBit(k);
                auto result = bch.decode(corrupted);
                EXPECT_TRUE(result.detected) << "Triple " << i << "," << j << "," << k;
                EXPECT_FALSE(result.success && result.data == message)
                    << "Triple " << i << "," << j << "," << k;
            }
        }
    }
}

