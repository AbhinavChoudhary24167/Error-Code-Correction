import hashlib
from pathlib import Path

# Expected SHA256 checksums for example artifacts
EXPECTED = {
    Path("reports/examples/sku-64b-128Gb/mbu-light_ci-0.55_scrub-5/pareto.csv"): "75c45a7395eb52f2364fe42f70352b753e8b2ae24306a91898b51bc62cf45c82",
    Path("reports/examples/sku-64b-128Gb/mbu-light_ci-0.55_scrub-5/tradeoffs.json"): "3c4fbc4cf72f40cd725b02299238e931dfee600171f3312aef7d10108402bf74",
    Path("reports/examples/sku-64b-128Gb/mbu-light_ci-0.55_scrub-5/archetypes.json"): "2de0f890b7e0551bb1b38e17b2d80ab3951c25a9fa6549b03b3ba51cbed112c0",
    Path("reports/examples/sku-64b-128Gb/mbu-light_ci-0.55_scrub-5/sensitivity-vdd.json"): "c32ea8166125e96de647638097d1056bae3d30dd5db6c5bb0c113da094355223",
    Path("reports/examples/sku-32b-1Gb/mbu-light_ci-0.55_scrub-5/pareto.csv"): "4c8d5f78be74f07e878f3066df53409eea346515b9200a0985ff221b2a406f23",
    Path("reports/examples/sku-32b-1Gb/mbu-light_ci-0.55_scrub-5/tradeoffs.json"): "7af20d1a83e0b94095c422575cd7d288e8a4d55208bc16405ae557a0e998dda2",
    Path("reports/examples/sku-32b-1Gb/mbu-light_ci-0.55_scrub-5/archetypes.json"): "436f60b88b74d27d4615a77a899f5edf5b3d945163760d85dd57cc1bdb1eb884",
    Path("reports/examples/sku-32b-1Gb/mbu-light_ci-0.55_scrub-5/sensitivity-vdd.json"): "c32ea8166125e96de647638097d1056bae3d30dd5db6c5bb0c113da094355223",
}


def sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def test_example_artifacts_present_and_valid():
    for path, expected in EXPECTED.items():
        assert path.is_file(), f"missing artifact: {path}"
        digest = sha256sum(path)
        assert digest == expected, f"checksum mismatch for {path}"
