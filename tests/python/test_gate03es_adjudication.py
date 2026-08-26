import json
from pathlib import Path

from scripts.gate03es.adjudicate_duplicate_json import adjudicate, flatten, read_ordered


def test_flatten_preserves_ordered_duplicate_occurrences(tmp_path: Path) -> None:
    source = tmp_path / "value.json"
    source.write_text('{"metric": 1, "metric": 2, "nested": {"x": 3, "x": 4}}\n')

    leaves = flatten(read_ordered(source))

    assert [(leaf.occurrence_path, leaf.value) for leaf in leaves] == [
        ("metric#1", 1),
        ("metric#2", 2),
        ("nested#1.x#1", 3),
        ("nested#1.x#2", 4),
    ]
    assert all(leaf.duplicate for leaf in leaves)


def test_adjudication_checks_each_scientific_occurrence_and_allows_runtime(tmp_path: Path) -> None:
    run_5, run_6 = tmp_path / "run5", tmp_path / "run6"
    relative = Path("logs/sky130hd/gcd/base/example.json")
    for root, text in (
        (run_5, '{"qor": 10, "qor": 20, "runtime_s": 1.0}\n'),
        (run_6, '{"qor": 10, "qor": 20, "runtime_s": 2.0}\n'),
    ):
        (root / relative).parent.mkdir(parents=True)
        (root / relative).write_text(text)
    schema = tmp_path / "schema.json"
    schema.write_text(
        json.dumps(
            {
                "metrics": [
                    {
                        "artifact": relative.as_posix(),
                        "path": "qor",
                        "classification": "SCIENTIFIC_EXACT",
                        "gating": True,
                        "absolute_tolerance": 0.0,
                    },
                    {
                        "artifact": relative.as_posix(),
                        "path": "runtime_s",
                        "classification": "RUNTIME_RESOURCE_OBSERVATION",
                        "gating": False,
                        "absolute_tolerance": None,
                    },
                ]
            }
        )
    )

    result = adjudicate(run_5, run_6, schema)

    assert result["summary"]["duplicate_key_occurrence_comparisons"] == 2
    assert result["summary"]["duplicate_scientific_failures"] == 0
    assert result["summary"]["runtime_resource_differing_occurrences"] == 1
    assert result["summary"]["scientific_or_unresolved_differing_occurrences"] == 0
    assert result["summary"]["pass"] is True


def test_exact_platform_unit_declaration_is_not_unresolved(tmp_path: Path) -> None:
    run_5, run_6 = tmp_path / "run5", tmp_path / "run6"
    relative = Path("logs/sky130hd/gcd/base/example.json")
    text = '{"run__flow__platform__time_units": "1ns"}\n'
    for root in (run_5, run_6):
        (root / relative).parent.mkdir(parents=True)
        (root / relative).write_text(text)
    schema = tmp_path / "schema.json"
    schema.write_text('{"metrics": []}\n')

    result = adjudicate(run_5, run_6, schema)

    assert result["summary"]["unresolved_occurrences"] == 0
    assert result["summary"]["scientific_failures"] == 0
    assert result["summary"]["pass"] is True
