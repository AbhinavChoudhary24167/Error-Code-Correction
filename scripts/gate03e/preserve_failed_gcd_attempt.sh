#!/usr/bin/env bash
set -euo pipefail

readonly evidence_root="/var/lib/green-ecc-gate03e"
readonly source="$evidence_root/runs/gcd-run-01"
readonly destination="$evidence_root/attempts/gcd-native-lec-avx512-failure-01"

test -d "$source"
test "$source" = "/var/lib/green-ecc-gate03e/runs/gcd-run-01"
test ! -e "$destination"
install -d -m 0755 "$evidence_root/attempts"
mv -- "$source" "$destination"
test ! -e "$source"
test -d "$destination"
echo "PRESERVED_FAILED_ATTEMPT $destination"
