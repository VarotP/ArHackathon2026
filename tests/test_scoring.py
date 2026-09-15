"""Score contracts and routing targets; run with unittest discovery.

Routing targets intentionally fail until the router meets them. Small scripted
drivers establish that each target is achievable under the actual engine rules.
"""

import math
from pathlib import Path
import unittest

from ar_hackathon.api.routing import drive_unit_next_move
from ar_hackathon.engine.game_engine import GameEngine
from ar_hackathon.utils.routing_utils import is_valid_move


CASES = Path(__file__).resolve().parents[1] / 'test_cases' / 'scoring'


def direct_delivery(unit_id, state):
    """Contract fixtures use a single source and one reachable station."""
    unit = state.get_drive_unit(unit_id)
    return 1 if unit.current_node == 0 and unit.carrying else None


def reference_route(name, unit_id, state):
    """Known feasible routes, not a replacement general-purpose router."""
    unit = state.get_drive_unit(unit_id)
    if not unit.carrying:
        if name == 'nearest_pickup_long_delivery' and unit.current_node == 0:
            return 2
        return None
    if name == 'far_destination_first':
        if unit.current_node == 0:
            return 2 if state.get_pod('B').delivery_time is None else 1
        return 0
    if name == 'unreachable_first_cargo':
        return 2 if unit.current_node == 0 else None
    if name == 'nearest_pickup_long_delivery':
        return 4 if unit.current_node == 2 else None
    if name == 'blocked_node_detour':
        moves = {0: {0: 2, 2: 3}, 1: {1: 0, 0: 4}}
        return moves[unit_id].get(unit.current_node)
    raise AssertionError(f'Unknown reference scenario: {name}')


class ScoringContractTests(unittest.TestCase):
    def run_case(self, name):
        engine = GameEngine(str(CASES / f'{name}.json'), direct_delivery)
        engine.run_until_finished()
        return engine

    def test_exact_decay_and_undelivered_denominator(self):
        engine = self.run_case('partial_delivery_decay')
        stats = engine.stats
        self.assertEqual(stats['total_pods'], 2)
        self.assertEqual(stats['delivered_pods'], 1)
        self.assertEqual(stats['average_delivery_time'], 50)
        self.assertEqual(stats['delivery_percentage'], 50)
        self.assertAlmostEqual(stats['raw_score'], 100 * math.exp(-1))
        self.assertAlmostEqual(stats['score'], 50 * math.exp(-1))

    def test_score_depends_on_duration_not_absolute_entry_time(self):
        early = self.run_case('early_entry')
        late = self.run_case('late_entry')
        for engine, entry in [(early, 0), (late, 10)]:
            with self.subTest(entry=entry):
                pod, = engine.graph_state.delivered_pods
                self.assertEqual(pod.entry_time, entry)
                self.assertEqual(pod.delivery_time, entry + 5)
                self.assertEqual(engine.stats['average_delivery_time'], 5)
                self.assertAlmostEqual(engine.stats['score'], 100 * math.exp(-0.1))
        self.assertAlmostEqual(early.stats['score'], late.stats['score'])

    def test_unspawned_cutoff_pod_counts_in_denominator(self):
        engine = self.run_case('cutoff_denominator')
        self.assertEqual(engine.stats['total_time_steps'], 2)
        self.assertEqual(engine.stats['total_pods'], 2)
        self.assertEqual(engine.stats['delivered_pods'], 1)
        self.assertIsNone(engine.graph_state.get_pod('B'))
        self.assertEqual(engine.graph_state.active_pods, [])
        self.assertAlmostEqual(engine.stats['score'], 50 * math.exp(-1 / 50))

    def test_one_step_delivery_scores_100_before_clock_increment(self):
        engine = self.run_case('one_step_delivery')
        pod, = engine.graph_state.delivered_pods
        self.assertEqual(pod.delivery_time, pod.entry_time)
        self.assertEqual(engine.stats['total_time_steps'], 1)
        self.assertEqual(engine.stats['score'], 100)
        self.assertEqual(engine.stats['average_delivery_time'], 0)


class RoutingScoreTests(unittest.TestCase):
    def run_case(self, name, driver=drive_unit_next_move):
        errors = []

        def checked_driver(unit_id, state):
            # safe_execute converts exceptions to waits; keep failures visible.
            try:
                result = driver(unit_id, state)
                if result is not None and not is_valid_move(
                        state, state.get_drive_unit(unit_id), result):
                    errors.append(f'Invalid move by {unit_id}: {result}')
                return result
            except Exception as error:
                errors.append(repr(error))
                return None

        engine = GameEngine(str(CASES / f'{name}.json'), checked_driver)
        engine.run_until_finished()
        self.assertEqual(errors, [])
        return engine

    def assert_target(self, name, engine):
        delivered = {pod.id: pod for pod in engine.graph_state.delivered_pods}
        if name == 'far_destination_first':
            self.assertEqual(set(delivered), {'A', 'B'})
            self.assertLess(delivered['B'].delivery_time, delivered['A'].delivery_time)
            self.assertLessEqual(engine.stats['total_time_steps'], 22)
            self.assertGreaterEqual(engine.stats['score'] + 1e-9,
                                    50 * (1 + math.exp(-21 / 50)))
        elif name == 'unreachable_first_cargo':
            self.assertEqual(set(delivered), {'B'})
            self.assertAlmostEqual(engine.stats['score'], 50)
        elif name == 'nearest_pickup_long_delivery':
            self.assertEqual(set(delivered), {'B'})
            self.assertLessEqual(delivered['B'].delivery_time, 2)
            self.assertGreaterEqual(engine.stats['score'] + 1e-9,
                                    50 * math.exp(-2 / 50))
        elif name == 'blocked_node_detour':
            self.assertEqual(set(delivered), {'A', 'B'})
            self.assertLessEqual(engine.stats['total_time_steps'], 4)
            self.assertGreaterEqual(engine.stats['score'] + 1e-9,
                                    50 * (math.exp(-3 / 50) + math.exp(-1 / 50)))
        else:
            self.fail(f'Unknown target: {name}')

    def test_reference_routes_achieve_all_targets(self):
        for name in ('far_destination_first', 'unreachable_first_cargo',
                     'nearest_pickup_long_delivery', 'blocked_node_detour'):
            with self.subTest(case=name):
                engine = self.run_case(
                    name, lambda uid, state: reference_route(name, uid, state))
                self.assert_target(name, engine)

    def test_near_destination_before_far_batch_member(self):
        name = 'far_destination_first'
        self.assert_target(name, self.run_case(name))

    def test_unreachable_cargo_does_not_block_reachable_cargo(self):
        name = 'unreachable_first_cargo'
        self.assert_target(name, self.run_case(name))

    def test_pickup_selection_accounts_for_delivery_time(self):
        name = 'nearest_pickup_long_delivery'
        self.assert_target(name, self.run_case(name))

    def test_occupied_node_uses_available_detour(self):
        name = 'blocked_node_detour'
        engine = GameEngine(str(CASES / f'{name}.json'), drive_unit_next_move)
        engine.step()
        self.assertEqual(engine.graph_state.get_drive_unit(0).transit_destination, 2)
        self.assert_target(name, self.run_case(name))


if __name__ == '__main__':
    unittest.main()
