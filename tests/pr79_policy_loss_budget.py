"""Offline reference cases for the proposed PLB admission rule, in synthetic units.

Run with python -m unittest tests.pr79_policy_loss_budget. This module has no
TRADEGEN runtime imports. The same cases must be run against the transactional
controller when PLB is implemented.
"""
from fractions import Fraction as Q
from itertools import product
import unittest


def remaining_after_purchase(*, raw_cash, owner_reserved, app_pending, quantity,
                             limit_price, fee_rate, flow_adjusted_floor, net_flow,
                             protected_raw_floor):
    """raw_cash includes both reservations. The order under test is not in app_pending."""
    required_cash = max(flow_adjusted_floor + net_flow, protected_raw_floor)
    order_debit = quantity * limit_price * (1 + fee_rate)
    return raw_cash - owner_reserved - app_pending - order_debit - required_cash


class LossBudgetDesignCases(unittest.TestCase):
    def setUp(self):
        self.example = dict(raw_cash=Q(100), owner_reserved=Q(1), app_pending=Q(2),
                            quantity=Q(20), limit_price=Q(1), fee_rate=Q(1, 20),
                            flow_adjusted_floor=Q(76), net_flow=Q(0),
                            protected_raw_floor=Q(76))

    def room(self, **changes):
        return remaining_after_purchase(**(self.example | changes))

    def test_equality_and_one_tick_higher_debit(self):
        self.assertEqual(self.room(), 0)
        self.assertLess(self.room(limit_price=Q(1001, 1000)), 0)
        self.assertLess(self.room(fee_rate=Q(51, 1000)), 0)

    def test_cash_deposit_does_not_enlarge_headroom(self):
        self.assertEqual(self.room(raw_cash=Q(107), net_flow=Q(7)), self.room())

    def test_coin_deposit_without_cash_does_not_add_buying_power(self):
        self.assertEqual(self.room(net_flow=Q(7)), -7)

    def test_withdrawal_preserves_floor_and_return_restores_room_once(self):
        self.assertEqual(self.room(raw_cash=Q(93), net_flow=Q(-7)), -7)
        self.assertEqual(self.room(raw_cash=Q(100), net_flow=Q(0)), 0)

    def test_higher_carried_raw_peak_binds(self):
        self.assertEqual(self.room(protected_raw_floor=Q(79)), -3)

    def test_settled_cash_and_cash_already_net_of_owner_reservations_agree(self):
        self.assertEqual(self.room(), self.room(raw_cash=Q(99), owner_reserved=Q(0)))
        self.assertLess(self.room(owner_reserved=Q(2)), 0)
        self.assertLess(self.room(app_pending=Q(3)), 0)

    def test_admitted_orders_with_a_gap_to_zero_preserve_required_cash(self):
        outcomes = set()
        for raw_cash, owner_reserved, pending, quantity, price, fee, flow in product(
            (90, 100, 110), (0, 5), (0, 4), (1, 12, 20),
            (Q(1), Q(3, 2)), (Q(0), Q(1, 20)), (-6, 0, 8),
        ):
            values = dict(raw_cash=raw_cash, owner_reserved=owner_reserved,
                          app_pending=pending, quantity=quantity, limit_price=price,
                          fee_rate=fee, net_flow=flow)
            accepted = self.room(**values) >= 0
            outcomes.add(accepted)
            if accepted:
                # Worst fixture path: reservations settle completely, the new buy
                # fills at its limit plus fee, and all purchased units become worthless.
                cash_left = raw_cash - owner_reserved - pending - quantity * price * (1 + fee)
                self.assertGreaterEqual(cash_left, 76)
                self.assertGreaterEqual(cash_left - flow, 76)
        self.assertEqual(outcomes, {False, True})


if __name__ == "__main__":
    unittest.main()
