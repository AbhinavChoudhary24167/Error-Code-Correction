#!/usr/bin/env bash
set -euo pipefail

readonly root="/var/lib/green-ecc-gate03e"
readonly source="$root/mapping"
readonly destination="$root/mapping-attempts/production-secded-package-elaboration-failure"

test -d "$source/secded-combinational"
test -s "$source/secded-combinational/container.log"
test ! -e "$destination"
install -d -m 0755 "$root/mapping-attempts"
mv -- "$source" "$destination"
test ! -e "$source"
test -d "$destination"
echo "PRESERVED_MAPPING_ATTEMPT $destination"
