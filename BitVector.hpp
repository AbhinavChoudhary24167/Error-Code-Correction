#ifndef BITVECTOR_HPP
#define BITVECTOR_HPP

#include <array>
#include <cstdint>
#include <cstddef>

struct BitVector {
    std::array<uint64_t,2> words{};

    BitVector() : words{0,0} {}
    BitVector(uint64_t low, uint64_t high=0) : words{low,high} {}

    bool get(std::size_t pos) const {
        if (pos >= 128) return false;
        return (words[pos/64] >> (pos % 64)) & 1ULL;
    }

    void set(std::size_t pos, bool value) {
        if (pos >= 128) return;
        if (value)
            words[pos/64] |= (1ULL << (pos % 64));
        else
            words[pos/64] &= ~(1ULL << (pos % 64));
    }
};

#endif // BITVECTOR_HPP
