cmake_minimum_required(VERSION 3.14)
project(ECCsim LANGUAGES CXX)

# Prefer a specific system installation of nlohmann_json but fall back to
# the header vendored in the repository if it is not available.  Requiring
# the exact version avoids mismatches that previously triggered compilation
# failures in downstream builds.
find_package(nlohmann_json 3.11.2 QUIET)

include(FetchContent)
FetchContent_Declare(
    googletest
    URL https://github.com/google/googletest/archive/refs/heads/main.zip
)
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

add_library(ecc_core INTERFACE)
target_include_directories(ecc_core INTERFACE
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/nlohmann)
target_compile_features(ecc_core INTERFACE cxx_std_17)
target_compile_definitions(ecc_core INTERFACE NLOHMANN_JSON_NAMESPACE_NO_VERSION=1)
if(nlohmann_json_FOUND)
    target_link_libraries(ecc_core INTERFACE nlohmann_json::nlohmann_json)
else()
    message(STATUS "nlohmann_json 3.11.2 not found; using vendored header")
endif()

enable_testing()

add_executable(secdaec_tests tests/unit/SecDaec64_test.cpp)
target_link_libraries(secdaec_tests PRIVATE ecc_core gtest_main)
add_test(NAME secdaec_ctest COMMAND secdaec_tests)
