from pipeline.physician_assignment import (
    MAX_OPPORTUNITIES_PER_PHYSICIAN,
    MAX_PHYSICIANS_PER_OPPORTUNITY,
    compute_global_assignments,
    opportunity_clinical_tags,
    physician_clinical_tags,
    physician_match_for_case,
)


def test_theromics_tags_exclude_pure_heme_onc_without_ablation_tags():
    opp = {
        "case_id": "theromics_ri",
        "opportunity_type": "platform",
        "required_roles": "reviewer|advisor",
        "required_specialties": "interventional radiology|surgical oncology|radiation oncology",
    }
    tags = opportunity_clinical_tags(opp, patent_rows=[])
    assert "thermal_ablation" in tags
    heme_tags = physician_clinical_tags("HEMATOLOGY/ONCOLOGY")
    assert "hematology_oncology" in heme_tags
    assert "thermal_ablation" not in heme_tags


def test_global_caps_enforced():
    opportunities = {
        f"opp_{idx}": {
            "case_id": f"opp_{idx}",
            "opportunity_type": "platform",
            "required_roles": "reviewer",
            "required_specialties": "interventional radiology",
            "clinical_tags": "thermal_ablation|interventional_radiology",
        }
        for idx in range(15)
    }
    physicians = [
        {
            "physician_id": f"npi_{idx}",
            "name": f"DOC {idx}",
            "specialty": "INTERVENTIONAL RADIOLOGY",
            "institution": "RI HOSPITAL",
            "roles_willing": "reviewer|advisor",
            "availability_hours_month": "20",
            "compensation_floor_usd": "500",
            "conflict_tags": "none",
            "investor_interest_level": "high",
            "mocked": "false",
            "source_type": "cms_nppes_csv",
            "confidence_0_1": "0.84",
            "clinical_tags": "interventional_radiology|thermal_ablation",
        }
        for idx in range(5)
    ]
    assignments = compute_global_assignments(opportunities, physicians, {})
    for case_id in opportunities:
        assert len(assignments[case_id]["candidate_physicians"]) <= MAX_PHYSICIANS_PER_OPPORTUNITY
    counts: dict[str, int] = {}
    for case_id in opportunities:
        for match in assignments[case_id]["candidate_physicians"]:
            pid = str(match["physician_id"])
            counts[pid] = counts.get(pid, 0) + 1
    for count in counts.values():
        assert count <= MAX_OPPORTUNITIES_PER_PHYSICIAN


def test_physician_match_for_case_uses_policy_metadata():
    load = physician_match_for_case("theromics_ri")
    assert "assignment_policy" in load
    assert load["assignment_policy"]["max_opportunities_per_physician"] == 10
