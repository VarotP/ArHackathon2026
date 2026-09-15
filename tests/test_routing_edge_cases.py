"""Behavior and safety checks for the runnable edge-case scenarios."""

import json
from pathlib import Path
import unittest

from ar_hackathon.api.routing import drive_unit_next_move
from ar_hackathon.engine.game_engine import GameEngine
from ar_hackathon.utils.routing_utils import is_valid_move


CASES = Path(__file__).resolve().parents[1] / 'test_cases' / 'edge_cases'


class RoutingEdgeCaseTests(unittest.TestCase):
    def engine(self, name, driver=drive_unit_next_move):
        return GameEngine(str(CASES / f'{name}.json'), driver)

    def test_every_scenario_preserves_safety_and_completes_as_expected(self):
        for path in sorted(CASES.glob('*.json')):
            with self.subTest(case=path.stem):
                errors = []

                def checked_driver(unit_id, state):
                    # The engine converts exceptions to waits; retain them so
                    # a silently failing router cannot pass these tests.
                    try:
                        result = drive_unit_next_move(unit_id, state)
                        unit = state.get_drive_unit(unit_id)
                        if result is not None and not is_valid_move(state, unit, result):
                            errors.append(f'Invalid move from {unit.current_node}: {result}')
                        return result
                    except Exception as error:
                        errors.append(repr(error))
                        return None

                engine = GameEngine(str(path), checked_driver)
                while not engine.is_finished:
                    state, _ = engine.step()
                    for unit in state.drive_units:
                        self.assertLessEqual(len(unit.carrying), unit.capacity)
                    for edge in state.edges:
                        if edge.capacity is not None:
                            self.assertLessEqual(
                                state.edge_occupancy(edge.from_node, edge.to_node),
                                edge.capacity)
                    for node in state.nodes:
                        if node.capacity is not None:
                            self.assertLessEqual(state.node_occupancy(node.id), node.capacity)
                    carried = [pod_id for unit in state.drive_units for pod_id in unit.carrying]
                    self.assertEqual(len(carried), len(set(carried)))
                    for pod in state.active_pods:
                        if pod.carried_by is not None:
                            self.assertIn(pod.id, state.get_drive_unit(pod.carried_by).carrying)
                            self.assertIsNone(pod.current_node)
                    delivered = {pod.id for pod in state.delivered_pods}
                    self.assertFalse(delivered.intersection(carried))
                    self.assertFalse(delivered.intersection(pod.id for pod in state.active_pods))
                self.assertEqual(errors, [])
                data = json.loads(path.read_text())
                self.assertEqual(engine.stats['delivered_pods'],
                                 data['metadata']['expected_delivered_pods'])
                self.assertLessEqual(engine.stats['total_time_steps'],
                                     data['metadata']['max_time_steps'])

    def test_weighted_and_fractional_routes_choose_fastest_first_hop(self):
        for name, expected in [('weighted_detour', 1), ('fractional_weights', 2)]:
            with self.subTest(case=name):
                engine = self.engine(name)
                engine.step()
                unit = engine.graph_state.get_drive_unit(0)
                actual = unit.transit_destination if unit.in_transit else unit.current_node
                self.assertEqual(actual, expected)
                self.assertEqual(engine.run_until_finished()['total_time_steps'], 3)

    def test_invalid_unit_and_in_transit_calls_wait(self):
        engine = self.engine('fractional_weights')
        self.assertIsNone(drive_unit_next_move(999, engine.graph_state))
        engine.step()
        self.assertTrue(engine.graph_state.get_drive_unit(0).in_transit)
        self.assertIsNone(drive_unit_next_move(0, engine.graph_state))

    def test_intermediate_pickup_uses_free_capacity(self):
        engine = self.engine('pickup_in_transit_route')
        engine.step()
        self.assertEqual(set(engine.graph_state.get_drive_unit(0).carrying), {'A', 'B'})
        self.assertEqual(engine.run_until_finished()['delivered_pods'], 2)

    def test_last_step_delivery_counts_but_cutoff_spawn_does_not(self):
        result = self.engine('last_step_delivery').run_until_finished()
        self.assertEqual(result['delivered_pods'], 1)
        self.assertEqual(result['total_time_steps'], 5)
        engine = self.engine('spawn_at_cutoff')
        result = engine.run_until_finished()
        self.assertEqual(result['delivered_pods'], 0)
        self.assertEqual(engine.graph_state.active_pods, [])
        self.assertEqual(result['total_time_steps'], 5)


if __name__ == '__main__':
    unittest.main()
