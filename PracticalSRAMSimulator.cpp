#include <algorithm>
#include <bitset>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

class HammingSecdedCodec {
public:
    enum class DecodeStatus {
        CLEAN_READ,
        CORRECTED_READ,
        DETECTED_UNCORRECTABLE,
        UNDETECTED_ERROR
    };

    struct DecodeResult {
        uint64_t corrected_data = 0;
        uint64_t corrected_codeword = 0;
        DecodeStatus status = DecodeStatus::CLEAN_READ;
        bool data_corrected = false;
        bool overall_parity_odd = false;
        int syndrome = 0;
        int error_position = 0;
    };

    explicit HammingSecdedCodec(int data_bits)
        : data_bits_(data_bits),
          parity_bits_(requiredParityBits(data_bits)),
          total_bits_(data_bits + parity_bits_ + 1),
          parity_positions_(buildParityPositions(parity_bits_)),
          data_positions_(buildDataPositions(total_bits_, parity_positions_)) {
        if (data_bits_ <= 0 || data_bits_ > 57) {
            throw std::invalid_argument("data_bits must be in [1, 57]");
        }
    }

    int dataBits() const { return data_bits_; }
    int parityBits() const { return parity_bits_; }
    int totalBits() const { return total_bits_; }

    uint64_t encode(uint64_t data) const {
        const uint64_t masked_data = data & dataMask();
        uint64_t codeword = 0;

        for (int i = 0; i < data_bits_; ++i) {
            if ((masked_data >> i) & 1ULL) {
                setBit(codeword, data_positions_[i], true);
            }
        }

        for (int parity_pos : parity_positions_) {
            int parity = 0;
            for (int pos = 1; pos <= total_bits_ - 1; ++pos) {
                if ((pos & parity_pos) && getBit(codeword, pos)) {
                    parity ^= 1;
                }
            }
            setBit(codeword, parity_pos, parity != 0);
        }

        int overall_parity = 0;
        for (int pos = 1; pos <= total_bits_ - 1; ++pos) {
            if (getBit(codeword, pos)) {
                overall_parity ^= 1;
            }
        }
        setBit(codeword, total_bits_, overall_parity != 0);

        return codeword;
    }

    DecodeResult decode(uint64_t received) const {
        DecodeResult result;
        uint64_t working = received & codewordMask();

        for (int i = 0; i < parity_bits_; ++i) {
            const int parity_pos = parity_positions_[i];
            int parity = 0;
            for (int pos = 1; pos <= total_bits_ - 1; ++pos) {
                if ((pos & parity_pos) && getBit(working, pos)) {
                    parity ^= 1;
                }
            }
            if (parity) {
                result.syndrome |= (1 << i);
            }
        }

        int overall = 0;
        for (int pos = 1; pos <= total_bits_; ++pos) {
            if (getBit(working, pos)) {
                overall ^= 1;
            }
        }
        result.overall_parity_odd = (overall != 0);

        if (result.syndrome == 0 && !result.overall_parity_odd) {
            result.status = DecodeStatus::CLEAN_READ;
        } else if (result.syndrome == 0 && result.overall_parity_odd) {
            result.status = DecodeStatus::CORRECTED_READ;
            result.error_position = total_bits_;
            flipBit(working, total_bits_);
            result.data_corrected = true;
        } else if (result.syndrome != 0 && result.overall_parity_odd) {
            result.status = DecodeStatus::CORRECTED_READ;
            result.error_position = result.syndrome;
            if (result.error_position >= 1 && result.error_position <= total_bits_ - 1) {
                flipBit(working, result.error_position);
                result.data_corrected = true;
            }
        } else {
            result.status = DecodeStatus::DETECTED_UNCORRECTABLE;
        }

        result.corrected_data = extractData(working);
        result.corrected_codeword = working;
        return result;
    }

    uint64_t dataMask() const {
        if (data_bits_ == 64) {
            return ~0ULL;
        }
        return (1ULL << data_bits_) - 1ULL;
    }

    static const char* statusToString(DecodeStatus status) {
        switch (status) {
            case DecodeStatus::CLEAN_READ:
                return "clean read";
            case DecodeStatus::CORRECTED_READ:
                return "corrected read";
            case DecodeStatus::DETECTED_UNCORRECTABLE:
                return "detected uncorrectable error";
            case DecodeStatus::UNDETECTED_ERROR:
                return "undetected error";
        }
        return "unknown";
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

    static std::vector<int> buildDataPositions(int total_bits,
                                               const std::vector<int>& parity_positions) {
        std::vector<int> data_positions;
        for (int pos = 1; pos <= total_bits - 1; ++pos) {
            if (std::find(parity_positions.begin(), parity_positions.end(), pos) == parity_positions.end()) {
                data_positions.push_back(pos);
            }
        }
        return data_positions;
    }

    uint64_t codewordMask() const {
        if (total_bits_ == 64) {
            return ~0ULL;
        }
        return (1ULL << total_bits_) - 1ULL;
    }

    static bool getBit(uint64_t value, int pos1) {
        return (value >> (pos1 - 1)) & 1ULL;
    }

    static void setBit(uint64_t& value, int pos1, bool bit) {
        if (bit) {
            value |= (1ULL << (pos1 - 1));
        } else {
            value &= ~(1ULL << (pos1 - 1));
        }
    }

    static void flipBit(uint64_t& value, int pos1) {
        value ^= (1ULL << (pos1 - 1));
    }

    uint64_t extractData(uint64_t codeword) const {
        uint64_t data = 0;
        for (int i = 0; i < data_bits_; ++i) {
            if (getBit(codeword, data_positions_[i])) {
                data |= (1ULL << i);
            }
        }
        return data;
    }
};

class SRAMSimulator {
public:
    struct ReadResult {
        uint64_t data = 0;
        HammingSecdedCodec::DecodeStatus status = HammingSecdedCodec::DecodeStatus::CLEAN_READ;
        int syndrome = 0;
        int error_position = 0;
    };

    SRAMSimulator(std::size_t total_bytes, int word_width_bits)
        : total_bytes_(total_bytes),
          word_width_bits_(word_width_bits),
          codec_(word_width_bits),
          depth_words_(computeDepth(total_bytes, word_width_bits)),
          memory_(depth_words_, codec_.encode(0)),
          golden_(depth_words_, 0),
          rng_(1234567) {}

    std::size_t depthWords() const { return depth_words_; }
    std::size_t totalBytes() const { return total_bytes_; }
    int wordWidthBits() const { return word_width_bits_; }

    void write(std::size_t address, uint64_t data) {
        checkAddress(address);
        const uint64_t masked = data & codec_.dataMask();
        golden_[address] = masked;
        memory_[address] = codec_.encode(masked);
    }

    ReadResult read(std::size_t address) {
        checkAddress(address);
        auto decoded = codec_.decode(memory_[address]);

        ReadResult result;
        result.data = decoded.corrected_data;
        result.syndrome = decoded.syndrome;
        result.error_position = decoded.error_position;
        result.status = decoded.status;

        if (decoded.data_corrected) {
            memory_[address] = codec_.encode(decoded.corrected_data);
        }

        if (result.status == HammingSecdedCodec::DecodeStatus::CLEAN_READ &&
            result.data != golden_[address]) {
            result.status = HammingSecdedCodec::DecodeStatus::UNDETECTED_ERROR;
        }

        return result;
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
            const int bit = start_position_1_based + i;
            if (bit >= 1 && bit <= codec_.totalBits()) {
                memory_[address] ^= (1ULL << (bit - 1));
            }
        }
    }

    void injectRandomFaults(std::size_t address, int count) {
        checkAddress(address);
        if (count <= 0) {
            return;
        }
        std::uniform_int_distribution<int> dist(1, codec_.totalBits());
        for (int i = 0; i < count; ++i) {
            injectSingleBitFault(address, dist(rng_));
        }
    }

    bool injectUndetectedPattern(std::size_t address, int max_weight = 4) {
        checkAddress(address);
        if (max_weight < 2) {
            return false;
        }

        const uint64_t original = memory_[address];
        const uint64_t expected = golden_[address];
        const int n = codec_.totalBits();

        for (int i = 1; i <= n; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                for (int k = j + 1; k <= n; ++k) {
                    for (int l = k + 1; l <= n; ++l) {
                        uint64_t candidate = original;
                        candidate ^= (1ULL << (i - 1));
                        candidate ^= (1ULL << (j - 1));
                        candidate ^= (1ULL << (k - 1));
                        candidate ^= (1ULL << (l - 1));
                        auto dec = codec_.decode(candidate);
                        if (dec.status == HammingSecdedCodec::DecodeStatus::CLEAN_READ &&
                            dec.corrected_data != expected) {
                            memory_[address] = candidate;
                            return true;
                        }
                    }
                }
            }
        }

        return false;
    }

private:
    std::size_t total_bytes_;
    int word_width_bits_;
    HammingSecdedCodec codec_;
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
        if (bit_position_1_based < 1 || bit_position_1_based > codec_.totalBits()) {
            throw std::out_of_range("bit position out of range");
        }
    }
};

static void printConfigSummary(const SRAMSimulator& sim) {
    std::cout << "SRAM " << (sim.totalBytes() / 1024) << "KB, word width "
              << sim.wordWidthBits() << "-bit, depth=" << sim.depthWords() << " words\n";
}

static void runDemo(std::size_t total_bytes, int width_bits, uint64_t test_data) {
    SRAMSimulator sim(total_bytes, width_bits);
    printConfigSummary(sim);

    const std::size_t addr = 17;
    sim.write(addr, test_data);

    auto clean = sim.read(addr);
    std::cout << "  Clean read -> data=0x" << std::hex << clean.data << std::dec
              << ", status=" << HammingSecdedCodec::statusToString(clean.status) << "\n";

    sim.injectSingleBitFault(addr, 3);
    auto corrected = sim.read(addr);
    std::cout << "  Single-bit fault -> data=0x" << std::hex << corrected.data << std::dec
              << ", syndrome=" << corrected.syndrome
              << ", status=" << HammingSecdedCodec::statusToString(corrected.status) << "\n";

    sim.injectSingleBitFault(addr, 5);
    sim.injectSingleBitFault(addr, 9);
    auto detected = sim.read(addr);
    std::cout << "  Double-bit fault -> data=0x" << std::hex << detected.data << std::dec
              << ", syndrome=" << detected.syndrome
              << ", status=" << HammingSecdedCodec::statusToString(detected.status) << "\n";

    sim.write(addr, test_data);
    const bool injected = sim.injectUndetectedPattern(addr);
    auto undetected = sim.read(addr);
    std::cout << "  4-bit pattern search -> injected=" << (injected ? "yes" : "no")
              << ", status=" << HammingSecdedCodec::statusToString(undetected.status)
              << ", data=0x" << std::hex << undetected.data << std::dec << "\n\n";
}

int main() {
    const std::vector<std::size_t> sizes_kb = {64, 128, 256};
    const std::vector<int> widths = {8, 16, 32};

    std::cout << "Practical SRAM SEC-DED simulator for 9 configurations\n";
    for (std::size_t kb : sizes_kb) {
        for (int width : widths) {
            SRAMSimulator sim(kb * 1024, width);
            std::cout << "  " << std::setw(3) << kb << "KB x " << std::setw(2) << width
                      << "-bit => depth " << sim.depthWords() << " words\n";
        }
    }
    std::cout << "\nDetailed demos:\n";

    runDemo(64 * 1024, 8, 0xA5);
    runDemo(128 * 1024, 16, 0xBEEF);
    runDemo(256 * 1024, 32, 0xDEADBEEF);
    return 0;
}
