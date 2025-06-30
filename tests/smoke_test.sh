#!/usr/bin/env bash
set -e

# Run each compiled binary with a short timeout
for prog in BCHvsHamming Hamming32bit1Gb Hamming64bit128Gb SATDemo; do
    echo "Testing $prog"
    timeout 5s ./"$prog" >/dev/null
done

echo "All smoke tests passed."
