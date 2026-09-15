"""
Amazon Robotics Hackathon - Routing API

This module defines the routing API for the Amazon Robotics Hackathon.
Students will implement the drive_unit_next_move function in this module.

*****IMPORTANT*****
Team name: Tarit&Val
Email address: varotpava@gmail.com
*******************
"""

from heapq import heappop, heappush
from math import ceil
from typing import Optional
from ar_hackathon.models.graph_state import GraphState
from ar_hackathon.utils.routing_utils import is_valid_move


def drive_unit_next_move(drive_unit_id: int, state: GraphState) -> Optional[int]:
    """
    Determine the next node for a drive unit to move to.

    This is the function that students will implement. The game engine will
    call this function for each idle drive unit at each time step to
    determine where it should go next.

    Pickups and deliveries are automatic: a drive unit with free capacity
    that stops at (or passes through) a node with a waiting pod picks it up,
    and a drive unit that reaches a carried pod's destination station drops
    it off.

    Args:
        drive_unit_id: ID of the drive unit being routed
        state: GraphState object containing the current state of the floor

    Returns:
        next_node_id: ID of an adjacent node to move to, or None to wait
                      at the current node
    """
    unit = state.get_drive_unit(drive_unit_id)
    if unit is None or unit.in_transit:
        return None

    # Estimate when each aisle has a free slot. Both directions share the
    # capacity of a bidirectional edge, including moves committed this step.
    adjacency = {}
    for edge in state.edges:
        release = 0
        if edge.capacity is not None:
            if edge.capacity <= 0:
                continue
            departures = sorted(
                max(1, ceil(other.transit_remaining_time))
                for other in state.drive_units
                if other.in_transit
                and edge.connects(other.current_node, other.transit_destination)
            )
            if len(departures) >= edge.capacity:
                release = departures[len(departures) - edge.capacity]
        weight = max(1, ceil(edge.weight))
        adjacency.setdefault(edge.from_node, []).append((edge.to_node, weight, release))
        if edge.bidirectional:
            adjacency.setdefault(edge.to_node, []).append((edge.from_node, weight, release))

    def routes(start, delay=0, graph=None):
        """Earliest arrival times, allowing waits for currently occupied aisles."""
        graph = adjacency if graph is None else graph
        distances = {start: delay}
        first_hops = {}
        queue = [(delay, start)]
        while queue:
            distance, node = heappop(queue)
            if distance != distances[node]:
                continue
            for neighbor, weight, release in graph.get(node, []):
                candidate = max(distance, release) + weight
                if candidate < distances.get(neighbor, float("inf")):
                    distances[neighbor] = candidate
                    first_hops[neighbor] = (
                        neighbor if node == start else first_hops[node]
                    )
                    heappush(queue, (candidate, neighbor))
        return distances, first_hops

    distances, first_hops = routes(unit.current_node)
    if unit.carrying:
        pod = state.get_pod(unit.carrying[0])
        target = pod.destination_station if pod is not None else None
    else:
        waiting = [
            pod for pod in state.active_pods
            if pod.carried_by is None and pod.current_node is not None
            and pod.delivery_time is None
        ]
        # Greedily match the earliest pickup opportunities, once per robot and
        # pod. Include empty robots in transit so their work stays accounted for.
        candidates = []
        for other in state.drive_units:
            if other.carrying or not other.has_capacity:
                continue
            if other.id == unit.id:
                arrivals = distances
            else:
                start = (other.transit_destination if other.in_transit
                         else other.current_node)
                delay = (max(1, ceil(other.transit_remaining_time))
                         if other.in_transit else 0)
                arrivals, _ = routes(start, delay)
            for pod in waiting:
                if pod.current_node in arrivals:
                    candidates.append((arrivals[pod.current_node], pod.entry_time,
                                       other.id, pod.id, pod.current_node))
        assigned_units = set()
        assigned_pods = set()
        target = None
        for _, _, unit_id, pod_id, source in sorted(candidates):
            if unit_id in assigned_units or pod_id in assigned_pods:
                continue
            assigned_units.add(unit_id)
            assigned_pods.add(pod_id)
            if unit_id == unit.id:
                target = source

        if target is None:
            # With no assigned pickup, stage near storage for future arrivals.
            # Reverse searches measure candidate -> storage travel, including
            # one-way aisles. Ignore transient congestion when choosing a home
            # so its location does not fluctuate as other robots move.
            reverse = {}
            for source, edges in adjacency.items():
                for destination, weight, _ in edges:
                    reverse.setdefault(destination, []).append((source, weight, 0))
            storage_distances = [
                routes(node.id, graph=reverse)[0]
                for node in state.nodes if node.node_type == "storage"
            ]
            # Assign staging spots globally, largest carrier first. A spot is
            # reserved even when it has unlimited physical capacity: sharing
            # storage would let the engine's lower-ID pickup order defeat this
            # preference. Empty unassigned occupants can yield their old spot.
            idle = [other for other in state.drive_units
                    if not other.carrying and other.has_capacity
                    and other.id not in assigned_units]
            idle_ids = {other.id for other in idle}
            reserved = set()
            for other in sorted(idle, key=lambda robot: (-robot.capacity, robot.id)):
                start = (other.transit_destination if other.in_transit
                         else other.current_node)
                arrivals, _ = routes(start)
                parking = []
                for node in state.nodes:
                    if (node.node_type == "station" or node.id not in arrivals
                            or node.id in reserved):
                        continue
                    # Working robots retain their physical/inbound slots.
                    occupancy = sum(
                        1 for robot in state.drive_units
                        if robot.id not in idle_ids
                        and (robot.transit_destination if robot.in_transit
                             else robot.current_node) == node.id
                    )
                    if node.capacity is not None and occupancy >= node.capacity:
                        continue
                    travel_times = [
                        costs[node.id] for costs in storage_distances if node.id in costs
                    ]
                    if not travel_times:
                        continue
                    parking.append((
                        -len(travel_times), sum(travel_times) / len(travel_times),
                        max(travel_times), arrivals[node.id], node.id,
                    ))
                if parking:
                    spot = min(parking)[-1]
                    reserved.add(spot)
                    if other.id == unit.id:
                        target = spot
                        break

    next_node = first_hops.get(target)
    # If waiting for a busy aisle beats a detour, wait and replan next step.
    if next_node is not None and is_valid_move(state, unit, next_node):
        return next_node
    return None
