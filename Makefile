CXX ?= g++
CXXFLAGS ?= -std=c++11 -O2
CXXFLAGS += -MMD -MP

SRC = BCHvsHamming.cpp Hamming32bit1Gb.cpp Hamming64bit128Gb.cpp SAT.cpp
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

Hamming64bit128Gb: Hamming64bit128Gb.o
	$(CXX) $(CXXFLAGS) $< -o $@

SATDemo: SAT.o
	$(CXX) $(CXXFLAGS) $< -o $@

clean:
	rm -f $(BINARIES) $(OBJ) $(DEP)

-include $(DEP)

.PHONY: test clean gtest

gtest:
	cmake -S . -B build
	cmake --build build
	cd build && ctest --output-on-failure

test: all gtest
	./tests/smoke_test.sh
	PYTHONPATH=. pytest -q tests/python

epc-report:
	python3 parse_telemetry.py --csv $(CSV) --node $(NODE) --vdd $(VDD)
