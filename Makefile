CXX ?= g++
CXXFLAGS ?= -std=c++17 -O2
# Ensure local headers are found by adding the repository root to the include
# search path.
CXXFLAGS += -MMD -MP -I.

# Include shared utilities for energy lookup
SRC = BCHvsHamming.cpp Hamming32bit1Gb.cpp Hamming64bit128Gb.cpp SAT.cpp \
      src/energy_loader.cpp
OBJ = $(SRC:.cpp=.o)
DEP = $(OBJ:.o=.d)

BINARIES = BCHvsHamming Hamming32bit1Gb Hamming64bit128Gb SATDemo

all: $(BINARIES)

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

BCHvsHamming: BCHvsHamming.o
	$(CXX) $(CXXFLAGS) $< -o $@

Hamming32bit1Gb: Hamming32bit1Gb.o
	$(CXX) $(CXXFLAGS) $< -o $@

Hamming64bit128Gb: Hamming64bit128Gb.o src/energy_loader.o
	$(CXX) $(CXXFLAGS) $^ -o $@

SATDemo: SAT.o
	$(CXX) $(CXXFLAGS) $< -o $@

clean:
	rm -f $(BINARIES) $(OBJ) $(DEP) tests/unit/SecDaec64_test tests/unit/SecDaec64_test.d

-include $(DEP)

.PHONY: test clean gtest

# Build and run C++ unit tests without relying on CMake or external gtest
gtest: tests/unit/SecDaec64_test
	./tests/unit/SecDaec64_test

tests/unit/SecDaec64_test: tests/unit/SecDaec64_test.cpp SecDaec64.hpp BitVector.hpp ParityCheckMatrix.hpp telemetry.hpp
	$(CXX) $(CXXFLAGS) $< -o $@

test: all gtest
	./tests/smoke_test.sh
	PYTHONPATH=. pytest -q tests/python

epc-report:
	python3 parse_telemetry.py --csv $(CSV) --node $(NODE) --vdd $(VDD)
