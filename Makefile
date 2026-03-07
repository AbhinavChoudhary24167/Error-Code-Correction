CXX ?= g++
CXXFLAGS ?= -std=c++17 -O2
# Ensure local headers are found by adding the repository root to the include
# search path.
CXXFLAGS += -MMD -MP -I.

# Include shared utilities for energy lookup
SRC = BCHvsHamming.cpp Hamming32bit1Gb.cpp Hamming64bit128Gb.cpp SAT.cpp PracticalSRAMSimulator.cpp \
      src/energy_loader.cpp src/bch63.cpp
OBJ = $(SRC:.cpp=.o)
DEP = $(OBJ:.o=.d)

BINARIES = BCHvsHamming Hamming32bit1Gb Hamming64bit128Gb SATDemo PracticalSRAMSimulator

all: $(BINARIES)

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

BCHvsHamming: BCHvsHamming.o src/bch63.o
	$(CXX) $(CXXFLAGS) $^ -o $@

Hamming32bit1Gb: Hamming32bit1Gb.o
	$(CXX) $(CXXFLAGS) $< -o $@

Hamming64bit128Gb: Hamming64bit128Gb.o src/energy_loader.o
	$(CXX) $(CXXFLAGS) $^ -o $@

SATDemo: SAT.o
	$(CXX) $(CXXFLAGS) $< -o $@

PracticalSRAMSimulator: PracticalSRAMSimulator.o
	$(CXX) $(CXXFLAGS) $< -o $@

ifeq ($(OS),Windows_NT)
RM := cmd /C del /Q
else
RM := rm -f
endif

clean:
	$(RM) $(BINARIES) $(OBJ) $(DEP) tests/unit/SecDaec64_test tests/unit/SecDaec64_test.d

-include $(DEP)

.PHONY: test clean gtest

# Build and run C++ unit tests without relying on CMake or external gtest
gtest: tests/unit/SecDaec64_test
	./tests/unit/SecDaec64_test

# Build unit test without -O2 to avoid UB-sensitive crashes on some toolchains
tests/unit/SecDaec64_test: tests/unit/SecDaec64_test.cpp SecDaec64.hpp BitVector.hpp ParityCheckMatrix.hpp telemetry.hpp
	$(CXX) -std=c++17 -O0 -I. $< -o $@

test: all gtest
ifeq ($(OS),Windows_NT)
	if not exist BCHvsHamming.exe exit /b 1
	if not exist Hamming32bit1Gb.exe exit /b 1
	if not exist Hamming64bit128Gb.exe exit /b 1
	if not exist SATDemo.exe exit /b 1
	python ecc_selector.py 1e-6 2 0.6 1e-15 1 --sustainability >NUL
	set PYTHONPATH=.&& pytest -q tests/python
else
	./tests/smoke_test.sh
	PYTHONPATH=. pytest -q tests/python
endif

epc-report:
	python3 parse_telemetry.py --csv $(CSV) --node $(NODE) --vdd $(VDD)
