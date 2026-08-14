#!/usr/bin/env bash
set -euo pipefail

# Retain the exact registry responses used to bind the human-readable ORFS tag
# to the frozen linux/amd64 manifest.  The anonymous bearer token is ephemeral
# and deliberately is not written to the evidence directory.

readonly repository="openroad/orfs"
readonly tag="26Q3-275-g56496f398"
readonly expected_amd64_digest="sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
readonly evidence_root="/var/lib/green-ecc-gate03e/registry"

install -d -m 0755 "$evidence_root"
token_file="$(mktemp)"
trap 'rm -f "$token_file"' EXIT

curl --fail --silent --show-error --location \
  "https://auth.docker.io/token?service=registry.docker.io&scope=repository:${repository}:pull" \
  --output "$token_file"
token="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["token"])' "$token_file")"

index_accept="application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json"
manifest_accept="application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json"

curl --fail --silent --show-error --location \
  --header "Authorization: Bearer ${token}" \
  --header "Accept: ${index_accept}" \
  --dump-header "$evidence_root/tag-response.headers" \
  "https://registry-1.docker.io/v2/${repository}/manifests/${tag}" \
  --output "$evidence_root/tag-index.raw.json"

actual_amd64_digest="$(python3 - "$evidence_root/tag-index.raw.json" <<'PY'
import json
import sys

with open(sys.argv[1], "rb") as handle:
    index = json.load(handle)
matches = [
    item["digest"]
    for item in index.get("manifests", [])
    if item.get("platform", {}).get("os") == "linux"
    and item.get("platform", {}).get("architecture") == "amd64"
]
if len(matches) != 1:
    raise SystemExit(f"expected exactly one linux/amd64 manifest, found {len(matches)}")
print(matches[0])
PY
)"
if [[ "$actual_amd64_digest" != "$expected_amd64_digest" ]]; then
  echo "linux/amd64 digest mismatch: expected $expected_amd64_digest, got $actual_amd64_digest" >&2
  exit 10
fi

curl --fail --silent --show-error --location \
  --header "Authorization: Bearer ${token}" \
  --header "Accept: ${manifest_accept}" \
  --dump-header "$evidence_root/amd64-response.headers" \
  "https://registry-1.docker.io/v2/${repository}/manifests/${actual_amd64_digest}" \
  --output "$evidence_root/amd64-manifest.raw.json"

computed_amd64_digest="sha256:$(sha256sum "$evidence_root/amd64-manifest.raw.json" | awk '{print $1}')"
if [[ "$computed_amd64_digest" != "$expected_amd64_digest" ]]; then
  echo "raw manifest hash mismatch: expected $expected_amd64_digest, got $computed_amd64_digest" >&2
  exit 11
fi

config_digest="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["config"]["digest"])' "$evidence_root/amd64-manifest.raw.json")"
curl --fail --silent --show-error --location \
  --header "Authorization: Bearer ${token}" \
  "https://registry-1.docker.io/v2/${repository}/blobs/${config_digest}" \
  --output "$evidence_root/amd64-config.raw.json"

computed_config_digest="sha256:$(sha256sum "$evidence_root/amd64-config.raw.json" | awk '{print $1}')"
if [[ "$computed_config_digest" != "$config_digest" ]]; then
  echo "raw config hash mismatch: expected $config_digest, got $computed_config_digest" >&2
  exit 12
fi

python3 - "$evidence_root" "$tag" "$actual_amd64_digest" "$config_digest" <<'PY'
import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
index_bytes = (root / "tag-index.raw.json").read_bytes()
summary = {
    "schema_version": 1,
    "repository": "openroad/orfs",
    "tag": sys.argv[2],
    "tag_response_sha256": hashlib.sha256(index_bytes).hexdigest(),
    "linux_amd64_manifest_digest": sys.argv[3],
    "config_digest": sys.argv[4],
}
(root / "registry-summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PY

(cd "$evidence_root" && sha256sum * | LC_ALL=C sort > evidence-files.sha256)
echo "ORFS_REGISTRY_QUERY_PASS $actual_amd64_digest"
