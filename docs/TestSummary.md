# Test Summary

This document provides an overview of the automated tests in the project and how faults are injected into the memory simulators. The tests come from `Hamming32bit1Gb.cpp` and `Hamming64bit128Gb.cpp`.

## Fault Injection Helpers

Both simulators share three helper functions:

- **`injectError(address, bit_position)`** – flips a single bit at the specified position within the encoded word at `address`.
- **`injectBurstError(address, start_position, burst_length)`** – flips `burst_length` adjacent bits beginning at `start_position`.
- **`injectRandomErrors(address, num_errors)`** – flips a random set of bits in the code word at `address` without repeating positions.

These helpers operate on encoded data stored in memory so that subsequent reads exercise the Hamming decoder's correction and detection capabilities.

## Tests in `Hamming32bit1Gb.cpp`

`AdvancedTestSuite::runAllTests()` executes seven scenarios:

1. **No Error Test (SEC-DED)** – writes a variety of values and verifies that reading them back with no faults reports no errors.
2. **Single Bit Error Test (SEC-DED)** – injects one error at several different bit positions and checks that the decoder corrects the value.
3. **Double Bit Error Test (SEC-DED Detection)** – injects two errors at chosen positions to demonstrate that the decoder detects but cannot correct double faults.
4. **Overall Parity Bit Error Test** – flips only the overall parity bit and reads the result.
5. **Burst Error Test** – injects bursts of two to six adjacent bits and displays how the decoder reacts.
6. **Random Multiple Error Test** – introduces three to eight errors at random positions for each word.
7. **Mixed Workload Simulation** – for twenty iterations writes random data and probabilistically injects zero, one, two or several errors to mimic a diverse workload.

## Tests in `Hamming64bit128Gb.cpp`

The 64‑bit variant includes all previous scenarios and one additional large address space check:

1. **No Error Test (SEC-DED)** – identical purpose as the 32‑bit version but with 64‑bit words.
2. **Single Bit Error Test (SEC-DED)** – single bit faults at various data and parity positions.
3. **Double Bit Error Test (SEC-DED Detection)** – two simultaneous errors at selected positions.
4. **Overall Parity Bit Error Test** – flips the overall parity bit alone.
5. **Burst Error Test** – burst lengths from two to eight bits.
6. **Random Multiple Error Test** – injects three to twelve random errors.
7. **Mixed Workload Simulation** – writes random values and applies no, single, double or multiple errors based on random chance.
8. **Large Address Space Test (128GB Demonstration)** – writes to sparse addresses across the theoretical 128GB range, injecting a single random error at each to show that the simulator allocates memory only for used addresses.

These tests collectively demonstrate the behaviour of the SEC-DED Hamming implementation across a variety of fault patterns and memory sizes.
