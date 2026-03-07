#include <algorithm>
#include <array>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <memory>
#include <numeric>
#include <optional>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
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
            result.status = DecodeStatus::Corrected;
            if (result.syndrome >= 1 && result.syndrome <= total_bits_ - 1) {
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

class TAECCodec final : public ChecksumSearchCodecBase {
public:
    explicit TAECCodec(int data_bits)
        : ChecksumSearchCodecBase("TAEC", data_bits, 12, 3, 3,
                                  "Corrects up to 3 adjacent flips (search-based)",
                                  "High-probability detection via 12-bit checksum") {}
};

class BCHCodec final : public ChecksumSearchCodecBase {
public:
    explicit BCHCodec(int data_bits)
        : ChecksumSearchCodecBase("BCH", data_bits, 16, 2, 0,
                                  "Corrects up to 2 bit flips (t=2 emulation)",
                                  "High-probability detection via 16-bit checksum") {}
};

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

    std::string name() const override { return "Polar"; }
    int dataBits() const override { return data_bits_; }
    int codewordBits() const override { return n_; }

    ECCMetadata metadata() const override {
        return ECCMetadata{"Polar", n_ - data_bits_,
                           "Corrects low-weight noise by CRC-aided single-flip search",
                           "CRC8 + frozen-bit constraints detect most multi-bit errors"};
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
    if (codec_name == "taec") {
        return std::make_unique<TAECCodec>(word_bits);
    }
    if (codec_name == "bch") {
        return std::make_unique<BCHCodec>(word_bits);
    }
    if (codec_name == "polar") {
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

class SRAMSimulator {
public:
    struct ReadResult {
        uint64_t data = 0;
        DecodeStatus status = DecodeStatus::Clean;
        int syndrome = 0;
        bool mismatch_vs_golden = false;
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

    bool injectUndetectedPattern(std::size_t address, int max_weight = 4) {
        checkAddress(address);
        if (max_weight < 2 || codec_->codewordBits() > 40) {
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

class StressTestRunner {
public:
    struct Options {
        std::uint32_t seed = 42;
        std::size_t iterations = 5000;
        bool verbose = false;
    };

    static StressStats run(SRAMSimulator& sim, const Options& options) {
        StressStats stats;
        std::mt19937 rng(options.seed);
        std::uniform_int_distribution<std::size_t> addr_dist(0, sim.depthWords() - 1);
        std::uniform_int_distribution<int> op_dist(0, 99);
        std::uniform_int_distribution<int> burst_len_dist(2, 5);
        std::uniform_int_distribution<int> random_fault_count(2, 4);

        for (std::size_t i = 0; i < options.iterations; ++i) {
            const auto addr = addr_dist(rng);
            const int op = op_dist(rng);
            if (op < 35) {
                uint64_t value = (static_cast<uint64_t>(rng()) << 32) ^ rng();
                sim.write(addr, value);
                ++stats.total_writes;
                continue;
            }

            if (op < 65) {
                std::uniform_int_distribution<int> bit_dist(1, sim.codec().codewordBits());
                sim.injectSingleBitFault(addr, bit_dist(rng));
                ++stats.injected_single;
            } else if (op < 85) {
                std::uniform_int_distribution<int> start_dist(1, std::max(1, sim.codec().codewordBits() - 4));
                sim.injectBurstFault(addr, start_dist(rng), burst_len_dist(rng));
                ++stats.injected_burst;
            } else {
                sim.injectRandomFaults(addr, random_fault_count(rng));
                ++stats.injected_random_multi;
            }

            auto rr = sim.read(addr);
            ++stats.total_reads;
            if (rr.status == DecodeStatus::Corrected) {
                ++stats.corrected_errors;
                if (rr.mismatch_vs_golden) {
                    ++stats.miscorrections;
                }
            } else if (rr.status == DecodeStatus::DetectedUncorrectable) {
                ++stats.detected_uncorrectable;
            } else if (rr.status == DecodeStatus::UndetectedError) {
                ++stats.undetected_errors;
            }

            if (options.verbose && (i % 500 == 0)) {
                std::cout << "  iter=" << i << " status=" << statusToString(rr.status)
                          << " data=0x" << std::hex << rr.data << std::dec << "\n";
            }
        }

        // single-bit sweep
        for (std::size_t a = 0; a < std::min<std::size_t>(sim.depthWords(), 128); ++a) {
            sim.write(a, static_cast<uint64_t>(a * 2654435761ULL));
            ++stats.total_writes;
            for (int b = 1; b <= sim.codec().codewordBits(); ++b) {
                sim.injectSingleBitFault(a, b);
                ++stats.injected_single;
                auto rr = sim.read(a);
                ++stats.total_reads;
                if (rr.status == DecodeStatus::Corrected) {
                    ++stats.corrected_errors;
                } else if (rr.status == DecodeStatus::DetectedUncorrectable) {
                    ++stats.detected_uncorrectable;
                } else if (rr.status == DecodeStatus::UndetectedError) {
                    ++stats.undetected_errors;
                }
            }
        }

        // burst sweep
        for (std::size_t a = 0; a < std::min<std::size_t>(sim.depthWords(), 64); ++a) {
            sim.write(a, 0xA5A5A5A5ULL ^ static_cast<uint64_t>(a));
            ++stats.total_writes;
            for (int len = 2; len <= 4; ++len) {
                for (int start = 1; start <= std::max(1, sim.codec().codewordBits() - len + 1); start += len) {
                    sim.injectBurstFault(a, start, len);
                    ++stats.injected_burst;
                    auto rr = sim.read(a);
                    ++stats.total_reads;
                    if (rr.status == DecodeStatus::Corrected) {
                        ++stats.corrected_errors;
                    } else if (rr.status == DecodeStatus::DetectedUncorrectable) {
                        ++stats.detected_uncorrectable;
                    } else if (rr.status == DecodeStatus::UndetectedError) {
                        ++stats.undetected_errors;
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

static void runStress(const std::string& codec_name, SRAMConfig cfg, std::size_t iterations, uint32_t seed,
                      bool verbose) {
    auto codec = createCodec(codec_name, cfg.word_width_bits);
    SRAMSimulator sim(cfg, std::move(codec), seed);

    std::cout << "\nStress test: codec=" << sim.codec().name() << ", SRAM=" << (cfg.total_bytes / 1024)
              << "KB x " << cfg.word_width_bits << "-bit, iterations=" << iterations << ", seed=" << seed
              << "\n";

    StressTestRunner::Options options;
    options.seed = seed;
    options.iterations = iterations;
    options.verbose = verbose;
    auto stats = StressTestRunner::run(sim, options);
    printStats(stats);
}

static void runCompare(SRAMConfig cfg, std::size_t iterations, uint32_t seed, bool verbose) {
    std::vector<std::string> codecs = {"secded", "taec", "bch", "polar"};
    std::cout << "\nECC comparison on " << (cfg.total_bytes / 1024) << "KB x " << cfg.word_width_bits
              << "-bit, iterations=" << iterations << ", seed=" << seed << "\n";
    std::cout << "  " << std::left << std::setw(8) << "Codec" << std::right << std::setw(12) << "Corrected"
              << std::setw(14) << "DetUncorr" << std::setw(12) << "Undetected" << std::setw(10)
              << "CorrRate" << std::setw(10) << "SDC" << "\n";

    for (const auto& c : codecs) {
        auto codec = createCodec(c, cfg.word_width_bits);
        SRAMSimulator sim(cfg, std::move(codec), seed);
        StressTestRunner::Options options{seed, iterations, verbose};
        auto stats = StressTestRunner::run(sim, options);
        std::cout << "  " << std::left << std::setw(8) << sim.codec().name() << std::right << std::setw(12)
                  << stats.corrected_errors << std::setw(14) << stats.detected_uncorrectable << std::setw(12)
                  << stats.undetected_errors << std::setw(10) << std::fixed << std::setprecision(3)
                  << stats.correctionRate() << std::setw(10) << stats.sdcRate() << "\n";
    }
}

static void printUsage(const char* argv0) {
    std::cout << "Usage: " << argv0
              << " [--mode demo|stress|compare] [--codec secded|taec|bch|polar|all]"
                 " [--size-kb 64|128|256] [--word-bits 8|16|32] [--iterations N] [--seed N] [--verbose]\n";
}

int main(int argc, char** argv) {
    std::string mode = "demo";
    std::string codec = "all";
    int size_kb = 64;
    int word_bits = 8;
    std::size_t iterations = 5000;
    std::uint32_t seed = 42;
    bool verbose = false;

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
                runStress(c, cfg, iterations, seed, verbose);
            }
        } else {
            runStress(codec, cfg, iterations, seed, verbose);
        }
    } else if (mode == "compare") {
        runCompare(cfg, iterations, seed, verbose);
    } else {
        throw std::invalid_argument("mode must be demo, stress, or compare");
    }

    return 0;
}
