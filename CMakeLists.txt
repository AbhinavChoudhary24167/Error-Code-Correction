cmake_minimum_required(VERSION 3.14)
project(ECCsim LANGUAGES CXX)

include(FetchContent)
FetchContent_Declare(
    googletest
    URL https://github.com/google/googletest/archive/refs/heads/main.zip
)
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

add_library(ecc_core INTERFACE)
target_include_directories(ecc_core INTERFACE
    ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_features(ecc_core INTERFACE cxx_std_17)

enable_testing()

add_executable(secdaec_tests tests/unit/SecDaec64_test.cpp)
target_link_libraries(secdaec_tests PRIVATE ecc_core gtest_main)
add_test(NAME secdaec_ctest COMMAND secdaec_tests)

add_executable(bch63_tests
    tests/unit/BCH63_test.cpp
    src/bch63.cpp)
target_link_libraries(bch63_tests PRIVATE ecc_core gtest_main)
add_test(NAME bch63_ctest COMMAND bch63_tests)
