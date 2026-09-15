# Amazon Robotics Hackathon: optimization strategy

Researched 2026-09-15. Scope: the Drive Unit Routing challenge in this checkout.

## Recommendation

Use bounded, congestion-aware heuristics to maximize the actual score on a diverse set of challenge-like scenarios. Accept occasional suboptimal routes; invest in preventing widespread stalls, bad assignments, and runtime failures. Randomize realistic challenge structures for validation, rather than treating arbitrary random graphs as the expected grading distribution. This is a recommendation inferred from the rules, not a disclosed description of hidden tests.

## What the current rules reward

The supplied [README](../../README.md#scoring) and [engine](../../ar_hackathon/engine/game_engine.py) agree that each case scores:

`S = (100 / total_pods) * sum(exp(-delivery_duration / 50) for delivered pods)`

Duration is delivery time minus entry time. Undelivered pods contribute zero and remain in the denominator. The final result is the sum of normalized case scores. Each case therefore has the same maximum contribution regardless of pod count. The README says hidden cases have similar size and difficulty to practice cases; their distribution and level counts are not published here.

The [rules](../../README.md#rules) impose a one-second callback limit and two-minute case limit on the grading machine. They do not award additional points for lower CPU time within those limits. Runtime headroom is a feasibility requirement; simulated delivery quality is the objective.

Consequences derived from this formula:

- A delivery after 10, 50, or 100 steps retains approximately 81.9%, 36.8%, or 13.5% of its maximum value.
- Mean delivery duration is not an equivalent objective. Two pods delivered after 10 and 90 steps score 49.20; delivery after 50 and 50 steps scores 36.79, despite identical mean duration. These are illustrative outcomes, not a claim that both schedules are feasible on any particular graph.
- Completion percentage alone is also insufficient. Saving one very late pod can be worse than accelerating several fresh pods. Prevent starvation caused by broken routing, but do not assume oldest-first always maximizes score.
- Do not optimize the time the final robot finishes as the sole objective.
- Small regressions on rare cases can be rational if gains elsewhere outweigh them. For a two-group illustrative model, improving common cases by 3 points while losing 30 on rare cases helps only if the rare group is under about 9.1% of evaluation cases. Its actual frequency is unknown.

The engine timestamps arrivals before incrementing its clock. A weight-one immediate delivery can have duration zero. The README's blanket claim that 100 is impossible is therefore not exact; [local scoring contracts](../../test_cases/scoring/README.md#scoring-contracts) document this behavior. Use the engine formula when evaluating candidates.

## What counts as representative

The original six practice cases explicitly exercise:

| Family | Evidence | Optimization target |
| --- | --- | --- |
| Weighted travel | [Level 1](../../test_cases/level1/) | Shortest weighted paths; return trips and sequential arrivals |
| Shared aisles | [Level 2](../../test_cases/level2/) | Narrow bridge congestion, grid traffic, robot-to-pod assignment |
| Docks and carrying | [Level 3](../../test_cases/level3/) | Clear occupied docks, batch compatible cargo, order deliveries |

The six originals have 4–9 nodes, 1–3 robots, and 1–8 pods. This establishes the provided scale, not a strict bound on hidden inputs. Graph sizes were counted from the checked-out JSON files. The initial commit `aac0d7f` includes the scoring and hidden-case rules quoted above.

The current repository also has many added edge-case and scoring fixtures. These are valuable regression checks, but counting every handcrafted case equally can accidentally make the optimization target mostly unusual cases. Report original-practice, representative-generated, and stress-case results separately.

Recommended evaluation design:

1. Keep the existing correctness and regression suite.
2. Generate held-out variants of corridors, grids, bridges, multiple storage locations, and constrained docks. Vary edge weights, capacities, unit counts, destinations, arrival bursts, and carrying capacities. Use the documented scale as the starting point and include a modest scaling margin.
3. Include low and high congestion, bidirectional and directed routes, and both spread-out and synchronized arrivals. Randomization is useful within these structures.
4. Compare policies using the exact normalized score on identical seeds, with breakdowns by family. Keep tuning seeds separate from validation seeds.
5. Track failed deliveries, stalled progress, invalid moves, exceptions, callback tail/max latency, and total case runtime. A fast mean callback can hide a disqualifying slow callback.
6. Preserve simple baselines and test one change at a time. A weight that helps a narrow bridge should also survive sparse traffic and constrained docks.

These benchmark weights and structures are our proposed validation strategy, not organizer-disclosed probabilities.

## Implementation priorities for this checkout

The current [router](../../ar_hackathon/api/routing.py) already includes weighted earliest-arrival search using current aisle occupancy, reward-per-travel-time assignment, bounded carried-batch sequencing, blocked-node detours, and idle positioning. This is source inspection of the current working tree, including pre-existing uncommitted changes; no new performance claim is made here.

The next experiments should measure improvements in assignment stability, dock clearing and bottleneck coordination before adding a much larger global optimizer. Estimate pickup plus delivery travel and congestion; optimize reward obtained by the fleet, not each robot's distance independently. Replan with current observations and bound any lookahead. Cheap fallbacks and small exact subproblems can coexist with a heuristic overall planner.

The callback [GraphState](../../ar_hackathon/models/graph_state.py) exposes current and delivered pods, but not the future arrival schedule or case deadline. Proposed policies must work with those information limits.

## Amazon's broader engineering priorities

Amazon's own [May 2022 explanation of robot congestion](https://www.amazon.science/latest-news/how-amazon-robots-navigate-congestion) describes throughput lost to interference, task allocation and trip reduction, and hybrid planning that combines fast individual routing with coordination. It describes continually updating an existing plan as conditions change. This supports congestion-aware, incremental planning as a practical engineering direction; it is not an additional judging rubric for this hackathon.

## Limits of the research

The supplied challenge rules and engine are the strongest evidence for what this submission should optimize. No public hidden-test distribution or separate subjective judging rubric was established. Prior-event algorithm evidence is useful precedent, not proof of optimality or a guarantee of winning this version.

# Past-winner evidence

Researched 2026-09-15. Participant sources establish what teams publicly claim; I did not find an organizer-published final leaderboard. These are related Amazon Robotics university hackathons, not proof of identical 2026 evaluation distributions.

## Strongest close precedent: September 26, 2025

Rababb Pannu's repository explicitly claims first place at Amazon Robotics Hackathon on September 26, 2025. It is a fork of `jamzaon/ArHackathon2025`. The challenge routed packages between fulfillment centers, whereas this checkout routes robots carrying pods within one floor. Its README uses an exponentially discounted delivery score, `exp(-delivery_duration / 50)`, normalized per test case and summed across cases; public examples and additional hidden cases were evaluated. This makes it a close algorithm/scoring precedent despite different entities and constraints. [Participant repository](https://github.com/Rababb-P/Amazon-Robotics-2025-Hackathon-1st-Place)

Pannu describes modeling 16 fulfillment centers and 30+ packages as a directed weighted graph and extending Dijkstra with congestion penalties and real-time adaptation. The participant emphasizes system throughput and handling increasingly difficult uniform, weighted, and capacity-constrained cases. This supports congestion-aware heuristics as a demonstrated successful approach; it does not establish whether the hidden cases were realistic, uniformly random, or adversarial. [Participant account](https://ca.linkedin.com/in/rababb-pannu)

The University of Waterloo independently confirms an Amazon Robotics Day on September 26, 2025, with a two-hour hackathon. Its page does not name the winners. Matching the date corroborates the event's existence, not the competition result. [University event page](https://uwaterloo.ca/events/events/amazon-robotics-day)

### Published implementation inspected

Verified repository HEAD: `409365384d928e803de10c52d7b16f8334476479`; default branch is `github`. Its `routing.py` computes a Dijkstra edge cost from base cost, a quadratic congestion term, and a same-timestep edge-use counter. It can select an alternate outgoing hop when the preferred hop is highly utilized. Thresholds and penalties are heuristic; there is no global optimum guarantee. The source measures planned outgoing demand, so do not describe its variable names as proof that it correctly models actual in-transit occupancy. We inspected the published implementation, but did not reproduce its competition score or prove that this exact revision was submitted on the competition day. [Pinned source](https://github.com/Rababb-P/Amazon-Robotics-2025-Hackathon-1st-Place/blob/409365384d928e803de10c52d7b16f8334476479/ar_hackathon/api/routing.py)

Practical inference: copy the idea of estimating shared-resource delay, not the numeric thresholds or implementation. Current-state semantics differ, and an adaptive routing rule needs fresh validation here.

## Earlier Waterloo CRYSP winner: BFS plus obstacle heuristics

Haseeb-Ur-Rehman Faheem's public repository claims first place using breadth-first pathfinding in a 2D robotics simulator. It is forked from `dawaraziz/AR_Day_2024`, so the repository lineage points to the 2024 activity, although an exact event date was not established. Its rules ranked completed levels first, then movement score, and could rerun ties with another random seed. Its explicit lifting/dropping actions and grid movement differ from the present API. [Participant repository and rules](https://github.com/haseeburrehmanfaheem/Amazon-Robotics-Hackathon)

A teammate's account, reposted on Faheem's profile, calls the team CRYSP and says its Waterloo solution used tailored BFS with obstacle-avoidance heuristics. Faheem's personal site independently repeats his first-place/BFS claim. These remain participant reports, not independent organizer results. [Reposted participant account](https://ca.linkedin.com/in/haseeburrrehman), [personal site](https://haseeburrehmanfaheem.github.io/)

## Separate 2025 Robotics Day winner: A* and sensor-based avoidance

Shaurya Santhosh reports first place at an Amazon Robotics Day 2025 event with Fayaaz Ahmed and Ali Shavandi. Their task used a randomly generated Pygame warehouse, A* routing, tracking delivered pod identifiers, and sensor-based avoidance of other robots. The post does not establish that this was the same venue, edition, or scoring system as the September 2025 FC-routing event. It is a relevant example of successful practical search, but not evidence for the current hidden-case distribution. [Direct participant post](https://www.linkedin.com/posts/snt-shaurya_hackathon-amazonrobotics-pathfinding-activity-7301097603327279104-gDMy)

## Exclusions and conclusion

The Amazon Robotics Challenge 2017 concerned physical picking/stowing robots. Amazon Last Mile Routing Challenge and League of Robot Runners are different competitions. Their winners should not be presented as winners of this hackathon.

The closest public winning approaches use established graph search plus task-specific heuristics. None of the inspected evidence supports prioritizing arbitrary uniform-random graphs, assuming production warehouse distributions, or demanding optimal worst-case routes. The defensible target remains the current documented scoring rule, realistic variations of the supplied levels, and safeguards against large failures on valid unusual inputs.
