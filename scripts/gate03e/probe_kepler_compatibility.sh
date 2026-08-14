#!/usr/bin/env bash
set -euo pipefail

readonly image="openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
readonly evidence="/var/lib/green-ecc-gate03e/image"

set +e
docker run --rm --platform linux/amd64 \
  --entrypoint /OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal \
  "$image" --help > "$evidence/kepler-direct-smoke.log" 2>&1
status=$?
set -e
printf '%s\n' "$status" > "$evidence/kepler-direct-smoke.exit-status"
if [[ "$status" != "132" ]]; then
  echo "Expected SIGILL exit 132 from the direct Kepler probe; got $status." >&2
  exit 1
fi
echo "KEPLER_AVX512_INCOMPATIBILITY_CONFIRMED exit_status=$status"
