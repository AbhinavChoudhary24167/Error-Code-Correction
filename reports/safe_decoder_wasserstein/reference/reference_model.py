#!/usr/bin/env python3
"""Generated bit-exact reference for forge-hotspot-8-4-v1-safe."""
from __future__ import annotations
import argparse

K = 4
R = 4
N = 8
H_COLUMNS = [11, 14, 7, 13, 1, 2, 4, 8]
G = [[1, 0, 0, 0, 1, 1, 0, 1], [0, 1, 0, 0, 0, 1, 1, 1], [0, 0, 1, 0, 1, 1, 1, 0], [0, 0, 0, 1, 1, 0, 1, 1]]
DECODER = {1: 16, 3: 48, 5: 3, 8: 128, 9: 6, 10: 12, 15: 132}

def syndrome(word: int) -> int:
    value = 0
    for position, column in enumerate(H_COLUMNS):
        if (word >> position) & 1:
            value ^= column
    return value

def encode(data: int) -> int:
    if data < 0 or data >= (1 << K):
        raise ValueError("data does not fit")
    out = 0
    for bit in range(N):
        value = 0
        for source in range(K):
            value ^= ((data >> source) & 1) & G[source][bit]
        out |= value << bit
    return out

def decode(received: int, original_data: int | None = None) -> dict:
    syn = syndrome(received)
    if syn == 0:
        decoded = received & ((1 << K) - 1)
        outcome = "correct" if original_data is None or decoded == original_data else "silent_corruption"
        return {"outcome": outcome, "syndrome": syn, "decoded_data": decoded, "correction_mask": 0}
    if syn not in DECODER:
        return {"outcome": "detected_uncorrectable", "syndrome": syn, "decoded_data": None, "correction_mask": 0}
    mask = DECODER[syn]
    corrected = received ^ mask
    if syndrome(corrected) != 0:
        return {"outcome": "decoder_failure", "syndrome": syn, "decoded_data": None, "correction_mask": mask}
    decoded = corrected & ((1 << K) - 1)
    outcome = "corrected" if original_data is None or decoded == original_data else "silent_corruption"
    return {"outcome": outcome, "syndrome": syn, "decoded_data": decoded, "correction_mask": mask}

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data", type=lambda value: int(value, 0))
    parser.add_argument("error_mask", type=lambda value: int(value, 0))
    args = parser.parse_args()
    codeword = encode(args.data)
    result = decode(codeword ^ args.error_mask, args.data)
    print(f"{codeword} {codeword ^ args.error_mask} {result['syndrome']} {result['outcome']} {result['decoded_data'] if result['decoded_data'] is not None else -1}")

if __name__ == "__main__":
    main()
