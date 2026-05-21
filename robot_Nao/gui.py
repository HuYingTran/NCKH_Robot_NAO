# -*- coding: utf-8 -*-
"""
gui.py  —  Trung tâm điều khiển GUI cho robot NAO
Tất cả thao tác xoay quanh giao diện này:
  • Cấu hình bài toán (map 100×100, đơn hàng, vật cản)
  • Chạy GA (Bước 1) và A* (Bước 2)
  • Mô phỏng (animation robot di chuyển trên bản đồ)
  • Chạy thật trên NAO (NAOqi / qi-framework, có chế độ FAKE)
  • Xuất biểu đồ đánh giá GA & A*

Run:
    python gui.py
"""
from __future__ import annotations

import os
import random
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

import numpy as np
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk,
)
from matplotlib.figure import Figure

from astar import inflate_obstacles, path_length
from ga_planner import (
    GAConfig,
    Order,
    expand_full_path,
    run_ga,
    task_is_pickup,
    task_order_id,
)
from nao_controller import NaoController

MAP_W = 100
MAP_H = 100

PALETTE = [
    "#1f77b4", "#2ca02c", "#d62728", "#9467bd", "#ff7f0e",
    "#17becf", "#bcbd22", "#8c564b", "#e377c2", "#7f7f7f",
    "#393b79", "#637939", "#8c6d31", "#843c39", "#7b4173",
    "#5254a3", "#8ca252", "#bd9e39", "#ad494a", "#a55194",
]


# ---------------------------------------------------------------------------
# Random environment helpers
# ---------------------------------------------------------------------------
def generate_random_obstacles(n_blocks, min_size=4, max_size=12, seed=None):
    rng = random.Random(seed)
    grid = [[0] * MAP_W for _ in range(MAP_H)]
    for _ in range(n_blocks):
        bw = rng.randint(min_size, max_size)
        bh = rng.randint(min_size, max_size)
        bx = rng.randint(0, MAP_W - bw)
        by = rng.randint(0, MAP_H - bh)
        for y in range(by, by + bh):
            for x in range(bx, bx + bw):
                grid[y][x] = 1
    return grid


def random_free_point(grid_inflated, rng, exclude=None, max_tries=5000):
    exclude = exclude or set()
    for _ in range(max_tries):
        x = rng.randint(0, MAP_W - 1)
        y = rng.randint(0, MAP_H - 1)
        if (x, y) not in exclude and grid_inflated[y][x] == 0:
            return (x, y)
    raise RuntimeError("Không tìm thấy ô trống.")


def color_for(idx: int) -> str:
    return PALETTE[idx % len(PALETTE)]


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("NAO Delivery — GA + A* | Trung tâm điều khiển")
        self.root.geometry("1280x880")

        # ---- environment / planning state ----
        self.grid_raw = None
        self.grid_inflated = None
        self.start = (0, 0)
        self.orders = []
        self.unmatched_pickups = []
        self.unmatched_dropoffs = []
        self.result = None
        self.full_path = None
        self.actual_distance = 0.0

        # ---- simulation state ----
        self.sim_running = False
        self.sim_paused = False
        self.sim_index = 0
        self.sim_after_id = None
        self._robot_dot = None
        self._sim_msg = None  # text artist

        # ---- NAO state ----
        self.nao = NaoController()
        self.nao_running = False
        self._nao_stop_flag = False

        self._build_ui()
        self._draw_empty()

    # ------------------------------------------------------------ UI build
    def _build_ui(self):
        # left: notebook with tabs + status bar at the bottom
        left = ttk.Frame(self.root, padding=6)
        left.pack(side=tk.LEFT, fill=tk.Y)

        self.nb = ttk.Notebook(left, width=320)
        self.nb.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.tab_problem = ttk.Frame(self.nb, padding=10)
        self.tab_sim     = ttk.Frame(self.nb, padding=10)
        self.tab_nao     = ttk.Frame(self.nb, padding=10)
        self.tab_eval    = ttk.Frame(self.nb, padding=10)
        self.nb.add(self.tab_problem, text="📋 Bài toán")
        self.nb.add(self.tab_sim,     text="▶ Mô phỏng")
        self.nb.add(self.tab_nao,     text="🤖 NAO thật")
        self.nb.add(self.tab_eval,    text="📊 Đánh giá")

        self._build_tab_problem(self.tab_problem)
        self._build_tab_sim(self.tab_sim)
        self._build_tab_nao(self.tab_nao)
        self._build_tab_eval(self.tab_eval)

        ttk.Separator(left).pack(fill=tk.X, pady=4)
        ttk.Label(left, text="TRẠNG THÁI",
                  font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        self.status_var = tk.StringVar(value="Sẵn sàng. Hãy tạo môi trường.")
        ttk.Label(left, textvariable=self.status_var,
                  foreground="#1f4f8b", wraplength=300,
                  justify=tk.LEFT).pack(anchor=tk.W, pady=(2, 4))

        # right: matplotlib canvas
        right = ttk.Frame(self.root)
        right.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

        self.fig = Figure(figsize=(8.5, 8.5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(expand=True, fill=tk.BOTH)
        NavigationToolbar2Tk(self.canvas, right).update()

    # -------- Tab 1: Bài toán ----------
    def _build_tab_problem(self, p):
        ttk.Label(p, text="MÔI TRƯỜNG (100 × 100)",
                  font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)

        ttk.Label(p, text="Số điểm nhận hàng:").pack(anchor=tk.W, pady=(8, 0))
        self.var_pickups = tk.IntVar(value=5)
        ttk.Spinbox(p, from_=1, to=50, textvariable=self.var_pickups,
                    width=10).pack(anchor=tk.W)

        ttk.Label(p, text="Số điểm trả hàng:").pack(anchor=tk.W, pady=(6, 0))
        self.var_dropoffs = tk.IntVar(value=5)
        ttk.Spinbox(p, from_=1, to=50, textvariable=self.var_dropoffs,
                    width=10).pack(anchor=tk.W)

        ttk.Label(p, text="Số khối vật cản:").pack(anchor=tk.W, pady=(6, 0))
        self.var_obstacles = tk.IntVar(value=20)
        ttk.Spinbox(p, from_=0, to=120, textvariable=self.var_obstacles,
                    width=10).pack(anchor=tk.W)

        ttk.Label(p, text="Seed:").pack(anchor=tk.W, pady=(6, 0))
        self.var_seed = tk.IntVar(value=42)
        ttk.Entry(p, textvariable=self.var_seed, width=12).pack(anchor=tk.W)

        ttk.Separator(p).pack(fill=tk.X, pady=8)

        ttk.Label(p, text="THAM SỐ GA",
                  font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(p, text="Population:").pack(anchor=tk.W, pady=(4, 0))
        self.var_pop = tk.IntVar(value=80)
        ttk.Spinbox(p, from_=10, to=500, textvariable=self.var_pop,
                    width=10).pack(anchor=tk.W)
        ttk.Label(p, text="Số thế hệ tối đa:").pack(anchor=tk.W, pady=(6, 0))
        self.var_gen = tk.IntVar(value=200)
        ttk.Spinbox(p, from_=10, to=2000, textvariable=self.var_gen,
                    width=10).pack(anchor=tk.W)

        ttk.Separator(p).pack(fill=tk.X, pady=8)

        ttk.Button(p, text="🌍  Tạo môi trường",
                   command=self.action_generate).pack(fill=tk.X, pady=2)
        self.ga_btn = ttk.Button(p, text="① Bước 1: Chạy GA",
                                 command=self.action_run_ga)
        self.ga_btn.pack(fill=tk.X, pady=2)
        self.astar_btn = ttk.Button(p, text="② Bước 2: Chạy A*",
                                    command=self.action_run_astar,
                                    state=tk.DISABLED)
        self.astar_btn.pack(fill=tk.X, pady=2)
        ttk.Button(p, text="🧹  Reset",
                   command=self.action_reset).pack(fill=tk.X, pady=2)

    # -------- Tab 2: Mô phỏng ----------
    def _build_tab_sim(self, p):
        ttk.Label(p, text="MÔ PHỎNG ROBOT",
                  font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(p, text="Robot di chuyển dọc đường A* trên bản đồ.\n"
                          "Cần chạy xong Bước 2 (A*) trước.",
                  foreground="#555", justify=tk.LEFT,
                  wraplength=290).pack(anchor=tk.W, pady=(2, 8))

        ttk.Label(p, text="Tốc độ (số ô / giây):").pack(anchor=tk.W)
        self.var_sim_speed = tk.DoubleVar(value=20.0)
        ttk.Scale(p, from_=2.0, to=80.0, orient=tk.HORIZONTAL,
                  variable=self.var_sim_speed, length=260
                  ).pack(anchor=tk.W, pady=(2, 6))
        self.sim_speed_lbl = ttk.Label(p, text="20.0 ô/s")
        self.sim_speed_lbl.pack(anchor=tk.W)
        self.var_sim_speed.trace_add(
            "write",
            lambda *_: self.sim_speed_lbl.configure(
                text=f"{self.var_sim_speed.get():.1f} ô/s"))

        ttk.Separator(p).pack(fill=tk.X, pady=8)

        self.sim_play_btn = ttk.Button(p, text="▶  Phát",
                                       command=self.action_sim_play)
        self.sim_play_btn.pack(fill=tk.X, pady=2)
        self.sim_pause_btn = ttk.Button(p, text="⏸  Tạm dừng / tiếp tục",
                                        command=self.action_sim_pause,
                                        state=tk.DISABLED)
        self.sim_pause_btn.pack(fill=tk.X, pady=2)
        self.sim_stop_btn = ttk.Button(p, text="■  Dừng",
                                       command=self.action_sim_stop,
                                       state=tk.DISABLED)
        self.sim_stop_btn.pack(fill=tk.X, pady=2)

        ttk.Separator(p).pack(fill=tk.X, pady=8)
        ttk.Label(p, text="Tiến độ:").pack(anchor=tk.W)
        self.sim_progress = ttk.Progressbar(p, length=260, mode="determinate")
        self.sim_progress.pack(anchor=tk.W, pady=(2, 4))
        self.sim_msg_var = tk.StringVar(value="(chờ nhấn Phát)")
        ttk.Label(p, textvariable=self.sim_msg_var,
                  foreground="#1f4f8b",
                  wraplength=290, justify=tk.LEFT).pack(anchor=tk.W)

    # -------- Tab 3: NAO thật ----------
    def _build_tab_nao(self, p):
        ttk.Label(p, text="ĐIỀU KHIỂN NAO THẬT",
                  font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(p, text="Kết nối qua NAOqi/qi-framework.\n"
                          "Nếu SDK chưa cài → chế độ FAKE (in lệnh).",
                  foreground="#555", justify=tk.LEFT,
                  wraplength=290).pack(anchor=tk.W, pady=(2, 8))

        ttk.Label(p, text="IP của NAO:").pack(anchor=tk.W)
        self.var_nao_ip = tk.StringVar(value="127.0.0.1")
        ttk.Entry(p, textvariable=self.var_nao_ip, width=20
                  ).pack(anchor=tk.W, pady=(2, 6))

        ttk.Label(p, text="Cổng:").pack(anchor=tk.W)
        self.var_nao_port = tk.IntVar(value=9559)
        ttk.Entry(p, textvariable=self.var_nao_port, width=10
                  ).pack(anchor=tk.W, pady=(2, 6))

        ttk.Label(p, text="Kích thước 1 ô lưới (mét):").pack(anchor=tk.W)
        self.var_cell_m = tk.DoubleVar(value=0.10)
        ttk.Spinbox(p, from_=0.02, to=1.0, increment=0.01,
                    textvariable=self.var_cell_m, width=10
                    ).pack(anchor=tk.W, pady=(2, 6))

        self.var_nao_fake = tk.BooleanVar(value=True)
        ttk.Checkbutton(p, text="Bắt buộc chế độ FAKE (chỉ in lệnh)",
                        variable=self.var_nao_fake
                        ).pack(anchor=tk.W, pady=(4, 6))

        ttk.Separator(p).pack(fill=tk.X, pady=6)

        self.nao_connect_btn = ttk.Button(p, text="🔌  Kết nối NAO",
                                          command=self.action_nao_connect)
        self.nao_connect_btn.pack(fill=tk.X, pady=2)
        self.nao_run_btn = ttk.Button(p, text="🚶  Chạy thật theo đường A*",
                                      command=self.action_nao_run,
                                      state=tk.DISABLED)
        self.nao_run_btn.pack(fill=tk.X, pady=2)
        self.nao_stop_btn = ttk.Button(p, text="🛑  Dừng khẩn",
                                       command=self.action_nao_stop,
                                       state=tk.DISABLED)
        self.nao_stop_btn.pack(fill=tk.X, pady=2)
        self.nao_disconnect_btn = ttk.Button(p, text="❌  Ngắt kết nối",
                                             command=self.action_nao_disconnect,
                                             state=tk.DISABLED)
        self.nao_disconnect_btn.pack(fill=tk.X, pady=2)

        ttk.Separator(p).pack(fill=tk.X, pady=6)
        ttk.Label(p, text="Nhật ký NAO:").pack(anchor=tk.W)
        self.nao_log = scrolledtext.ScrolledText(p, height=8, width=38,
                                                 font=("Consolas", 8))
        self.nao_log.pack(fill=tk.BOTH, expand=True, pady=(2, 0))

    # -------- Tab 4: Đánh giá ----------
    def _build_tab_eval(self, p):
        ttk.Label(p, text="BIỂU ĐỒ ĐÁNH GIÁ",
                  font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(p, text="Chạy bộ thí nghiệm và xuất 7 biểu đồ "
                          "cho GA và A* (lưu ở ./charts/).",
                  foreground="#555", justify=tk.LEFT,
                  wraplength=290).pack(anchor=tk.W, pady=(2, 8))

        self.eval_btn = ttk.Button(p, text="📊  Xuất tất cả biểu đồ",
                                   command=self.action_eval_run)
        self.eval_btn.pack(fill=tk.X, pady=2)
        ttk.Button(p, text="📁  Mở thư mục charts",
                   command=self.action_eval_open_folder).pack(fill=tk.X, pady=2)

        ttk.Separator(p).pack(fill=tk.X, pady=8)
        ttk.Label(p, text="Danh sách biểu đồ:").pack(anchor=tk.W)
        self.eval_list = tk.Listbox(p, height=10, font=("Consolas", 9))
        self.eval_list.pack(fill=tk.BOTH, expand=True, pady=(2, 4))
        self.eval_list.bind("<Double-Button-1>", self._on_eval_open_chart)
        ttk.Button(p, text="Xem biểu đồ đã chọn",
                   command=self._on_eval_open_chart_btn
                   ).pack(fill=tk.X, pady=(2, 0))
        self._refresh_chart_list()

    # =========================================================== Drawing
    def _draw_empty(self):
        self.ax.clear()
        self.ax.set_xlim(0, MAP_W)
        self.ax.set_ylim(MAP_H, 0)
        self.ax.set_aspect("equal")
        self._apply_grid_ticks(self.ax)
        self.ax.set_title("Bản đồ 100 × 100 (chia lưới) — chưa có dữ liệu")
        self.ax.text(MAP_W / 2, MAP_H / 2,
                     "Nhấn « Tạo môi trường »",
                     ha="center", va="center", fontsize=14, color="#888")
        self._robot_dot = None
        self._sim_msg = None
        self.canvas.draw_idle()

    def _apply_grid_ticks(self, ax):
        ax.set_xticks(range(0, MAP_W + 1, 10))
        ax.set_yticks(range(0, MAP_H + 1, 10))
        ax.set_xticks(range(0, MAP_W + 1, 1), minor=True)
        ax.set_yticks(range(0, MAP_H + 1, 1), minor=True)
        ax.grid(which="minor", color="#dddddd", linewidth=0.3, alpha=0.6)
        ax.grid(which="major", color="#888888", linewidth=0.6, alpha=0.7)
        ax.tick_params(axis="both", which="major", labelsize=8)

    def _draw_environment(self):
        self.ax.clear()
        h, w = MAP_H, MAP_W

        img = np.ones((h, w, 3), dtype=float)
        for y in range(h):
            for x in range(w):
                if self.grid_raw[y][x] == 1:
                    img[y, x] = (0.15, 0.15, 0.15)
                elif self.grid_inflated[y][x] == 1:
                    img[y, x] = (0.85, 0.85, 0.85)
        self.ax.imshow(img, extent=(0, w, h, 0), interpolation="nearest",
                       zorder=0)
        self.ax.set_axisbelow(False)

        sx, sy = self.start
        self.ax.scatter([sx + 0.5], [sy + 0.5], s=240, c="gold",
                        edgecolors="black", marker="*", zorder=6,
                        label="Start")

        for i, o in enumerate(self.orders):
            c = color_for(i)
            self.ax.scatter([o.pickup[0] + 0.5], [o.pickup[1] + 0.5],
                            s=70, c=c, edgecolors="black", marker="o",
                            zorder=5)
            self.ax.scatter([o.dropoff[0] + 0.5], [o.dropoff[1] + 0.5],
                            s=70, c=c, edgecolors="black", marker="s",
                            zorder=5)
            self.ax.text(o.pickup[0] + 0.5, o.pickup[1] - 1.6,
                         f"P{o.label}", ha="center", fontsize=7,
                         color=c, fontweight="bold")
            self.ax.text(o.dropoff[0] + 0.5, o.dropoff[1] - 1.6,
                         f"D{o.label}", ha="center", fontsize=7,
                         color=c, fontweight="bold")
        for p in self.unmatched_pickups:
            self.ax.scatter([p[0] + 0.5], [p[1] + 0.5], s=50, c="#cccccc",
                            edgecolors="black", marker="o", zorder=4)
        for d in self.unmatched_dropoffs:
            self.ax.scatter([d[0] + 0.5], [d[1] + 0.5], s=50, c="#cccccc",
                            edgecolors="black", marker="s", zorder=4)

        if self.full_path:
            xs = [p[0] + 0.5 for p in self.full_path]
            ys = [p[1] + 0.5 for p in self.full_path]
            self.ax.plot(xs, ys, "-", color="#2ca02c", lw=1.8, alpha=0.9,
                         label="A* path", zorder=3)
            for idx, (x, y) in enumerate(self.result.best_route[1:], start=1):
                self.ax.text(x + 0.5, y + 0.5, str(idx),
                             ha="center", va="center", fontsize=6.5,
                             color="white", fontweight="bold", zorder=7)
        elif self.result is not None:
            xs = [p[0] + 0.5 for p in self.result.best_route]
            ys = [p[1] + 0.5 for p in self.result.best_route]
            self.ax.plot(xs, ys, "--", color="#ff7f0e", lw=1.6, alpha=0.9,
                         label="GA waypoint order", zorder=3)
            for idx, (x, y) in enumerate(self.result.best_route[1:], start=1):
                self.ax.text(x + 0.5, y + 0.5, str(idx),
                             ha="center", va="center", fontsize=6.5,
                             color="white", fontweight="bold", zorder=7)

        self.ax.set_xlim(0, w); self.ax.set_ylim(h, 0)
        self.ax.set_aspect("equal")
        self._apply_grid_ticks(self.ax)
        title = (f"Map 100×100 | {len(self.orders)} đơn hàng | "
                 f"○ pickup, □ dropoff")
        if self.full_path is not None:
            title += (f"\n[Bước 2 ✓] Quãng đường thực tế (A*): "
                      f"{self.actual_distance:.2f} ô"
                      f", {len(self.full_path)} bước")
        elif self.result is not None:
            title += (f"\n[Bước 1 ✓] GA xong — đường thẳng tham chiếu: "
                      f"{self.result.total_distance:.2f} ô  (chưa chạy A*)")
        self.ax.set_title(title, fontsize=11)

        # add (empty) robot dot artist for animation
        self._robot_dot, = self.ax.plot([], [], "o", color="#d62728",
                                        markersize=10, zorder=8,
                                        markeredgecolor="black")
        self._sim_msg = self.ax.text(0, 0, "", color="#d62728", fontsize=10,
                                     fontweight="bold", zorder=9)
        self.canvas.draw_idle()

    # ============================================================ Actions
    def action_generate(self):
        n_pick = max(1, self.var_pickups.get())
        n_drop = max(1, self.var_dropoffs.get())
        n_obs = max(0, self.var_obstacles.get())
        seed = self.var_seed.get()
        n_orders = min(n_pick, n_drop)
        if n_pick != n_drop:
            messagebox.showwarning("Cảnh báo",
                f"Số pickup ({n_pick}) khác số dropoff ({n_drop}). "
                f"Hệ thống chỉ ghép được {n_orders} đơn hàng.")
        rng = random.Random(seed)
        self.grid_raw = generate_random_obstacles(n_obs, seed=seed)
        self.grid_inflated = inflate_obstacles(self.grid_raw, radius=1)
        for y in range(3):
            for x in range(3):
                self.grid_raw[y][x] = 0
                self.grid_inflated[y][x] = 0
        self.start = (0, 0)
        try:
            used = {self.start}
            pickups = []
            for _ in range(n_pick):
                p = random_free_point(self.grid_inflated, rng, exclude=used)
                used.add(p); pickups.append(p)
            dropoffs = []
            for _ in range(n_drop):
                d = random_free_point(self.grid_inflated, rng, exclude=used)
                used.add(d); dropoffs.append(d)
        except RuntimeError as e:
            messagebox.showerror("Lỗi", f"Không thể đặt đủ điểm: {e}"); return
        self.orders = [Order(pickup=pickups[i], dropoff=dropoffs[i],
                             label=str(i + 1)) for i in range(n_orders)]
        self.unmatched_pickups = pickups[n_orders:]
        self.unmatched_dropoffs = dropoffs[n_orders:]
        self.result = None; self.full_path = None; self.actual_distance = 0.0
        self.astar_btn.configure(state=tk.DISABLED)
        self._update_sim_buttons()
        self._update_nao_run_button()
        self.status_var.set(
            f"Đã tạo môi trường:\n  • {n_orders} đơn hàng\n"
            f"  • {n_obs} khối vật cản\n  • Start = (0, 0)\n\n"
            f"→ Sang tab « Bài toán » để chạy GA, "
            f"hoặc « Mô phỏng » sau khi có đường A*.")
        self._draw_environment()

    # ---- Bước 1: GA ----
    def action_run_ga(self):
        if not self.orders:
            messagebox.showinfo("Thông báo", "Hãy tạo môi trường trước."); return
        self._stop_simulation()
        self.ga_btn.configure(state=tk.DISABLED)
        self.astar_btn.configure(state=tk.DISABLED)
        self.status_var.set("⏳ Bước 1: GA đang chạy (Octile)...")
        threading.Thread(target=self._run_ga_thread, daemon=True).start()

    def _run_ga_thread(self):
        try:
            cfg = GAConfig(pop_size=self.var_pop.get(),
                           max_gen=self.var_gen.get(),
                           crossover_rate=0.85, mutation_rate=0.20,
                           tournament_k=3, elitism_ratio=0.05,
                           early_stop_gen=80, seed=self.var_seed.get(),
                           distance_method="octile")
            self.result = run_ga(self.grid_inflated, self.start,
                                 self.orders, cfg)
            self.full_path = None; self.actual_distance = 0.0
            self.root.after(0, self._on_ga_done)
        except Exception as e:
            err = str(e)
            self.root.after(0, lambda: self._on_error(err, step="GA"))

    def _on_ga_done(self):
        self.ga_btn.configure(state=tk.NORMAL)
        self.astar_btn.configure(state=tk.NORMAL)
        order_str = " → ".join(
            f"{'P' if task_is_pickup(t) else 'D'}"
            f"{self.orders[task_order_id(t)].label}"
            for t in self.result.best_sequence)
        self.status_var.set(
            f"✓ Bước 1 (GA) xong\n"
            f"  • Octile: {self.result.total_distance:.2f} ô\n"
            f"  • Số thế hệ: {self.result.generations_run}\n"
            f"  • Thứ tự: {order_str}\n→ Bước 2: chạy A*.")
        self._update_sim_buttons(); self._update_nao_run_button()
        self._draw_environment()

    # ---- Bước 2: A* ----
    def action_run_astar(self):
        if self.result is None:
            messagebox.showinfo("Thông báo", "Hãy chạy Bước 1 (GA) trước."); return
        self._stop_simulation()
        self.ga_btn.configure(state=tk.DISABLED)
        self.astar_btn.configure(state=tk.DISABLED)
        self.status_var.set("⏳ Bước 2: A* đang dò đường tránh vật cản...")
        threading.Thread(target=self._run_astar_thread, daemon=True).start()

    def _run_astar_thread(self):
        try:
            self.full_path = expand_full_path(self.grid_inflated,
                                              self.result.best_route)
            self.actual_distance = path_length(self.full_path)
            self.root.after(0, self._on_astar_done)
        except Exception as e:
            err = str(e)
            self.root.after(0, lambda: self._on_error(err, step="A*"))

    def _on_astar_done(self):
        self.ga_btn.configure(state=tk.NORMAL)
        self.astar_btn.configure(state=tk.NORMAL)
        gain = self.actual_distance - self.result.total_distance
        sign = "+" if gain >= 0 else ""
        self.status_var.set(
            f"✓ Bước 2 (A*) xong\n"
            f"  • Quãng đường thực tế: {self.actual_distance:.2f} ô\n"
            f"  • Số bước: {len(self.full_path)}\n"
            f"  • Δ so với GA: {sign}{gain:.2f} ô\n\n"
            f"→ Có thể MÔ PHỎNG hoặc CHẠY THẬT trên NAO.")
        self._update_sim_buttons(); self._update_nao_run_button()
        self._draw_environment()

    def _on_error(self, msg, step="GA"):
        self.ga_btn.configure(state=tk.NORMAL)
        if self.result is not None:
            self.astar_btn.configure(state=tk.NORMAL)
        self.status_var.set(f"Lỗi ở bước {step}: {msg}")
        messagebox.showerror(f"Lỗi khi chạy {step}", msg)

    def action_reset(self):
        self._stop_simulation()
        self.grid_raw = None; self.grid_inflated = None
        self.orders = []; self.unmatched_pickups = []; self.unmatched_dropoffs = []
        self.result = None; self.full_path = None; self.actual_distance = 0.0
        self.astar_btn.configure(state=tk.DISABLED)
        self._update_sim_buttons(); self._update_nao_run_button()
        self._draw_empty()
        self.status_var.set("Đã reset.")

    # ===================================================== Simulation
    def _update_sim_buttons(self):
        ready = self.full_path is not None
        self.sim_play_btn.configure(state=tk.NORMAL if ready else tk.DISABLED)
        if not ready:
            self.sim_pause_btn.configure(state=tk.DISABLED)
            self.sim_stop_btn.configure(state=tk.DISABLED)

    def action_sim_play(self):
        if not self.full_path:
            messagebox.showinfo("Thông báo", "Chưa có đường A*."); return
        if self.sim_running and self.sim_paused:
            self.sim_paused = False
            self.sim_msg_var.set("Đang chạy...")
            self._sim_step()
            return
        # fresh start
        self.sim_running = True; self.sim_paused = False
        self.sim_index = 0
        self.sim_progress.configure(maximum=len(self.full_path) - 1, value=0)
        self.sim_msg_var.set("Đang chạy...")
        self.sim_pause_btn.configure(state=tk.NORMAL)
        self.sim_stop_btn.configure(state=tk.NORMAL)
        self._waypoint_set = {wp: idx for idx, wp
                              in enumerate(self.result.best_route)}
        self._sim_step()

    def action_sim_pause(self):
        if not self.sim_running:
            return
        self.sim_paused = not self.sim_paused
        if self.sim_paused:
            self.sim_msg_var.set("⏸ Tạm dừng.")
            if self.sim_after_id is not None:
                self.root.after_cancel(self.sim_after_id)
                self.sim_after_id = None
        else:
            self.sim_msg_var.set("Đang chạy...")
            self._sim_step()

    def action_sim_stop(self):
        self._stop_simulation()
        self.sim_msg_var.set("■ Đã dừng.")

    def _stop_simulation(self):
        self.sim_running = False; self.sim_paused = False
        if self.sim_after_id is not None:
            try: self.root.after_cancel(self.sim_after_id)
            except Exception: pass
            self.sim_after_id = None
        self.sim_pause_btn.configure(state=tk.DISABLED)
        self.sim_stop_btn.configure(state=tk.DISABLED)
        if self._robot_dot is not None:
            self._robot_dot.set_data([], [])
        if self._sim_msg is not None:
            self._sim_msg.set_text("")
        self.canvas.draw_idle()

    def _sim_step(self):
        if not self.sim_running or self.sim_paused: return
        if self.sim_index >= len(self.full_path):
            self.sim_msg_var.set("✓ Mô phỏng hoàn tất.")
            self._stop_simulation()
            return
        x, y = self.full_path[self.sim_index]
        if self._robot_dot is not None:
            self._robot_dot.set_data([x + 0.5], [y + 0.5])
        # waypoint event?
        if (x, y) in self._waypoint_set and self.sim_index > 0:
            wp_idx = self._waypoint_set[(x, y)]
            if 1 <= wp_idx <= 2 * len(self.orders):
                t = self.result.best_sequence[wp_idx - 1]
                label = self.orders[task_order_id(t)].label
                kind = "📦 Lấy" if task_is_pickup(t) else "🏁 Trả"
                msg = f"{kind} hàng {label}"
                if self._sim_msg is not None:
                    self._sim_msg.set_position((x + 1.5, y + 1.5))
                    self._sim_msg.set_text(msg)
                self.sim_msg_var.set(f"{msg}  (bước {self.sim_index}/"
                                     f"{len(self.full_path) - 1})")
        self.sim_progress.configure(value=self.sim_index)
        self.canvas.draw_idle()
        self.sim_index += 1
        speed = max(1.0, self.var_sim_speed.get())
        delay_ms = max(15, int(1000.0 / speed))
        self.sim_after_id = self.root.after(delay_ms, self._sim_step)

    # ===================================================== NAO real
    def _log_nao(self, msg: str):
        self.nao_log.insert(tk.END, msg + "\n")
        self.nao_log.see(tk.END)

    def _update_nao_run_button(self):
        ready = self.nao.connected and self.full_path is not None
        self.nao_run_btn.configure(state=tk.NORMAL if ready else tk.DISABLED)

    def action_nao_connect(self):
        ip = self.var_nao_ip.get().strip() or "127.0.0.1"
        port = int(self.var_nao_port.get())
        self.nao = NaoController(cell_size_m=float(self.var_cell_m.get()),
                                 fake=bool(self.var_nao_fake.get()))
        ok, msg = self.nao.connect(ip, port)
        self._log_nao(f"[connect] {msg}")
        if ok:
            self.nao_connect_btn.configure(state=tk.DISABLED)
            self.nao_disconnect_btn.configure(state=tk.NORMAL)
            self._update_nao_run_button()
            self.nao.stand_init()
            self._log_nao(f"[sdk] {self.nao.sdk_name}")
        else:
            messagebox.showerror("NAO", msg)

    def action_nao_disconnect(self):
        if self.nao_running:
            self._nao_stop_flag = True
            self._log_nao("[stop] yêu cầu dừng trước khi ngắt...")
            return
        self.nao.disconnect()
        self._log_nao("[disconnect] ngắt kết nối.")
        self.nao_connect_btn.configure(state=tk.NORMAL)
        self.nao_disconnect_btn.configure(state=tk.DISABLED)
        self.nao_run_btn.configure(state=tk.DISABLED)
        self.nao_stop_btn.configure(state=tk.DISABLED)

    def action_nao_run(self):
        if not (self.nao.connected and self.full_path):
            messagebox.showinfo("NAO", "Chưa sẵn sàng (kết nối + A*)."); return
        if self.nao_running: return
        self.nao_running = True; self._nao_stop_flag = False
        self.nao.cell_size_m = float(self.var_cell_m.get())
        self.nao_run_btn.configure(state=tk.DISABLED)
        self.nao_stop_btn.configure(state=tk.NORMAL)
        self.nao_disconnect_btn.configure(state=tk.DISABLED)
        self._waypoint_set = {wp: idx for idx, wp
                              in enumerate(self.result.best_route)}
        self._log_nao(f"[run] đi theo {len(self.full_path)} ô "
                      f"({self.nao.cell_size_m:.2f} m/ô)")
        threading.Thread(target=self._nao_run_thread, daemon=True).start()

    def _nao_run_thread(self):
        try:
            self.nao.say("Bắt đầu giao hàng")

            def on_progress(i, n):
                # i is the index in path[1:], so cell = full_path[i]
                cell = self.full_path[i]
                self.root.after(0, self._on_nao_step, i, n, cell)

            self.nao.follow_path_cells(
                self.full_path,
                on_progress=on_progress,
                stop_flag=lambda: self._nao_stop_flag)
            self.nao.say("Giao hàng hoàn tất")
            self.root.after(0, self._on_nao_done, False)
        except Exception as e:
            err = str(e)
            self.root.after(0, lambda: self._on_nao_done(True, err))

    def _on_nao_step(self, i, n, cell):
        # update on-canvas robot dot too
        if self._robot_dot is not None:
            self._robot_dot.set_data([cell[0] + 0.5], [cell[1] + 0.5])
            self.canvas.draw_idle()
        if cell in self._waypoint_set and i > 0:
            wp_idx = self._waypoint_set[cell]
            if 1 <= wp_idx <= 2 * len(self.orders):
                t = self.result.best_sequence[wp_idx - 1]
                label = self.orders[task_order_id(t)].label
                if task_is_pickup(t):
                    self.nao.say(f"Đã lấy hàng {label}")
                    self._log_nao(f"  ► P{label}  (cell {cell})")
                else:
                    self.nao.say(f"Đã giao hàng {label}")
                    self._log_nao(f"  ► D{label}  (cell {cell})")

    def _on_nao_done(self, error: bool, msg: str = ""):
        self.nao_running = False
        self.nao_run_btn.configure(state=tk.NORMAL if self.nao.connected
                                   else tk.DISABLED)
        self.nao_stop_btn.configure(state=tk.DISABLED)
        self.nao_disconnect_btn.configure(state=tk.NORMAL if self.nao.connected
                                          else tk.DISABLED)
        if error:
            self._log_nao(f"[error] {msg}")
            messagebox.showerror("NAO", msg)
        else:
            self._log_nao("[done] hoàn tất hành trình.")

    def action_nao_stop(self):
        self._nao_stop_flag = True
        self._log_nao("[stop] đang dừng tại waypoint kế tiếp...")

    # ===================================================== Evaluate
    def action_eval_run(self):
        self.eval_btn.configure(state=tk.DISABLED)
        rand = bool(self.var_eval_random.get())
        tag = "ngẫu nhiên" if rand else "tái lập"
        self.status_var.set(f"⏳ Đang sinh biểu đồ đánh giá ({tag}, ~30s)...")
        threading.Thread(target=self._eval_run_thread,
                         args=(rand,), daemon=True).start()

    def _eval_run_thread(self, random_mode: bool):
        try:
            import importlib, evaluate
            importlib.reload(evaluate)
            evaluate.main(random_mode=random_mode)
            self.root.after(0, self._on_eval_done, None)
        except Exception as e:
            err = str(e)
            self.root.after(0, self._on_eval_done, err)

    def _on_eval_done(self, err):
        self.eval_btn.configure(state=tk.NORMAL)
        if err:
            self.status_var.set(f"Lỗi xuất biểu đồ: {err}")
            messagebox.showerror("Đánh giá", err); return
        self.status_var.set("✓ Đã xuất biểu đồ vào ./charts/")
        self._refresh_chart_list()

    def _refresh_chart_list(self):
        self.eval_list.delete(0, tk.END)
        if not os.path.isdir("charts"): return
        for f in sorted(os.listdir("charts")):
            if f.lower().endswith(".png"):
                self.eval_list.insert(tk.END, f)

    def action_eval_open_folder(self):
        path = os.path.abspath("charts")
        os.makedirs(path, exist_ok=True)
        self._open_path(path)

    def _on_eval_open_chart(self, _ev=None):
        self._on_eval_open_chart_btn()

    def _on_eval_open_chart_btn(self):
        sel = self.eval_list.curselection()
        if not sel:
            messagebox.showinfo("Đánh giá", "Hãy chọn 1 biểu đồ."); return
        f = self.eval_list.get(sel[0])
        self._open_path(os.path.abspath(os.path.join("charts", f)))

    @staticmethod
    def _open_path(path: str):
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Không mở được", str(e))


def main():
    root = tk.Tk()
    try:
        ttk.Style(root).theme_use("vista")
    except tk.TclError:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
