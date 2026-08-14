#!/usr/bin/env bash
set -euo pipefail

# Gate 03E: install only the Docker Engine CE components needed to execute the
# pinned ORFS image.  Package candidates and the complete apt transaction are
# frozen before installation under the external evidence root.

if [[ "$(id -u)" != "0" ]]; then
  echo "This script must run as root inside Ubuntu 24.04 WSL2." >&2
  exit 2
fi

source /etc/os-release
if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != "24.04" || "${VERSION_CODENAME:-}" != "noble" ]]; then
  echo "Expected Ubuntu 24.04 noble; found ${ID:-unknown} ${VERSION_ID:-unknown} ${VERSION_CODENAME:-unknown}." >&2
  exit 3
fi
if [[ "$(dpkg --print-architecture)" != "amd64" ]]; then
  echo "Expected amd64 Ubuntu userspace." >&2
  exit 4
fi

evidence_root=/var/lib/green-ecc-gate03e/provision
install -d -m 0755 "$evidence_root"

export DEBIAN_FRONTEND=noninteractive
apt-get update 2>&1 | tee "$evidence_root/ubuntu-apt-update.log"

candidate_version() {
  # Consume the complete apt-cache stream.  Exiting awk early can give
  # apt-cache SIGPIPE; with pipefail that would abort before any install.
  apt-cache policy "$1" | awk '/Candidate:/ { candidate = $2 } END { print candidate }'
}

base_packages=(ca-certificates curl git)
: > "$evidence_root/ubuntu-package-candidates.tsv"
base_specs=()
for package in "${base_packages[@]}"; do
  version="$(candidate_version "$package")"
  if [[ -z "$version" || "$version" == "(none)" ]]; then
    echo "No candidate version for required package $package" >&2
    exit 5
  fi
  printf '%s\t%s\n' "$package" "$version" | tee -a "$evidence_root/ubuntu-package-candidates.tsv"
  base_specs+=("$package=$version")
done

apt-get --simulate install --no-install-recommends "${base_specs[@]}" \
  > "$evidence_root/ubuntu-package-transaction.simulate.log"
apt-get install -y --no-install-recommends "${base_specs[@]}" \
  2>&1 | tee "$evidence_root/ubuntu-package-install.log"

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
sha256sum /etc/apt/keyrings/docker.asc \
  > "$evidence_root/docker-repository-key.sha256"

printf '%s\n' \
  'Types: deb' \
  'URIs: https://download.docker.com/linux/ubuntu' \
  'Suites: noble' \
  'Components: stable' \
  'Architectures: amd64' \
  'Signed-By: /etc/apt/keyrings/docker.asc' \
  > /etc/apt/sources.list.d/docker.sources
cp /etc/apt/sources.list.d/docker.sources "$evidence_root/docker.sources"

apt-get update 2>&1 | tee "$evidence_root/docker-apt-update.log"

docker_packages=(docker-ce docker-ce-cli containerd.io)
: > "$evidence_root/docker-package-candidates.tsv"
docker_specs=()
for package in "${docker_packages[@]}"; do
  version="$(candidate_version "$package")"
  if [[ -z "$version" || "$version" == "(none)" ]]; then
    echo "No candidate version for required package $package" >&2
    exit 6
  fi
  printf '%s\t%s\n' "$package" "$version" | tee -a "$evidence_root/docker-package-candidates.tsv"
  docker_specs+=("$package=$version")
done

apt-get --simulate install --no-install-recommends "${docker_specs[@]}" \
  > "$evidence_root/docker-package-transaction.simulate.log"
apt-get install -y --no-install-recommends "${docker_specs[@]}" \
  2>&1 | tee "$evidence_root/docker-package-install.log"

systemctl enable --now containerd.service docker.service
systemctl is-active containerd.service docker.service \
  | tee "$evidence_root/docker-services-active.log"
docker version > "$evidence_root/docker-version.log"
docker info > "$evidence_root/docker-info.log"
dpkg-query -W -f='${binary:Package}\t${Version}\t${Architecture}\n' \
  | LC_ALL=C sort > "$evidence_root/dpkg-query.tsv"

echo "DOCKER_CE_PROVISIONING_PASS"
