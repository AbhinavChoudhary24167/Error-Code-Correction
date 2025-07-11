#include "SecDaec64.hpp"
#include <gtest/gtest.h>

TEST(SecDaec64, AdjacentDataPairErrors) {
    SecDaec64 codec;
    auto clean = codec.encode(0x12345678abcdefULL);
    auto dataPos = codec.getDataPositions();
    for(size_t i=0; i+1<dataPos.size(); ++i) {
        SecDaec64::CodeWord cw = clean;
        cw.bits.set(dataPos[i], !cw.bits.get(dataPos[i]));
        cw.bits.set(dataPos[i+1], !cw.bits.get(dataPos[i+1]));
        auto res = codec.decode(cw);
        ASSERT_TRUE(res.detected) << "Decoder failed to detect corruption at pair index " << i;
    }
}
