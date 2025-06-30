#ifndef PARITYCHECKMATRIX_HPP
#define PARITYCHECKMATRIX_HPP

#include <array>
#include <cstdint>
#include <vector>
#include "BitVector.hpp"

class ParityCheckMatrix {
public:
    std::vector<std::array<uint64_t,2>> rows;  // up to 128 cols

    BitVector syndrome(const BitVector& cw) const {
        BitVector syn;
        for (std::size_t i = 0; i < rows.size(); ++i) {
            uint64_t a = rows[i][0] & cw.words[0];
            uint64_t b = rows[i][1] & cw.words[1];
            unsigned parity = __builtin_popcountll(a) + __builtin_popcountll(b);
            if (parity & 1)
                syn.set(i, true);
        }
        return syn;
    }
};

#endif // PARITYCHECKMATRIX_HPP
