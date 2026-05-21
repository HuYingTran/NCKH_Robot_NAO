# -*- coding: utf-8 -*-
"""
main_demo.py
End-to-end demo: GA finds the optimal pickup-delivery sequence for the NAO robot,
then A* generates a cell-by-cell path between waypoints.

Run:
    python main_demo.py
"""
from __future__ import annotations

from astar import inflate_obstacles
from ga_planner import (
    GAConfig,
    Order,
    chromosome_to_label,
    expand_full_path,
    run_ga,
)


# ---------------------------------------------------------------------------
# Environment definition
# ---------------------------------------------------------------------------
# 20 columns x 15 rows. 0 = free, 1 = obstacle.
RAW_MAP = [
    "....................",
    "....................",
    "....##......##......",
    "....##......##......",
    "....##......##......",
    "............##......",
    "..####..............",
    "..####....######....",
    "..........######....",
    "....................",
    "..............##....",
    "..####........##....",
    "..####..............",
    "....................",
    "....................",
]


def build_grid(rows):
    return [[1 if c == '#' else 0 for c in row] for row in rows]


def print_grid_with_route(grid, route, full_path=None):
    """ASCII visualization of the environment, waypoints and full path."""
    h = len(grid)
    w = len(grid[0])
    canvas = [['#' if grid[y][x] == 1 else '.' for x in range(w)] for y in range(h)]

    # Mark the cell-by-cell path
    if full_path:
        for x, y in full_path:
            if canvas[y][x] == '.':
                canvas[y][x] = '·'

    # Mark high-level waypoints
    for idx, (x, y) in enumerate(route):
        if 0 <= x < w and 0 <= y < h:
            if idx == 0:
                canvas[y][x] = 'S'
            else:
                canvas[y][x] = str((idx - 1) % 10)

    print('  ' + ''.join(str(x % 10) for x in range(w)))
    for y, row in enumerate(canvas):
        print(f"{y:2d}" + ''.join(row))


# ---------------------------------------------------------------------------
def main() -> None:
    grid_raw = build_grid(RAW_MAP)
    # Inflate obstacles by 1 cell to keep the NAO body away from walls
    grid = inflate_obstacles(grid_raw, radius=1)

    start = (0, 0)

    # 5 delivery orders; each order has a pickup point and a dropoff point
    # (chosen so they are not blocked by obstacle-inflation)
    orders = [
        Order(pickup=(2, 1),  dropoff=(18, 1),  label="A"),
        Order(pickup=(0, 12), dropoff=(15, 13), label="B"),
        Order(pickup=(8, 0),  dropoff=(8, 14),  label="C"),
        Order(pickup=(19, 7), dropoff=(0, 9),   label="D"),
        Order(pickup=(13, 0), dropoff=(12, 10), label="E"),
    ]

    config = GAConfig(
        pop_size=80,
        max_gen=300,
        crossover_rate=0.85,
        mutation_rate=0.20,
        tournament_k=3,
        elitism_ratio=0.05,
        early_stop_gen=60,
        seed=42,
    )

    print(f"Environment: {len(grid[0])}x{len(grid)} grid (after obstacle inflation)")
    print(f"Start: {start}")
    print(f"Orders: {len(orders)}")
    for o in orders:
        print(f"  Order {o.label}: pickup={o.pickup}, dropoff={o.dropoff}")
    print()

    print("Running Genetic Algorithm...")
    result = run_ga(grid, start, orders, config)

    print()
    print("=" * 60)
    print("RESULT")
    print("=" * 60)
    print(f"Generations run     : {result.generations_run}")
    print(f"Total distance      : {result.total_distance:.2f} cells")
    print(f"Optimal task order  : {chromosome_to_label(result.best_sequence, orders)}")
    print(f"Waypoint route      : {result.best_route}")
    print()

    # Show the convergence curve (sampled)
    if result.history:
        print("Convergence (best distance per generation, every 10 gens):")
        for g in range(0, len(result.history), max(1, len(result.history) // 10)):
            print(f"  gen {g:3d}: {result.history[g]:.2f}")
        print(f"  gen {len(result.history) - 1:3d}: {result.history[-1]:.2f}")
        print()

    # Expand the full A* path between waypoints
    full_path = expand_full_path(grid, result.best_route)
    print(f"Full A* path length (cells): {len(full_path)}")
    print()
    print("Map (S=start, 0..n=waypoints in visit order, ·=A* path, #=obstacle):")
    print_grid_with_route(grid, result.best_route, full_path)


if __name__ == "__main__":
    main()
