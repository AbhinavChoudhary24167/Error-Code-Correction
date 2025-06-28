#include <iostream>
#include <vector>
#include <bitset>
#include <random>
#include <iomanip>
#include <cassert>
#include <cmath>
#include <chrono>
#include <map>
#include <set>

class HammingCodeSECDED {
public:
    static const int DATA_BITS = 64;
    static const int PARITY_BITS = 7;  // 2^7 = 128 >= 64 + 7 + 1 = 72
    static const int OVERALL_PARITY_BIT = 1;  // SEC-DED enhancement
    static const int TOTAL_BITS = DATA_BITS + PARITY_BITS + OVERALL_PARITY_BIT;  // 72 bits
    
private:
    // Parity bit positions (powers of 2): 1, 2, 4, 8, 16, 32, 64
    std::vector<int> parity_positions = {1, 2, 4, 8, 16, 32, 64};
    
public:
    struct CodeWord {
        uint64_t data_low;   // Lower 64 bits
        uint16_t data_high;  // Upper 8 bits (72-64=8 bits needed)
        
        CodeWord() : data_low(0), data_high(0) {}
        CodeWord(uint64_t d_low, uint16_t d_high = 0) : data_low(d_low), data_high(d_high & 0xFF) {}
        
        bool getBit(int pos) const {
            if (pos <= 0 || pos > TOTAL_BITS) return false;
            if (pos <= 64) {
                return (data_low >> (pos - 1)) & 1;
            } else {
                return (data_high >> (pos - 65)) & 1;
            }
        }
        
        void setBit(int pos, bool value) {
            if (pos <= 0 || pos > TOTAL_BITS) return;
            if (pos <= 64) {
                if (value) {
                    data_low |= (1ULL << (pos - 1));
                } else {
                    data_low &= ~(1ULL << (pos - 1));
                }
            } else {
                if (value) {
                    data_high |= (1 << (pos - 65));
                } else {
                    data_high &= ~(1 << (pos - 65));
                }
            }
        }
        
        void flipBit(int pos) {
            if (pos <= 0 || pos > TOTAL_BITS) return;
            if (pos <= 64) {
                data_low ^= (1ULL << (pos - 1));
            } else {
                data_high ^= (1 << (pos - 65));
            }
        }
        
        int countOnes() const {
            return __builtin_popcountll(data_low) + __builtin_popcount(data_high & 0xFF);
        }
    };
    
    enum ErrorType {
        NO_ERROR,
        SINGLE_ERROR_CORRECTABLE,
        DOUBLE_ERROR_DETECTABLE,
        MULTIPLE_ERROR_UNCORRECTABLE,
        OVERALL_PARITY_ERROR
    };
    
    struct DecodingResult {
        uint64_t corrected_data;
        int syndrome;
        int error_position;
        ErrorType error_type;
        bool overall_parity;
        std::string syndrome_binary;
        std::string error_type_string;
        bool data_corrected;
    };
    
    // Check if position is a parity bit position
    bool isParityPosition(int pos) {
        return (pos & (pos - 1)) == 0 && pos <= 64;  // Check if pos is power of 2 <= 64
    }
    
    // Check if position is overall parity position
    bool isOverallParityPosition(int pos) {
        return pos == TOTAL_BITS;  // Position 72
    }
    
    // Get data bit positions (non-parity, non-overall-parity positions)
    std::vector<int> getDataPositions() {
        std::vector<int> positions;
        for (int i = 1; i <= TOTAL_BITS; i++) {
            if (!isParityPosition(i) && !isOverallParityPosition(i)) {
                positions.push_back(i);
            }
        }
        return positions;
    }
    
    // Encode 64-bit data into 72-bit SEC-DED Hamming codeword
    CodeWord encode(uint64_t data) {
        CodeWord codeword;
        
        // Place data bits in non-parity positions
        std::vector<int> data_positions = getDataPositions();
        for (int i = 0; i < DATA_BITS; i++) {
            bool bit_value = (data >> i) & 1ULL;
            codeword.setBit(data_positions[i], bit_value);
        }
        
        // Calculate and set Hamming parity bits
        for (int parity_bit : parity_positions) {
            int parity = 0;
            
            // Check all positions that this parity bit covers
            for (int pos = 1; pos <= TOTAL_BITS - 1; pos++) {  // Exclude overall parity
                if ((pos & parity_bit) != 0) {  // If bit is set in binary representation
                    if (codeword.getBit(pos)) {
                        parity ^= 1;
                    }
                }
            }
            
            codeword.setBit(parity_bit, parity);
        }
        
        // Calculate and set overall parity bit (SEC-DED)
        int overall_parity = 0;
        for (int pos = 1; pos <= TOTAL_BITS - 1; pos++) {
            if (codeword.getBit(pos)) {
                overall_parity ^= 1;
            }
        }
        codeword.setBit(TOTAL_BITS, overall_parity);
        
        return codeword;
    }
    
    // Decode SEC-DED Hamming codeword with enhanced error detection
    DecodingResult decode(CodeWord received) {
        DecodingResult result;
        result.syndrome = 0;
        result.error_position = 0;
        result.data_corrected = false;
        
        // Calculate Hamming syndrome
        for (int i = 0; i < PARITY_BITS; i++) {
            int parity_bit = parity_positions[i];
            int parity = 0;
            
            // Check all positions that this parity bit covers (excluding overall parity)
            for (int pos = 1; pos <= TOTAL_BITS - 1; pos++) {
                if ((pos & parity_bit) != 0) {
                    if (received.getBit(pos)) {
                        parity ^= 1;
                    }
                }
            }
            
            if (parity != 0) {
                result.syndrome |= (1 << i);
            }
        }
        
        // Calculate overall parity
        int calculated_overall_parity = 0;
        for (int pos = 1; pos <= TOTAL_BITS; pos++) {
            if (received.getBit(pos)) {
                calculated_overall_parity ^= 1;
            }
        }
        result.overall_parity = (calculated_overall_parity != 0);
        
        // Convert syndrome to binary string
        result.syndrome_binary = std::bitset<PARITY_BITS>(result.syndrome).to_string();
        
        // SEC-DED Analysis
        if (result.syndrome == 0 && !result.overall_parity) {
            // No error
            result.error_type = NO_ERROR;
            result.error_type_string = "No Error";
        } else if (result.syndrome == 0 && result.overall_parity) {
            // Error in overall parity bit only
            result.error_type = OVERALL_PARITY_ERROR;
            result.error_type_string = "Overall Parity Error";
            result.error_position = TOTAL_BITS;
            received.flipBit(TOTAL_BITS);
            result.data_corrected = true;
        } else if (result.syndrome != 0 && result.overall_parity) {
            // Single error (correctable)
            result.error_type = SINGLE_ERROR_CORRECTABLE;
            result.error_type_string = "Single Error (Correctable)";
            result.error_position = result.syndrome;
            
            if (result.error_position <= TOTAL_BITS - 1) {
                received.flipBit(result.error_position);
                result.data_corrected = true;
            }
        } else if (result.syndrome != 0 && !result.overall_parity) {
            // Double error (detectable, not correctable)
            result.error_type = DOUBLE_ERROR_DETECTABLE;
            result.error_type_string = "Double Error (Detectable, Not Correctable)";
            result.data_corrected = false;
        } else {
            // Multiple error (uncorrectable)
            result.error_type = MULTIPLE_ERROR_UNCORRECTABLE;
            result.error_type_string = "Multiple Error (Uncorrectable)";
            result.data_corrected = false;
        }
        
        // Extract data bits from (possibly corrected) codeword
        std::vector<int> data_positions = getDataPositions();
        result.corrected_data = 0;
        for (int i = 0; i < DATA_BITS; i++) {
            if (received.getBit(data_positions[i])) {
                result.corrected_data |= (1ULL << i);
            }
        }
        
        return result;
    }
};

class ECCStatistics {
private:
    std::map<std::string, uint64_t> counters;
    std::chrono::steady_clock::time_point start_time;
    
public:
    ECCStatistics() {
        start_time = std::chrono::steady_clock::now();
        reset();
    }
    
    void reset() {
        counters.clear();
        counters["total_writes"] = 0;
        counters["total_reads"] = 0;
        counters["no_errors"] = 0;
        counters["single_errors_corrected"] = 0;
        counters["double_errors_detected"] = 0;
        counters["multiple_errors_uncorrectable"] = 0;
        counters["overall_parity_errors"] = 0;
        counters["data_corruption_prevented"] = 0;
    }
    
    void recordWrite() {
        counters["total_writes"]++;
    }
    
    void recordRead(const HammingCodeSECDED::DecodingResult& result) {
        counters["total_reads"]++;
        
        switch (result.error_type) {
            case HammingCodeSECDED::NO_ERROR:
                counters["no_errors"]++;
                break;
            case HammingCodeSECDED::SINGLE_ERROR_CORRECTABLE:
                counters["single_errors_corrected"]++;
                counters["data_corruption_prevented"]++;
                break;
            case HammingCodeSECDED::DOUBLE_ERROR_DETECTABLE:
                counters["double_errors_detected"]++;
                counters["data_corruption_prevented"]++;
                break;
            case HammingCodeSECDED::MULTIPLE_ERROR_UNCORRECTABLE:
                counters["multiple_errors_uncorrectable"]++;
                break;
            case HammingCodeSECDED::OVERALL_PARITY_ERROR:
                counters["overall_parity_errors"]++;
                counters["data_corruption_prevented"]++;
                break;
        }
    }
    
    void printStatistics() {
        auto end_time = std::chrono::steady_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
        
        std::cout << "\n" << std::string(60, '=') << std::endl;
        std::cout << "ECC STATISTICS SUMMARY" << std::endl;
        std::cout << std::string(60, '=') << std::endl;
        std::cout << "Simulation Duration: " << duration.count() << " ms" << std::endl;
        std::cout << "Total Memory Operations:" << std::endl;
        std::cout << "  Writes: " << counters["total_writes"] << std::endl;
        std::cout << "  Reads:  " << counters["total_reads"] << std::endl;
        std::cout << std::endl;
        
        std::cout << "Error Detection & Correction:" << std::endl;
        std::cout << "  No Errors:                    " << counters["no_errors"] 
                  << " (" << std::fixed << std::setprecision(2) 
                  << (100.0 * counters["no_errors"] / counters["total_reads"]) << "%)" << std::endl;
        std::cout << "  Single Errors Corrected:      " << counters["single_errors_corrected"]
                  << " (" << std::fixed << std::setprecision(2) 
                  << (100.0 * counters["single_errors_corrected"] / counters["total_reads"]) << "%)" << std::endl;
        std::cout << "  Double Errors Detected:       " << counters["double_errors_detected"]
                  << " (" << std::fixed << std::setprecision(2) 
                  << (100.0 * counters["double_errors_detected"] / counters["total_reads"]) << "%)" << std::endl;
        std::cout << "  Overall Parity Errors:        " << counters["overall_parity_errors"]
                  << " (" << std::fixed << std::setprecision(2) 
                  << (100.0 * counters["overall_parity_errors"] / counters["total_reads"]) << "%)" << std::endl;
        std::cout << "  Multiple Errors (Uncorrectable): " << counters["multiple_errors_uncorrectable"]
                  << " (" << std::fixed << std::setprecision(2) 
                  << (100.0 * counters["multiple_errors_uncorrectable"] / counters["total_reads"]) << "%)" << std::endl;
        
        std::cout << std::endl;
        std::cout << "Data Integrity Metrics:" << std::endl;
        std::cout << "  Data Corruption Prevented:    " << counters["data_corruption_prevented"]
                  << " (" << std::fixed << std::setprecision(2) 
                  << (100.0 * counters["data_corruption_prevented"] / counters["total_reads"]) << "%)" << std::endl;
        
        uint64_t total_errors = counters["single_errors_corrected"] + 
                               counters["double_errors_detected"] + 
                               counters["multiple_errors_uncorrectable"] + 
                               counters["overall_parity_errors"];
        
        if (total_errors > 0) {
            std::cout << "  Error Recovery Rate:           " 
                      << std::fixed << std::setprecision(2)
                      << (100.0 * counters["data_corruption_prevented"] / total_errors) << "%" << std::endl;
        }
        
        std::cout << std::string(60, '=') << std::endl;
    }
};

class AdvancedMemorySimulator {
private:
    static const size_t MEMORY_SIZE_WORDS = 16ULL * 1024 * 1024 * 1024;  // 128GB / 8 bytes = 16G words
    std::map<uint64_t, HammingCodeSECDED::CodeWord> memory;  // Sparse memory representation
    HammingCodeSECDED hamming;
    ECCStatistics stats;
    std::mt19937 rng;
    
public:
    AdvancedMemorySimulator() : rng(std::random_device{}()) {
        std::cout << "Initialized SEC-DED 128GB memory simulator with " 
                  << MEMORY_SIZE_WORDS << " 64-bit words capacity" << std::endl;
        std::cout << "Memory capacity: " << (MEMORY_SIZE_WORDS * 8ULL) / (1024*1024*1024) << " GB" << std::endl;
        std::cout << "Using sparse memory allocation (map-based)" << std::endl;
        std::cout << "Total bits per codeword: " << HammingCodeSECDED::TOTAL_BITS 
                  << " (64 data + 7 parity + 1 overall parity)" << std::endl;
    }
    
    // Write data to memory with SEC-DED encoding
    void write(uint64_t address, uint64_t data) {
        if (address >= MEMORY_SIZE_WORDS) {
            throw std::out_of_range("Address out of range");
        }
        
        memory[address] = hamming.encode(data);
        stats.recordWrite();
    }
    
    // Read data from memory with error detection/correction
    HammingCodeSECDED::DecodingResult read(uint64_t address) {
        auto it = memory.find(address);
        if (it == memory.end()) {
            throw std::out_of_range("Address not written");
        }
        
        auto result = hamming.decode(it->second);
        stats.recordRead(result);
        return result;
    }
    
    // Inject single-bit error at specific position
    void injectError(uint64_t address, int bit_position) {
        auto it = memory.find(address);
        if (it == memory.end()) {
            throw std::out_of_range("Address not written");
        }
        
        if (bit_position < 1 || bit_position > HammingCodeSECDED::TOTAL_BITS) {
            throw std::out_of_range("Invalid bit position");
        }
        
        it->second.flipBit(bit_position);
        std::cout << "Injected error at address 0x" << std::hex << address << std::dec
                  << ", bit position " << bit_position << std::endl;
    }
    
    // Inject burst error (adjacent bits)
    void injectBurstError(uint64_t address, int start_position, int burst_length) {
        auto it = memory.find(address);
        if (it == memory.end()) {
            throw std::out_of_range("Address not written");
        }
        
        if (start_position < 1 || start_position + burst_length - 1 > HammingCodeSECDED::TOTAL_BITS) {
            throw std::out_of_range("Invalid burst error parameters");
        }
        
        std::cout << "Injecting burst error at address 0x" << std::hex << address << std::dec
                  << ", positions " << start_position << "-" << (start_position + burst_length - 1) << ": ";
        
        for (int i = 0; i < burst_length; i++) {
            int pos = start_position + i;
            it->second.flipBit(pos);
            std::cout << pos << " ";
        }
        std::cout << std::endl;
    }
    
    // Inject random errors
    void injectRandomErrors(uint64_t address, int num_errors) {
        auto it = memory.find(address);
        if (it == memory.end()) {
            throw std::out_of_range("Address not written");
        }
        
        std::uniform_int_distribution<int> bit_dist(1, HammingCodeSECDED::TOTAL_BITS);
        std::cout << "Injecting " << num_errors << " random errors at address 0x" << std::hex << address << std::dec << ": ";
        
        std::set<int> used_positions;
        for (int i = 0; i < num_errors; i++) {
            int bit_pos;
            do {
                bit_pos = bit_dist(rng);
            } while (used_positions.count(bit_pos));
            
            used_positions.insert(bit_pos);
            it->second.flipBit(bit_pos);
            std::cout << bit_pos << " ";
        }
        std::cout << std::endl;
    }
    
    size_t getMemorySize() const {
        return memory.size();
    }
    
    size_t getMemoryCapacity() const {
        return MEMORY_SIZE_WORDS;
    }
    
    void printStatistics() {
        stats.printStatistics();
    }
    
    void resetStatistics() {
        stats.reset();
    }
};

class AdvancedTestSuite {
private:
    AdvancedMemorySimulator& memory;
    HammingCodeSECDED hamming;
    
    void printTestHeader(const std::string& test_name) {
        std::cout << "\n" << std::string(60, '=') << std::endl;
        std::cout << "TEST: " << test_name << std::endl;
        std::cout << std::string(60, '=') << std::endl;
    }
    
    void printDecodingResult(uint64_t address, uint64_t original_data, 
                           const HammingCodeSECDED::DecodingResult& result) {
        std::cout << "Address: 0x" << std::hex << address << std::dec << std::endl;
        std::cout << "Original Data: 0x" << std::hex << original_data 
                  << " (" << std::bitset<64>(original_data) << ")" << std::endl;
        std::cout << "Syndrome: " << result.syndrome 
                  << " (" << result.syndrome_binary << ")" << std::endl;
        std::cout << "Overall Parity: " << (result.overall_parity ? "ODD" : "EVEN") << std::endl;
        std::cout << "Error Type: " << result.error_type_string << std::endl;
        std::cout << "Error Position: " << result.error_position << std::endl;
        std::cout << "Data Corrected: " << (result.data_corrected ? "YES" : "NO") << std::endl;
        std::cout << "Corrected Data: 0x" << std::hex << result.corrected_data 
                  << " (" << std::bitset<64>(result.corrected_data) << ")" << std::endl;
        std::cout << "Data Integrity: " << ((original_data == result.corrected_data || 
                                             result.error_type == HammingCodeSECDED::DOUBLE_ERROR_DETECTABLE) ? "MAINTAINED" : "COMPROMISED") << std::endl;
        std::cout << std::string(40, '-') << std::endl;
    }
    
public:
    AdvancedTestSuite(AdvancedMemorySimulator& mem) : memory(mem) {}
    
    void runAllTests() {
        testNoError();
        testSingleBitErrors();
        testDoubleBitErrors();
        testOverallParityErrors();
        testBurstErrors();
        testRandomMultipleErrors();
        testMixedWorkload();
        testLargeAddressSpace();
    }
    
    void testNoError() {
        printTestHeader("No Error Test (SEC-DED)");
        
        std::vector<uint64_t> test_data = {
            0x0000000000000000ULL, 
            0xFFFFFFFFFFFFFFFFULL, 
            0x123456789ABCDEF0ULL, 
            0xA5A5A5A5A5A5A5A5ULL, 
            0x5A5A5A5A5A5A5A5AULL
        };
        
        for (size_t i = 0; i < test_data.size(); i++) {
            uint64_t address = i;
            uint64_t data = test_data[i];
            
            memory.write(address, data);
            auto result = memory.read(address);
            
            std::cout << "Test " << (i + 1) << ":" << std::endl;
            printDecodingResult(address, data, result);
        }
    }
    
    void testSingleBitErrors() {
        printTestHeader("Single Bit Error Test (SEC-DED)");
        
        uint64_t test_data = 0x123456789ABCDEF0ULL;
        uint64_t base_address = 1000;
        
        // Test a sampling of positions including data, parity, and overall parity
        std::vector<int> test_positions = {1, 2, 3, 4, 5, 8, 15, 16, 20, 32, 40, 64, 70, 72};
        
        for (int pos : test_positions) {
            uint64_t address = base_address + pos;
            
            memory.write(address, test_data);
            memory.injectError(address, pos);
            auto result = memory.read(address);
            
            std::cout << "Single error at position " << pos << ":" << std::endl;
            printDecodingResult(address, test_data, result);
        }
    }
    
    void testDoubleBitErrors() {
        printTestHeader("Double Bit Error Test (SEC-DED Detection)");
        
        uint64_t test_data = 0xAAAAAAAAAAAAAAAAULL;
        uint64_t base_address = 2000;
        
        std::vector<std::pair<int, int>> double_error_pairs = {
            {1, 3}, {2, 5}, {10, 15}, {20, 25}, {30, 35}, {50, 60}
        };
        
        for (size_t i = 0; i < double_error_pairs.size(); i++) {
            uint64_t address = base_address + i;
            auto& pair = double_error_pairs[i];
            
            memory.write(address, test_data);
            memory.injectError(address, pair.first);
            memory.injectError(address, pair.second);
            auto result = memory.read(address);
            
            std::cout << "Double error at positions " << pair.first << ", " << pair.second << ":" << std::endl;
            printDecodingResult(address, test_data, result);
        }
    }
    
    void testOverallParityErrors() {
        printTestHeader("Overall Parity Bit Error Test");
        
        uint64_t test_data = 0x5555555555555555ULL;
        uint64_t address = 3000;
        
        memory.write(address, test_data);
        memory.injectError(address, HammingCodeSECDED::TOTAL_BITS);  // Position 72
        auto result = memory.read(address);
        
        std::cout << "Overall parity bit error:" << std::endl;
        printDecodingResult(address, test_data, result);
    }
    
    void testBurstErrors() {
        printTestHeader("Burst Error Test");
        
        uint64_t test_data = 0x8765432187654321ULL;
        uint64_t base_address = 4000;
        
        std::vector<std::pair<int, int>> burst_configs = {
            {1, 2},   // 2-bit burst
            {5, 3},   // 3-bit burst
            {10, 4},  // 4-bit burst
            {20, 5},  // 5-bit burst
            {30, 6},  // 6-bit burst
            {50, 8}   // 8-bit burst
        };
        
        for (size_t i = 0; i < burst_configs.size(); i++) {
            uint64_t address = base_address + i;
            auto& config = burst_configs[i];
            
            memory.write(address, test_data);
            memory.injectBurstError(address, config.first, config.second);
            auto result = memory.read(address);
            
            std::cout << "Burst error (" << config.second << " bits):" << std::endl;
            printDecodingResult(address, test_data, result);
        }
    }
    
    void testRandomMultipleErrors() {
        printTestHeader("Random Multiple Error Test");
        
        uint64_t test_data = 0xDEADBEEFCAFEBABEULL;
        uint64_t base_address = 5000;
        
        std::vector<int> error_counts = {3, 4, 5, 6, 7, 8, 10, 12};
        
        for (size_t i = 0; i < error_counts.size(); i++) {
            uint64_t address = base_address + i;
            
            memory.write(address, test_data);
            memory.injectRandomErrors(address, error_counts[i]);
            auto result = memory.read(address);
            
            std::cout << "Random multiple errors (" << error_counts[i] << " bits):" << std::endl;
            printDecodingResult(address, test_data, result);
        }
    }
    
    void testMixedWorkload() {
        printTestHeader("Mixed Workload Simulation");
        
        std::mt19937 rng(12345);
        std::uniform_int_distribution<uint64_t> data_dist(0, UINT64_MAX);
        std::uniform_int_distribution<int> error_type_dist(0, 100);
        
        for (int i = 0; i < 20; i++) {
            uint64_t address = 6000 + i;
            uint64_t data = data_dist(rng);
            
            memory.write(address, data);
            
            int error_chance = error_type_dist(rng);
            std::string scenario;
            
            if (error_chance < 70) {
                // 70% - No error
                scenario = "No Error";
            } else if (error_chance < 85) {
                // 15% - Single error
                std::uniform_int_distribution<int> bit_dist(1, HammingCodeSECDED::TOTAL_BITS);
                memory.injectError(address, bit_dist(rng));
                scenario = "Single Error";
            } else if (error_chance < 95) {
                // 10% - Double error
                memory.injectRandomErrors(address, 2);
                scenario = "Double Error";
            } else {
                // 5% - Multiple errors
                std::uniform_int_distribution<int> count_dist(3, 6);
                memory.injectRandomErrors(address, count_dist(rng));
                scenario = "Multiple Errors";
            }
            
            auto result = memory.read(address);
            
            std::cout << "Mixed workload " << (i + 1) << " (" << scenario << "):" << std::endl;
            printDecodingResult(address, data, result);
        }
    }
    
    void testLargeAddressSpace() {
        printTestHeader("Large Address Space Test (128GB Demonstration)");
        
        // Test addresses spanning the full 128GB range
        std::vector<uint64_t> large_addresses = {
            0x0,                              // Start
            0x100000,                         // 1M words (8MB)
            0x40000000ULL,                    // 1GB words (8GB)  
            0x100000000ULL,                   // 4GB words (32GB)
            0x200000000ULL,                   // 8GB words (64GB)
            0x300000000ULL                    // 12GB words (96GB) - reduced from max to avoid issues
        };
        
        std::vector<uint64_t> test_patterns = {
            0x0123456789ABCDEFULL,
            0xFEDCBA9876543210ULL,
            0xAAAAAAAAAAAAAAAAULL,
            0x5555555555555555ULL,
            0xF0F0F0F0F0F0F0F0ULL,
            0x0F0F0F0F0F0F0F0FULL
        };
        
        for (size_t i = 0; i < large_addresses.size(); i++) {
            uint64_t address = large_addresses[i];
            uint64_t data = test_patterns[i];
            
            try {
                memory.write(address, data);
                
                // Inject a single error for testing
                std::mt19937 rng(address);  // Use address as seed for reproducibility
                std::uniform_int_distribution<int> bit_dist(1, HammingCodeSECDED::TOTAL_BITS);
                int error_pos = bit_dist(rng);
                memory.injectError(address, error_pos);
                
                auto result = memory.read(address);
                
                std::cout << "Large address test (Address: 0x" << std::hex << address 
                          << ", ~" << std::dec << (address * 8) / (1024*1024*1024) << "GB offset):" << std::endl;
                printDecodingResult(address, data, result);
                
            } catch (const std::exception& e) {
                std::cout << "Large address 0x" << std::hex << address 
                          << " test failed: " << e.what() << std::endl;
            }
        }
        
        std::cout << "Large address space testing demonstrates scalability to 128GB memory." << std::endl;
        std::cout << "Sparse allocation only uses memory for addresses actually written." << std::endl;
        std::cout << "Memory efficiency: Only " << memory.getMemorySize() << " words allocated out of " 
                  << memory.getMemoryCapacity() << " possible." << std::endl;
    }
};

int main() {
    try {
        std::cout << "Advanced Hamming SEC-DED Memory Simulator (64-bit)" << std::endl;
        std::cout << "Data bits: 64, Parity bits: 7, Overall parity: 1, Total bits: 72" << std::endl;
        std::cout << "Memory size: 128GB (16G 64-bit words)" << std::endl;
        std::cout << "Features: Single Error Correction, Double Error Detection" << std::endl;
        
        AdvancedMemorySimulator memory;
        AdvancedTestSuite tests(memory);
        
        tests.runAllTests();
        
        memory.printStatistics();
        
        std::cout << "\n" << std::string(60, '=') << std::endl;
        std::cout << "ADVANCED 64-BIT SIMULATION COMPLETE" << std::endl;
        std::cout << "Total memory words used: " << memory.getMemorySize() << std::endl;
        std::cout << "Memory utilization: " << std::fixed << std::setprecision(6) 
                  << (100.0 * memory.getMemorySize()) / (16ULL * 1024 * 1024 * 1024) << "% of 128GB capacity" << std::endl;
        std::cout << "Actual memory consumed: ~" << (memory.getMemorySize() * sizeof(HammingCodeSECDED::CodeWord)) / (1024*1024) << " MB" << std::endl;
        std::cout << std::string(60, '=') << std::endl;
        
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
    
    return 0;
}