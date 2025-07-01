CXX ?= g++
CXXFLAGS ?= -std=c++11 -O2

BINARIES = BCHvsHamming Hamming32bit1Gb Hamming64bit128Gb SATDemo

all: $(BINARIES)

BCHvsHamming: BCHvsHamming.cpp
	$(CXX) $(CXXFLAGS) $< -o $@

Hamming32bit1Gb: Hamming32bit1Gb.cpp
	$(CXX) $(CXXFLAGS) $< -o $@

Hamming64bit128Gb: Hamming64bit128Gb.cpp
	$(CXX) $(CXXFLAGS) $< -o $@

SATDemo: SAT.cpp
	$(CXX) $(CXXFLAGS) $< -o $@

clean:
	rm -f $(BINARIES)

.PHONY: test clean gtest

gtest:
	cmake -S . -B build
	cmake --build build
	cd build && ctest --output-on-failure

test: all gtest
	./tests/smoke_test.sh
	PYTHONPATH=. pytest -q tests/python
