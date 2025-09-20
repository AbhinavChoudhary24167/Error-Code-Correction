#pragma once

#include <array>
#include <cstdint>
#include <vector>

class BCH63 {
public:
    static constexpr int N = 63;
    static constexpr int M = 6;
    static constexpr int T = 2;

    struct Codeword {
        std::array<bool, N> bits{};

        bool getBit(int pos) const;
        void setBit(int pos, bool value);
        void flipBit(int pos);
        int countErrors(const Codeword& other) const;
        uint64_t toUInt64() const;
        static Codeword fromUInt64(uint64_t value);
    };

    struct DecodeResult {
        Codeword corrected;
        std::vector<bool> data;
        std::vector<int> error_locations;
        bool success{false};
        bool detected{false};
    };

    BCH63();

    Codeword encode(const std::vector<bool>& data_bits) const;
    DecodeResult decode(const Codeword& received) const;
    std::vector<bool> extractData(const Codeword& codeword) const;

    int dataLength() const { return k_; }
    int parityLength() const { return generator_degree_; }
    const std::vector<int>& generatorPolynomial() const { return generator_; }

private:
    static constexpr int PRIMITIVE_POLY = 0x43; // x^6 + x + 1

    std::array<int, N> alpha_to_{};
    std::array<int, (1 << M)> index_of_{};
    std::vector<int> generator_;
    int generator_degree_{};
    int k_{};
    uint64_t generator_mask_{};

    void buildField();
    void buildGenerator();

    std::vector<int> minimalPolynomialFor(int exponent, std::vector<bool>& visited) const;
    std::vector<int> minimalPolynomialFromClass(const std::vector<int>& cls) const;
    std::vector<int> polyMultiplyGF2(const std::vector<int>& a, const std::vector<int>& b) const;

    std::array<int, 2 * T> computeSyndromes(const Codeword& cw) const;
    std::vector<int> berlekampMassey(const std::array<int, 2 * T>& syndromes) const;
    std::vector<int> chienSearch(const std::vector<int>& locator) const;

    uint64_t codewordToUInt64(const Codeword& cw) const;
    uint64_t polynomialMod(uint64_t dividend, uint64_t divisor) const;

    int gfMul(int a, int b) const;
    int gfInv(int a) const;
    int gfDiv(int a, int b) const;
};

