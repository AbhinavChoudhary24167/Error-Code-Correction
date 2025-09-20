#pragma once

#include <array>
#include <bitset>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <random>
#include <set>
#include <string>
#include <type_traits>
#include <vector>

#include "BitVector.hpp"
#include "ParityCheckMatrix.hpp"

namespace ecc {

template <typename WordTraits>
class HammingCodeSECDED;

template <typename WordTraits, typename WorkloadTraits>
class ECCStatistics;

template <typename WordTraits, typename WorkloadTraits>
class AdvancedMemorySimulator;

template <typename WordTraits, typename WorkloadTraits>
class AdvancedTestSuite;

void runEccSchemeDemo(int trials = 1000, unsigned seed = 1);

void printArchetypeReport(const std::string& json_path);

}  // namespace ecc

#include "hamming_simulator.tpp"

