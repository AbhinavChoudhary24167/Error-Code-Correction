# Gate 3 attempt 02 — storage preflight

## Decision

**PASS** at 2026-08-29T20:15:39+05:30.

The Ubuntu-24.04 WSL distribution and its Docker/container storage were relocated from C: to an ext4 VHDX physically stored on F: before any Gate-3 compiler pull or build. A byte-size-matched VHD export was created and SHA-256 hashed before the supported move operation.

## Before relocation

| Item | Observation |
|---|---:|
| C: free | 89,395,200 bytes |
| F: free | 195,841,818,624 bytes |
| Ubuntu VHDX | `C:/Users/Abhinav/AppData/Local/wsl/{a5848298-28a1-4b03-aec8-731a9306cef8}/ext4.vhdx` |
| Ubuntu VHDX size | 23,702,011,904 bytes |
| WSL version | 2.7.11.0 |
| Distribution | Ubuntu-24.04, WSL2, stopped |

The original state was unsafe because C: could be exhausted by another container pull.

## Backup and supported relocation

- Backup: `F:/green-ecc-iscas-sustainability-temp/wsl-backup/Ubuntu-24.04-pre-move-20260829.vhdx`
- Backup size: 23,702,011,904 bytes
- Backup SHA-256: `bb17b4515fe1c5e4fff9a33850fc024c692e6411ce2d10d613e58334195c7c62`
- Command: `wsl --export Ubuntu-24.04 ... --format vhd`
- Relocation command: `wsl --manage Ubuntu-24.04 --move F:\green-ecc-iscas-sustainability-temp\wsl-relocated\Ubuntu-24.04`
- Result: both operations completed successfully; no unregister or destructive deletion was used.

## After relocation

| Item | Observation |
|---|---:|
| C: free | 23,953,571,840 bytes |
| F: free (Windows observation) | 148,437,794,816 bytes |
| F: free via `/mnt/f` | 148,404,240,384 bytes |
| WSL root logical free | 1,004,231,122,944 bytes |
| Relocated VHDX | `F:/green-ecc-iscas-sustainability-temp/wsl-relocated/Ubuntu-24.04/ext4.vhdx` |
| Relocated VHDX size | 23,702,011,904 bytes |
| Root filesystem | `/dev/sdd`, ext4, read-write |
| Docker root | `/var/lib/docker` on relocated ext4 filesystem |
| Container content | `/var/lib/containerd` on relocated ext4 filesystem |
| Docker engine | 29.7.2, overlayfs |
| Protected evidence root | readable |
| Protected manifest verification | PASS, 7,094 files, no changes/additions/missing files |

## Budget and fail-closed thresholds

The bounded OpenRAM image, source, SKY130 dependency, build/cache, macro intermediates, and outputs are assigned a conservative combined budget of **50 GiB**. Heavy Linux-native files must stay inside the relocated F:-backed ext4 VHDX. F:/`/mnt/f` is used for the immutable backup and optional staging, not as the active overlay/container filesystem.

Attempt 02 must stop before a heavy command if any condition becomes false:

- C: free ≥ 15 GiB;
- F: physical free ≥ 80 GiB;
- WSL root logical free ≥ 80 GiB;
- Docker root resolves inside the relocated Ubuntu filesystem;
- relocated ext4 remains read-write;
- protected evidence root remains readable.

Current observations satisfy every threshold.

## Runtime threshold event and mitigation

During the first pinned-container pull, Windows pagefile growth temporarily
pushed C: below the 15 GiB fail-closed threshold even though Docker's Linux
layers were being written to the relocated ext4 VHDX. Compilation did not
begin under that condition. The exact minimum byte count was not retained and
is therefore not inferred.

Before retrying the pull, WSL2 was constrained to 4 GiB RAM and four
processors, its 8 GiB swap VHDX was placed on F:, and Docker was limited to one
concurrent download and upload. The recorded settings are in
`wslconfig_attempt02.ini` and `docker_daemon_attempt02.json`.

## Final observation

At 2026-08-30T17:10:56.7920904+05:30, after run04 terminated and its evidence
was preserved:

| Item | Observation |
|---|---:|
| C: free | 20,330,397,696 bytes |
| F: free | 122,574,663,680 bytes |
| WSL root size | 1,081,101,176,832 bytes |
| WSL root used | 48,347,492,352 bytes |
| WSL root free | 977,761,329,152 bytes |
| Relocated VHDX size | 49,565,138,944 bytes |
| Attempt-02 namespace | 5,414,290,927 bytes |
| Docker image storage | 27.69 GB reported; zero active containers |

Every fail-closed threshold remained satisfied during the scientific run. The
run04 failure is therefore not classified as an infrastructure or storage
failure.
