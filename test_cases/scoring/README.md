# Score-sensitive scenarios

These nine runnable scenarios bring the full suite to 48 scenarios. They cover
four routing targets and four scoring contracts (entry-time invariance uses two
fixtures). Assertions live in `tests/test_scoring.py`.

```bash
python3 -m unittest discover -s tests -p 'test_scoring.py' -v
python3 -m unittest discover -s tests -v
python3 scripts/run_game.py test_cases/scoring/far_destination_first.json
python3 scripts/run_game.py --all
```

## Routing targets

| Scenario | Required behavior | Score target |
| --- | --- | --- |
| `far_destination_first` | Deliver B on the 1-step branch before A on the 20-step branch; finish within 22 steps. | At least `50 * (1 + exp(-21/50))`, approximately 82.85. |
| `unreachable_first_cargo` | Deliver reachable B even though the first carried pod A has no route to its station. | 50; A remains undelivered. |
| `nearest_pickup_long_delivery` | Choose B's 2-step pickup plus 1-step delivery over A's 1-step pickup plus 30-step delivery, within a 10-step horizon. | At least `50 * exp(-2/50)`, approximately 48.04. |
| `blocked_node_detour` | Escape opposing loaded robots at capacity-1 nodes using the open detour; deliver both within 4 steps. | At least `50 * (exp(-3/50) + exp(-1/50))`, approximately 96.10. |

The tests include small scripted reference routes that satisfy these targets
through the real engine. Returned moves are checked for validity, and routing
exceptions are retained as test failures instead of being hidden by engine waits.
These are achievable targets for these specific graphs, not general claims that
nearest-first routing is always optimal.

At addition, all four router tests fail against the existing algorithm. The
existing all-scenarios delivery-count test also reports failures for the latter
three scenarios. These failures are intentionally visible, not skipped or marked
as expected failures. The algorithm and engine have not been changed.

## Scoring contracts

These tests use a direct-delivery driver to isolate the referee's scoring from
routing decisions.

| Scenario | Contract |
| --- | --- |
| `partial_delivery_decay` | One of two pods delivers after duration 50: raw score `100/e`, normalized score `50/e`; the unreachable pod remains in the denominator. |
| `early_entry`, `late_entry` | Spawn at time 0 or 10 and deliver after duration 5: both score `100 * exp(-5/50)`. |
| `cutoff_denominator` | A delivers at time 1, B is scheduled at the cutoff of 2 and never spawns; score is `50 * exp(-1/50)`. |
| `one_step_delivery` | A weight-1 edge delivers at its spawn timestamp and earns 100; the reported elapsed simulation time is 1. |

Delivery timestamps are recorded before the engine increments its clock. Thus a
pod picked up at spawn and delivered over a path taking L steps has duration
L - 1. The one-step contract captures actual engine behavior, despite the main
README's claim that a score of 100 is unattainable.

`metadata.expected_delivered_pods` describes the intended outcome, rather than
the current router's result. Intentionally unreachable and cutoff pods still
reduce normalized scores even when the target behavior is achieved.
