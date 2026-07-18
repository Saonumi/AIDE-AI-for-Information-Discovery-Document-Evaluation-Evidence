"""Golden dataset is LOAD-BEARING (Final spec §11.3): ground_truth.json drives
real engine runs — every review target file must classify as labeled, and the
seeded amendment must produce the labeled impact.
"""
from __future__ import annotations

import json
import os
from datetime import date

import pytest

from infra.neo4j_client import reset_graph_for_tests
from infra.opensearch_client import reset_store_for_tests

GOLDEN = os.path.join(os.path.dirname(__file__), os.pardir, "data", "golden")


@pytest.fixture()
def seeded():
    reset_store_for_tests()
    reset_graph_for_tests()
    from infra.postgres import get_engine, init_db
    from infra.db_models import Base
    init_db()
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    from data.seed import seed_all
    seed_all()
    yield


def _ground_truth() -> dict:
    with open(os.path.join(GOLDEN, "ground_truth.json"), encoding="utf-8") as f:
        return json.load(f)


def test_all_golden_review_targets_match_ground_truth(seeded):
    from backend.app.workflows.compliance_checks.service import run_compliance_check

    gt = _ground_truth()
    review_date = date.fromisoformat(gt["review_date"])
    for filename, expectations in gt["review_targets"].items():
        path = os.path.join(GOLDEN, "review_targets", filename)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        report = run_compliance_check(text, review_date=review_date)
        assert report.assessments, f"{filename}: engine produced NO assessments"
        for exp in expectations:
            matching = [a for a in report.assessments if exp["text_contains"] in a.source_text]
            assert matching, f"{filename}: no claim containing {exp['text_contains']!r}"
            statuses = {a.status.value for a in matching}
            if "expected_status" in exp:
                assert statuses == {exp["expected_status"]}, \
                    f"{filename} claim {exp['text_contains']!r}: {statuses} != {exp['expected_status']}"
            if "expected_status_not" in exp:
                assert exp["expected_status_not"] not in statuses, \
                    f"{filename} claim {exp['text_contains']!r} must not be {exp['expected_status_not']}"


def test_golden_impact_matches_ground_truth(seeded):
    from backend.app.workflows.impact_analysis import impact_engine

    gt = _ground_truth()
    link = gt["policy_links"][0]
    rep = impact_engine.run(link["amending_document_id"])
    assert rep.impacted_policies, "seeded amendment must impact the linked policy"
    pol = rep.impacted_policies[0]
    assert pol.reason == link["expected_impact"]["reason"]
    assert pol.severity == link["expected_impact"]["severity"]
