"""Run with: python3 -m unittest discover -s tests -v."""

from pathlib import Path
import json
import unittest

from ar_hackathon.api.routing import drive_unit_next_move
from ar_hackathon.engine.game_engine import GameEngine


ROOT = Path(__file__).resolve().parents[1]


class IdlePositioningTests(unittest.TestCase):
    def engine(self, name):
        return GameEngine(
            str(ROOT / 'test_cases' / 'custom' / f'mixed_capacity_{name}.json'),
            drive_unit_next_move,
        )

    def test_larger_robot_gets_storage_and_picks_up_entire_batch(self):
        for name in ('storage', 'unlimited_storage'):
            with self.subTest(name=name):
                engine = self.engine(name)
                for _ in range(8):
                    engine.step()
                state = engine.graph_state
                large = state.get_drive_unit(9)
                small = state.get_drive_unit(0)
                self.assertEqual(large.current_node, 0)
                self.assertFalse(large.in_transit)
                self.assertNotEqual(small.current_node, 0)
                engine.step()
                self.assertEqual(len(large.carrying), 3)
                self.assertEqual(small.carrying, [])
                self.assertEqual(large.transit_destination, 3)

    def test_larger_robot_gets_center_despite_higher_id(self):
        engine = self.engine('center')
        for _ in range(10):
            engine.step()
        units = engine.graph_state.drive_units
        self.assertEqual(engine.graph_state.get_drive_unit(7).current_node, 1)
        self.assertTrue(all(not unit.in_transit for unit in units))
        self.assertEqual(len({unit.current_node for unit in units}), len(units))
        # With no new work, staging should stay settled.
        for unit in units:
            self.assertIsNone(drive_unit_next_move(unit.id, engine.graph_state))

    def test_all_scenarios_match_expected_deliveries_and_reset_cleanly(self):
        for path in sorted((ROOT / 'test_cases').glob('*/*.json')):
            with self.subTest(path=path.name):
                engine = GameEngine(str(path), drive_unit_next_move)
                result = engine.run_until_finished()
                data = json.loads(path.read_text())
                expected = data.get('metadata', {}).get(
                    'expected_delivered_pods', result['total_pods'])
                self.assertEqual(result['delivered_pods'], expected)
                engine.reset()
                self.assertEqual(engine.run_until_finished(), result)


if __name__ == '__main__':
    unittest.main()
