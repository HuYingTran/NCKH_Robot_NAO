# -*- coding: utf-8 -*-
"""
visualize.py
Graphical simulation of the NAO delivery problem:
- Static plot showing obstacles, waypoints, GA-optimal task order and full A* path.
- Animation showing the robot moving cell-by-cell along the planned path.

Usage:
    python visualize.py            # static figure + animation
    python visualize.py --static   # only static figure (faster)
"""
from __future__ import annotations

import argparse
import sys

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from astar import inflate_obstacles
from ga_planner import (
    GAConfig,
    Order,
    chromosome_to_label,
    expand_full_path,
    run_ga,
    task_is_pickup,
    task_order_id,
)
from main_demo import RAW_MAP, build_grid


def make_environment():
    grid_raw = build_grid(RAW_MAP)
    grid = inflate_obstacles(grid_raw, radius=1)
    start = (0, 0)
    orders = [
        Order(pickup=(2, 1),  dropoff=(18, 1),  label="A"),
        Order(pickup=(0, 12), dropoff=(15, 13), label="B"),
        Order(pickup=(8, 0),  dropoff=(8, 14),  label="C"),
        Order(pickup=(19, 7), dropoff=(0, 9),   label="D"),
        Order(pickup=(13, 0), dropoff=(12, 10), label="E"),
    ]
    return grid_raw, grid, start, orders


def draw_grid(ax, grid_raw, grid_inflated):
    """Draw obstacles (dark) and inflation halo (light)."""
    h = len(grid_raw)
    w = len(grid_raw[0])
    for y in range(h):
        for x in range(w):
            if grid_raw[y][x] == 1:
                ax.add_patch(mpatches.Rectangle((x, y), 1, 1,
                                                facecolor="#222222",
                                                edgecolor="none"))
            elif grid_inflated[y][x] == 1:
                ax.add_patch(mpatches.Rectangle((x, y), 1, 1,
                                                facecolor="#cccccc",
                                                edgecolor="none"))
    ax.set_xlim(0, w)
    ax.set_ylim(h, 0)              # invert Y so (0,0) is top-left
    ax.set_aspect("equal")
    ax.set_xticks(range(0, w + 1, 2))
    ax.set_yticks(range(0, h + 1, 2))
    ax.grid(True, color="#dddddd", linewidth=0.5)


def color_for_order(label):
    palette = {
        "A": "#1f77b4", "B": "#2ca02c", "C": "#d62728",
        "D": "#9467bd", "E": "#ff7f0e",
    }
    return palette.get(label, "#444444")


def draw_orders(ax, orders):
    """Pickup = circle, dropoff = square. Same color per order."""
    for o in orders:
        c = color_for_order(o.label)
        px, py = o.pickup
        dx, dy = o.dropoff
        ax.add_patch(mpatches.Circle((px + 0.5, py + 0.5), 0.35,
                                     facecolor=c, edgecolor="black", lw=1.2))
        ax.add_patch(mpatches.Rectangle((dx + 0.15, dy + 0.15), 0.7, 0.7,
                                        facecolor=c, edgecolor="black", lw=1.2))
        ax.text(px + 0.5, py + 0.5, f"P{o.label}", ha="center", va="center",
                fontsize=7, color="white", fontweight="bold")
        ax.text(dx + 0.5, dy + 0.5, f"D{o.label}", ha="center", va="center",
                fontsize=7, color="white", fontweight="bold")


def plot_static(grid_raw, grid, start, orders, result, full_path):
    fig, axes = plt.subplots(1, 2, figsize=(15, 7),
                             gridspec_kw={"width_ratios": [3, 2]})

    # Left: route on the map
    ax = axes[0]
    draw_grid(ax, grid_raw, grid)
    draw_orders(ax, orders)

    # Start
    sx, sy = start
    ax.add_patch(mpatches.RegularPolygon((sx + 0.5, sy + 0.5), 3, radius=0.4,
                                         orientation=0, facecolor="gold",
                                         edgecolor="black", lw=1.5))
    ax.text(sx + 0.5, sy - 0.25, "Start", ha="center", fontsize=8)

    # Full A* path
    xs = [p[0] + 0.5 for p in full_path]
    ys = [p[1] + 0.5 for p in full_path]
    ax.plot(xs, ys, "-", color="#2ca02c", lw=2.0, alpha=0.7, label="A* path")

    # Visit-order numbers on waypoints
    for idx, (x, y) in enumerate(result.best_route[1:], start=1):
        ax.annotate(str(idx), (x + 0.5, y + 0.5), color="white",
                    fontsize=8, fontweight="bold",
                    ha="center", va="center")

    legend = [
        mpatches.Patch(color="#222222", label="Obstacle"),
        mpatches.Patch(color="#cccccc", label="Inflated buffer"),
        mpatches.Circle((0, 0), 0.3, facecolor="#1f77b4", label="Pickup"),
        mpatches.Rectangle((0, 0), 1, 1, facecolor="#1f77b4", label="Dropoff"),
        plt.Line2D([0], [0], color="#2ca02c", lw=2, label="A* path"),
    ]
    ax.legend(handles=legend, loc="lower right", fontsize=8)
    ax.set_title(f"GA + A* route   (total = {result.total_distance:.2f} cells, "
                 f"{len(full_path)} steps)")

    # Right: convergence curve
    ax2 = axes[1]
    ax2.plot(result.history, color="#1f77b4")
    ax2.set_xlabel("Generation")
    ax2.set_ylabel("Best total distance (cells)")
    ax2.set_title("GA Convergence")
    ax2.grid(True, alpha=0.3)

    fig.suptitle("NAO Delivery — GA + A* Simulation", fontsize=13, fontweight="bold")
    plt.tight_layout()
    return fig


def animate(grid_raw, grid, start, orders, result, full_path):
    fig, ax = plt.subplots(figsize=(11, 8))
    draw_grid(ax, grid_raw, grid)
    draw_orders(ax, orders)

    sx, sy = start
    ax.add_patch(mpatches.RegularPolygon((sx + 0.5, sy + 0.5), 3, radius=0.4,
                                         orientation=0, facecolor="gold",
                                         edgecolor="black", lw=1.5))

    # Trail line + robot dot
    trail_line, = ax.plot([], [], "-", color="#2ca02c", lw=2.2, alpha=0.8)
    robot = mpatches.Circle((sx + 0.5, sy + 0.5), 0.35,
                            facecolor="#d62728", edgecolor="black", lw=1.5,
                            zorder=5)
    ax.add_patch(robot)

    # Status text
    status_txt = ax.text(0.02, 0.98, "", transform=ax.transAxes,
                         fontsize=10, va="top", ha="left",
                         bbox=dict(facecolor="white", alpha=0.85,
                                   edgecolor="#888888"))

    # Map each waypoint position to the action text it triggers
    waypoint_actions = {}
    for t_idx, t in enumerate(result.best_sequence):
        order = orders[task_order_id(t)]
        action = (f"Pickup {order.label}" if task_is_pickup(t)
                  else f"Deliver {order.label}")
        waypoint_actions[result.best_route[t_idx + 1]] = action

    xs_full = [p[0] + 0.5 for p in full_path]
    ys_full = [p[1] + 0.5 for p in full_path]

    def init():
        trail_line.set_data([], [])
        robot.center = (sx + 0.5, sy + 0.5)
        status_txt.set_text("Ready to depart...")
        return trail_line, robot, status_txt

    def update(i):
        trail_line.set_data(xs_full[:i + 1], ys_full[:i + 1])
        cx, cy = full_path[i]
        robot.center = (cx + 0.5, cy + 0.5)

        action = waypoint_actions.get((cx, cy))
        if action:
            status_txt.set_text(f"Step {i+1}/{len(full_path)}\n>> {action} at ({cx},{cy})")
        else:
            status_txt.set_text(f"Step {i+1}/{len(full_path)}\nMoving toward next waypoint")
        return trail_line, robot, status_txt

    ax.set_title("NAO Delivery Animation — GA task order + A* paths")
    anim = FuncAnimation(fig, update, frames=len(full_path),
                         init_func=init, blit=False,
                         interval=180, repeat=False)
    plt.tight_layout()
    return fig, anim


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--static", action="store_true",
                        help="Only show the static figure (skip animation).")
    parser.add_argument("--save", type=str, default=None,
                        help="Optional path to save the static figure (e.g. result.png).")
    args = parser.parse_args()

    grid_raw, grid, start, orders = make_environment()

    print("Running GA...")
    config = GAConfig(pop_size=80, max_gen=300, mutation_rate=0.2,
                      early_stop_gen=60, seed=42)
    result = run_ga(grid, start, orders, config)
    print(f"  best total distance: {result.total_distance:.2f}")
    print(f"  task order: {chromosome_to_label(result.best_sequence, orders)}")

    full_path = expand_full_path(grid, result.best_route)

    fig_static = plot_static(grid_raw, grid, start, orders, result, full_path)
    if args.save:
        fig_static.savefig(args.save, dpi=150, bbox_inches="tight")
        print(f"Saved static figure: {args.save}")

    if not args.static:
        fig_anim, _ = animate(grid_raw, grid, start, orders, result, full_path)

    plt.show()


if __name__ == "__main__":
    sys.exit(main() or 0)
