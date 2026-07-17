#!/usr/bin/env python3
"""kuni-umi 国産 — agent gate tests (offline, no kotoba host, no network, no LLM).

ADR-2605201400. Exercises the planetary-infra deployment constitutional gates:
witness quorum (G8, mandatory >=2 independent robot DIDs), land-registry anchor
(G10), deployment planning, construction, commissioning, audit witness,
decommission, and the USDC + tithe settlement (G7/G15).

    python3 test_agent.py
"""
from __future__ import annotations

import agent


def _check(name: str, cond: bool) -> None:
    print(("  ok  " if cond else "  FAIL") + f"  {name}")
    return cond


def test_witness_quorum_satisfied() -> None:
    result = agent.witness_quorum_ok(["did:robot:otete-001", "did:robot:mimi-001"])
    assert _check("witness quorum >=2 accepted (G8)", result["ok"] is True)


def test_witness_quorum_single() -> None:
    result = agent.witness_quorum_ok(["did:robot:otete-001"])
    assert _check("single witness rejected (G8)", result["ok"] is False and result.get("escalate_council_lv6"))


def test_witness_quorum_empty() -> None:
    result = agent.witness_quorum_ok([])
    assert _check("no witnesses rejected (G8)", result["ok"] is False and result.get("escalate_council_lv6"))


def test_witness_quorum_duplicates() -> None:
    result = agent.witness_quorum_ok(["did:robot:otete-001", "did:robot:otete-001"])
    assert _check("duplicate witness DIDs rejected (G8)", result["ok"] is False and result.get("escalate_council_lv6"))


def test_site_survey_valid() -> None:
    out = agent.handle_site_survey("site-001", "35.6789,139.7656", "did:web:registry.example")
    assert _check("site survey with valid land-registry anchor (G10)", out.get(":siteAttestation/id") == "site-001")


def test_site_survey_invalid_anchor() -> None:
    out = agent.handle_site_survey("site-002", "35.6789,139.7656", "not-a-did")
    assert _check("site survey rejected on invalid DID (G10)", out.get("blocked") is True)


def test_deployment_planning() -> None:
    out = agent.handle_deployment_planning("site-001", "otete,mimi,quad", "did:member:001")
    assert _check("deployment planning generates intent (G14)", out.get(":deploymentIntent/state") == "planned")


def test_construction_witness_ok() -> None:
    out = agent.handle_construction_orchestration(
        "deploy.site-001",
        "otete,mimi",
        ["did:robot:otete-001", "did:robot:mimi-001"]
    )
    assert _check("construction with witness quorum >=2 accepted (G8)", out.get(":constructionRecord/state") == "ready-qc")


def test_construction_witness_fail() -> None:
    out = agent.handle_construction_orchestration(
        "deploy.site-001",
        "otete,mimi",
        ["did:robot:otete-001"]
    )
    assert _check("construction with single witness rejected (G8)", out.get("blocked") is True and out.get("escalate"))


def test_commissioning_witness_ok() -> None:
    out = agent.handle_commissioning(
        "const.deploy.site-001",
        ["did:robot:otete-001", "did:robot:mimi-001"]
    )
    assert _check("commissioning with witness quorum >=2 passes (G8)", out.get(":commissioningRecord/state") == "passed")


def test_commissioning_witness_fail() -> None:
    out = agent.handle_commissioning(
        "const.deploy.site-001",
        ["did:robot:otete-001"]
    )
    assert _check("commissioning with single witness fails (G8)", out.get("blocked") is True and out.get("escalate"))


def test_audit_witness_ok() -> None:
    out = agent.handle_audit_witness(
        "comm.const.deploy.site-001",
        ["did:robot:otete-001", "did:robot:mimi-001"]
    )
    assert _check("audit witness with quorum >=2 completes (G8)", out.get(":auditRecord/state") == "complete")


def test_audit_witness_fail() -> None:
    out = agent.handle_audit_witness(
        "comm.const.deploy.site-001",
        ["did:robot:otete-001"]
    )
    assert _check("audit witness with single witness fails (G8)", out.get("blocked") is True and out.get("escalate"))


def test_decommission_witness_ok() -> None:
    out = agent.handle_decommission(
        "audit.comm.const.deploy.site-001",
        ["did:robot:otete-001", "did:robot:quad-001"]
    )
    assert _check("decommission with witness quorum >=2 completes (G8)", out.get(":decommissionRecord/state") == "complete")


def test_decommission_witness_fail() -> None:
    out = agent.handle_decommission(
        "audit.comm.const.deploy.site-001",
        []
    )
    assert _check("decommission with no witnesses rejected (G8)", out.get("blocked") is True and out.get("escalate"))


def test_settlement_tithe_split() -> None:
    s = agent.build_settlement_intent(20_000_000)
    assert _check("10% tithe + stops at intent (G7/G15)", s["titheMinor"] == 2_000_000 and s["state"] == "intent" and s["rail"] == "usdc-base-l2")


def test_settlement_executed_with_sig() -> None:
    s = agent.build_settlement_intent(1_000_000, buyer_sig_ref="0xsig")
    assert _check("settlement executes only with member signature (G15)", s["state"] == "executed")


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    print(f"kuni-umi agent — {len(tests)} tests")
    for test in tests:
        test()
    print(f"\n{len(tests)}/{len(tests)} passed")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
