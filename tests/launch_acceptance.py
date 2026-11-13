"""First-trade foundation tests; hermetic E1/E3 seams and temporary state."""
from __future__ import annotations

import importlib
import sys

from tests.control_acceptance import _wrap

MODULES = ("launch_guards", "network_route", "accounts_collector", "launch_profile",
           "launch_strategy", "launch_runner", "launch_cli", "launch_capture", "launch_workflow",
           "launch_deployment", "launch_review_request", "launch_driver", "launch_review_auth",
           "launch_private_input", "launch_windows_owner_authority", "launch_baseline_head",
           "launch_account_interval", "launch_live_history", "launch_coordinator", "launch_study",
           "launch_quote_diagnostics", "launch_shortened_study", "launch_study_review",
           "launch_instrument_refresh", "launch_owner_ops", "owner_guards", "launch_owner_rehearsal",
           "launch_universe_store", "launch_floor_state_check", "launch_clock_check", "launch_program",
           "launch_universe_history", "launch_evidence_objects", "launch_history_storage",
           "launch_lossless_history", "launch_protective_state", "launch_protective_store",
           "launch_toast_queue", "launch_runner_universe", "launch_coordinator_universe",
           "launch_owner_universe", "launch_pr4e_regressions", "launch_research_outcomes",
           "launch_managed_behavior", "launch_driver_carry", "launch_carry_evaluator",
           "launch_capture_v2", "launch_workflow_v2", "launch_carry_strategy",
           "launch_carry_review", "launch_carry_coordinator",
           "launch_study_evidence", "launch_study_family", "launch_study_receipts", "launch_research_bundle_format",
           "launch_research_bundle_store", "launch_research_bundle",
           "launch_bundle_attestation", "launch_bundle_auth", "launch_bundle_review",
           "launch_research_revocation", "launch_research_revocation_auth",
           "launch_bundle_recovery", "launch_recovery_artifact", "launch_committed_account",
           "launch_study_review_backend", "launch_sealed_study_review", "launch_sealed_study_cli",
           "launch_research_incidents", "launch_research_incident_store",
           "launch_research_incident_monitor", "launch_research_incident_cli",
           "launch_research_incident_integration")


def tests():
    found = []
    for stem in MODULES:
        try:
            module = importlib.import_module("tests." + stem)
        except Exception as exc:
            def broken(exc=exc):
                raise exc
            found.append((stem + "/import", _wrap(broken)))
            continue
        for name, function in sorted(vars(module).items()):
            if name.startswith("test_") and callable(function) and getattr(function, "__module__", None) == module.__name__:
                found.append((stem + "/" + name, _wrap(function)))
    return found


def main(argv=None):
    from tests.run_all import run
    args = list(sys.argv[1:] if argv is None else argv)
    rows = run([(name, fn) for name, fn in tests() if not args or args[0] in name])
    counts = {status: sum(row["status"] == status for row in rows) for status in ("PASS", "FAIL", "NOT_RUN")}
    print(counts)
    return 0 if rows and counts["FAIL"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
