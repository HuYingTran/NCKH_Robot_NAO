# -*- coding: utf-8 -*-
"""
evaluate.py
Run a battery of experiments and emit evaluation charts for the GA + A*
planner used by the NAO delivery system.

Charts produced (saved to ./charts/*.png):

  GA-1  ga_convergence.png        : best / mean / worst distance per generation
  GA-2  ga_vs_baselines.png       : GA vs Greedy vs Random across many seeds
  GA-3  ga_scaling.png            : total distance and runtime vs n_orders
  GA-4  ga_param_sensitivity.png  : effect of population size and mutation rate
  AS-1  astar_runtime_density.png : A* runtime / cells-expanded vs obstacle density
  AS-2  astar_path_quality.png    : actual path length vs Octile lower-bound
  AS-3  astar_breakdown.png       : runtime breakdown of the full pipeline

Run:
    python evaluate.py
"""
from __future__ import annotations

import os
import random
import statistics
import time
from typing import List, Tuple

import matplotlib.pyplot as plt
import numpy as np

# DejaVu Sans (matplotlib default) supports Vietnamese diacritics; keep it
# explicit so future font changes don't break Vietnamese rendering.
plt.rcParams["font.family"] = ["DejaVu Sans", "Segoe UI", "Arial"]
plt.rcParams["axes.unicode_minus"] = False

from astar import astar, astar_with_stats, inflate_obstacles, octile, path_length
from ga_planner import (
    GAConfig,
    Order,
    build_distance_matrix,
    build_distance_matrix_octile,
    evaluate,
    expand_full_path,
    greedy_chromosome,
    precedence_repair,
    random_valid_chromosome,
    run_ga,
)
from gui import generate_random_obstacles, random_free_point

CHARTS_DIR = "charts"
os.makedirs(CHARTS_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Seed control
# ---------------------------------------------------------------------------
# When _RANDOM_MODE is True, all hard-coded seeds are replaced by fresh
# integers derived from a SystemRandom-seeded RNG → charts truly change
# every run. When False (default), the deterministic seeds are used so a
# paper's reviewer can reproduce the figures exactly.
_RANDOM_MODE = False
_SEED_GEN = random.Random()


def set_random_mode(flag: bool):
    """Toggle global random-seed mode."""
    global _RANDOM_MODE, _SEED_GEN
    _RANDOM_MODE = bool(flag)
    if _RANDOM_MODE:
        _SEED_GEN = random.Random(random.SystemRandom().randrange(2**31))
    else:
        _SEED_GEN = random.Random(0)


def _seed(default: int) -> int:
    """Return either the fixed default seed or a fresh random one."""
    if _RANDOM_MODE:
        return _SEED_GEN.randrange(0, 2**30)
    return default


# ---------------------------------------------------------------------------
# Common helpers
# ---------------------------------------------------------------------------
def make_problem(seed, n_orders, n_obstacles=20):
    """
    Build a deterministic 100×100 environment with `n_orders` random orders.
    All chosen pickup/dropoff cells are guaranteed to be A*-reachable from
    the start, so the (1+2n)×(1+2n) distance matrix has no infinities.
    """
    rng = random.Random(seed)
    grid_raw = generate_random_obstacles(n_obstacles, seed=seed)
    grid = inflate_obstacles(grid_raw, radius=1)
    for y in range(3):
        for x in range(3):
            grid_raw[y][x] = 0
            grid[y][x] = 0
    start = (0, 0)
    used = {start}
    orders = []
    for k in range(n_orders):
        # pick reachable pickup
        for _ in range(500):
            p = random_free_point(grid, rng, exclude=used)
            if astar(grid, start, p) is not None:
                break
        else:
            raise RuntimeError(
                f"make_problem: pickup #{k+1} unreachable after 500 tries")
        used.add(p)
        for _ in range(500):
            d = random_free_point(grid, rng, exclude=used)
            if astar(grid, start, d) is not None:
                break
        else:
            raise RuntimeError(
                f"make_problem: dropoff #{k+1} unreachable after 500 tries")
        used.add(d)
        orders.append(Order(pickup=p, dropoff=d, label=str(k + 1)))
    return grid, start, orders


def baseline_random(start, orders, dist_matrix, point_to_task, rng):
    n = len(orders)
    chrom = random_valid_chromosome(n, rng)
    return evaluate(chrom, dist_matrix, point_to_task, 0)


def baseline_greedy(start, orders, dist_matrix, point_to_task):
    n = len(orders)
    chrom = greedy_chromosome(0, n, dist_matrix, point_to_task)
    return evaluate(chrom, dist_matrix, point_to_task, 0)


def build_pdp_matrix(grid, start, orders, method="astar"):
    """Build the (1+2n) x (1+2n) distance matrix and the point_to_task map."""
    points = [start]
    point_to_task = {}
    for k, o in enumerate(orders):
        points.append(o.pickup); point_to_task[2 * k] = len(points) - 1
        points.append(o.dropoff); point_to_task[2 * k + 1] = len(points) - 1
    if method == "octile":
        return build_distance_matrix_octile(points), point_to_task
    return build_distance_matrix(grid, points), point_to_task


# ---------------------------------------------------------------------------
# GA-1: convergence curve over multiple independent runs
# ---------------------------------------------------------------------------
def chart_ga_convergence(n_runs=5, n_orders=8):
    base_seed = _seed(11)
    grid, start, orders = make_problem(seed=base_seed,
                                       n_orders=n_orders, n_obstacles=20)

    histories = []
    final_bests = []
    for run in range(n_runs):
        run_seed = _seed(11 + run * 7919)  # truly independent seed per run
        cfg = GAConfig(pop_size=80, max_gen=300, mutation_rate=0.20,
                       early_stop_gen=400,
                       seed=run_seed,
                       distance_method="astar")
        res = run_ga(grid, start, orders, cfg)
        histories.append(res.history)
        final_bests.append(res.total_distance)

    # pad each history to the same length for the mean curve
    max_len = max(len(h) for h in histories)
    padded = np.array([h + [h[-1]] * (max_len - len(h)) for h in histories])
    mean_curve = padded.mean(axis=0)
    std_curve = padded.std(axis=0)
    gens = np.arange(1, max_len + 1)

    fig, ax = plt.subplots(figsize=(9, 5))
    for i, h in enumerate(histories):
        ax.plot(range(1, len(h) + 1), h, color="#1f77b4",
                lw=0.9, alpha=0.35,
                label="Lần chạy đơn lẻ" if i == 0 else None)
    ax.fill_between(gens, mean_curve - std_curve, mean_curve + std_curve,
                    color="#1f77b4", alpha=0.18, label="±1 độ lệch chuẩn")
    ax.plot(gens, mean_curve, color="#1f77b4", lw=2.4,
            label=f"Trung bình {n_runs} lần chạy")

    ax.set_xlabel("Thế hệ")
    ax.set_ylabel("Tổng quãng đường tốt nhất (ô)")
    mode_tag = "ngẫu nhiên" if _RANDOM_MODE else "tái lập (seed cố định)"
    ax.set_title(f"GA-1: Đường cong hội tụ — {n_runs} lần chạy độc lập  "
                 f"(n_đơn hàng={n_orders}, mode {mode_tag})")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "ga_convergence.png"), dpi=150)
    plt.close(fig)
    print(f"[GA-1] saved ga_convergence.png   "
          f"finals={[round(x,1) for x in final_bests]}  "
          f"mean={statistics.mean(final_bests):.2f}±"
          f"{statistics.stdev(final_bests):.2f}")


# ---------------------------------------------------------------------------
# GA-2: GA vs Greedy vs Random (multiple seeds, boxplot)
# ---------------------------------------------------------------------------
def chart_ga_vs_baselines(n_orders=6, n_seeds=15):
    ga_vals, greedy_vals, random_vals = [], [], []
    base = _seed(0)
    for k in range(n_seeds):
        seed = base + k
        grid, start, orders = make_problem(seed=seed, n_orders=n_orders,
                                           n_obstacles=20)
        dm, p2t = build_pdp_matrix(grid, start, orders, method="astar")
        rng = random.Random(seed)

        cfg = GAConfig(pop_size=60, max_gen=200, mutation_rate=0.20,
                       early_stop_gen=60, seed=seed, distance_method="astar")
        res = run_ga(grid, start, orders, cfg)
        ga_vals.append(res.total_distance)
        greedy_vals.append(baseline_greedy(start, orders, dm, p2t))
        # average of 5 random restarts to reduce variance
        rnd = [baseline_random(start, orders, dm, p2t, rng) for _ in range(5)]
        random_vals.append(statistics.mean(rnd))

    fig, ax = plt.subplots(figsize=(8, 5))
    bp = ax.boxplot([ga_vals, greedy_vals, random_vals],
                    tick_labels=["GA (đề xuất)", "Tham lam (NN)", "Ngẫu nhiên"],
                    patch_artist=True, widths=0.55)
    colors = ["#1f77b4", "#2ca02c", "#d62728"]
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c); patch.set_alpha(0.5)
    ax.set_ylabel("Tổng quãng đường (ô)")
    ax.set_title(f"GA-2: GA so với phương pháp tham chiếu  "
                 f"(n_đơn hàng={n_orders}, {n_seeds} lần thử)")
    ax.grid(axis="y", alpha=0.3)

    medians = [statistics.median(v) for v in (ga_vals, greedy_vals, random_vals)]
    for i, m in enumerate(medians, start=1):
        ax.text(i, m, f" trung vị={m:.1f}", va="center")

    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "ga_vs_baselines.png"), dpi=150)
    plt.close(fig)
    ga_avg = statistics.mean(ga_vals); gr_avg = statistics.mean(greedy_vals)
    rd_avg = statistics.mean(random_vals)
    print(f"[GA-2] saved ga_vs_baselines.png   "
          f"GA={ga_avg:.1f} | Greedy={gr_avg:.1f} | Random={rd_avg:.1f}  "
          f"(GA better than Greedy by {(gr_avg-ga_avg)/gr_avg*100:.1f}%, "
          f"than Random by {(rd_avg-ga_avg)/rd_avg*100:.1f}%)")


# ---------------------------------------------------------------------------
# GA-3: scaling with n_orders (multi-seed → error bars)
# ---------------------------------------------------------------------------
def chart_ga_scaling(n_seeds=3):
    sizes = [3, 5, 7, 10, 13]
    dist_mean, dist_std = [], []
    time_mean, time_std = [], []
    base = _seed(99)
    for n in sizes:
        ds, ts = [], []
        for k in range(n_seeds):
            seed = base + k * 1000 + n
            grid, start, orders = make_problem(seed=seed, n_orders=n,
                                               n_obstacles=20)
            cfg = GAConfig(pop_size=80, max_gen=300, mutation_rate=0.20,
                           early_stop_gen=80, seed=seed,
                           distance_method="astar")
            t0 = time.perf_counter()
            res = run_ga(grid, start, orders, cfg)
            ts.append(time.perf_counter() - t0)
            ds.append(res.total_distance)
        dist_mean.append(statistics.mean(ds))
        dist_std.append(statistics.stdev(ds) if len(ds) > 1 else 0.0)
        time_mean.append(statistics.mean(ts))
        time_std.append(statistics.stdev(ts) if len(ts) > 1 else 0.0)

    fig, ax1 = plt.subplots(figsize=(8, 5))
    ax1.errorbar(sizes, dist_mean, yerr=dist_std, fmt="o-",
                 color="#1f77b4", lw=2, capsize=4,
                 label="Quãng đường tốt nhất")
    ax1.set_xlabel("Số đơn hàng (n)")
    ax1.set_ylabel("Tổng quãng đường (ô)", color="#1f77b4")
    ax1.tick_params(axis="y", labelcolor="#1f77b4")
    ax1.grid(alpha=0.3)
    ax2 = ax1.twinx()
    ax2.errorbar(sizes, time_mean, yerr=time_std, fmt="s--",
                 color="#d62728", lw=1.5, capsize=4,
                 label="Thời gian GA (s)")
    ax2.set_ylabel("Thời gian chạy (s)", color="#d62728")
    ax2.tick_params(axis="y", labelcolor="#d62728")
    ax1.set_title(f"GA-3: Khả năng mở rộng theo kích thước bài toán  "
                  f"({n_seeds} seed/mức)")
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "ga_scaling.png"), dpi=150)
    plt.close(fig)
    print(f"[GA-3] saved ga_scaling.png   sizes={sizes}, "
          f"distances={[round(d,1) for d in dist_mean]} (±std)")


# ---------------------------------------------------------------------------
# GA-4: parameter sensitivity (population size and mutation rate)
# ---------------------------------------------------------------------------
def chart_ga_param_sensitivity(n_orders=6, n_seeds=5):
    pop_sizes = [20, 40, 80, 160]
    mut_rates = [0.05, 0.10, 0.20, 0.40]

    pop_results = {p: [] for p in pop_sizes}
    mut_results = {m: [] for m in mut_rates}

    base = _seed(0)
    for k in range(n_seeds):
        seed = base + k
        grid, start, orders = make_problem(seed=seed, n_orders=n_orders,
                                           n_obstacles=20)
        for p in pop_sizes:
            cfg = GAConfig(pop_size=p, max_gen=200, mutation_rate=0.20,
                           early_stop_gen=60, seed=seed,
                           distance_method="astar")
            res = run_ga(grid, start, orders, cfg)
            pop_results[p].append(res.total_distance)
        for m in mut_rates:
            cfg = GAConfig(pop_size=60, max_gen=200, mutation_rate=m,
                           early_stop_gen=60, seed=seed,
                           distance_method="astar")
            res = run_ga(grid, start, orders, cfg)
            mut_results[m].append(res.total_distance)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    axes[0].errorbar(pop_sizes,
                     [statistics.mean(pop_results[p]) for p in pop_sizes],
                     yerr=[statistics.stdev(pop_results[p]) for p in pop_sizes],
                     marker="o", color="#1f77b4", capsize=4)
    axes[0].set_xlabel("Kích thước quần thể")
    axes[0].set_ylabel("Quãng đường tốt nhất (mean ± std)")
    axes[0].set_title("Ảnh hưởng của kích thước quần thể")
    axes[0].grid(alpha=0.3)

    axes[1].errorbar(mut_rates,
                     [statistics.mean(mut_results[m]) for m in mut_rates],
                     yerr=[statistics.stdev(mut_results[m]) for m in mut_rates],
                     marker="s", color="#d62728", capsize=4)
    axes[1].set_xlabel("Tỷ lệ đột biến")
    axes[1].set_ylabel("Quãng đường tốt nhất (mean ± std)")
    axes[1].set_title("Ảnh hưởng của tỷ lệ đột biến")
    axes[1].grid(alpha=0.3)

    fig.suptitle(f"GA-4: Khảo sát độ nhạy tham số  "
                 f"(n_đơn hàng={n_orders}, {n_seeds} lần thử)")
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "ga_param_sensitivity.png"), dpi=150)
    plt.close(fig)
    print("[GA-4] saved ga_param_sensitivity.png")


# ---------------------------------------------------------------------------
# AS-1: A* runtime / cells-expanded vs obstacle density
# ---------------------------------------------------------------------------
def chart_astar_runtime_density():
    densities = [0, 5, 10, 20, 35, 50, 70]
    n_queries = 25
    times = []
    expanded = []
    base = _seed(0)

    for density in densities:
        ts, exs = [], []
        for q in range(n_queries):
            seed = base + density * 1000 + q
            rng = random.Random(seed)
            grid_raw = generate_random_obstacles(density, seed=seed)
            grid = inflate_obstacles(grid_raw, radius=1)
            for y in range(3):
                for x in range(3):
                    grid[y][x] = 0
            try:
                a = random_free_point(grid, rng)
                b = random_free_point(grid, rng, exclude={a})
            except RuntimeError:
                continue
            path, st = astar_with_stats(grid, a, b)
            if path is not None:
                ts.append(st["time_ms"])
                exs.append(st["expanded"])
        times.append(statistics.mean(ts) if ts else 0.0)
        expanded.append(statistics.mean(exs) if exs else 0.0)

    fig, ax1 = plt.subplots(figsize=(8, 5))
    ax1.plot(densities, times, "o-", color="#1f77b4", lw=2,
             label="Thời gian (ms)")
    ax1.set_xlabel("Số khối vật cản")
    ax1.set_ylabel("Thời gian trung bình (ms)", color="#1f77b4")
    ax1.tick_params(axis="y", labelcolor="#1f77b4")
    ax1.grid(alpha=0.3)
    ax2 = ax1.twinx()
    ax2.plot(densities, expanded, "s--", color="#2ca02c", lw=1.5,
             label="Số ô mở rộng")
    ax2.set_ylabel("Số ô trung bình mở rộng", color="#2ca02c")
    ax2.tick_params(axis="y", labelcolor="#2ca02c")
    ax1.set_title(f"AS-1: Chi phí A* theo độ phức tạp bản đồ  "
                  f"({n_queries} truy vấn / mức)")
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "astar_runtime_density.png"), dpi=150)
    plt.close(fig)
    print("[AS-1] saved astar_runtime_density.png")


# ---------------------------------------------------------------------------
# AS-2: actual path length vs Octile lower-bound (path quality)
# ---------------------------------------------------------------------------
def chart_astar_path_quality(n_queries=200, n_obstacles=25):
    seed = _seed(7)
    grid_raw = generate_random_obstacles(n_obstacles, seed=seed)
    grid = inflate_obstacles(grid_raw, radius=1)
    for y in range(3):
        for x in range(3):
            grid[y][x] = 0
    rng = random.Random(seed)

    octile_d, actual_d, ratios = [], [], []
    for _ in range(n_queries):
        try:
            a = random_free_point(grid, rng)
            b = random_free_point(grid, rng, exclude={a})
        except RuntimeError:
            continue
        path = astar(grid, a, b)
        if path is None:
            continue
        actual = path_length(path)
        oct_d = octile(a, b)
        if oct_d < 1e-6:
            continue
        octile_d.append(oct_d)
        actual_d.append(actual)
        ratios.append(actual / oct_d)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    axes[0].scatter(octile_d, actual_d, alpha=0.5, s=15, color="#1f77b4")
    lim = max(max(octile_d), max(actual_d))
    axes[0].plot([0, lim], [0, lim], "--", color="#d62728",
                 label="y = x (không vòng)")
    axes[0].set_xlabel("Khoảng cách Octile (cận dưới)")
    axes[0].set_ylabel("Độ dài đường A* thực tế")
    axes[0].set_title("Đường thực tế so với cận dưới")
    axes[0].grid(alpha=0.3); axes[0].legend()

    axes[1].hist(ratios, bins=25, color="#2ca02c", alpha=0.75,
                 edgecolor="black")
    axes[1].axvline(1.0, color="#d62728", linestyle="--", label="tỷ số = 1.0")
    axes[1].set_xlabel("Tỷ số vòng  (thực tế / Octile)")
    axes[1].set_ylabel("Tần suất")
    axes[1].set_title(f"Phân bố tỷ số vòng  "
                      f"(trung bình={statistics.mean(ratios):.3f})")
    axes[1].grid(alpha=0.3); axes[1].legend()

    fig.suptitle(f"AS-2: Chất lượng đường đi A*  ({len(ratios)} truy vấn, "
                 f"{n_obstacles} khối vật cản)")
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "astar_path_quality.png"), dpi=150)
    plt.close(fig)
    print(f"[AS-2] saved astar_path_quality.png   "
          f"mean detour ratio={statistics.mean(ratios):.3f}")


# ---------------------------------------------------------------------------
# AS-3: full pipeline runtime breakdown (multi-run → error bars)
# ---------------------------------------------------------------------------
def chart_astar_breakdown(n_orders=8, n_runs=5):
    base = _seed(42)
    times_dm, times_ga, times_ast = [], [], []
    for k in range(n_runs):
        seed = base + k
        grid, start, orders = make_problem(seed=seed, n_orders=n_orders,
                                           n_obstacles=20)
        t0 = time.perf_counter()
        dm, p2t = build_pdp_matrix(grid, start, orders, method="astar")
        times_dm.append(time.perf_counter() - t0)

        # GA loop only (Octile distance ⇒ matrix cost ~ 0)
        t0 = time.perf_counter()
        res = run_ga(grid, start, orders,
                     GAConfig(pop_size=80, max_gen=300, mutation_rate=0.20,
                              early_stop_gen=80, seed=seed,
                              distance_method="octile"))
        times_ga.append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        expand_full_path(grid, res.best_route)
        times_ast.append(time.perf_counter() - t0)

    parts = ["Ma trận khoảng cách A*", "Vòng lặp GA", "Mở rộng A*"]
    means = [statistics.mean(x) for x in (times_dm, times_ga, times_ast)]
    stds = [statistics.stdev(x) if len(x) > 1 else 0.0
            for x in (times_dm, times_ga, times_ast)]
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(parts, means, yerr=stds, color=colors, edgecolor="black",
                  capsize=6, error_kw=dict(elinewidth=1.4))
    for b, m, s in zip(bars, means, stds):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + s + 0.01,
                f"{m*1000:.0f} ± {s*1000:.0f} ms",
                ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("Thời gian chạy (s)")
    ax.set_title(f"AS-3: Phân bổ thời gian pipeline  "
                 f"(n_đơn hàng={n_orders}, {n_runs} lần chạy)")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, "astar_breakdown.png"), dpi=150)
    plt.close(fig)
    total = sum(means)
    print(f"[AS-3] saved astar_breakdown.png   "
          f"matrix={means[0]:.2f}±{stds[0]:.2f}s  "
          f"GA={means[1]:.2f}±{stds[1]:.2f}s  "
          f"expansion={means[2]:.2f}±{stds[2]:.2f}s  "
          f"total≈{total:.2f}s")


# ---------------------------------------------------------------------------
def main(random_mode: bool = False):
    set_random_mode(random_mode)
    mode_tag = "NGẪU NHIÊN (mỗi lần khác nhau)" if random_mode \
        else "TÁI LẬP (seed cố định)"
    print(f"Saving charts into ./{CHARTS_DIR}/   [mode: {mode_tag}]")
    chart_ga_convergence()
    chart_ga_vs_baselines()
    chart_ga_scaling()
    chart_ga_param_sensitivity()
    chart_astar_runtime_density()
    chart_astar_path_quality()
    chart_astar_breakdown()
    print(f"\nDone. Open the .png files in '{CHARTS_DIR}/' to view all charts.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Run GA + A* evaluation experiments and emit charts.")
    parser.add_argument("--random", action="store_true",
                        help="Use fresh seeds each run (charts will differ "
                             "every time). Default = deterministic.")
    args = parser.parse_args()
    main(random_mode=args.random)
