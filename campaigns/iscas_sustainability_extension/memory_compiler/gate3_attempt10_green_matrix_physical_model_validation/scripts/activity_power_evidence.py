"""Collect the bounded original-Liberty seed11 annotation diagnostic honestly."""
from __future__ import annotations
import json
import re
from activity_energy import CAMPAIGN, ROOT, PARENT, sha, write_json


def main():
    rows = []
    for arch in ("U0", "E0"):
        run = CAMPAIGN / f"energy/postroute/read_dominant/{arch}/slash_scope"
        counts = {name: int(count) for name, count in re.findall(r"^(vcd|unannotated)\s+(\d+)", (run / "annotation.rpt").read_text(), re.M)}
        power = re.search(r"^Total\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)", (run / "power.rpt").read_text(), re.M)
        final = PARENT / f"raw/openroad/work/results/sky130hd/attempt09_{arch.lower()}/seed11"
        sources = [final / name for name in ("6_final.odb", "6_final.spef", "6_final.sdc", "6_final.v")]
        sources += [CAMPAIGN / f"energy/raw/read_dominant/{arch}/activity.vcd", CAMPAIGN / "energy/traces/read_dominant.json"]
        sources += [PARENT / f"raw/liberty/{macro}_tt_025C_1v80.lib" for macro in (["sram22_256x64m4w8", "sram22_256x8m8w1"] if arch == "E0" else ["sram22_256x64m4w8"])]
        sources += list(run.glob("*.rpt"))
        rows.append({"architecture_id": arch, "seed": 11, "workload_id": "read_dominant", "liberty_model": "UPSTREAM_ORIGINAL",
            "annotation_scope": "tb/dut", "annotated_pin_count": counts.get("vcd", 0), "unannotated_pin_count": counts["unannotated"],
            "annotated_pin_fraction": counts.get("vcd", 0) / sum(counts.values()),
            **dict(zip(("power_internal_w", "power_switching_w", "power_leakage_w", "power_total_w"), map(float, power.groups()))),
            "power_evidence_level": "PARTIALLY_RTL_ACTIVITY_ANNOTATED_POSTROUTE_TOOL_ESTIMATE",
            "energy_evidence_level": "NOT_QUALIFIED", "energy_access_j": "NOT_QUALIFIED",
            "source_provenance": {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in sources},
            "blockers": ["unannotated gate pins and synthesis-name mismatch", "no mapped glitch-aware gate simulation",
                         "no independent read/write-conditioned macro power validation", "encoder/decoder/control power partition unavailable"],
            "five_seed_robustness": "NOT_RUN_FOR_ACTIVITY_POWER", "sensitivity_liberty_models": "NOT_RUN_FOR_ACTIVITY_POWER"})
    write_json(CAMPAIGN / "energy/POSTROUTE_ACTIVITY_DIAGNOSTIC.json", {"schema_version": 1, "rows": rows,
        "frozen_docker_image": "sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e",
        "tool_version": "OpenROAD 26Q3-1080-gab6fd26351",
        "mount_policy": "entire repository read-only at /work; Attempt10 energy only writable at /output; Docker network disabled",
        "initial_scope_diagnostic": "tb.dut annotated zero pins. Its U0 reports are retained one directory above slash_scope; accepted OpenSTA hierarchy separator is tb/dut.",
        "interpretation": "Power values remain incomplete activity estimates, not qualified read/write/access energy. Default/inferred activity influences unmatched pins. These rows are excluded from GREEN energy/carbon scoring."})
    (CAMPAIGN / "energy/POSTROUTE_ACTIVITY_DIAGNOSTIC.md").write_text(
        "# Partial postroute activity annotation\n\n" + "\n".join(
            f"- {r['architecture_id']}, original Liberty, seed 11, read-dominant: {r['annotated_pin_count']}/{r['annotated_pin_count'] + r['unannotated_pin_count']} pins annotated ({r['annotated_pin_fraction']:.2%}); tool total {r['power_total_w']:.9g} W."
            for r in rows) + "\n\nClassification: PARTIALLY_RTL_ACTIVITY_ANNOTATED_POSTROUTE_TOOL_ESTIMATE. Energy remains NOT_QUALIFIED. "
        "The five physical seeds and diagnostic Liberty models are not covered by this bounded check. "
        "The preserved power groups include macro internal-power estimates from existing Liberty; no independent macro power validation or complete RTL-to-gate activity mapping was established. "
        "The missing pin activity is explicit in annotated/unannotated lists. E0 hierarchy has been flattened into dotted cell names, while the VCD has nested module scopes. "
        "These figures must not be compared as qualified ECC energy overhead and must not be integrated into carbon/GREEN scores.\n", encoding="utf-8")
    print(json.dumps({"diagnostic_rows": len(rows), "energy_qualification": "NOT_QUALIFIED"}))


if __name__ == "__main__": main()
