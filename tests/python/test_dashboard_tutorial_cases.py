from web.tutorial_backend import CASE_TEMPLATES, generate_tutorial_cases


def test_tutorial_backend_generates_three_cases_per_dataset():
    payload = generate_tutorial_cases()
    datasets = payload.get("datasets", {})
    assert datasets

    for dataset in datasets.values():
        cases = dataset.get("cases", [])
        assert len(cases) == 3


def test_tutorial_case_ids_match_templates():
    payload = generate_tutorial_cases()
    expected_ids = [template.case_id for template in CASE_TEMPLATES]

    for dataset in payload["datasets"].values():
        actual_ids = [case["id"] for case in dataset["cases"]]
        assert actual_ids == expected_ids


def test_tutorial_inference_contains_lever_guidance():
    payload = generate_tutorial_cases()
    for dataset in payload["datasets"].values():
        for case in dataset["cases"]:
            assert "Use this mode" in case["inference"]
            assert case["lever"] in case["inference"]
