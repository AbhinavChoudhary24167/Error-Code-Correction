# Gate 3 infrastructure incident — WSL storage became unsafe

## Outcome

Gate 3 is **NOT_ASSESSABLE**. No SRAM macro was generated, no macro view was admitted, and no numeric value may flow into Gate 4 or Gate 6.

This is an infrastructure result, not negative evidence about OpenRAM.

## Gate contract

### Inputs

- Gate 2 `CONDITIONAL_PASS` and selected OpenRAM 1.2.48 path.
- Planned 256×72, single-`rw`, one-bank macro.
- External evidence root `/var/lib/green-ecc-iscas-sustainability/`.
- Ubuntu-24.04 WSL distribution and Docker tool environment.

### Outputs expected

- Pinned compiler/tool/PDK manifests.
- Hashed LEF, GDS, Liberty, SPICE, and Verilog views.
- View-consistency, corner, DRC/LVS, timing, read/write-energy, and leakage qualification.

### Evidence actually produced

- A pre-stage capacity observation: `/dev/sdd`, 1007 GiB displayed size, 21 GiB used, 936 GiB available, 3% use.
- One failed toolchain setup attempt with zero scientific measurements.
- This incident record and `GATE3_STATUS.json`.

### Tests

- The status schema asserts zero admitted artifacts and forbids downstream numerical propagation.
- No macro-view or characterization test is marked passed.

### PASS criteria

The planned macro produces non-empty, mutually consistent, hashed LEF/GDS/Liberty/SPICE/Verilog views; the exact tool/PDK/corner identity is frozen; and the required physical/timing/energy qualification passes.

### CONDITIONAL_PASS criteria

Physical views are qualified but a bounded characterization item is unavailable, and downstream use is restricted to fields with direct evidence.

### FAIL criteria

The bounded compiler attempt completes and shows that the selected organization cannot produce required valid views or meet declared physical qualification.

### NOT_ASSESSABLE criteria

Infrastructure prevents a safe, reproducible bounded attempt before compiler or macro validity can be evaluated.

The observed state satisfies **NOT_ASSESSABLE**.

## Incident chronology

1. Read-only inventory found `git`, `python3`, and Docker in WSL; `make`, Nix, Magic, Netgen, ngspice, KLayout, and OpenROAD were not present on the host path.
2. The only cached container image was an OpenROAD-flow image, not an OpenRAM toolchain.
3. Pulling the official `vlsida/openram-ubuntu:latest` image began normally. The digest could not be pinned because the pull did not complete.
4. Docker failed with:

   ```text
   failed to copy: failed to send write: write /var/lib/containerd/io.containerd.content.v1.content/ingest/.../data: read-only file system
   ```

5. WSL subsequently reported the Ubuntu-24.04 distribution stopped. One clean service shutdown/restart attempt was made because the distribution was already stopped.
6. The read-only post-restart check failed with:

   ```text
   Catastrophic failure
   Error code: Wsl/Service/E_UNEXPECTED
   ```

7. The host C: volume then reported exactly **0 free bytes**. The Ubuntu backing file was identified at `C:/Users/Abhinav/AppData/Local/wsl/{a5848298-28a1-4b03-aec8-731a9306cef8}/ext4.vhdx` (23,702,011,904 bytes, last written during the pull). Thus the logically spacious ext4 filesystem was physically backed by the unsafe C: volume; the pre-stage `df` result alone did not establish host-capacity safety.

No attempt was made to install packages, repair the filesystem, delete partial layers, or redirect large data onto Windows C:. Those actions would exceed a scientifically safe evidence-generation step.

## Dependency decision

Gate 4's physical mapping requires an admitted macro organization and physical-coordinate contract. Gate 6 requires characterized macro area/energy. Continuing either as if the 256×72 macro existed would introduce an unqualified identity, so the sequential campaign stops here under the user's explicit unsafe-storage stop rule.

Abstract mapping software can be designed later, but it must not be presented as macro-derived physical evidence until Gate 3 is recovered.

## Recovery procedure

1. Repair or replace the Ubuntu-24.04 WSL distribution/container store outside this campaign.
2. Confirm a writable ext4 evidence namespace and record exact byte capacity.
3. Verify Docker/containerd can ingest and retain a test layer without an I/O or read-only error.
4. Pull the OpenRAM image, record its immutable digest, and clone OpenRAM v1.2.48 at its exact commit.
5. Start a new `/var/lib/green-ecc-iscas-sustainability/gate3_openram_attempt02/` namespace. Preserve any attempt01 residue; do not overwrite it.
6. Resume the predeclared 256×72 qualification contract without changing the scientific target.
