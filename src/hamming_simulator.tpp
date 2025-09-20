#pragma once

#include <algorithm>
#include <cstdlib>
#include <limits>
#include <sstream>
#include <stdexcept>

#include "third_party/nlohmann/json.hpp"

namespace ecc {

namespace detail {

template <int Bits>
struct CodeWordStorage {
    static constexpr int storage_words = (Bits + 63) / 64;
    static_assert(storage_words <= 2, "CodeWordStorage supports up to 128 bits");

    std::array<uint64_t, storage_words> words{};

    bool getBit(int pos) const {
        if (pos <= 0 || pos > Bits) {
            return false;
        }
        int index = pos - 1;
        int word = index / 64;
        int offset = index % 64;
        return (words[word] >> offset) & 1ULL;
    }

    void setBit(int pos, bool value) {
        if (pos <= 0 || pos > Bits) {
            return;
        }
        int index = pos - 1;
        int word = index / 64;
        int offset = index % 64;
        if (value) {
            words[word] |= (1ULL << offset);
        } else {
            words[word] &= ~(1ULL << offset);
        }
    }

    void flipBit(int pos) {
        if (pos <= 0 || pos > Bits) {
            return;
        }
        int index = pos - 1;
        int word = index / 64;
        int offset = index % 64;
        words[word] ^= (1ULL << offset);
    }

    int countOnes() const {
        int total = 0;
        if constexpr (storage_words > 0) {
            total += __builtin_popcountll(words[0]);
        }
        if constexpr (storage_words > 1) {
            total += __builtin_popcountll(words[1]);
        }
        return total;
    }

    std::array<uint64_t, 2> rawWords() const {
        std::array<uint64_t, 2> raw{0, 0};
        if constexpr (storage_words > 0) {
            raw[0] = words[0];
        }
        if constexpr (storage_words > 1) {
            raw[1] = words[1];
        }
        return raw;
    }
};

}  // namespace detail

template <typename WordTraits>
class HammingCodeSECDED {
public:
    using DataType = typename WordTraits::DataType;
    static constexpr int DATA_BITS = WordTraits::DATA_BITS;
    static constexpr int PARITY_BITS = static_cast<int>(WordTraits::parity_positions.size());
    static constexpr int OVERALL_PARITY_BIT = 1;
    static constexpr int TOTAL_BITS = DATA_BITS + PARITY_BITS + OVERALL_PARITY_BIT;

    struct CodeWord : public detail::CodeWordStorage<TOTAL_BITS> {
        using detail::CodeWordStorage<TOTAL_BITS>::CodeWordStorage;
    };

    enum ErrorType {
        NO_ERROR,
        SINGLE_ERROR_CORRECTABLE,
        DOUBLE_ERROR_DETECTABLE,
        MULTIPLE_ERROR_UNCORRECTABLE,
        OVERALL_PARITY_ERROR
    };

    struct DecodingResult {
        DataType corrected_data{};
        int syndrome = 0;
        int error_position = 0;
        ErrorType error_type = NO_ERROR;
        bool overall_parity = false;
        std::string syndrome_binary;
        std::string error_type_string;
        bool data_corrected = false;
    };

private:
    ParityCheckMatrix pcm_;

    static bool isParityPosition(int pos) {
        for (int parity : WordTraits::parity_positions) {
            if (parity == pos) {
                return true;
            }
        }
        return false;
    }

    static bool isOverallParityPosition(int pos) {
        return pos == TOTAL_BITS;
    }

    void buildParityCheckMatrix() {
        pcm_.rows.clear();
        for (int parity_bit : WordTraits::parity_positions) {
            std::array<uint64_t, 2> row{0, 0};
            for (int pos = 1; pos <= TOTAL_BITS - 1; ++pos) {
                if (pos & parity_bit) {
                    int idx = pos - 1;
                    if (idx < 64) {
                        row[0] |= (1ULL << idx);
                    } else {
                        row[1] |= (1ULL << (idx - 64));
                    }
                }
            }
            pcm_.rows.push_back(row);
        }
    }

    std::vector<int> getDataPositions() const {
        std::vector<int> positions;
        positions.reserve(DATA_BITS);
        for (int pos = 1; pos <= TOTAL_BITS; ++pos) {
            if (!isParityPosition(pos) && !isOverallParityPosition(pos)) {
                positions.push_back(pos);
            }
        }
        return positions;
    }

    static std::string errorTypeToString(ErrorType type) {
        switch (type) {
            case NO_ERROR:
                return "No Error";
            case SINGLE_ERROR_CORRECTABLE:
                return "Single Error (Correctable)";
            case DOUBLE_ERROR_DETECTABLE:
                return "Double Error (Detectable, Not Correctable)";
            case MULTIPLE_ERROR_UNCORRECTABLE:
                return "Multiple Error (Uncorrectable)";
            case OVERALL_PARITY_ERROR:
                return "Overall Parity Error";
        }
        return "Unknown";
    }

public:
    HammingCodeSECDED() {
        buildParityCheckMatrix();
    }

    void resetPCM() {
        buildParityCheckMatrix();
    }

    bool loadPCMFromFile(const std::string& filename) {
        std::ifstream file(filename);
        if (!file) {
            return false;
        }
        pcm_.rows.clear();
        std::string line;
        while (std::getline(file, line)) {
            std::array<uint64_t, 2> row{0, 0};
            std::size_t col = 0;
            for (char c : line) {
                if (c != '0' && c != '1') {
                    continue;
                }
                if (c == '1') {
                    if (col < 64) {
                        row[0] |= (1ULL << col);
                    } else if (col < static_cast<std::size_t>(TOTAL_BITS - 1)) {
                        row[1] |= (1ULL << (col - 64));
                    }
                }
                ++col;
                if (col >= static_cast<std::size_t>(TOTAL_BITS - 1)) {
                    break;
                }
            }
            if (col > 0) {
                pcm_.rows.push_back(row);
            }
        }
        return !pcm_.rows.empty();
    }

    CodeWord encode(DataType data) const {
        CodeWord codeword;
        auto data_positions = getDataPositions();
        using UnsignedData = std::make_unsigned_t<DataType>;
        UnsignedData value = static_cast<UnsignedData>(data);
        for (int i = 0; i < DATA_BITS; ++i) {
            bool bit_value = (value >> i) & static_cast<UnsignedData>(1);
            codeword.setBit(data_positions[static_cast<std::size_t>(i)], bit_value);
        }

        for (int parity_bit : WordTraits::parity_positions) {
            int parity = 0;
            for (int pos = 1; pos <= TOTAL_BITS - 1; ++pos) {
                if (pos & parity_bit) {
                    if (codeword.getBit(pos)) {
                        parity ^= 1;
                    }
                }
            }
            codeword.setBit(parity_bit, parity != 0);
        }

        int overall_parity = 0;
        for (int pos = 1; pos <= TOTAL_BITS - 1; ++pos) {
            if (codeword.getBit(pos)) {
                overall_parity ^= 1;
            }
        }
        codeword.setBit(TOTAL_BITS, overall_parity != 0);
        return codeword;
    }

    DecodingResult decode(CodeWord received) const {
        DecodingResult result;
        BitVector cwVec;
        for (int pos = 1; pos <= TOTAL_BITS - 1; ++pos) {
            if (received.getBit(pos)) {
                cwVec.set(static_cast<std::size_t>(pos - 1), true);
            }
        }

        BitVector synVec = pcm_.syndrome(cwVec);
        for (int i = 0; i < PARITY_BITS; ++i) {
            if (synVec.get(static_cast<std::size_t>(i))) {
                result.syndrome |= (1 << i);
            }
        }

        int calculated_overall_parity = 0;
        for (int pos = 1; pos <= TOTAL_BITS; ++pos) {
            if (received.getBit(pos)) {
                calculated_overall_parity ^= 1;
            }
        }
        result.overall_parity = (calculated_overall_parity != 0);
        result.syndrome_binary = std::bitset<PARITY_BITS>(static_cast<unsigned long long>(result.syndrome)).to_string();

        if (result.syndrome == 0 && !result.overall_parity) {
            result.error_type = NO_ERROR;
        } else if (result.syndrome == 0 && result.overall_parity) {
            result.error_type = OVERALL_PARITY_ERROR;
            result.error_position = TOTAL_BITS;
            received.flipBit(TOTAL_BITS);
            result.data_corrected = true;
        } else if (result.syndrome != 0 && result.overall_parity) {
            result.error_type = SINGLE_ERROR_CORRECTABLE;
            result.error_position = result.syndrome;
            if (result.error_position >= 1 && result.error_position <= TOTAL_BITS - 1) {
                received.flipBit(result.error_position);
                result.data_corrected = true;
            }
        } else if (result.syndrome != 0 && !result.overall_parity) {
            result.error_type = DOUBLE_ERROR_DETECTABLE;
        } else {
            result.error_type = MULTIPLE_ERROR_UNCORRECTABLE;
        }

        result.error_type_string = errorTypeToString(result.error_type);

        auto data_positions = getDataPositions();
        DataType corrected = 0;
        for (int i = 0; i < DATA_BITS; ++i) {
            if (received.getBit(data_positions[static_cast<std::size_t>(i)])) {
                corrected |= static_cast<DataType>(1) << i;
            }
        }
        result.corrected_data = corrected;
        return result;
    }
};

template <typename WordTraits, typename WorkloadTraits>
class ECCStatistics {
public:
    using Params = typename WorkloadTraits::Params;
    using Hamming = HammingCodeSECDED<WordTraits>;

    explicit ECCStatistics(const Params& params)
        : counters_{},
          start_time_(std::chrono::steady_clock::now()),
          energy_accumulator_(0.0),
          energy_per_xor_(params.energy_per_xor),
          energy_per_and_(params.energy_per_and) {
        reset();
    }

    void reset() {
        counters_.clear();
        counters_["total_writes"] = 0;
        counters_["total_reads"] = 0;
        counters_["no_errors"] = 0;
        counters_["single_errors_corrected"] = 0;
        counters_["double_errors_detected"] = 0;
        counters_["multiple_errors_uncorrectable"] = 0;
        counters_["overall_parity_errors"] = 0;
        counters_["data_corruption_prevented"] = 0;
        energy_accumulator_ = 0.0;
        start_time_ = std::chrono::steady_clock::now();
    }

    void recordWrite() {
        counters_["total_writes"]++;
    }

    void recordRead(const typename Hamming::DecodingResult& result) {
        counters_["total_reads"]++;
        energy_accumulator_ += (Hamming::PARITY_BITS + Hamming::OVERALL_PARITY_BIT) * energy_per_xor_;
        switch (result.error_type) {
            case Hamming::NO_ERROR:
                counters_["no_errors"]++;
                break;
            case Hamming::SINGLE_ERROR_CORRECTABLE:
                counters_["single_errors_corrected"]++;
                counters_["data_corruption_prevented"]++;
                energy_accumulator_ += energy_per_and_;
                break;
            case Hamming::DOUBLE_ERROR_DETECTABLE:
                counters_["double_errors_detected"]++;
                counters_["data_corruption_prevented"]++;
                energy_accumulator_ += energy_per_and_;
                break;
            case Hamming::MULTIPLE_ERROR_UNCORRECTABLE:
                counters_["multiple_errors_uncorrectable"]++;
                energy_accumulator_ += energy_per_and_;
                break;
            case Hamming::OVERALL_PARITY_ERROR:
                counters_["overall_parity_errors"]++;
                counters_["data_corruption_prevented"]++;
                energy_accumulator_ += energy_per_and_;
                break;
        }
    }

    void printStatistics() const {
        auto end_time = std::chrono::steady_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time_);

        std::cout << "\n" << std::string(60, '=') << std::endl;
        std::cout << "ECC STATISTICS SUMMARY" << std::endl;
        std::cout << std::string(60, '=') << std::endl;
        std::cout << "Simulation Duration: " << duration.count() << " ms" << std::endl;
        std::cout << "Total Memory Operations:" << std::endl;
        std::cout << "  Writes: " << counters_.at("total_writes") << std::endl;
        std::cout << "  Reads:  " << counters_.at("total_reads") << std::endl;
        std::cout << std::endl;

        auto reads = counters_.at("total_reads");
        auto safeDiv = [reads](uint64_t value) -> double {
            if (reads == 0) {
                return 0.0;
            }
            return 100.0 * static_cast<double>(value) / static_cast<double>(reads);
        };

        std::cout << "Error Detection & Correction:" << std::endl;
        std::cout << "  No Errors:                    " << counters_.at("no_errors")
                  << " (" << std::fixed << std::setprecision(2)
                  << safeDiv(counters_.at("no_errors")) << "%)" << std::endl;
        std::cout << "  Single Errors Corrected:      " << counters_.at("single_errors_corrected")
                  << " (" << safeDiv(counters_.at("single_errors_corrected")) << "%)" << std::endl;
        std::cout << "  Double Errors Detected:       " << counters_.at("double_errors_detected")
                  << " (" << safeDiv(counters_.at("double_errors_detected")) << "%)" << std::endl;
        std::cout << "  Overall Parity Errors:        " << counters_.at("overall_parity_errors")
                  << " (" << safeDiv(counters_.at("overall_parity_errors")) << "%)" << std::endl;
        std::cout << "  Multiple Errors (Uncorrectable): " << counters_.at("multiple_errors_uncorrectable")
                  << " (" << safeDiv(counters_.at("multiple_errors_uncorrectable")) << "%)" << std::endl;

        std::cout << std::endl;
        std::cout << "Data Integrity Metrics:" << std::endl;
        std::cout << "  Data Corruption Prevented:    " << counters_.at("data_corruption_prevented")
                  << " (" << safeDiv(counters_.at("data_corruption_prevented")) << "%)" << std::endl;

        uint64_t total_errors = counters_.at("single_errors_corrected") +
                                counters_.at("double_errors_detected") +
                                counters_.at("multiple_errors_uncorrectable") +
                                counters_.at("overall_parity_errors");
        if (total_errors > 0) {
            double recovery = 100.0 * static_cast<double>(counters_.at("data_corruption_prevented")) /
                               static_cast<double>(total_errors);
            std::cout << "  Error Recovery Rate:           " << std::fixed << std::setprecision(2)
                      << recovery << "%" << std::endl;
        }

        std::cout << std::string(60, '-') << std::endl;
        std::cout << "Estimated energy consumed: " << std::scientific
                  << energy_accumulator_ << " J" << std::endl;
        std::cout << std::string(60, '=') << std::endl;

        // Structured logging of statistics
        std::ofstream json_out("ecc_stats.json");
        if (json_out) {
            double ber = 0.0;
            if (reads > 0) {
                ber = static_cast<double>(total_errors) /
                      (static_cast<double>(reads) * static_cast<double>(Hamming::DATA_BITS));
            }
            json_out << "{\n";
            json_out << "  \"total_reads\": " << reads << ",\n";
            json_out << "  \"total_writes\": " << counters_.at("total_writes") << ",\n";
            json_out << "  \"single_errors_corrected\": " << counters_.at("single_errors_corrected") << ",\n";
            json_out << "  \"double_errors_detected\": " << counters_.at("double_errors_detected") << ",\n";
            json_out << "  \"multiple_errors_uncorrectable\": " << counters_.at("multiple_errors_uncorrectable") << ",\n";
            json_out << "  \"overall_parity_errors\": " << counters_.at("overall_parity_errors") << ",\n";
            json_out << "  \"dynamic_J\": " << energy_accumulator_ << ",\n";
            json_out << "  \"leakage_J\": 0.0,\n";
            json_out << "  \"total_J\": " << energy_accumulator_ << ",\n";
            json_out << "  \"ber\": " << ber << "\n";
            json_out << "}\n";
        }

        std::ofstream csv_out("ecc_stats.csv");
        if (csv_out) {
            csv_out << "metric,value\n";
            for (const auto& p : counters_) {
                csv_out << p.first << ',' << p.second << "\n";
            }
            double ber = 0.0;
            if (reads > 0) {
                ber = static_cast<double>(total_errors) /
                      (static_cast<double>(reads) * static_cast<double>(Hamming::DATA_BITS));
            }
            csv_out << "dynamic_J," << energy_accumulator_ << "\n";
            csv_out << "leakage_J,0\n";
            csv_out << "total_J," << energy_accumulator_ << "\n";
            csv_out << "ber," << ber << "\n";
        }
    }

private:
    std::map<std::string, uint64_t> counters_;
    mutable std::chrono::steady_clock::time_point start_time_;
    double energy_accumulator_;
    double energy_per_xor_;
    double energy_per_and_;
};

template <typename WordTraits, typename WorkloadTraits>
class AdvancedMemorySimulator {
public:
    using AddressType = typename WorkloadTraits::AddressType;
    using Hamming = HammingCodeSECDED<WordTraits>;
    using CodeWord = typename Hamming::CodeWord;
    using Params = typename WorkloadTraits::Params;

    explicit AdvancedMemorySimulator(const Params& params = WorkloadTraits::defaultParams())
        : memory_{},
          hamming_{},
          stats_{params},
          rng_(std::random_device{}()),
          params_(params) {
        std::cout << "Initialized SEC-DED memory simulator with "
                  << WorkloadTraits::memory_size_words << " words" << std::endl;
        std::cout << "Total bits per codeword: " << Hamming::TOTAL_BITS
                  << " (" << Hamming::DATA_BITS << " data + "
                  << Hamming::PARITY_BITS << " parity + "
                  << Hamming::OVERALL_PARITY_BIT << " overall parity)" << std::endl;
    }

    void reinitializeECC() {
        hamming_.resetPCM();
    }

    void write(AddressType address, typename WordTraits::DataType data) {
        if (address >= WorkloadTraits::memory_size_words) {
            throw std::out_of_range("Address out of range");
        }
        memory_[address] = hamming_.encode(data);
        stats_.recordWrite();
    }

    typename Hamming::DecodingResult read(AddressType address) {
        auto it = memory_.find(address);
        if (it == memory_.end()) {
            throw std::out_of_range("Address not written");
        }
        auto result = hamming_.decode(it->second);
        if (result.data_corrected) {
            it->second = hamming_.encode(result.corrected_data);
        }
        stats_.recordRead(result);
        return result;
    }

    void injectError(AddressType address, int bit_position) {
        auto it = memory_.find(address);
        if (it == memory_.end()) {
            throw std::out_of_range("Address not written");
        }
        if (bit_position < 1 || bit_position > Hamming::TOTAL_BITS) {
            throw std::out_of_range("Invalid bit position");
        }
        it->second.flipBit(bit_position);
        std::cout << "Injected error at address 0x" << std::hex
                  << static_cast<unsigned long long>(address) << std::dec
                  << ", bit position " << bit_position << std::endl;
    }

    void injectBurstError(AddressType address, int start_position, int burst_length) {
        auto it = memory_.find(address);
        if (it == memory_.end()) {
            throw std::out_of_range("Address not written");
        }
        if (start_position < 1 || start_position + burst_length - 1 > Hamming::TOTAL_BITS) {
            throw std::out_of_range("Invalid burst error parameters");
        }
        std::cout << "Injecting burst error at address 0x" << std::hex
                  << static_cast<unsigned long long>(address) << std::dec
                  << ", positions " << start_position << "-" << (start_position + burst_length - 1) << ": ";
        for (int i = 0; i < burst_length; ++i) {
            int pos = start_position + i;
            it->second.flipBit(pos);
            std::cout << pos << " ";
        }
        std::cout << std::endl;
    }

    void injectRandomErrors(AddressType address, int num_errors) {
        auto it = memory_.find(address);
        if (it == memory_.end()) {
            throw std::out_of_range("Address not written");
        }
        std::uniform_int_distribution<int> bit_dist(1, Hamming::TOTAL_BITS);
        std::set<int> used_positions;
        std::cout << "Injecting " << num_errors << " random errors at address 0x"
                  << std::hex << static_cast<unsigned long long>(address) << std::dec << ": ";
        for (int i = 0; i < num_errors; ++i) {
            int bit_pos;
            do {
                bit_pos = bit_dist(rng_);
            } while (!used_positions.insert(bit_pos).second);
            it->second.flipBit(bit_pos);
            std::cout << bit_pos << " ";
        }
        std::cout << std::endl;
    }

    bool loadParityCheckMatrix(const std::string& path) {
        return hamming_.loadPCMFromFile(path);
    }

    std::size_t getMemorySize() const {
        return memory_.size();
    }

    AddressType getMemoryCapacity() const {
        return WorkloadTraits::memory_size_words;
    }

    void printStatistics() {
        stats_.printStatistics();
    }

    void resetStatistics() {
        stats_.reset();
    }

    void printFinalSummary(const std::string& banner) const {
        std::cout << "\n" << std::string(60, '=') << std::endl;
        std::cout << banner << std::endl;
        std::cout << "Total memory words used: " << memory_.size() << std::endl;
        double utilization = 0.0;
        if (WorkloadTraits::memory_size_words > 0) {
            utilization = 100.0 * static_cast<double>(memory_.size()) /
                          static_cast<double>(WorkloadTraits::memory_size_words);
        }
        std::cout << "Memory utilization: " << std::fixed << std::setprecision(6)
                  << utilization << "% of " << WorkloadTraits::summary_capacity_label << std::endl;
        double approx_mb = (static_cast<double>(memory_.size()) * sizeof(CodeWord)) /
                           (1024.0 * 1024.0);
        std::cout << "Actual memory consumed: ~" << approx_mb << " MB" << std::endl;
        std::cout << std::string(60, '=') << std::endl;
    }

    Hamming& hamming() {
        return hamming_;
    }

private:
    using MemoryContainer = typename WorkloadTraits::template MemoryContainer<CodeWord>;

    MemoryContainer memory_;
    Hamming hamming_;
    ECCStatistics<WordTraits, WorkloadTraits> stats_;
    std::mt19937 rng_;
    Params params_;
};

template <typename WordTraits, typename WorkloadTraits>
class AdvancedTestSuite {
public:
    using DataType = typename WordTraits::DataType;
    using AddressType = typename WorkloadTraits::AddressType;
    using MemorySimulator = AdvancedMemorySimulator<WordTraits, WorkloadTraits>;
    using Hamming = HammingCodeSECDED<WordTraits>;

    explicit AdvancedTestSuite(MemorySimulator& memory)
        : memory_(memory), hamming_() {}

    void runAllTests() {
        if constexpr (WorkloadTraits::include_known_vectors) {
            testKnownVectors();
        }
        testNoError();
        testSingleBitErrors();
        testDoubleBitErrors();
        testOverallParityErrors();
        testBurstErrors();
        testRandomMultipleErrors();
        testMixedWorkload();
        if constexpr (WorkloadTraits::include_large_address_test) {
            testLargeAddressSpace();
        }
        if constexpr (WorkloadTraits::include_million_dataset) {
            testMillionWordDataset();
        }
        if constexpr (WorkloadTraits::include_batch_fault_injection) {
            batchFaultInjection();
        }
        if constexpr (WorkloadTraits::include_stress_test) {
            const char* stress = std::getenv(WorkloadTraits::stress_env_var);
            if (stress && std::string(stress) == "1") {
                stressOneMillionReadWrite();
            }
        }
    }

private:
    MemorySimulator& memory_;
    Hamming hamming_;

    static void printTestHeader(const std::string& name) {
        std::cout << "\n" << std::string(60, '=') << std::endl;
        std::cout << "TEST: " << name << std::endl;
        std::cout << std::string(60, '=') << std::endl;
    }

    void printDecodingResult(AddressType address,
                              DataType original,
                              const typename Hamming::DecodingResult& result) {
        std::cout << "Address: 0x" << std::hex
                  << static_cast<unsigned long long>(address) << std::dec << std::endl;
        std::cout << "Original Data: 0x" << std::hex
                  << static_cast<unsigned long long>(original) << std::dec
                  << " (" << std::bitset<WordTraits::DATA_BITS>(static_cast<unsigned long long>(original)) << ")" << std::endl;
        std::cout << "Syndrome: " << result.syndrome
                  << " (" << result.syndrome_binary << ")" << std::endl;
        std::cout << "Overall Parity: " << (result.overall_parity ? "ODD" : "EVEN") << std::endl;
        std::cout << "Error Type: " << result.error_type_string << std::endl;
        std::cout << "Error Position: " << result.error_position << std::endl;
        std::cout << "Data Corrected: " << (result.data_corrected ? "YES" : "NO") << std::endl;
        std::cout << "Corrected Data: 0x" << std::hex
                  << static_cast<unsigned long long>(result.corrected_data) << std::dec
                  << " (" << std::bitset<WordTraits::DATA_BITS>(static_cast<unsigned long long>(result.corrected_data))
                  << ")" << std::endl;
        bool integrity = (original == result.corrected_data) ||
                         (result.error_type == Hamming::DOUBLE_ERROR_DETECTABLE) ||
                         (result.error_type == Hamming::MULTIPLE_ERROR_UNCORRECTABLE);
        std::cout << "Data Integrity: " << (integrity ? "MAINTAINED" : "COMPROMISED") << std::endl;
        std::cout << std::string(40, '-') << std::endl;

        std::ofstream csv_log("decoding_results.csv", std::ios::app);
        if (csv_log) {
            csv_log << static_cast<unsigned long long>(address) << ','
                    << static_cast<unsigned long long>(original) << ','
                    << result.error_type_string << ','
                    << (result.data_corrected ? 1 : 0) << '\n';
        }
        std::ofstream json_log("decoding_results.json", std::ios::app);
        if (json_log) {
            json_log << "{\"address\": " << static_cast<unsigned long long>(address)
                     << ", \"error_type\": \"" << result.error_type_string << "\",";
            json_log << " \"data_corrected\": " << (result.data_corrected ? "true" : "false")
                     << "}" << std::endl;
        }
    }

    void testKnownVectors() {
        printTestHeader("Known Test Vectors");
        for (const auto& vector : WorkloadTraits::known_vectors) {
            auto cw = hamming_.encode(vector.data);
            auto raw = cw.rawWords();
            if (raw != vector.encoded) {
                std::ostringstream oss;
                oss << "Encoding mismatch for data 0x" << std::hex
                    << static_cast<unsigned long long>(vector.data);
                throw std::runtime_error(oss.str());
            }
            auto result = hamming_.decode(cw);
            if (result.corrected_data != vector.data) {
                throw std::runtime_error("Decoding mismatch for known vector");
            }
            printDecodingResult(0, vector.data, result);
        }
    }

    void testNoError() {
        printTestHeader("No Error Test (SEC-DED)");
        for (std::size_t i = 0; i < WorkloadTraits::no_error_data.size(); ++i) {
            AddressType address = WorkloadTraits::no_error_base + static_cast<AddressType>(i);
            DataType data = WorkloadTraits::no_error_data[i];
            memory_.write(address, data);
            auto result = memory_.read(address);
            std::cout << "Test " << (i + 1) << ":" << std::endl;
            printDecodingResult(address, data, result);
        }
    }

    void testSingleBitErrors() {
        printTestHeader("Single Bit Error Test (SEC-DED)");
        DataType data = WorkloadTraits::single_error_data;
        for (int pos : WorkloadTraits::single_error_positions) {
            AddressType address = WorkloadTraits::single_error_base + static_cast<AddressType>(pos);
            memory_.write(address, data);
            memory_.injectError(address, pos);
            auto result = memory_.read(address);
            std::cout << "Single error at position " << pos << ":" << std::endl;
            printDecodingResult(address, data, result);
        }
    }

    void testDoubleBitErrors() {
        printTestHeader("Double Bit Error Test (SEC-DED Detection)");
        DataType data = WorkloadTraits::double_error_data;
        for (std::size_t i = 0; i < WorkloadTraits::double_error_pairs.size(); ++i) {
            AddressType address = WorkloadTraits::double_error_base + static_cast<AddressType>(i);
            const auto& pair = WorkloadTraits::double_error_pairs[i];
            memory_.write(address, data);
            memory_.injectError(address, pair.first);
            memory_.injectError(address, pair.second);
            auto result = memory_.read(address);
            std::cout << "Double error at positions " << pair.first << ", " << pair.second << ":" << std::endl;
            printDecodingResult(address, data, result);
        }
    }

    void testOverallParityErrors() {
        printTestHeader("Overall Parity Bit Error Test");
        DataType data = WorkloadTraits::overall_parity_data;
        AddressType address = WorkloadTraits::overall_parity_address;
        memory_.write(address, data);
        memory_.injectError(address, Hamming::TOTAL_BITS);
        auto result = memory_.read(address);
        std::cout << "Overall parity bit error:" << std::endl;
        printDecodingResult(address, data, result);
    }

    void testBurstErrors() {
        printTestHeader("Burst Error Test");
        DataType data = WorkloadTraits::burst_data;
        for (std::size_t i = 0; i < WorkloadTraits::burst_configs.size(); ++i) {
            AddressType address = WorkloadTraits::burst_base + static_cast<AddressType>(i);
            auto [start, length] = WorkloadTraits::burst_configs[i];
            memory_.write(address, data);
            memory_.injectBurstError(address, start, length);
            auto result = memory_.read(address);
            std::cout << "Burst error (" << length << " bits):" << std::endl;
            printDecodingResult(address, data, result);
        }
    }

    void testRandomMultipleErrors() {
        printTestHeader("Random Multiple Error Test");
        DataType data = WorkloadTraits::random_multiple_data;
        for (std::size_t i = 0; i < WorkloadTraits::random_error_counts.size(); ++i) {
            AddressType address = WorkloadTraits::random_multiple_base + static_cast<AddressType>(i);
            memory_.write(address, data);
            memory_.injectRandomErrors(address, WorkloadTraits::random_error_counts[i]);
            auto result = memory_.read(address);
            std::cout << "Random multiple errors (" << WorkloadTraits::random_error_counts[i] << " bits):" << std::endl;
            printDecodingResult(address, data, result);
        }
    }

    void testMixedWorkload() {
        printTestHeader("Mixed Workload Simulation");
        std::mt19937 rng(WorkloadTraits::mixed_workload_seed);
        std::uniform_int_distribution<DataType> data_dist(0, std::numeric_limits<DataType>::max());
        std::uniform_int_distribution<int> error_type_dist(0, 100);
        for (int i = 0; i < WorkloadTraits::mixed_workload_iterations; ++i) {
            AddressType address = WorkloadTraits::mixed_workload_base + static_cast<AddressType>(i);
            DataType data = data_dist(rng);
            memory_.write(address, data);
            int error_chance = error_type_dist(rng);
            std::string scenario;
            if (error_chance < 70) {
                scenario = "No Error";
            } else if (error_chance < 85) {
                std::uniform_int_distribution<int> bit_dist(1, Hamming::TOTAL_BITS);
                memory_.injectError(address, bit_dist(rng));
                scenario = "Single Error";
            } else if (error_chance < 95) {
                memory_.injectRandomErrors(address, 2);
                scenario = "Double Error";
            } else {
                std::uniform_int_distribution<int> count_dist(3, 6);
                memory_.injectRandomErrors(address, count_dist(rng));
                scenario = "Multiple Errors";
            }
            auto result = memory_.read(address);
            std::cout << "Mixed workload " << (i + 1) << " (" << scenario << "):" << std::endl;
            printDecodingResult(address, data, result);
        }
    }

    void batchFaultInjection() {
        printTestHeader("Batch Fault Injection");
        std::mt19937 rng(WorkloadTraits::batch_seed);
        std::uniform_int_distribution<DataType> data_dist(0, std::numeric_limits<DataType>::max());
        std::uniform_int_distribution<int> error_count_dist(WorkloadTraits::batch_min_errors,
                                                            WorkloadTraits::batch_max_errors);
        std::uniform_int_distribution<int> pos_dist(1, Hamming::TOTAL_BITS);
        int detections = 0;
        int corrections = 0;
        std::ofstream log("batch_results.csv");
        if (log) {
            log << "trial,errors,detected,corrected\n";
        }
        for (unsigned trial = 0; trial < WorkloadTraits::batch_fault_trials; ++trial) {
            DataType data = data_dist(rng);
            auto cw = hamming_.encode(data);
            int num_errors = error_count_dist(rng);
            std::set<int> used;
            for (int i = 0; i < num_errors; ++i) {
                int pos;
                do {
                    pos = pos_dist(rng);
                } while (!used.insert(pos).second);
                cw.flipBit(pos);
            }
            auto result = hamming_.decode(cw);
            bool detected = (result.error_type != Hamming::NO_ERROR);
            bool corrected = (result.corrected_data == data);
            if (detected) {
                detections++;
            }
            if (corrected) {
                corrections++;
            }
            if (log) {
                log << trial << ',' << num_errors << ',' << detected << ',' << corrected << '\n';
            }
        }
        std::cout << "Detection rate: " << (100.0 * detections / WorkloadTraits::batch_fault_trials)
                  << "%" << std::endl;
        std::cout << "Correction rate: " << (100.0 * corrections / WorkloadTraits::batch_fault_trials)
                  << "%" << std::endl;
    }

    void testLargeAddressSpace() {
        printTestHeader("Large Address Space Test");
        for (std::size_t i = 0; i < WorkloadTraits::large_addresses.size(); ++i) {
            AddressType address = WorkloadTraits::large_addresses[i];
            DataType data = WorkloadTraits::large_address_patterns[i];
            try {
                memory_.write(address, data);
                std::mt19937 rng(static_cast<unsigned int>(address));
                std::uniform_int_distribution<int> bit_dist(1, Hamming::TOTAL_BITS);
                int error_pos = bit_dist(rng);
                memory_.injectError(address, error_pos);
                auto result = memory_.read(address);
                std::cout << "Large address test (Address: 0x" << std::hex
                          << static_cast<unsigned long long>(address) << std::dec
                          << ", ~" << static_cast<unsigned long long>((address * (WordTraits::DATA_BITS / 8)) / (1024 * 1024 * 1024))
                          << "GB offset):" << std::endl;
                printDecodingResult(address, data, result);
            } catch (const std::exception& e) {
                std::cout << "Large address 0x" << std::hex
                          << static_cast<unsigned long long>(address) << std::dec
                          << " test failed: " << e.what() << std::endl;
            }
        }
        std::cout << "Large address space testing demonstrates scalability to large memories." << std::endl;
        std::cout << "Sparse allocation only uses memory for addresses actually written." << std::endl;
        std::cout << "Memory efficiency: Only " << memory_.getMemorySize() << " words allocated out of "
                  << memory_.getMemoryCapacity() << " possible." << std::endl;
    }

    void testMillionWordDataset() {
        printTestHeader("Million Word Dataset");
        std::mt19937 rng(WorkloadTraits::million_dataset_seed);
        std::uniform_int_distribution<DataType> data_dist(0, std::numeric_limits<DataType>::max());
        std::uniform_int_distribution<int> err_dist(0, WorkloadTraits::million_dataset_error_upper);
        std::uniform_int_distribution<int> bit_dist(1, Hamming::TOTAL_BITS);
        std::map<typename Hamming::ErrorType, uint64_t> counts;
        for (uint64_t i = 0; i < WorkloadTraits::million_dataset_size; ++i) {
            AddressType address = WorkloadTraits::million_dataset_base + static_cast<AddressType>(i);
            DataType data = data_dist(rng);
            memory_.write(address, data);
            int chance = err_dist(rng);
            if (chance < 995) {
                // no error
            } else if (chance < 997) {
                memory_.injectError(address, bit_dist(rng));
            } else if (chance < 999) {
                memory_.injectRandomErrors(address, 2);
            } else {
                memory_.injectRandomErrors(address, 3);
            }
            auto result = memory_.read(address);
            counts[result.error_type]++;
        }
        std::cout << "Processed " << WorkloadTraits::million_dataset_size << " addresses." << std::endl;
        std::cout << "  No Errors: " << counts[Hamming::NO_ERROR] << std::endl;
        std::cout << "  Single Errors Corrected: " << counts[Hamming::SINGLE_ERROR_CORRECTABLE] << std::endl;
        std::cout << "  Double Errors Detected: " << counts[Hamming::DOUBLE_ERROR_DETECTABLE] << std::endl;
        std::cout << "  Multiple Errors (Uncorrectable): " << counts[Hamming::MULTIPLE_ERROR_UNCORRECTABLE] << std::endl;
        std::cout << "  Overall Parity Errors: " << counts[Hamming::OVERALL_PARITY_ERROR] << std::endl;
    }

    void stressOneMillionReadWrite() {
        printTestHeader("One Million Read/Write Stress Test");
        std::mt19937 rng(WorkloadTraits::stress_test_seed);
        std::uniform_int_distribution<DataType> data_dist(0, std::numeric_limits<DataType>::max());
        std::vector<DataType> values(WorkloadTraits::stress_test_count);
        for (uint64_t i = 0; i < WorkloadTraits::stress_test_count; ++i) {
            DataType data = data_dist(rng);
            values[static_cast<std::size_t>(i)] = data;
            memory_.write(WorkloadTraits::stress_test_base + static_cast<AddressType>(i), data);
        }
        uint64_t mismatches = 0;
        for (uint64_t i = 0; i < WorkloadTraits::stress_test_count; ++i) {
            auto result = memory_.read(WorkloadTraits::stress_test_base + static_cast<AddressType>(i));
            if (result.corrected_data != values[static_cast<std::size_t>(i)] ||
                result.error_type != Hamming::NO_ERROR) {
                mismatches++;
            }
        }
        std::cout << "Stress test completed. " << WorkloadTraits::stress_test_count
                  << " addresses verified." << std::endl;
        std::cout << "Mismatched reads: " << mismatches << std::endl;
    }
};

inline void runEccSchemeDemo(int trials, unsigned seed) {
    using Pattern = std::pair<int, std::string>;
    const std::vector<Pattern> patterns = {
        {1, ""}, {2, "adj"}, {2, "nonadj"}, {3, "adj"}, {3, "nonadj"}
    };
    const std::set<Pattern> correctable_hamming = {{1, ""}};
    const std::set<Pattern> detectable_hamming = {{2, "adj"}, {2, "nonadj"}};
    const std::set<Pattern> correctable_taec = {{1, ""}, {2, "adj"}, {3, "adj"}};
    const std::set<Pattern> detectable_taec = {{2, "nonadj"}, {3, "nonadj"}};

    std::map<Pattern, int> pattern_counts;
    struct Stats { int corrected = 0; int detected = 0; int undetected = 0; };
    std::map<std::string, Stats> stats = {{"SEC-DED", {}}, {"TAEC", {}}};

    std::mt19937 rng(seed);
    std::uniform_int_distribution<std::size_t> dist(0, patterns.size() - 1);
    for (int i = 0; i < trials; ++i) {
        const Pattern& pattern = patterns[dist(rng)];
        pattern_counts[pattern]++;
        auto update = [&](const std::string& code,
                          const std::set<Pattern>& correctable,
                          const std::set<Pattern>& detectable) {
            if (correctable.count(pattern)) {
                stats[code].corrected++;
            } else if (detectable.count(pattern)) {
                stats[code].detected++;
            } else {
                stats[code].undetected++;
            }
        };
        update("SEC-DED", correctable_hamming, detectable_hamming);
        update("TAEC", correctable_taec, detectable_taec);
    }

    auto label = [](const Pattern& pattern) {
        if (pattern.first == 1) {
            return std::string("1-bit single");
        }
        std::string type = (pattern.second == "adj") ? "adjacent" : "nonadjacent";
        return std::to_string(pattern.first) + "-bit " + type;
    };

    std::cout << "\nPattern distribution:" << std::endl;
    for (const auto& pattern : patterns) {
        std::cout << "  " << label(pattern) << ": " << pattern_counts[pattern] << std::endl;
    }

    std::cout << "\nECC results:" << std::endl;
    for (const auto& kv : stats) {
        const auto& code = kv.first;
        const auto& s = kv.second;
        std::cout << "  " << std::setw(7) << code
                  << " -> corrected: " << s.corrected
                  << " (" << std::fixed << std::setprecision(2)
                  << (100.0 * s.corrected / trials) << "%), "
                  << "detected-only: " << s.detected
                  << " (" << (100.0 * s.detected / trials) << "%), "
                  << "undetected: " << s.undetected
                  << " (" << (100.0 * s.undetected / trials) << "%)" << std::endl;
    }
}

inline void printArchetypeReport(const std::string& json_path) {
    std::ifstream file(json_path);
    if (!file) {
        std::cerr << "Warning: unable to open archetype config at '" << json_path << "'" << std::endl;
        return;
    }
    nlohmann::json data;
    try {
        file >> data;
    } catch (const std::exception& e) {
        std::cerr << "Warning: failed to parse archetype config: " << e.what() << std::endl;
        return;
    }

    std::cout << "\n" << std::string(60, '=') << std::endl;
    std::cout << "ARCHETYPE GUIDANCE" << std::endl;
    std::cout << std::string(60, '=') << std::endl;

    const auto& archetypes = data["archetypes"];
    for (const auto& archetype : archetypes) {
        std::cout << "Archetype: \"" << archetype.value("name", "") << "\" ("
                  << archetype.value("tagline", "") << ")" << std::endl;
        std::cout << "Design Rationale: \"" << archetype.value("design_rationale", "") << "\"" << std::endl;
        for (const auto& section : archetype["sections"]) {
            std::cout << section.value("heading", "") << ':' << std::endl;
            for (const auto& item : section["items"]) {
                std::cout << "- " << item.get<std::string>() << std::endl;
            }
        }
        std::cout << std::string(40, '-') << std::endl;
    }

    const auto& tradeoff = data["tradeoff"];
    std::cout << tradeoff.value("heading", "") << ':' << std::endl;
    std::cout << tradeoff.value("matrix_title", "") << ':' << std::endl;
    const auto& columns = tradeoff["columns"];
    std::cout << std::setw(18) << "";
    for (const auto& col : columns) {
        std::cout << std::setw(13) << col.get<std::string>();
    }
    std::cout << std::endl;
    for (const auto& row : tradeoff["rows"]) {
        std::cout << std::setw(18) << row.value("label", "");
        const auto& values = row["values"];
        for (const auto& val : values) {
            std::cout << std::setw(13) << val.get<std::string>();
        }
        std::cout << std::endl;
    }
    std::cout << std::string(60, '=') << std::endl;
}

}  // namespace ecc

