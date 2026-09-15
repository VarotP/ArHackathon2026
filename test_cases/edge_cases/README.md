# Routing edge cases

These 30 scenarios extend the practice suite to 39 scenarios. They cover a broad
set of boundary conditions, not every possible graph or combination of events.
All JSON files are runnable with the standard game runner.

```bash
python3 scripts/run_game.py --all
python3 scripts/run_game.py test_cases/edge_cases/opposing_narrow_traffic.json
python3 -m unittest discover -s tests -v
```

## Coverage

| Area | Scenarios |
| --- | --- |
| Weighted routes | `weighted_detour`, `fractional_weights`, `equal_cost_diamond` |
| Graph direction and representation | `directed_return_loop`, `reverse_bidirectional`, `sparse_ids`, `self_loop` |
| Missing or unreachable work | `no_pods`, `no_units`, `isolated_robot`, `unreachable_destination`, `wrong_way_only`, `separate_components`, `partly_unreachable` |
| Pickup locations | `same_source_destination`, `no_storage_labels` |
| Timing | `late_first_batch`, `last_step_delivery`, `spawn_at_cutoff`, `transit_at_cutoff` |
| Carrying capacity | `batch_over_capacity`, `multiple_destinations`, `pickup_in_transit_route` |
| Robot coordination | `more_robots_than_pods`, `opposing_narrow_traffic`, `edge_capacity_two`, `single_dock_batches` |
| Idle positioning | `equal_capacity_idle_tie`, `three_storage_center`, `more_robots_than_parking` |

The existing `custom/mixed_capacity_*.json` scenarios cover larger robots taking
priority at storage and at a shared central position.

## Expected outcomes

Each scenario has `metadata.expected_delivered_pods`. The engine ignores this
extra metadata; the automated tests use it to check the intended outcome.

Seven scenarios intentionally cannot deliver all pods: `no_units`,
`isolated_robot`, `unreachable_destination`, `wrong_way_only`,
`partly_unreachable`, `spawn_at_cutoff`, and `transit_at_cutoff`.
`no_pods` also scores zero because there is no work. These cases lower the batch
score even when the router behaves correctly. Total score is a comparison metric,
not a pass/fail result; use the unittest command to check expected behavior.

The tests check delivery counts, repeatability after reset, valid moves, absence
of routing exceptions, carrying/aisle/node capacity, and pod ownership. Focused
checks verify shortest travel times, intermediate pickups, and cutoff timing.
Existing practice cases still require every pod to be delivered.
