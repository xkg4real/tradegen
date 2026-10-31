"""Standalone offline tests; no repository application or acceptance runner imports."""

from dataclasses import replace
from decimal import Decimal, localcontext
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from equity_policy_preview import Diagnostic, Observation, Policy, evaluate

D = Decimal


class EquityPolicyPreviewTests(unittest.TestCase):
    def setUp(self):
        self.policy = Policy(
            initial_equity=D("2000"), drawdown_activation_equity=D("8000"),
            positive_profit_loss_fraction=D("0.2"), peak_drawdown_fraction=D("0.25"),
            zero_profit_day_target_fraction=D("0.1"),
        )
        self.observation = Observation(
            equity=D("2500"), prior_high_watermark=D("2500"), day_start_equity=D("2500"),
            current_day_realized_net_profit=D("0"), prior_day_realized_net_profit=D("50"),
            is_first_trading_day=False, approved_effective_floor=D("2500"),
            first_or_zero_day_loss_budget=None, observed_daily_loss=D("0"),
        )

    def diagnostic(self, **changes):
        result = evaluate(self.policy, replace(self.observation, **changes))
        self.assertIsInstance(result, Diagnostic)
        self.assertTrue(result.exits_allowed)
        return result

    def test_equity_equal_to_floor_is_not_a_breach_or_cash_reserve(self):
        result = self.diagnostic()
        self.assertFalse(result.new_entry_blocked)
        self.assertEqual(result.effective_floor, D("2500"))
        self.assertEqual(result.daily_loss_budget, D("10"))
        self.assertEqual(result.reasons, ())

    def test_observed_fee_reduction_below_floor_blocks_with_exits_open(self):
        result = self.diagnostic(equity=D("2499.7"), observed_daily_loss=D("0.3"))
        self.assertTrue(result.new_entry_blocked)
        self.assertIn("EQUITY_BELOW_EFFECTIVE_FLOOR", result.reasons)
        self.assertEqual(result.high_watermark, D("2500"))

    def test_activation_does_not_automatically_relax_effective_floor(self):
        result = self.diagnostic(equity=D("8000"), prior_high_watermark=D("7999"),
                                 approved_effective_floor=D("7999"))
        self.assertEqual(result.calculated_floor, D("6000"))
        self.assertEqual(result.effective_floor, D("7999"))
        self.assertTrue(result.relaxation_pending)
        self.assertFalse(result.new_entry_blocked)
        below = self.diagnostic(equity=D("7998"), prior_high_watermark=D("8000"),
                                approved_effective_floor=D("7999"))
        self.assertTrue(below.new_entry_blocked)

    def test_tightening_is_immediate_and_principal_floor_survives(self):
        result = self.diagnostic(equity=D("2600"), prior_high_watermark=D("2500"))
        self.assertEqual(result.effective_floor, D("2600"))
        self.assertFalse(result.relaxation_pending)
        changed = replace(self.policy, peak_drawdown_fraction=D("0.9"))
        result = evaluate(changed, replace(self.observation, equity=D("8000"),
                          prior_high_watermark=D("8000"), approved_effective_floor=D("2000")))
        self.assertEqual(result.calculated_floor, D("2000"))

    def test_prior_loss_overrides_first_day_flag_and_explicit_budget(self):
        result = self.diagnostic(prior_day_realized_net_profit=D("-1"), is_first_trading_day=True,
                                 first_or_zero_day_loss_budget=D("500"))
        self.assertTrue(result.new_entry_blocked)
        self.assertIn("PREVIOUS_DAY_LOSS", result.reasons)
        self.assertEqual(result.daily_loss_budget, D("0"))
        self.assertIsNone(result.daily_profit_target)

    def test_zero_profit_day_has_target_but_no_invented_loss_budget(self):
        result = self.diagnostic(prior_day_realized_net_profit=D("0"))
        self.assertIn("ZERO_PROFIT_DAY_LOSS_BUDGET_UNCONFIGURED", result.reasons)
        self.assertIsNone(result.daily_loss_budget)
        self.assertEqual(result.daily_profit_target, D("250"))
        self.assertFalse(result.daily_profit_target_met)

    def test_target_miss_and_success_do_not_change_budget_or_entry_diagnostic(self):
        common = dict(prior_day_realized_net_profit=D("0"), first_or_zero_day_loss_budget=D("7"))
        missed = self.diagnostic(**common, current_day_realized_net_profit=D("249.99"))
        met = self.diagnostic(**common, current_day_realized_net_profit=D("250"))
        self.assertFalse(missed.daily_profit_target_met)
        self.assertTrue(met.daily_profit_target_met)
        for result in (missed, met):
            self.assertFalse(result.new_entry_blocked)
            self.assertEqual(result.daily_loss_budget, D("7"))
        blocked = self.diagnostic(**common, current_day_realized_net_profit=D("500"),
                                  observed_daily_loss=D("7"))
        self.assertTrue(blocked.daily_profit_target_met)
        self.assertTrue(blocked.new_entry_blocked)

    def test_missing_prior_result_is_not_a_known_zero_day(self):
        result = self.diagnostic(prior_day_realized_net_profit=None,
                                 first_or_zero_day_loss_budget=D("7"))
        self.assertIn("PREVIOUS_DAY_RESULT_MISSING", result.reasons)
        self.assertIsNone(result.daily_loss_budget)
        self.assertIsNone(result.daily_profit_target)

    def test_first_day_needs_explicit_budget_and_does_not_waive_floor(self):
        common = dict(prior_day_realized_net_profit=None, is_first_trading_day=True)
        missing = self.diagnostic(**common)
        self.assertIn("FIRST_DAY_LOSS_BUDGET_UNCONFIGURED", missing.reasons)
        allowed = self.diagnostic(**common, first_or_zero_day_loss_budget=D("8"))
        self.assertFalse(allowed.new_entry_blocked)
        self.assertIsNone(allowed.daily_profit_target)
        breached = self.diagnostic(**common, first_or_zero_day_loss_budget=D("8"), equity=D("2499"))
        self.assertIn("EQUITY_BELOW_EFFECTIVE_FLOOR", breached.reasons)

    def test_observed_loss_is_independent_of_realized_profit_and_limit_is_inclusive(self):
        result = self.diagnostic(current_day_realized_net_profit=D("200"), observed_daily_loss=D("10"))
        self.assertIn("DAILY_LOSS_BUDGET_REACHED", result.reasons)
        self.assertEqual(result.daily_loss_budget, D("10"))
        result = self.diagnostic(current_day_realized_net_profit=D("-200"), observed_daily_loss=D("1"))
        self.assertFalse(result.new_entry_blocked)  # caller's loss measure, not an inferred replacement
        explicit_zero = self.diagnostic(prior_day_realized_net_profit=D("0"),
                                         first_or_zero_day_loss_budget=D("0"))
        self.assertIn("DAILY_LOSS_BUDGET_REACHED", explicit_zero.reasons)

    def test_unknown_flows_incomplete_data_or_missing_floor_fail_closed(self):
        for changes, reason in ((dict(external_flows_known=False), "EXTERNAL_FLOWS_UNKNOWN"),
                                (dict(data_complete=False), "INCOMPLETE_ACCOUNTING_DATA"),
                                (dict(approved_effective_floor=None), "EFFECTIVE_FLOOR_UNCONFIGURED")):
            with self.subTest(reason=reason):
                result = self.diagnostic(**changes)
                self.assertTrue(result.new_entry_blocked)
                self.assertIn(reason, result.reasons)
        self.assertIsNone(self.diagnostic(approved_effective_floor=None).effective_floor)

    def test_decimal_boundaries_are_exact_even_with_low_ambient_precision(self):
        with localcontext() as context:
            context.prec = 3
            under = self.diagnostic(equity=D("7999.999999999999999999"),
                                    prior_high_watermark=D("7999.999999999999999999"),
                                    approved_effective_floor=D("7999.999999999999999999"))
            on = self.diagnostic(equity=D("8000"), prior_high_watermark=D("8000"),
                                 approved_effective_floor=D("8000"))
        self.assertEqual(under.calculated_floor, D("7999.999999999999999999"))
        self.assertFalse(under.relaxation_pending)
        self.assertEqual(on.calculated_floor, D("6000"))
        self.assertTrue(on.relaxation_pending)
        below = self.diagnostic(equity=D("2499.999999999999999999"))
        self.assertIn("EQUITY_BELOW_EFFECTIVE_FLOOR", below.reasons)

    def test_nonfinite_wrong_types_and_invalid_ranges_fail_closed(self):
        for value in (D("NaN"), D("sNaN"), D("Infinity"), D("-Infinity"), 2.0, 2, True):
            with self.subTest(value=str(value)):
                self.assertTrue(self.diagnostic(equity=value).new_entry_blocked)
        for changes in (dict(observed_daily_loss=D("-1")), dict(data_complete=1),
                        dict(first_or_zero_day_loss_budget=D("-1")), dict(day_start_equity=D("0")),
                        dict(prior_high_watermark=D("1999")), dict(day_start_equity=D("2501"))):
            self.assertTrue(self.diagnostic(**changes).new_entry_blocked)
        for changes in (dict(initial_equity=D("0")), dict(positive_profit_loss_fraction=D("1.01")),
                        dict(peak_drawdown_fraction=D("-0.01")),
                        dict(peak_drawdown_fraction=D("1")),
                        dict(zero_profit_day_target_fraction=D("NaN"))):
            self.assertTrue(evaluate(replace(self.policy, **changes), self.observation).new_entry_blocked)
        self.assertEqual(evaluate(None, self.observation).reasons, ("INVALID_ARGUMENT_TYPE",))

    def test_arithmetic_failure_is_a_diagnostic_not_a_crash_or_authorization(self):
        result = self.diagnostic(equity=D("1E+999999999"), prior_high_watermark=D("1E+999999999"))
        self.assertTrue(result.new_entry_blocked)
        self.assertEqual(result.reasons, ("ARITHMETIC_NOT_EXACT_OR_FINITE",))
        self.assertIsNone(result.effective_floor)


if __name__ == "__main__":
    unittest.main()
