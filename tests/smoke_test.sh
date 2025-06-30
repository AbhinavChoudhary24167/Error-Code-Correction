#!/usr/bin/env bash
set -e

# Run each compiled binary with a short timeout
for prog in BCHvsHamming Hamming32bit1Gb Hamming64bit128Gb SATDemo; do
    echo "Testing $prog"
    timeout 5s ./"$prog" >/dev/null
done

# Basic check of the ECC selector
echo "Testing ecc_selector.py"
python3 ecc_selector.py 1e-6 2 0.6 1e-15 1 --sustainability >/dev/null

echo "All smoke tests passed."
