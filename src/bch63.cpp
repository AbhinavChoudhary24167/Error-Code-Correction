#include "bch63.hpp"

#include <algorithm>
#include <stdexcept>

namespace {
constexpr uint64_t maskForBits(int bits) {
    return bits >= 64 ? UINT64_MAX : ((uint64_t{1} << bits) - 1);
}
}

bool BCH63::Codeword::getBit(int pos) const {
    if (pos < 0 || pos >= N) {
        return false;
    }
    return bits[static_cast<std::size_t>(pos)];
}

void BCH63::Codeword::setBit(int pos, bool value) {
    if (pos < 0 || pos >= N) {
        return;
    }
    bits[static_cast<std::size_t>(pos)] = value;
}

void BCH63::Codeword::flipBit(int pos) {
    if (pos < 0 || pos >= N) {
        return;
    }
    auto index = static_cast<std::size_t>(pos);
    bits[index] = !bits[index];
}

int BCH63::Codeword::countErrors(const Codeword& other) const {
    int count = 0;
    for (int i = 0; i < N; ++i) {
        if (bits[static_cast<std::size_t>(i)] != other.bits[static_cast<std::size_t>(i)]) {
            ++count;
        }
    }
    return count;
}

uint64_t BCH63::Codeword::toUInt64() const {
    uint64_t value = 0;
    for (int i = 0; i < N; ++i) {
        if (bits[static_cast<std::size_t>(i)]) {
            value |= (uint64_t{1} << i);
        }
    }
    return value;
}

BCH63::Codeword BCH63::Codeword::fromUInt64(uint64_t value) {
    Codeword cw;
    for (int i = 0; i < N; ++i) {
        cw.bits[static_cast<std::size_t>(i)] = (value >> i) & 1ULL;
    }
    return cw;
}

BCH63::BCH63() {
    buildField();
    buildGenerator();
}

void BCH63::buildField() {
    alpha_to_.fill(0);
    index_of_.fill(-1);

    alpha_to_[0] = 1;
    for (int i = 1; i < N; ++i) {
        int next = alpha_to_[i - 1] << 1;
        if (next & (1 << M)) {
            next ^= PRIMITIVE_POLY;
        }
        next &= maskForBits(M);
        alpha_to_[i] = next;
    }

    for (int i = 0; i < N; ++i) {
        index_of_[alpha_to_[i]] = i;
    }
    index_of_[0] = -1;
}

void BCH63::buildGenerator() {
    std::vector<bool> visited(N, false);
    generator_ = {1};

    for (int i = 1; i <= 2 * T; ++i) {
        if (visited[static_cast<std::size_t>(i)]) {
            continue;
        }
        auto minimal = minimalPolynomialFor(i % N, visited);
        generator_ = polyMultiplyGF2(generator_, minimal);
    }

    generator_degree_ = static_cast<int>(generator_.size()) - 1;
    k_ = N - generator_degree_;
    generator_mask_ = 0;
    for (std::size_t i = 0; i < generator_.size(); ++i) {
        if (generator_[i]) {
            generator_mask_ |= (uint64_t{1} << i);
        }
    }
}

std::vector<int> BCH63::minimalPolynomialFor(int exponent, std::vector<bool>& visited) const {
    std::vector<int> cls;
    int current = exponent % N;
    do {
        cls.push_back(current);
        visited[static_cast<std::size_t>(current)] = true;
        current = (current * 2) % N;
    } while (current != exponent % N);
    return minimalPolynomialFromClass(cls);
}

std::vector<int> BCH63::minimalPolynomialFromClass(const std::vector<int>& cls) const {
    std::vector<int> poly = {1};
    for (int exp : cls) {
        std::vector<int> next(poly.size() + 1, 0);
        int root = alpha_to_[static_cast<std::size_t>(exp)];
        for (std::size_t i = 0; i < poly.size(); ++i) {
            int coeff = poly[i];
            if (coeff != 0) {
                next[i] ^= gfMul(coeff, root);
            }
            next[i + 1] ^= coeff;
        }
        poly.swap(next);
    }

    // Convert coefficients to GF(2) representation.
    std::vector<int> binary(poly.size(), 0);
    for (std::size_t i = 0; i < poly.size(); ++i) {
        int coeff = poly[i];
        if (coeff == 0) {
            binary[i] = 0;
        } else if (coeff == 1) {
            binary[i] = 1;
        } else {
            throw std::runtime_error("Minimal polynomial has non-binary coefficient");
        }
    }
    while (binary.size() > 1 && binary.back() == 0) {
        binary.pop_back();
    }
    return binary;
}

std::vector<int> BCH63::polyMultiplyGF2(const std::vector<int>& a, const std::vector<int>& b) const {
    std::vector<int> result(a.size() + b.size() - 1, 0);
    for (std::size_t i = 0; i < a.size(); ++i) {
        if (!a[i]) continue;
        for (std::size_t j = 0; j < b.size(); ++j) {
            if (!b[j]) continue;
            result[i + j] ^= 1;
        }
    }
    while (result.size() > 1 && result.back() == 0) {
        result.pop_back();
    }
    return result;
}

uint64_t BCH63::codewordToUInt64(const Codeword& cw) const {
    return cw.toUInt64();
}

uint64_t BCH63::polynomialMod(uint64_t dividend, uint64_t divisor) const {
    if (divisor == 0) {
        throw std::invalid_argument("Divisor cannot be zero");
    }
    int divisor_degree = 63 - __builtin_clzll(divisor);
    while (dividend && (63 - __builtin_clzll(dividend)) >= divisor_degree) {
        int shift = (63 - __builtin_clzll(dividend)) - divisor_degree;
        dividend ^= (divisor << shift);
    }
    return dividend;
}

BCH63::Codeword BCH63::encode(const std::vector<bool>& data_bits) const {
    if (static_cast<int>(data_bits.size()) != k_) {
        throw std::invalid_argument("Data length must be 51 bits");
    }

    uint64_t message = 0;
    for (int i = 0; i < k_; ++i) {
        if (data_bits[static_cast<std::size_t>(i)]) {
            message |= (uint64_t{1} << i);
        }
    }

    uint64_t shifted = message << generator_degree_;
    uint64_t remainder = polynomialMod(shifted, generator_mask_);
    uint64_t codeword_value = shifted ^ remainder;
    codeword_value &= maskForBits(N);

    return Codeword::fromUInt64(codeword_value);
}

std::vector<bool> BCH63::extractData(const Codeword& codeword) const {
    std::vector<bool> data(k_, false);
    for (int i = 0; i < k_; ++i) {
        data[static_cast<std::size_t>(i)] = codeword.getBit(generator_degree_ + i);
    }
    return data;
}

std::array<int, 2 * BCH63::T> BCH63::computeSyndromes(const Codeword& cw) const {
    std::array<int, 2 * T> syndromes{};
    syndromes.fill(0);
    for (int j = 0; j < N; ++j) {
        if (!cw.getBit(j)) {
            continue;
        }
        for (int i = 0; i < 2 * T; ++i) {
            int exponent = ((i + 1) * j) % N;
            syndromes[static_cast<std::size_t>(i)] ^= alpha_to_[static_cast<std::size_t>(exponent)];
        }
    }
    return syndromes;
}

std::vector<int> BCH63::berlekampMassey(const std::array<int, 2 * T>& syndromes) const {
    std::vector<int> C(1, 1);
    std::vector<int> B(1, 1);
    int L = 0;
    int m = 1;
    int b = 1;

    auto polyAdd = [](const std::vector<int>& a, const std::vector<int>& b_vec) {
        std::vector<int> result(std::max(a.size(), b_vec.size()), 0);
        for (std::size_t i = 0; i < result.size(); ++i) {
            int ai = (i < a.size()) ? a[i] : 0;
            int bi = (i < b_vec.size()) ? b_vec[i] : 0;
            result[i] = ai ^ bi;
        }
        while (result.size() > 1 && result.back() == 0) {
            result.pop_back();
        }
        if (result.empty()) {
            result.push_back(0);
        }
        return result;
    };

    auto scaleAndShift = [&](const std::vector<int>& poly, int scalar, int shift) {
        if (scalar == 0) {
            return std::vector<int>{0};
        }
        std::vector<int> result(poly.size() + shift, 0);
        for (std::size_t i = 0; i < poly.size(); ++i) {
            if (poly[i] == 0) continue;
            result[i + shift] = gfMul(poly[i], scalar);
        }
        return result;
    };

    for (int n = 0; n < 2 * T; ++n) {
        int d = syndromes[static_cast<std::size_t>(n)];
        for (int i = 1; i <= L; ++i) {
            if (i >= static_cast<int>(C.size())) break;
            int Ci = C[static_cast<std::size_t>(i)];
            if (Ci != 0 && syndromes[static_cast<std::size_t>(n - i)] != 0) {
                d ^= gfMul(Ci, syndromes[static_cast<std::size_t>(n - i)]);
            }
        }
        if (d == 0) {
            ++m;
            continue;
        }
        int coef = gfMul(d, gfInv(b));
        auto T_poly = C;
        auto adjustment = scaleAndShift(B, coef, m);
        C = polyAdd(C, adjustment);
        if (2 * L <= n) {
            L = n + 1 - L;
            B = T_poly;
            b = d;
            m = 1;
        } else {
            ++m;
        }
    }

    return C;
}

std::vector<int> BCH63::chienSearch(const std::vector<int>& locator) const {
    int degree = static_cast<int>(locator.size()) - 1;
    std::vector<int> locations;
    if (degree <= 0) {
        return locations;
    }
    for (int i = 0; i < N; ++i) {
        int sum = locator[0];
        for (std::size_t j = 1; j < locator.size(); ++j) {
            int coeff = locator[j];
            if (coeff == 0) continue;
            int exponent = ((N - i) * static_cast<int>(j)) % N;
            sum ^= gfMul(coeff, alpha_to_[static_cast<std::size_t>(exponent)]);
        }
        if (sum == 0) {
            locations.push_back(i);
        }
    }
    return locations;
}

BCH63::DecodeResult BCH63::decode(const Codeword& received) const {
    DecodeResult result;
    result.detected = false;
    result.success = false;
    result.corrected = received;
    result.data = extractData(received);

    auto syndromes = computeSyndromes(received);
    for (int value : syndromes) {
        if (value != 0) {
            result.detected = true;
            break;
        }
    }
    if (!result.detected) {
        result.success = true;
        return result;
    }

    auto locator = berlekampMassey(syndromes);
    int degree = static_cast<int>(locator.size()) - 1;
    if (degree <= 0 || degree > T) {
        return result;
    }

    auto error_locations = chienSearch(locator);
    if (static_cast<int>(error_locations.size()) != degree) {
        return result;
    }

    Codeword corrected = received;
    for (int pos : error_locations) {
        corrected.flipBit(pos);
    }

    auto post_syndromes = computeSyndromes(corrected);
    bool cleared = std::all_of(post_syndromes.begin(), post_syndromes.end(), [](int s) { return s == 0; });
    if (!cleared) {
        return result;
    }

    result.success = true;
    result.corrected = corrected;
    result.error_locations = std::move(error_locations);
    result.data = extractData(corrected);
    return result;
}

int BCH63::gfMul(int a, int b) const {
    if (a == 0 || b == 0) {
        return 0;
    }
    int idx = index_of_[static_cast<std::size_t>(a)] + index_of_[static_cast<std::size_t>(b)];
    idx %= (N);
    return alpha_to_[static_cast<std::size_t>(idx)];
}

int BCH63::gfInv(int a) const {
    if (a == 0) {
        throw std::invalid_argument("Cannot invert zero in GF(2^6)");
    }
    int idx = index_of_[static_cast<std::size_t>(a)];
    idx = (N - idx) % N;
    return alpha_to_[static_cast<std::size_t>(idx)];
}

int BCH63::gfDiv(int a, int b) const {
    if (b == 0) {
        throw std::invalid_argument("Cannot divide by zero in GF(2^6)");
    }
    if (a == 0) {
        return 0;
    }
    int idx = index_of_[static_cast<std::size_t>(a)] - index_of_[static_cast<std::size_t>(b)];
    idx %= N;
    if (idx < 0) idx += N;
    return alpha_to_[static_cast<std::size_t>(idx)];
}

