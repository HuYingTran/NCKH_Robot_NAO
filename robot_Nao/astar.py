# -*- coding: utf-8 -*-
"""
astar.py
A* pathfinding on a 2D grid map with 8-directional movement.
Uses the Octile distance heuristic (admissible & consistent for 8-connected grids).

Grid convention:
    grid[y][x] = 0  -> free cell
    grid[y][x] = 1  -> obstacle
"""
from __future__ import annotations

import heapq
import math
from typing import List, Optional, Tuple

Point = Tuple[int, int]   # (x, y)

SQRT2 = math.sqrt(2)

# 8-connected neighbors: (dx, dy, cost)
NEIGHBORS_8 = [
    (1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
    (1, 1, SQRT2), (1, -1, SQRT2), (-1, 1, SQRT2), (-1, -1, SQRT2),
]


def octile(a: Point, b: Point) -> float:
    """Octile distance heuristic for 8-connected grids."""
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    return max(dx, dy) + (SQRT2 - 1) * min(dx, dy)


def in_bounds(grid: List[List[int]], p: Point) -> bool:
    h = len(grid)
    w = len(grid[0]) if h > 0 else 0
    return 0 <= p[0] < w and 0 <= p[1] < h


def is_free(grid: List[List[int]], p: Point) -> bool:
    return in_bounds(grid, p) and grid[p[1]][p[0]] == 0


def inflate_obstacles(grid: List[List[int]], radius: int = 1) -> List[List[int]]:
    """Inflate obstacles by `radius` cells to keep the NAO robot at a safe distance."""
    h = len(grid)
    w = len(grid[0]) if h > 0 else 0
    inflated = [row[:] for row in grid]
    for y in range(h):
        for x in range(w):
            if grid[y][x] == 1:
                for dy in range(-radius, radius + 1):
                    for dx in range(-radius, radius + 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and (dx != 0 or dy != 0):
                            inflated[ny][nx] = 1
    return inflated


def astar(grid: List[List[int]], start: Point, goal: Point) -> Optional[List[Point]]:
    """
    Run A* from start to goal on `grid`.
    Returns the list of points (including start and goal) or None if no path exists.
    """
    path, _ = astar_with_stats(grid, start, goal)
    return path


def astar_with_stats(
    grid: List[List[int]], start: Point, goal: Point
) -> Tuple[Optional[List[Point]], dict]:
    """
    Same as `astar` but also returns a dict with 'expanded' (closed-set size),
    'opened' (number of pushes onto the heap) and 'time_ms' (runtime).
    """
    import time
    t0 = time.perf_counter()
    stats = {"expanded": 0, "opened": 0, "time_ms": 0.0}

    if not is_free(grid, start) or not is_free(grid, goal):
        stats["time_ms"] = (time.perf_counter() - t0) * 1000.0
        return None, stats
    if start == goal:
        stats["time_ms"] = (time.perf_counter() - t0) * 1000.0
        return [start], stats

    open_heap: List[Tuple[float, int, Point]] = []
    counter = 0
    heapq.heappush(open_heap, (octile(start, goal), counter, start))
    stats["opened"] += 1

    came_from: dict[Point, Point] = {}
    g_score: dict[Point, float] = {start: 0.0}
    closed: set[Point] = set()

    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        if current in closed:
            continue
        if current == goal:
            stats["time_ms"] = (time.perf_counter() - t0) * 1000.0
            return _reconstruct(came_from, current), stats
        closed.add(current)
        stats["expanded"] += 1

        cx, cy = current
        for dx, dy, step_cost in NEIGHBORS_8:
            nx, ny = cx + dx, cy + dy
            neighbor = (nx, ny)
            if neighbor in closed or not is_free(grid, neighbor):
                continue
            if dx != 0 and dy != 0:
                if not is_free(grid, (cx + dx, cy)) or not is_free(grid, (cx, cy + dy)):
                    continue
            tentative_g = g_score[current] + step_cost
            if tentative_g < g_score.get(neighbor, float('inf')):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f = tentative_g + octile(neighbor, goal)
                counter += 1
                heapq.heappush(open_heap, (f, counter, neighbor))
                stats["opened"] += 1
    stats["time_ms"] = (time.perf_counter() - t0) * 1000.0
    return None, stats


def _reconstruct(came_from: dict[Point, Point], current: Point) -> List[Point]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def path_length(path: Optional[List[Point]]) -> float:
    """Return the geometric length of a path. Inf if path is None."""
    if path is None or len(path) < 2:
        return float('inf') if path is None else 0.0
    total = 0.0
    for i in range(1, len(path)):
        ax, ay = path[i - 1]
        bx, by = path[i]
        dx, dy = abs(ax - bx), abs(ay - by)
        total += SQRT2 if (dx == 1 and dy == 1) else 1.0
    return total
