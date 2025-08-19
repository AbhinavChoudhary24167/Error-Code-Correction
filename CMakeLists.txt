cmake_minimum_required(VERSION 3.14)
project(ECCsim LANGUAGES CXX)

# Prefer a system installation of nlohmann_json but fall back to the
# header vendored in the repository if it is not available.
find_package(nlohmann_json 3 QUIET)

include(FetchContent)
FetchContent_Declare(
    googletest
    URL https://github.com/google/googletest/archive/refs/heads/main.zip
)
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

add_library(ecc_core INTERFACE)
target_include_directories(ecc_core INTERFACE ${CMAKE_CURRENT_SOURCE_DIR})
if(nlohmann_json_FOUND)
    target_link_libraries(ecc_core INTERFACE nlohmann_json::nlohmann_json)
else()
    message(STATUS "nlohmann_json not found; using vendored header")
endif()

enable_testing()

add_executable(secdaec_tests tests/unit/SecDaec64_test.cpp)
target_link_libraries(secdaec_tests PRIVATE ecc_core gtest_main)
add_test(NAME secdaec_ctest COMMAND secdaec_tests)
