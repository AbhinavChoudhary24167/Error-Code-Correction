#include <algorithm>
#include <array>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <memory>
#include <numeric>
#include <optional>
#include <fstream>
#include <random>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <cmath>
#include <vector>

enum class DecodeStatus { Clean, Corrected, DetectedUncorrectable, UndetectedError };

struct DecodeResult {
    uint64_t data = 0;
    uint64_t corrected_codeword = 0;
    DecodeStatus status = DecodeStatus::Clean;
    int corrected_bits = 0;
    int syndrome = 0;
    std::string detail;
};

struct ECCMetadata {
    std::string name;
    int parity_bits = 0;
    std::string correction_capability;
    std::string detection_capability;
};

static uint64_t maskBits(int bits) {
    if (bits <= 0) {
        return 0;
    }
    if (bits >= 64) {
        return ~0ULL;
    }
    return (1ULL << bits) - 1ULL;
}

static bool getBit1(uint64_t v, int pos1) { return ((v >> (pos1 - 1)) & 1ULL) != 0; }
static void setBit1(uint64_t& v, int pos1, bool b) {
    if (b) {
        v |= (1ULL << (pos1 - 1));
    } else {
        v &= ~(1ULL << (pos1 - 1));
    }
}
static void flipBit1(uint64_t& v, int pos1) { v ^= (1ULL << (pos1 - 1)); }

class ECCCodec {
public:
    virtual ~ECCCodec() = default;
    virtual std::string name() const = 0;
    virtual int dataBits() const = 0;
    virtual int codewordBits() const = 0;
    virtual ECCMetadata metadata() const = 0;
    virtual uint64_t encode(uint64_t data) const = 0;
    virtual DecodeResult decode(uint64_t codeword) const = 0;
    virtual uint64_t dataMask() const { return maskBits(dataBits()); }
};

class HammingSecdedCodec final : public ECCCodec {
public:
    explicit HammingSecdedCodec(int data_bits)
        : data_bits_(data_bits),
          parity_bits_(requiredParityBits(data_bits)),
          total_bits_(data_bits + parity_bits_ + 1),
          parity_positions_(buildParityPositions(parity_bits_)),
          data_positions_(buildDataPositions(total_bits_, parity_positions_)) {
        if (data_bits_ <= 0 || data_bits_ > 57) {
            throw std::invalid_argument("SEC-DED data_bits must be in [1,57]");
        }
    }

    std::string name() const override { return "SEC-DED"; }
    int dataBits() const override { return data_bits_; }
    int codewordBits() const override { return total_bits_; }

    ECCMetadata metadata() const override {
        return ECCMetadata{"SEC-DED", parity_bits_ + 1, "Corrects 1 bit", "Detects 2-bit errors"};
    }

    uint64_t encode(uint64_t data) const override {
        const uint64_t masked_data = data & dataMask();
        uint64_t codeword = 0;

        for (int i = 0; i < data_bits_; ++i) {
            if ((masked_data >> i) & 1ULL) {
                setBit1(codeword, data_positions_[i], true);
            }
        }

        for (int parity_pos : parity_positions_) {
            int parity = 0;
            for (int pos = 1; pos <= total_bits_ - 1; ++pos) {
                if ((pos & parity_pos) && getBit1(codeword, pos)) {
                    parity ^= 1;
                }
            }
            setBit1(codeword, parity_pos, parity != 0);
        }

        int overall_parity = 0;
        for (int pos = 1; pos <= total_bits_ - 1; ++pos) {
            if (getBit1(codeword, pos)) {
                overall_parity ^= 1;
            }
        }
        setBit1(codeword, total_bits_, overall_parity != 0);
        return codeword & maskBits(total_bits_);
    }

    DecodeResult decode(uint64_t received) const override {
        DecodeResult result;
        uint64_t working = received & maskBits(total_bits_);

        for (int i = 0; i < parity_bits_; ++i) {
            const int parity_pos = parity_positions_[i];
            int parity = 0;
            for (int pos = 1; pos <= total_bits_ - 1; ++pos) {
                if ((pos & parity_pos) && getBit1(working, pos)) {
                    parity ^= 1;
                }
            }
            if (parity) {
                result.syndrome |= (1 << i);
            }
        }

        int overall = 0;
        for (int pos = 1; pos <= total_bits_; ++pos) {
            if (getBit1(working, pos)) {
                overall ^= 1;
            }
        }
        const bool overall_parity_odd = (overall != 0);

        if (result.syndrome == 0 && !overall_parity_odd) {
            result.status = DecodeStatus::Clean;
            result.detail = "No detected error";
        } else if (result.syndrome == 0 && overall_parity_odd) {
            result.status = DecodeStatus::Corrected;
            flipBit1(working, total_bits_);
            result.corrected_bits = 1;
            result.detail = "Corrected overall parity bit";
        } else if (result.syndrome != 0 && overall_parity_odd) {
            if (result.syndrome < 1 || result.syndrome > total_bits_ - 1) {
                result.status = DecodeStatus::DetectedUncorrectable;
                result.detail = "Syndrome out of valid range — likely 3+ bit error";
            } else {
                result.status = DecodeStatus::Corrected;
                flipBit1(working, result.syndrome);
                result.corrected_bits = 1;
                result.detail = "Corrected by syndrome";
            }
        } else {
            result.status = DecodeStatus::DetectedUncorrectable;
            result.detail = "Detected uncorrectable multi-bit error";
        }

        result.data = extractData(working);
        result.corrected_codeword = working;
        return result;
    }

private:
    int data_bits_;
    int parity_bits_;
    int total_bits_;
    std::vector<int> parity_positions_;
    std::vector<int> data_positions_;

    static int requiredParityBits(int data_bits) {
        int p = 0;
        while ((1 << p) < (data_bits + p + 1)) {
            ++p;
        }
        return p;
    }

    static std::vector<int> buildParityPositions(int parity_bits) {
        std::vector<int> positions;
        for (int i = 0; i < parity_bits; ++i) {
            positions.push_back(1 << i);
        }
        return positions;
    }

    static std::vector<int> buildDataPositions(int total_bits, const std::vector<int>& parity_positions) {
        std::vector<int> data_positions;
        for (int pos = 1; pos <= total_bits - 1; ++pos) {
            if (std::find(parity_positions.begin(), parity_positions.end(), pos) == parity_positions.end()) {
                data_positions.push_back(pos);
            }
        }
        return data_positions;
    }

    uint64_t extractData(uint64_t codeword) const {
        uint64_t data = 0;
        for (int i = 0; i < data_bits_; ++i) {
            if (getBit1(codeword, data_positions_[i])) {
                data |= (1ULL << i);
            }
        }
        return data;
    }
};

// Parity is computed via a non-cryptographic XOR-fold hash.
// Minimum Hamming distance is NOT guaranteed algebraically.
// Error correction is done by exhaustive candidate search (O(n^w) per decode
// where w is the maximum correction weight). This is NOT a BCH or standard
// TAEC code. Rename prefix "Hash" reflects the actual construction.
class ChecksumSearchCodecBase : public ECCCodec {
public:
    ChecksumSearchCodecBase(std::string codec_name,
                            int data_bits,
                            int parity_bits,
                            int max_search_weight,
                            int adjacent_limit,
                            std::string corr_cap,
                            std::string det_cap)
        : codec_name_(std::move(codec_name)),
          data_bits_(data_bits),
          parity_bits_(parity_bits),
          total_bits_(data_bits + parity_bits),
          max_search_weight_(max_search_weight),
          adjacent_limit_(adjacent_limit),
          corr_capability_(std::move(corr_cap)),
          det_capability_(std::move(det_cap)) {
        if (data_bits_ <= 0 || data_bits_ > 32) {
            throw std::invalid_argument("data_bits must be in [1,32]");
        }
        if (total_bits_ > 63) {
            throw std::invalid_argument("codeword too large for uint64 container");
        }
    }

    std::string name() const override { return codec_name_; }
    int dataBits() const override { return data_bits_; }
    int codewordBits() const override { return total_bits_; }

    ECCMetadata metadata() const override {
        return ECCMetadata{codec_name_, parity_bits_, corr_capability_, det_capability_};
    }

    uint64_t encode(uint64_t data) const override {
        const uint64_t payload = data & dataMask();
        const uint64_t p = computeParity(payload) & maskBits(parity_bits_);
        return payload | (p << data_bits_);
    }

    DecodeResult decode(uint64_t codeword) const override {
        const uint64_t clipped = codeword & maskBits(total_bits_);
        const uint64_t raw_data = clipped & dataMask();
        const uint64_t stored_p = (clipped >> data_bits_) & maskBits(parity_bits_);

        DecodeResult result;
        result.corrected_codeword = clipped;
        result.data = raw_data;

        if (stored_p == (computeParity(raw_data) & maskBits(parity_bits_))) {
            result.status = DecodeStatus::Clean;
            result.detail = "Checksum matched";
            return result;
        }

        std::vector<uint64_t> candidates;
        std::vector<int> weights;
        searchCandidates(clipped, candidates, weights);

        if (candidates.size() == 1) {
            result.status = DecodeStatus::Corrected;
            result.corrected_codeword = candidates.front();
            result.data = candidates.front() & dataMask();
            result.corrected_bits = weights.front();
            result.detail = "Pattern search corrected";
            return result;
        }

        result.status = DecodeStatus::DetectedUncorrectable;
        if (candidates.empty()) {
            result.detail = "No valid correction candidate";
        } else {
            result.detail = "Ambiguous correction candidates";
        }
        return result;
    }

protected:
    virtual uint64_t computeParity(uint64_t payload) const {
        uint64_t parity = 0;
        for (int i = 0; i < parity_bits_; ++i) {
            uint64_t x = payload ^ (payload >> ((i % 7) + 1));
            x ^= (x >> 13);
            x ^= (x >> 7);
            x ^= (x >> 3);
            const int bit = static_cast<int>(x & 1ULL);
            parity |= (static_cast<uint64_t>(bit) << i);
        }
        return parity;
    }

private:
    std::string codec_name_;
    int data_bits_;
    int parity_bits_;
    int total_bits_;
    int max_search_weight_;
    int adjacent_limit_;
    std::string corr_capability_;
    std::string det_capability_;

    bool passesAdjacencyConstraint(const std::vector<int>& positions) const {
        if (adjacent_limit_ <= 0 || positions.empty()) {
            return true;
        }
        const int minp = *std::min_element(positions.begin(), positions.end());
        const int maxp = *std::max_element(positions.begin(), positions.end());
        return (maxp - minp + 1) <= adjacent_limit_;
    }

    bool isCodewordValid(uint64_t cw) const {
        const uint64_t payload = cw & dataMask();
        const uint64_t p = (cw >> dataBits()) & maskBits(codewordBits() - dataBits());
        return p == (computeParity(payload) & maskBits(codewordBits() - dataBits()));
    }

    void searchCandidates(uint64_t clipped, std::vector<uint64_t>& candidates, std::vector<int>& weights) const {
        const int n = codewordBits();
        for (int i = 1; i <= n; ++i) {
            uint64_t c1 = clipped;
            flipBit1(c1, i);
            if (isCodewordValid(c1)) {
                candidates.push_back(c1);
                weights.push_back(1);
            }
        }
        if (max_search_weight_ < 2) {
            return;
        }
        for (int i = 1; i <= n; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                std::vector<int> p{i, j};
                if (!passesAdjacencyConstraint(p)) {
                    continue;
                }
                uint64_t c2 = clipped;
                flipBit1(c2, i);
                flipBit1(c2, j);
                if (isCodewordValid(c2)) {
                    candidates.push_back(c2);
                    weights.push_back(2);
                }
            }
        }
        if (max_search_weight_ < 3) {
            return;
        }
        for (int i = 1; i <= n; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                for (int k = j + 1; k <= n; ++k) {
                    std::vector<int> p{i, j, k};
                    if (!passesAdjacencyConstraint(p)) {
                        continue;
                    }
                    uint64_t c3 = clipped;
                    flipBit1(c3, i);
                    flipBit1(c3, j);
                    flipBit1(c3, k);
                    if (isCodewordValid(c3)) {
                        candidates.push_back(c3);
                        weights.push_back(3);
                    }
                }
            }
        }
    }
};

class HashAEC3Codec final : public ChecksumSearchCodecBase {
public:
    explicit HashAEC3Codec(int data_bits)
        : ChecksumSearchCodecBase("HashAEC3", data_bits, 12, 3, 3,
                                  "Probabilistic correction up to 3 adjacent flips (search-based)",
                                  "Probabilistic detection via 12-bit checksum") {}
};

class HashEC2Codec final : public ChecksumSearchCodecBase {
public:
    explicit HashEC2Codec(int data_bits)
        : ChecksumSearchCodecBase("HashEC2", data_bits, 16, 2, 0,
                                  "Probabilistic correction up to 2 bit flips (search-based)",
                                  "Probabilistic detection via 16-bit checksum") {}
};

// This is a CRC-8-aided Reed-Muller code, NOT a standard polar code.
// Frozen positions are assigned as the first (n - total_info_bits) indices,
// NOT by Bhattacharyya parameter or Gaussian approximation ordering.
// The decoder uses single-flip exhaustive search, not successive cancellation.
// Published polar code BER curves are not directly comparable to this codec.
class PolarCodec final : public ECCCodec {
public:
    explicit PolarCodec(int data_bits)
        : data_bits_(data_bits),
          crc_bits_(8),
          total_info_bits_(data_bits + crc_bits_),
          n_(nextPow2(total_info_bits_)),
          frozen_(n_, true),
          info_positions_(buildInfoPositions(n_, total_info_bits_)) {
        if (data_bits_ <= 0 || data_bits_ > 32) {
            throw std::invalid_argument("Polar data_bits must be in [1,32]");
        }
        if (n_ > 64) {
            throw std::invalid_argument("Polar shortened length exceeded 64 bits");
        }
        for (int pos : info_positions_) {
            frozen_[pos] = false;
        }
    }

    std::string name() const override { return "CRC-RM"; }
    int dataBits() const override { return data_bits_; }
    int codewordBits() const override { return n_; }

    ECCMetadata metadata() const override {
        return ECCMetadata{"CRC-RM", n_ - data_bits_,
                           "CRC-aided single-flip search correction (heuristic)",
                           "CRC8 + frozen-bit constraints detect many multi-bit errors"};
    }

    uint64_t encode(uint64_t data) const override {
        const uint64_t payload = data & dataMask();
        const uint8_t crc = crc8(payload, data_bits_);
        std::vector<int> u(n_, 0);
        std::vector<int> info_bits;
        info_bits.reserve(total_info_bits_);
        for (int i = 0; i < data_bits_; ++i) {
            info_bits.push_back(static_cast<int>((payload >> i) & 1ULL));
        }
        for (int i = 0; i < crc_bits_; ++i) {
            info_bits.push_back((crc >> i) & 1U);
        }
        for (std::size_t i = 0; i < info_positions_.size(); ++i) {
            u[info_positions_[i]] = info_bits[i];
        }
        polarTransform(u);

        uint64_t x = 0;
        for (int i = 0; i < n_; ++i) {
            if (u[i]) {
                x |= (1ULL << i);
            }
        }
        return x;
    }

    DecodeResult decode(uint64_t codeword) const override {
        DecodeResult result;
        const uint64_t clipped = codeword & maskBits(n_);

        auto tryDecode = [&](uint64_t candidate) -> std::optional<uint64_t> {
            std::vector<int> x(n_, 0);
            for (int i = 0; i < n_; ++i) {
                x[i] = static_cast<int>((candidate >> i) & 1ULL);
            }
            polarTransform(x); // inverse for F^n over GF(2)

            for (int i = 0; i < n_; ++i) {
                if (frozen_[i] && x[i] != 0) {
                    return std::nullopt;
                }
            }

            uint64_t payload = 0;
            uint8_t rx_crc = 0;
            for (int i = 0; i < data_bits_; ++i) {
                const int b = x[info_positions_[i]];
                payload |= (static_cast<uint64_t>(b) << i);
            }
            for (int i = 0; i < crc_bits_; ++i) {
                const int b = x[info_positions_[data_bits_ + i]];
                rx_crc |= static_cast<uint8_t>(b << i);
            }
            if (rx_crc != crc8(payload, data_bits_)) {
                return std::nullopt;
            }
            return payload & dataMask();
        };

        if (auto d = tryDecode(clipped)) {
            result.status = DecodeStatus::Clean;
            result.data = *d;
            result.corrected_codeword = clipped;
            result.detail = "CRC/frozen constraints satisfied";
            return result;
        }

        std::optional<uint64_t> recovered;
        int corrected_pos = -1;
        for (int i = 0; i < n_; ++i) {
            uint64_t candidate = clipped ^ (1ULL << i);
            auto d = tryDecode(candidate);
            if (!d) {
                continue;
            }
            if (recovered.has_value()) {
                result.status = DecodeStatus::DetectedUncorrectable;
                result.data = *d;
                result.corrected_codeword = candidate;
                result.detail = "Ambiguous single-flip correction candidates";
                return result;
            }
            recovered = d;
            corrected_pos = i;
        }

        if (recovered.has_value()) {
            result.status = DecodeStatus::Corrected;
            result.data = *recovered;
            result.corrected_codeword = clipped ^ (1ULL << corrected_pos);
            result.corrected_bits = 1;
            result.detail = "CRC-aided single-bit correction";
            return result;
        }

        result.status = DecodeStatus::DetectedUncorrectable;
        result.data = clipped & dataMask();
        result.corrected_codeword = clipped;
        result.detail = "Failed CRC-aided decode";
        return result;
    }

private:
    int data_bits_;
    int crc_bits_;
    int total_info_bits_;
    int n_;
    std::vector<bool> frozen_;
    std::vector<int> info_positions_;

    static int nextPow2(int x) {
        int n = 1;
        while (n < x) {
            n <<= 1;
        }
        return n;
    }

    static std::vector<int> buildInfoPositions(int n, int info_bits) {
        std::vector<int> positions;
        positions.reserve(info_bits);
        for (int i = n - info_bits; i < n; ++i) {
            positions.push_back(i);
        }
        return positions;
    }

    static void polarTransform(std::vector<int>& bits) {
        const int n = static_cast<int>(bits.size());
        for (int len = 1; len < n; len <<= 1) {
            for (int i = 0; i < n; i += (len << 1)) {
                for (int j = 0; j < len; ++j) {
                    bits[i + j] ^= bits[i + j + len];
                }
            }
        }
    }

    // CRC-8/ROHC: poly=0x07, init=0xFF, no final XOR, MSB-first bit processing.
    // Internally consistent for ECC purposes; not interoperable with CRC-8/SMBUS.
    static uint8_t crc8(uint64_t payload, int data_bits) {
        uint8_t crc = 0xFF;
        constexpr uint8_t poly = 0x07;
        for (int i = data_bits - 1; i >= 0; --i) {
            const uint8_t in = static_cast<uint8_t>((payload >> i) & 1ULL);
            const uint8_t mix = static_cast<uint8_t>(((crc >> 7) & 1U) ^ in);
            crc <<= 1;
            if (mix) {
                crc ^= poly;
            }
        }
        return crc;
    }
};

static std::unique_ptr<ECCCodec> createCodec(const std::string& codec_name, int word_bits) {
    if (codec_name == "secded") {
        return std::make_unique<HammingSecdedCodec>(word_bits);
    }
    if (codec_name == "taec" || codec_name == "hashaec3") {
        return std::make_unique<HashAEC3Codec>(word_bits);
    }
    if (codec_name == "bch" || codec_name == "hashec2") {
        return std::make_unique<HashEC2Codec>(word_bits);
    }
    if (codec_name == "polar" || codec_name == "crcrm") {
        return std::make_unique<PolarCodec>(word_bits);
    }
    throw std::invalid_argument("Unknown codec: " + codec_name);
}

static const char* statusToString(DecodeStatus status) {
    switch (status) {
        case DecodeStatus::Clean:
            return "clean read";
        case DecodeStatus::Corrected:
            return "corrected read";
        case DecodeStatus::DetectedUncorrectable:
            return "detected uncorrectable error";
        case DecodeStatus::UndetectedError:
            return "undetected error";
    }
    return "unknown";
}

struct SRAMConfig {
    std::size_t total_bytes = 0;
    int word_width_bits = 0;
};

struct StressStats {
    std::uint64_t total_reads = 0;
    std::uint64_t total_writes = 0;
    std::uint64_t injected_single = 0;
    std::uint64_t injected_burst = 0;
    std::uint64_t injected_random_multi = 0;
    std::uint64_t corrected_errors = 0;
    std::uint64_t detected_uncorrectable = 0;
    std::uint64_t undetected_errors = 0;
    std::uint64_t miscorrections = 0;
    std::uint64_t encode_ops = 0;
    std::uint64_t decode_ops = 0;
    std::uint64_t correction_ops = 0;

    double correctionRate() const {
        const double denom = static_cast<double>(corrected_errors + detected_uncorrectable + undetected_errors);
        return denom == 0.0 ? 0.0 : static_cast<double>(corrected_errors) / denom;
    }

    double detectionRate() const {
        const double denom = static_cast<double>(corrected_errors + detected_uncorrectable + undetected_errors);
        return denom == 0.0 ? 0.0 : static_cast<double>(corrected_errors + detected_uncorrectable) / denom;
    }

    double sdcRate() const {
        return total_reads == 0 ? 0.0 : static_cast<double>(undetected_errors) / static_cast<double>(total_reads);
    }
};

struct ConfidenceInterval {
    double mean = 0.0;
    double lower = 0.0;
    double upper = 0.0;
};

struct ResearchMetrics {
    int parity_bits = 0;
    double codeword_expansion_pct = 0.0;
    double heuristic_energy_score = 0.0;
    double heuristic_latency_score = 0.0;
    double correction_success_pct = 0.0;
    double detection_success_pct = 0.0;
    double sdc_pct = 0.0;
    double miscorrection_pct = 0.0;
    double effective_protection_score = 0.0;
};

struct CampaignResult {
    std::string codec;
    SRAMConfig config;
    std::string fault_model;
    std::size_t iterations = 0;
    StressStats stats;
    ResearchMetrics metrics;
    ConfidenceInterval sdc_ci;
    ConfidenceInterval undetected_ci;
};

class SRAMSimulator {
public:
    struct ReadResult {
        uint64_t data = 0;
        DecodeStatus status = DecodeStatus::Clean;
        int syndrome = 0;
        bool mismatch_vs_golden = false;
        bool was_miscorrected = false;
    };

    SRAMSimulator(SRAMConfig cfg, std::unique_ptr<ECCCodec> codec, std::uint32_t seed = 1234567)
        : cfg_(cfg),
          codec_(std::move(codec)),
          depth_words_(computeDepth(cfg.total_bytes, cfg.word_width_bits)),
          memory_(depth_words_, codec_->encode(0)),
          golden_(depth_words_, 0),
          rng_(seed) {
        if (!codec_) {
            throw std::invalid_argument("codec must not be null");
        }
        if (codec_->dataBits() != cfg.word_width_bits) {
            throw std::invalid_argument("codec data bits must match word width");
        }
    }

    std::size_t depthWords() const { return depth_words_; }
    SRAMConfig config() const { return cfg_; }
    const ECCCodec& codec() const { return *codec_; }

    void write(std::size_t address, uint64_t data) {
        checkAddress(address);
        const uint64_t masked = data & codec_->dataMask();
        golden_[address] = masked;
        memory_[address] = codec_->encode(masked);
    }

    ReadResult read(std::size_t address) {
        checkAddress(address);
        DecodeResult decoded = codec_->decode(memory_[address]);

        ReadResult rr;
        rr.data = decoded.data;
        rr.status = decoded.status;
        rr.syndrome = decoded.syndrome;
        rr.mismatch_vs_golden = (rr.data != golden_[address]);

        if (decoded.status == DecodeStatus::Corrected) {
            memory_[address] = codec_->encode(decoded.data);
        }
        if ((decoded.status == DecodeStatus::Clean || decoded.status == DecodeStatus::Corrected) && rr.mismatch_vs_golden) {
            if (decoded.status == DecodeStatus::Corrected) {
                rr.was_miscorrected = true;
            }
            rr.status = DecodeStatus::UndetectedError;
        }

        return rr;
    }

    void injectSingleBitFault(std::size_t address, int bit_position_1_based) {
        checkAddress(address);
        checkBitPosition(bit_position_1_based);
        memory_[address] ^= (1ULL << (bit_position_1_based - 1));
    }

    void injectBurstFault(std::size_t address, int start_position_1_based, int burst_length) {
        checkAddress(address);
        if (burst_length <= 0) {
            throw std::out_of_range("burst_length must be positive");
        }
        for (int i = 0; i < burst_length; ++i) {
            int pos = start_position_1_based + i;
            if (pos >= 1 && pos <= codec_->codewordBits()) {
                memory_[address] ^= (1ULL << (pos - 1));
            }
        }
    }

    void injectRandomFaults(std::size_t address, int count) {
        checkAddress(address);
        if (count <= 0) {
            return;
        }
        std::uniform_int_distribution<int> dist(1, codec_->codewordBits());
        for (int i = 0; i < count; ++i) {
            injectSingleBitFault(address, dist(rng_));
        }
    }

    void injectFaultPositions(std::size_t address, const std::vector<int>& bit_positions_1_based) {
        checkAddress(address);
        for (int pos : bit_positions_1_based) {
            if (pos >= 1 && pos <= codec_->codewordBits()) {
                memory_[address] ^= (1ULL << (pos - 1));
            }
        }
    }

    void injectRowFault(std::size_t row_start, std::size_t row_length, int bit_position_1_based) {
        checkBitPosition(bit_position_1_based);
        const std::size_t end = std::min(depth_words_, row_start + row_length);
        for (std::size_t a = row_start; a < end; ++a) {
            memory_[a] ^= (1ULL << (bit_position_1_based - 1));
        }
    }

    void injectColumnFault(int bit_position_1_based, std::size_t stride) {
        checkBitPosition(bit_position_1_based);
        if (stride == 0) {
            stride = 1;
        }
        for (std::size_t a = 0; a < depth_words_; a += stride) {
            memory_[a] ^= (1ULL << (bit_position_1_based - 1));
        }
    }

    void applyFaultMap(const std::map<std::size_t, std::set<int>>& fault_map) {
        for (const auto& kv : fault_map) {
            if (kv.first >= depth_words_) {
                continue;
            }
            for (int pos : kv.second) {
                if (pos >= 1 && pos <= codec_->codewordBits()) {
                    memory_[kv.first] ^= (1ULL << (pos - 1));
                }
            }
        }
    }

    std::size_t randomAddress(std::mt19937& rng) const {
        std::uniform_int_distribution<std::size_t> addr_dist(0, depth_words_ - 1);
        return addr_dist(rng);
    }

    int randomBitPosition(std::mt19937& rng) const {
        std::uniform_int_distribution<int> bit_dist(1, codec_->codewordBits());
        return bit_dist(rng);
    }

    bool injectUndetectedPattern(std::size_t address, int max_weight = 4) {
        checkAddress(address);
        if (max_weight < 2 || codec_->codewordBits() > 40) {
            if (codec_->codewordBits() > 40) {
                std::cerr << "[warn] injectUndetectedPattern: codeword too wide ("
                          << codec_->codewordBits() << " bits); skipping O(n^4) search\n";
            }
            return false;
        }

        const uint64_t base = memory_[address];
        for (int i = 1; i <= codec_->codewordBits(); ++i) {
            for (int j = i + 1; j <= codec_->codewordBits(); ++j) {
                for (int k = j + 1; k <= codec_->codewordBits(); ++k) {
                    for (int l = k + 1; l <= codec_->codewordBits(); ++l) {
                        uint64_t cand = base;
                        flipBit1(cand, i);
                        flipBit1(cand, j);
                        flipBit1(cand, k);
                        flipBit1(cand, l);
                        DecodeResult dr = codec_->decode(cand);
                        if ((dr.status == DecodeStatus::Clean || dr.status == DecodeStatus::Corrected) &&
                            dr.data != golden_[address]) {
                            memory_[address] = cand;
                            return true;
                        }
                    }
                }
            }
        }
        return false;
    }

private:
    SRAMConfig cfg_;
    std::unique_ptr<ECCCodec> codec_;
    std::size_t depth_words_;
    std::vector<uint64_t> memory_;
    std::vector<uint64_t> golden_;
    std::mt19937 rng_;

    static std::size_t computeDepth(std::size_t total_bytes, int word_width_bits) {
        if (word_width_bits % 8 != 0 || word_width_bits <= 0) {
            throw std::invalid_argument("word_width_bits must be positive and byte-aligned");
        }
        return total_bytes / static_cast<std::size_t>(word_width_bits / 8);
    }

    void checkAddress(std::size_t address) const {
        if (address >= depth_words_) {
            throw std::out_of_range("address out of range");
        }
    }

    void checkBitPosition(int bit_position_1_based) const {
        if (bit_position_1_based < 1 || bit_position_1_based > codec_->codewordBits()) {
            throw std::out_of_range("bit position out of range");
        }
    }
};


class FaultModel {
public:
    virtual ~FaultModel() = default;
    virtual std::string name() const = 0;
    virtual void inject(SRAMSimulator& sim,
                        std::size_t address,
                        std::mt19937& rng,
                        StressStats& stats,
                        std::size_t iteration) = 0;
};

class LegacyMixedFaultModel final : public FaultModel {
public:
    std::string name() const override { return "legacy_mixed"; }

    void inject(SRAMSimulator& sim, std::size_t address, std::mt19937& rng, StressStats& stats,
                std::size_t /*iteration*/) override {
        std::uniform_int_distribution<int> op_dist(0, 99);
        std::uniform_int_distribution<int> burst_len_dist(2, 5);
        std::uniform_int_distribution<int> random_fault_count(2, 4);
        const int op = op_dist(rng);
        if (op < 50) {
            sim.injectSingleBitFault(address, sim.randomBitPosition(rng));
            ++stats.injected_single;
        } else if (op < 80) {
            std::uniform_int_distribution<int> start_dist(1, std::max(1, sim.codec().codewordBits() - 4));
            sim.injectBurstFault(address, start_dist(rng), burst_len_dist(rng));
            ++stats.injected_burst;
        } else {
            sim.injectRandomFaults(address, random_fault_count(rng));
            ++stats.injected_random_multi;
        }
    }
};

struct FaultModelConfig {
    std::string model = "legacy";
    int adjacency_radius = 1;
    std::string adjacency_shape = "horizontal";
    std::size_t row_length = 64;
    std::size_t column_stride = 64;
    double retention_probability = 0.01;
    double soft_error_rate = 0.005;
    double burst_geo_p = 0.35;
    double fault_map_probability = 0.0001;
};

class AdvancedFaultModel final : public FaultModel {
public:
    explicit AdvancedFaultModel(FaultModelConfig cfg) : cfg_(std::move(cfg)) {}

    std::string name() const override { return cfg_.model; }

    void inject(SRAMSimulator& sim, std::size_t address, std::mt19937& rng, StressStats& stats,
                std::size_t iteration) override {
        maybeInitFaultMap(sim, rng);
        if (cfg_.model == "adjacent") {
            applyAdjacent(sim, address, rng, stats);
        } else if (cfg_.model == "row") {
            applyRow(sim, rng, stats);
        } else if (cfg_.model == "column") {
            applyColumn(sim, rng, stats);
        } else if (cfg_.model == "retention") {
            applyRetention(sim, address, rng, stats, iteration);
        } else if (cfg_.model == "soft") {
            applySoft(sim, address, rng, stats);
        } else if (cfg_.model == "geoburst") {
            applyGeometricBurst(sim, address, rng, stats);
        } else if (cfg_.model == "faultmap") {
            sim.applyFaultMap(fault_map_);
            ++stats.injected_random_multi;
        } else {
            fallback_.inject(sim, address, rng, stats, iteration);
        }
    }

private:
    FaultModelConfig cfg_;
    std::map<std::size_t, std::set<int>> fault_map_;
    bool fault_map_initialized_ = false;
    std::map<std::size_t, std::vector<int>> delayed_retention_;
    LegacyMixedFaultModel fallback_;

    void maybeInitFaultMap(SRAMSimulator& sim, std::mt19937& rng) {
        if (cfg_.model != "faultmap" || fault_map_initialized_) {
            return;
        }
        std::bernoulli_distribution defect(cfg_.fault_map_probability);
        for (std::size_t a = 0; a < sim.depthWords(); ++a) {
            for (int b = 1; b <= sim.codec().codewordBits(); ++b) {
                if (defect(rng)) {
                    fault_map_[a].insert(b);
                }
            }
        }
        fault_map_initialized_ = true;
    }

    void applyAdjacent(SRAMSimulator& sim, std::size_t address, std::mt19937& rng, StressStats& stats) {
        const int center = sim.randomBitPosition(rng);
        std::vector<int> positions{center};
        if (cfg_.adjacency_shape == "clustered") {
            for (int d = 1; d <= cfg_.adjacency_radius; ++d) {
                positions.push_back(center + d);
                positions.push_back(center - d);
            }
        } else {
            const int step = (cfg_.adjacency_shape == "vertical") ? 2 : 1;
            for (int d = 1; d <= cfg_.adjacency_radius; ++d) {
                positions.push_back(center + d * step);
            }
        }
        sim.injectFaultPositions(address, positions);
        ++stats.injected_random_multi;
    }

    void applyRow(SRAMSimulator& sim, std::mt19937& rng, StressStats& stats) {
        const std::size_t max_start = sim.depthWords() > cfg_.row_length ? sim.depthWords() - cfg_.row_length : 0;
        std::uniform_int_distribution<std::size_t> row_dist(0, max_start);
        sim.injectRowFault(row_dist(rng), cfg_.row_length, sim.randomBitPosition(rng));
        ++stats.injected_random_multi;
    }

    void applyColumn(SRAMSimulator& sim, std::mt19937& rng, StressStats& stats) {
        sim.injectColumnFault(sim.randomBitPosition(rng), cfg_.column_stride == 0 ? 1 : cfg_.column_stride);
        ++stats.injected_random_multi;
    }

    void applyRetention(SRAMSimulator& sim, std::size_t address, std::mt19937& rng, StressStats& stats,
                        std::size_t iteration) {
        auto it = delayed_retention_.find(iteration);
        if (it != delayed_retention_.end()) {
            sim.injectFaultPositions(address, it->second);
            ++stats.injected_random_multi;
            delayed_retention_.erase(it);
        }

        std::bernoulli_distribution trigger(cfg_.retention_probability);
        if (trigger(rng)) {
            std::uniform_int_distribution<int> delay_dist(1, 8);
            delayed_retention_[iteration + static_cast<std::size_t>(delay_dist(rng))].push_back(sim.randomBitPosition(rng));
        }
    }

    void applySoft(SRAMSimulator& sim, std::size_t address, std::mt19937& rng, StressStats& stats) {
        std::bernoulli_distribution ser(cfg_.soft_error_rate);
        int flips = 0;
        for (int b = 1; b <= sim.codec().codewordBits(); ++b) {
            if (ser(rng)) {
                sim.injectSingleBitFault(address, b);
                ++flips;
            }
        }
        if (flips == 1) {
            ++stats.injected_single;
        } else if (flips > 1) {
            ++stats.injected_random_multi;
        }
    }

    void applyGeometricBurst(SRAMSimulator& sim, std::size_t address, std::mt19937& rng, StressStats& stats) {
        const double p = std::clamp(cfg_.burst_geo_p, 0.01, 0.99);
        std::geometric_distribution<int> geo(p);
        const int len = std::min(sim.codec().codewordBits(), 1 + geo(rng));
        std::uniform_int_distribution<int> start_dist(1, std::max(1, sim.codec().codewordBits() - len + 1));
        sim.injectBurstFault(address, start_dist(rng), len);
        ++stats.injected_burst;
    }
};

class MetricsCalculator {
public:
    static ResearchMetrics calculate(const ECCCodec& codec, const StressStats& s) {
        ResearchMetrics m;
        const auto meta = codec.metadata();
        m.parity_bits = meta.parity_bits;
        m.codeword_expansion_pct = 100.0 * static_cast<double>(codec.codewordBits() - codec.dataBits()) /
                                   static_cast<double>(codec.dataBits());

        const double total_fault_reads = static_cast<double>(s.corrected_errors + s.detected_uncorrectable + s.undetected_errors);
        m.correction_success_pct = total_fault_reads == 0.0 ? 0.0 : (100.0 * s.corrected_errors / total_fault_reads);
        m.detection_success_pct = total_fault_reads == 0.0 ? 0.0 : (100.0 * (s.corrected_errors + s.detected_uncorrectable) / total_fault_reads);
        m.sdc_pct = s.total_reads == 0 ? 0.0 : (100.0 * s.undetected_errors / static_cast<double>(s.total_reads));
        m.miscorrection_pct = s.corrected_errors == 0 ? 0.0 : (100.0 * s.miscorrections / static_cast<double>(s.corrected_errors));

        // NOTE: The following scores use arbitrary unit weights (1.0 encode,
        // 1.2 decode, 1.8 correction; 0.5/0.5 latency split). They are
        // relative heuristics for comparing codecs within this simulator only.
        // They are NOT derived from a physical hardware energy or timing model.
        const double energy_raw = (1.0 * s.encode_ops) + (1.2 * s.decode_ops) + (1.8 * s.correction_ops);
        m.heuristic_energy_score = s.total_reads == 0 ? 0.0 : energy_raw / static_cast<double>(s.total_reads + s.total_writes + 1);

        const double parity_factor = 1.0 + static_cast<double>(m.parity_bits) / std::max(1, codec.dataBits());
        const double decode_factor = 1.0 + (0.02 * m.parity_bits);
        m.heuristic_latency_score = 0.5 * parity_factor + 0.5 * decode_factor;

        m.effective_protection_score = (0.55 * m.detection_success_pct + 0.35 * m.correction_success_pct -
                                        0.5 * m.sdc_pct - 0.2 * m.miscorrection_pct) /
                                       (1.0 + 0.01 * m.codeword_expansion_pct + 0.15 * m.heuristic_energy_score +
                                        0.15 * m.heuristic_latency_score);
        return m;
    }
};

class ExportWriter {
public:
    static void writeCSV(const std::string& path, const std::vector<CampaignResult>& rows) {
        std::ofstream out(path);
        if (!out) {
            throw std::runtime_error("Failed to open CSV export path: " + path);
        }
        out << "codec,size_kb,word_bits,fault_model,iterations,total_reads,total_writes,corrected,detected_uncorrectable,undetected,"
               "miscorrections,correction_rate,detection_rate,sdc_rate,parity_bits,expansion_pct,heuristic_energy_score,heuristic_latency_score,"
               "correction_success_pct,detection_success_pct,sdc_pct,miscorrection_pct,effective_protection_score\n";
        for (const auto& r : rows) {
            out << r.codec << ',' << (r.config.total_bytes / 1024) << ',' << r.config.word_width_bits << ',' << r.fault_model << ','
                << r.iterations << ',' << r.stats.total_reads << ',' << r.stats.total_writes << ',' << r.stats.corrected_errors << ','
                << r.stats.detected_uncorrectable << ',' << r.stats.undetected_errors << ',' << r.stats.miscorrections << ','
                << r.stats.correctionRate() << ',' << r.stats.detectionRate() << ',' << r.stats.sdcRate() << ','
                << r.metrics.parity_bits << ',' << r.metrics.codeword_expansion_pct << ',' << r.metrics.heuristic_energy_score << ','
                << r.metrics.heuristic_latency_score << ',' << r.metrics.correction_success_pct << ',' << r.metrics.detection_success_pct << ','
                << r.metrics.sdc_pct << ',' << r.metrics.miscorrection_pct << ',' << r.metrics.effective_protection_score << "\n";
        }
    }

    static void writeJSON(const std::string& path, const std::vector<CampaignResult>& rows) {
        std::ofstream out(path);
        if (!out) {
            throw std::runtime_error("Failed to open JSON export path: " + path);
        }
        out << "{\n  \"results\": [\n";
        for (std::size_t i = 0; i < rows.size(); ++i) {
            const auto& r = rows[i];
            out << "    {\n"
                << "      \"codec\": \"" << r.codec << "\",\n"
                << "      \"size_kb\": " << (r.config.total_bytes / 1024) << ",\n"
                << "      \"word_bits\": " << r.config.word_width_bits << ",\n"
                << "      \"fault_model\": \"" << r.fault_model << "\",\n"
                << "      \"iterations\": " << r.iterations << ",\n"
                << "      \"stats\": {\n"
                << "        \"reads\": " << r.stats.total_reads << ",\n"
                << "        \"writes\": " << r.stats.total_writes << ",\n"
                << "        \"corrected\": " << r.stats.corrected_errors << ",\n"
                << "        \"detected_uncorrectable\": " << r.stats.detected_uncorrectable << ",\n"
                << "        \"undetected\": " << r.stats.undetected_errors << ",\n"
                << "        \"miscorrections\": " << r.stats.miscorrections << "\n"
                << "      },\n"
                << "      \"metrics\": {\n"
                << "        \"parity_bits\": " << r.metrics.parity_bits << ",\n"
                << "        \"expansion_pct\": " << r.metrics.codeword_expansion_pct << ",\n"
                << "        \"heuristic_energy_score\": " << r.metrics.heuristic_energy_score << ",\n"
                << "        \"heuristic_latency_score\": " << r.metrics.heuristic_latency_score << ",\n"
                << "        \"correction_success_pct\": " << r.metrics.correction_success_pct << ",\n"
                << "        \"detection_success_pct\": " << r.metrics.detection_success_pct << ",\n"
                << "        \"sdc_pct\": " << r.metrics.sdc_pct << ",\n"
                << "        \"miscorrection_pct\": " << r.metrics.miscorrection_pct << ",\n"
                << "        \"effective_protection_score\": " << r.metrics.effective_protection_score << "\n"
                << "      },\n"
                << "      \"confidence_intervals\": {\n"
                << "        \"sdc\": {\"mean\": " << r.sdc_ci.mean << ", \"lower\": " << r.sdc_ci.lower
                << ", \"upper\": " << r.sdc_ci.upper << "},\n"
                << "        \"undetected\": {\"mean\": " << r.undetected_ci.mean << ", \"lower\": " << r.undetected_ci.lower
                << ", \"upper\": " << r.undetected_ci.upper << "}\n"
                << "      }\n"
                << "    }" << (i + 1 == rows.size() ? "\n" : ",\n");
        }
        out << "  ]\n}\n";
    }
};

// Wilson score CI for a proportion. Valid when samples are i.i.d. Bernoulli.
// In stress-test mode with legacy sweeps enabled, samples are NOT independent
// (systematic single-bit sweeps dominate). Treat reported CI as approximate.
static ConfidenceInterval wilson95(std::uint64_t hits, std::uint64_t total) {
    if (total == 0) {
        return {};
    }
    const double z = 1.95996398454005;
    const double n = static_cast<double>(total);
    const double phat = static_cast<double>(hits) / n;
    const double denom = 1.0 + (z * z) / n;
    const double center = (phat + (z * z) / (2.0 * n)) / denom;
    const double spread = (z * std::sqrt((phat * (1.0 - phat) / n) + ((z * z) / (4.0 * n * n)))) / denom;
    return {phat, std::max(0.0, center - spread), std::min(1.0, center + spread)};
}

class StressTestRunner {
public:
    struct Options {
        std::uint32_t seed = 42;
        std::size_t iterations = 5000;
        bool verbose = false;
        bool run_legacy_sweeps = true;
        std::size_t progress_interval = 500;
    };

    static StressStats run(SRAMSimulator& sim, FaultModel& fault_model, const Options& options) {
        StressStats stats;
        std::mt19937 rng(options.seed);
        std::uniform_int_distribution<std::size_t> addr_dist(0, sim.depthWords() - 1);

        for (std::size_t i = 0; i < options.iterations; ++i) {
            const auto addr = addr_dist(rng);
            std::uniform_int_distribution<int> op_dist(0, 99);
            const int op = op_dist(rng);
            if (op < 35) {
                uint64_t value = (static_cast<uint64_t>(rng()) << 32) ^ rng();
                sim.write(addr, value);
                ++stats.total_writes;
                ++stats.encode_ops;
                continue;
            }

            fault_model.inject(sim, addr, rng, stats, i);
            auto rr = sim.read(addr);
            ++stats.total_reads;
            ++stats.decode_ops;
            if (rr.status == DecodeStatus::Corrected) {
                ++stats.corrected_errors;
                ++stats.correction_ops;
            } else if (rr.status == DecodeStatus::DetectedUncorrectable) {
                ++stats.detected_uncorrectable;
            } else if (rr.status == DecodeStatus::UndetectedError) {
                ++stats.undetected_errors;
            }
            if (rr.was_miscorrected) {
                ++stats.miscorrections;
            }

            if (options.verbose && options.progress_interval > 0 && (i % options.progress_interval == 0)) {
                std::cout << "  iter=" << i << " status=" << statusToString(rr.status) << " data=0x" << std::hex << rr.data
                          << std::dec << "\n";
            }
        }

        if (options.run_legacy_sweeps) {
            for (std::size_t a = 0; a < std::min<std::size_t>(sim.depthWords(), 128); ++a) {
                sim.write(a, static_cast<uint64_t>(a * 2654435761ULL));
                ++stats.total_writes;
                ++stats.encode_ops;
                for (int b = 1; b <= sim.codec().codewordBits(); ++b) {
                    sim.injectSingleBitFault(a, b);
                    ++stats.injected_single;
                    auto rr = sim.read(a);
                    ++stats.total_reads;
                    ++stats.decode_ops;
                    if (rr.status == DecodeStatus::Corrected) {
                        ++stats.corrected_errors;
                        ++stats.correction_ops;
                    } else if (rr.status == DecodeStatus::DetectedUncorrectable) {
                        ++stats.detected_uncorrectable;
                    } else if (rr.status == DecodeStatus::UndetectedError) {
                        ++stats.undetected_errors;
                    }
                }
            }

            for (std::size_t a = 0; a < std::min<std::size_t>(sim.depthWords(), 64); ++a) {
                sim.write(a, 0xA5A5A5A5ULL ^ static_cast<uint64_t>(a));
                ++stats.total_writes;
                ++stats.encode_ops;
                for (int len = 2; len <= 4; ++len) {
                    for (int start = 1; start <= std::max(1, sim.codec().codewordBits() - len + 1); start += len) {
                        sim.injectBurstFault(a, start, len);
                        ++stats.injected_burst;
                        auto rr = sim.read(a);
                        ++stats.total_reads;
                        ++stats.decode_ops;
                        if (rr.status == DecodeStatus::Corrected) {
                            ++stats.corrected_errors;
                            ++stats.correction_ops;
                        } else if (rr.status == DecodeStatus::DetectedUncorrectable) {
                            ++stats.detected_uncorrectable;
                        } else if (rr.status == DecodeStatus::UndetectedError) {
                            ++stats.undetected_errors;
                        }
                    }
                }
            }
        }

        return stats;
    }
};

static void printConfigTable() {
    const std::vector<std::size_t> sizes_kb = {64, 128, 256};
    const std::vector<int> widths = {8, 16, 32};
    std::cout << "Supported SRAM configurations:\n";
    for (std::size_t kb : sizes_kb) {
        for (int width : widths) {
            const std::size_t depth = (kb * 1024) / static_cast<std::size_t>(width / 8);
            std::cout << "  " << std::setw(3) << kb << "KB x " << std::setw(2) << width
                      << "-bit => depth=" << depth << " words\n";
        }
    }
}

static void printStats(const StressStats& s) {
    std::cout << "  total_reads=" << s.total_reads << ", total_writes=" << s.total_writes << "\n"
              << "  injected_single=" << s.injected_single
              << ", injected_burst=" << s.injected_burst
              << ", injected_random_multi=" << s.injected_random_multi << "\n"
              << "  corrected_errors=" << s.corrected_errors
              << ", detected_uncorrectable=" << s.detected_uncorrectable
              << ", undetected_errors=" << s.undetected_errors
              << ", miscorrections=" << s.miscorrections << "\n"
              << std::fixed << std::setprecision(4)
              << "  correction_rate=" << s.correctionRate()
              << ", detection_rate=" << s.detectionRate()
              << ", sdc_rate=" << s.sdcRate() << "\n";
}

static void printResearchSummary(const ECCCodec& codec, const StressStats& s) {
    const auto m = MetricsCalculator::calculate(codec, s);
    std::cout << "  research: parity_bits=" << m.parity_bits << ", expansion_pct=" << std::fixed << std::setprecision(2)
              << m.codeword_expansion_pct << ", energy_heuristic=" << m.heuristic_energy_score
              << ", latency_heuristic=" << m.heuristic_latency_score << ", corr_success_pct=" << m.correction_success_pct
              << ", detect_success_pct=" << m.detection_success_pct << ", sdc_pct=" << m.sdc_pct
              << ", miscorrection_pct=" << m.miscorrection_pct << ", eps=" << m.effective_protection_score << "\n";
}

static CampaignResult buildCampaignResult(const ECCCodec& codec, SRAMConfig cfg, const std::string& fault_model,
                                          std::size_t iterations, const StressStats& stats) {
    CampaignResult r;
    r.codec = codec.name();
    r.config = cfg;
    r.fault_model = fault_model;
    r.iterations = iterations;
    r.stats = stats;
    r.metrics = MetricsCalculator::calculate(codec, stats);
    r.sdc_ci = wilson95(stats.undetected_errors, std::max<std::uint64_t>(1, stats.total_reads));
    r.undetected_ci = wilson95(stats.undetected_errors,
                               std::max<std::uint64_t>(1, stats.corrected_errors + stats.detected_uncorrectable + stats.undetected_errors));
    return r;
}

static void runDemo(const std::string& codec_name, SRAMConfig cfg) {
    auto codec = createCodec(codec_name, cfg.word_width_bits);
    SRAMSimulator sim(cfg, std::move(codec));
    std::cout << "\nDemo: codec=" << sim.codec().name() << ", SRAM=" << (cfg.total_bytes / 1024)
              << "KB x " << cfg.word_width_bits << "-bit, depth=" << sim.depthWords() << "\n";
    const auto meta = sim.codec().metadata();
    std::cout << "  parity_bits=" << meta.parity_bits << ", correction=\"" << meta.correction_capability
              << "\", detection=\"" << meta.detection_capability << "\"\n";

    const std::size_t addr = 17;
    const uint64_t test_data = cfg.word_width_bits == 8 ? 0xA5 : (cfg.word_width_bits == 16 ? 0xBEEF : 0xDEADBEEF);
    sim.write(addr, test_data);

    auto clean = sim.read(addr);
    std::cout << "  clean -> data=0x" << std::hex << clean.data << std::dec
              << ", status=" << statusToString(clean.status) << "\n";

    sim.injectSingleBitFault(addr, 2);
    auto single = sim.read(addr);
    std::cout << "  single-bit fault -> data=0x" << std::hex << single.data << std::dec
              << ", status=" << statusToString(single.status) << "\n";

    sim.injectBurstFault(addr, 3, 3);
    auto burst = sim.read(addr);
    std::cout << "  burst(3) fault -> data=0x" << std::hex << burst.data << std::dec
              << ", status=" << statusToString(burst.status) << "\n";

    sim.write(addr, test_data);
    bool undetected = sim.injectUndetectedPattern(addr);
    auto und = sim.read(addr);
    std::cout << "  searched undetected pattern -> injected=" << (undetected ? "yes" : "no")
              << ", status=" << statusToString(und.status) << "\n";
}

static CampaignResult runStress(const std::string& codec_name, SRAMConfig cfg, std::size_t iterations, uint32_t seed,
                                bool verbose, const FaultModelConfig& fm_cfg) {
    auto codec = createCodec(codec_name, cfg.word_width_bits);
    SRAMSimulator sim(cfg, std::move(codec), seed);

    std::cout << "\nStress test: codec=" << sim.codec().name() << ", SRAM=" << (cfg.total_bytes / 1024)
              << "KB x " << cfg.word_width_bits << "-bit, iterations=" << iterations << ", seed=" << seed
              << "\n";

    std::unique_ptr<FaultModel> fault_model;
    if (fm_cfg.model == "legacy") {
        fault_model = std::make_unique<LegacyMixedFaultModel>();
    } else {
        fault_model = std::make_unique<AdvancedFaultModel>(fm_cfg);
    }

    StressTestRunner::Options options;
    options.seed = seed;
    options.iterations = iterations;
    options.verbose = verbose;
    options.run_legacy_sweeps = (fm_cfg.model == "legacy");
    options.progress_interval = 500;

    auto stats = StressTestRunner::run(sim, *fault_model, options);
    printStats(stats);
    printResearchSummary(sim.codec(), stats);
    return buildCampaignResult(sim.codec(), cfg, fault_model->name(), iterations, stats);
}

static std::vector<CampaignResult> runCompare(SRAMConfig cfg, std::size_t iterations, uint32_t seed, bool verbose,
                                              const FaultModelConfig& fm_cfg, bool research_compare) {
    std::vector<std::string> codecs = {"secded", "taec", "bch", "polar"};
    std::vector<CampaignResult> results;

    if (!research_compare) {
        std::cout << "\nECC comparison on " << (cfg.total_bytes / 1024) << "KB x " << cfg.word_width_bits
                  << "-bit, iterations=" << iterations << ", seed=" << seed << "\n";
        std::cout << "  " << std::left << std::setw(8) << "Codec" << std::right << std::setw(12) << "Corrected"
                  << std::setw(14) << "DetUncorr" << std::setw(12) << "Undetected" << std::setw(10)
                  << "CorrRate" << std::setw(10) << "SDC" << "\n";
    } else {
        std::cout << "\nResearch ECC comparison on " << (cfg.total_bytes / 1024) << "KB x " << cfg.word_width_bits
                  << "-bit, fault-model=" << fm_cfg.model << ", iterations=" << iterations << "\n";
        std::cout << "  " << std::left << std::setw(8) << "Codec" << std::right << std::setw(10) << "Corr%"
                  << std::setw(10) << "Det%" << std::setw(10) << "SDC%" << std::setw(10) << "Red%"
                  << std::setw(12) << "EnergyH" << std::setw(12) << "LatencyH" << "\n";
    }

    for (const auto& c : codecs) {
        auto codec = createCodec(c, cfg.word_width_bits);
        SRAMSimulator sim(cfg, std::move(codec), seed);

        std::unique_ptr<FaultModel> fault_model;
        if (fm_cfg.model == "legacy") {
            fault_model = std::make_unique<LegacyMixedFaultModel>();
        } else {
            fault_model = std::make_unique<AdvancedFaultModel>(fm_cfg);
        }

        StressTestRunner::Options options{seed, iterations, verbose, fm_cfg.model == "legacy", 500};
        auto stats = StressTestRunner::run(sim, *fault_model, options);
        auto result = buildCampaignResult(sim.codec(), cfg, fault_model->name(), iterations, stats);
        results.push_back(result);

        if (!research_compare) {
            std::cout << "  " << std::left << std::setw(8) << sim.codec().name() << std::right << std::setw(12)
                      << stats.corrected_errors << std::setw(14) << stats.detected_uncorrectable << std::setw(12)
                      << stats.undetected_errors << std::setw(10) << std::fixed << std::setprecision(3)
                      << stats.correctionRate() << std::setw(10) << stats.sdcRate() << "\n";
        } else {
            const auto& m = result.metrics;
            std::cout << "  " << std::left << std::setw(8) << sim.codec().name() << std::right << std::setw(10)
                      << std::fixed << std::setprecision(2) << m.correction_success_pct << std::setw(10)
                      << m.detection_success_pct << std::setw(10) << m.sdc_pct << std::setw(10)
                      << m.codeword_expansion_pct << std::setw(12) << m.heuristic_energy_score << std::setw(12)
                      << m.heuristic_latency_score << "\n";
        }
    }
    return results;
}

static std::vector<CampaignResult> runMonteCarlo(const std::string& codec_name, SRAMConfig cfg, std::size_t iterations,
                                                 uint32_t seed, const FaultModelConfig& fm_cfg,
                                                 std::size_t progress_interval) {
    auto codec = createCodec(codec_name, cfg.word_width_bits);
    SRAMSimulator sim(cfg, std::move(codec), seed);
    std::cout << "\nMonte Carlo: codec=" << sim.codec().name() << ", SRAM=" << (cfg.total_bytes / 1024)
              << "KB x " << cfg.word_width_bits << "-bit, iterations=" << iterations << ", seed=" << seed
              << ", fault-model=" << fm_cfg.model << "\n";

    std::unique_ptr<FaultModel> fault_model;
    if (fm_cfg.model == "legacy") {
        fault_model = std::make_unique<LegacyMixedFaultModel>();
    } else {
        fault_model = std::make_unique<AdvancedFaultModel>(fm_cfg);
    }

    StressTestRunner::Options options{seed, iterations, true, false, progress_interval};
    auto stats = StressTestRunner::run(sim, *fault_model, options);
    printStats(stats);

    auto result = buildCampaignResult(sim.codec(), cfg, fault_model->name(), iterations, stats);
    std::cout << "  CI95 SDC: [" << result.sdc_ci.lower << ", " << result.sdc_ci.upper << "]"
              << ", undetected: [" << result.undetected_ci.lower << ", " << result.undetected_ci.upper << "]\n";
    std::cout << "  (CI assumes i.i.d. samples; legacy sweeps introduce correlation)\n";
    return {result};
}

static void printUsage(const char* argv0) {
    std::cout << "Usage: " << argv0
              << " [--mode demo|stress|compare|montecarlo] [--codec secded|taec|hashaec3|bch|hashec2|polar|crcrm|all]"
                 " [--size-kb 64|128|256] [--word-bits 8|16|32] [--iterations N] [--seed N] [--verbose]"
                 " [--fault-model legacy|adjacent|row|column|retention|soft|geoburst|faultmap]"
                 " [--adjacency-radius N] [--adjacency-shape horizontal|vertical|clustered]"
                 " [--row-length N] [--column-stride N] [--retention-prob P] [--ser-prob P] [--burst-geo-p P]"
                 " [--fault-map-prob P] [--research-compare] [--progress-interval N]"
                 " [--export-csv path] [--export-json path]\n";
}

int main(int argc, char** argv) {
    std::string mode = "demo";
    std::string codec = "all";
    int size_kb = 64;
    int word_bits = 8;
    std::size_t iterations = 5000;
    std::uint32_t seed = 42;
    bool verbose = false;
    bool research_compare = false;
    std::size_t progress_interval = 1000;
    std::string export_csv;
    std::string export_json;
    FaultModelConfig fault_cfg;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        auto require = [&](const std::string& flag) -> std::string {
            if (i + 1 >= argc) {
                throw std::invalid_argument("Missing value for " + flag);
            }
            return argv[++i];
        };

        if (arg == "--mode") {
            mode = require(arg);
        } else if (arg == "--codec") {
            codec = require(arg);
        } else if (arg == "--size-kb") {
            size_kb = std::stoi(require(arg));
        } else if (arg == "--word-bits") {
            word_bits = std::stoi(require(arg));
        } else if (arg == "--iterations") {
            iterations = static_cast<std::size_t>(std::stoull(require(arg)));
        } else if (arg == "--seed") {
            seed = static_cast<std::uint32_t>(std::stoul(require(arg)));
        } else if (arg == "--verbose") {
            verbose = true;
        } else if (arg == "--fault-model") {
            fault_cfg.model = require(arg);
        } else if (arg == "--adjacency-radius") {
            fault_cfg.adjacency_radius = std::stoi(require(arg));
        } else if (arg == "--adjacency-shape") {
            fault_cfg.adjacency_shape = require(arg);
        } else if (arg == "--row-length") {
            fault_cfg.row_length = static_cast<std::size_t>(std::stoull(require(arg)));
        } else if (arg == "--column-stride") {
            fault_cfg.column_stride = static_cast<std::size_t>(std::stoull(require(arg)));
        } else if (arg == "--retention-prob") {
            fault_cfg.retention_probability = std::stod(require(arg));
        } else if (arg == "--ser-prob") {
            fault_cfg.soft_error_rate = std::stod(require(arg));
        } else if (arg == "--burst-geo-p") {
            fault_cfg.burst_geo_p = std::stod(require(arg));
        } else if (arg == "--fault-map-prob") {
            fault_cfg.fault_map_probability = std::stod(require(arg));
        } else if (arg == "--research-compare") {
            research_compare = true;
        } else if (arg == "--progress-interval") {
            progress_interval = static_cast<std::size_t>(std::stoull(require(arg)));
        } else if (arg == "--export-csv") {
            export_csv = require(arg);
        } else if (arg == "--export-json") {
            export_json = require(arg);
        } else if (arg == "--help" || arg == "-h") {
            printUsage(argv[0]);
            return 0;
        } else {
            throw std::invalid_argument("Unknown argument: " + arg);
        }
    }

    if (!(size_kb == 64 || size_kb == 128 || size_kb == 256)) {
        throw std::invalid_argument("size-kb must be one of 64, 128, 256");
    }
    if (!(word_bits == 8 || word_bits == 16 || word_bits == 32)) {
        throw std::invalid_argument("word-bits must be one of 8, 16, 32");
    }

    SRAMConfig cfg{static_cast<std::size_t>(size_kb) * 1024, word_bits};
    printConfigTable();

    std::vector<CampaignResult> results;
    if (mode == "demo") {
        if (codec == "all") {
            for (const auto& c : std::vector<std::string>{"secded", "taec", "bch", "polar"}) {
                runDemo(c, cfg);
            }
        } else {
            runDemo(codec, cfg);
        }
    } else if (mode == "stress") {
        if (codec == "all") {
            for (const auto& c : std::vector<std::string>{"secded", "taec", "bch", "polar"}) {
                results.push_back(runStress(c, cfg, iterations, seed, verbose, fault_cfg));
            }
        } else {
            results.push_back(runStress(codec, cfg, iterations, seed, verbose, fault_cfg));
        }
    } else if (mode == "compare") {
        results = runCompare(cfg, iterations, seed, verbose, fault_cfg, research_compare);
    } else if (mode == "montecarlo") {
        if (codec == "all") {
            for (const auto& c : std::vector<std::string>{"secded", "taec", "bch", "polar"}) {
                auto part = runMonteCarlo(c, cfg, iterations, seed, fault_cfg, progress_interval);
                results.insert(results.end(), part.begin(), part.end());
            }
        } else {
            results = runMonteCarlo(codec, cfg, iterations, seed, fault_cfg, progress_interval);
        }
    } else {
        throw std::invalid_argument("mode must be demo, stress, compare, or montecarlo");
    }

    if (!export_csv.empty()) {
        ExportWriter::writeCSV(export_csv, results);
        std::cout << "Exported CSV: " << export_csv << "\n";
    }
    if (!export_json.empty()) {
        ExportWriter::writeJSON(export_json, results);
        std::cout << "Exported JSON: " << export_json << "\n";
    }

    return 0;
}
