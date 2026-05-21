# -*- coding: utf-8 -*-
"""
ga_planner.py
Thuật toán Di truyền (Genetic Algorithm) cho bài toán Lấy hàng - Giao hàng
(Pickup-and-Delivery Problem – PDP), phục vụ robot NAO.

Mã hóa nhiễm sắc thể (Chromosome encoding):
    Một hoán vị (permutation) của 2n chỉ số nhiệm vụ.
    Mỗi đơn hàng o_k có 2 nhiệm vụ:
        - Nhiệm vụ lấy hàng (pickup):  chỉ số 2k     (ký hiệu "P{k}")
        - Nhiệm vụ giao hàng (delivery): chỉ số 2k+1 (ký hiệu "D{k}")
    Ràng buộc: trong mọi nhiễm sắc thể hợp lệ, nhiệm vụ lấy hàng của
    đơn k phải xuất hiện TRƯỚC nhiệm vụ giao hàng của đơn k.

Các toán tử di truyền (Operators):
    - Chọn lọc bằng giải đấu (Tournament selection, k=3)
    - Lai ghép OX-PR (Order Crossover + Precedence Repair)
    - Đột biến hoán đổi (Swap mutation) kèm sửa ràng buộc
    - Bảo tồn cá thể ưu tú (Elitism – top 5% quần thể)
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from astar import astar, octile, path_length, Point


# ---------------------------------------------------------------------------
# Mô hình dữ liệu (Data model)
# ---------------------------------------------------------------------------

@dataclass
class Order:
    """Một đơn hàng: lấy tại `pickup`, giao đến `dropoff`."""
    pickup: Point       # Tọa độ (x, y) điểm lấy hàng
    dropoff: Point      # Tọa độ (x, y) điểm giao hàng
    label: str = ""     # Nhãn hiển thị (vd: "1", "2", …)


@dataclass
class GAConfig:
    """Tham số cấu hình cho thuật toán di truyền."""
    pop_size: int = 100            # Kích thước quần thể
    max_gen: int = 500             # Số thế hệ tối đa
    crossover_rate: float = 0.85   # Xác suất lai ghép
    mutation_rate: float = 0.15    # Xác suất đột biến
    tournament_k: int = 3          # Số cá thể trong mỗi vòng chọn lọc giải đấu
    elitism_ratio: float = 0.05    # Tỷ lệ cá thể ưu tú được bảo toàn
    early_stop_gen: int = 80       # Dừng sớm nếu không cải thiện sau N thế hệ
    seed: Optional[int] = None     # Hạt giống (để tái lập kết quả)
    distance_method: str = "astar" # "astar" (xét vật cản) hoặc "octile" (nhanh)


@dataclass
class GAResult:
    """Kết quả trả về từ thuật toán GA."""
    best_sequence: List[int]       # Nhiễm sắc thể tốt nhất (dãy 2n chỉ số)
    best_route: List[Point]        # Lộ trình: [start, task_1, task_2, …, task_2n]
    total_distance: float          # Tổng quãng đường (ô)
    generations_run: int           # Số thế hệ thực tế đã chạy
    history: List[float] = field(default_factory=list)         # Tốt nhất mỗi thế hệ
    history_mean: List[float] = field(default_factory=list)    # Trung bình mỗi thế hệ
    history_worst: List[float] = field(default_factory=list)   # Tệ nhất mỗi thế hệ


# ---------------------------------------------------------------------------
# Hàm tiện ích cho mã hóa nhiễm sắc thể
# ---------------------------------------------------------------------------

def task_is_pickup(task_idx: int) -> bool:
    """Kiểm tra nhiệm vụ task_idx có phải là lấy hàng không (chỉ số chẵn = pickup)."""
    return task_idx % 2 == 0


def task_order_id(task_idx: int) -> int:
    """Trả về mã đơn hàng (order index) tương ứng với nhiệm vụ task_idx."""
    return task_idx // 2


def task_point(task_idx: int, orders: List[Order]) -> Point:
    """Trả về tọa độ (x, y) của nhiệm vụ task_idx."""
    o = orders[task_order_id(task_idx)]
    return o.pickup if task_is_pickup(task_idx) else o.dropoff


def chromosome_to_label(chrom: List[int], orders: List[Order]) -> str:
    """Chuyển nhiễm sắc thể thành chuỗi dễ đọc, vd: 'P1 -> D1 -> P2 -> D2'."""
    parts = []
    for t in chrom:
        k = task_order_id(t)
        tag = "P" if task_is_pickup(t) else "D"
        label = orders[k].label or str(k + 1)
        parts.append(f"{tag}{label}")
    return " -> ".join(parts)


# ---------------------------------------------------------------------------
# Ma trận khoảng cách (Distance matrix)
# ---------------------------------------------------------------------------

def build_distance_matrix(
    grid: List[List[int]],
    points: List[Point],
) -> List[List[float]]:
    """
    Tính trước khoảng cách A* giữa mọi cặp điểm.

    Trả về ma trận NxN (N = len(points)).
    points[0] thường là vị trí xuất phát (Start).
    Khoảng cách = tổng chi phí đường đi A* (√2 cho bước chéo, 1 cho bước thẳng).
    Nếu không có đường → giá trị = inf.
    """
    n = len(points)
    dist = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            path = astar(grid, points[i], points[j])
            d = path_length(path)       # inf nếu path is None
            dist[i][j] = d
            dist[j][i] = d              # Ma trận đối xứng
    return dist


def build_distance_matrix_octile(points: List[Point]) -> List[List[float]]:
    """
    Ma trận khoảng cách nhanh dùng hàm Octile (bỏ qua vật cản).

    Dùng ở Bước 1 (GA-only): GA tối ưu thứ tự nhiệm vụ dựa trên khoảng cách
    Octile (cận dưới), sau đó Bước 2 (A*) sẽ tính đường thực tế tránh vật cản.
    """
    n = len(points)
    dist = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = octile(points[i], points[j])
            dist[i][j] = d
            dist[j][i] = d
    return dist


# ---------------------------------------------------------------------------
# Sửa ràng buộc thứ tự (Precedence Repair)
# ---------------------------------------------------------------------------

def precedence_repair(chrom: List[int]) -> List[int]:
    """
    Đảm bảo mỗi đơn hàng k luôn có pickup (2k) đứng trước delivery (2k+1).

    Nếu phát hiện vi phạm → hoán đổi vị trí 2 nhiệm vụ đó trong nhiễm sắc thể.
    Đây là bước bắt buộc sau mỗi thao tác lai ghép / đột biến.
    """
    chrom = chrom[:]                        # bản sao để không sửa gốc
    pos = {t: i for i, t in enumerate(chrom)}  # vị trí hiện tại của mỗi nhiệm vụ
    n_orders = len(chrom) // 2
    for k in range(n_orders):
        p_idx = pos[2 * k]       # vị trí pickup
        d_idx = pos[2 * k + 1]   # vị trí delivery
        if d_idx < p_idx:        # vi phạm → hoán đổi
            chrom[p_idx], chrom[d_idx] = chrom[d_idx], chrom[p_idx]
            pos[2 * k] = d_idx
            pos[2 * k + 1] = p_idx
    return chrom


# ---------------------------------------------------------------------------
# Khởi tạo quần thể (Population Initialization)
# ---------------------------------------------------------------------------

def random_valid_chromosome(n_orders: int, rng: random.Random) -> List[int]:
    """
    Tạo 1 nhiễm sắc thể ngẫu nhiên hợp lệ:
    hoán vị ngẫu nhiên 2n nhiệm vụ, rồi sửa ràng buộc.
    """
    chrom = list(range(2 * n_orders))
    rng.shuffle(chrom)
    return precedence_repair(chrom)


def greedy_chromosome(
    start_idx: int,
    n_orders: int,
    dist_matrix: List[List[float]],
    point_to_task: dict,
) -> List[int]:
    """
    Xây dựng nhiễm sắc thể tham lam (Nearest Neighbor) có tôn trọng ràng buộc:
      - Từ vị trí hiện tại, chọn nhiệm vụ chưa thực hiện CÓ khoảng cách ngắn nhất.
      - Chỉ cho phép chọn delivery khi pickup tương ứng đã được thực hiện.
    """
    visited_tasks: set = set()       # Tập nhiệm vụ đã xếp
    picked_orders: set = set()       # Tập đơn đã lấy hàng (pickup xong)
    chrom: List[int] = []            # Nhiễm sắc thể đang xây
    current_point_idx = start_idx    # Vị trí hiện tại (index trong distance matrix)
    total_tasks = 2 * n_orders

    while len(chrom) < total_tasks:
        best_task = -1
        best_d = float("inf")
        for t in range(total_tasks):
            if t in visited_tasks:
                continue
            k = task_order_id(t)
            # Chỉ cho phép delivery nếu đã pickup trước đó
            if not task_is_pickup(t) and k not in picked_orders:
                continue
            target_idx = point_to_task[t]
            d = dist_matrix[current_point_idx][target_idx]
            if d < best_d:
                best_d = d
                best_task = t
        if best_task < 0:
            # Fallback (không nên xảy ra nếu đồ thị liên thông)
            remaining = [t for t in range(total_tasks) if t not in visited_tasks]
            best_task = remaining[0]
        chrom.append(best_task)
        visited_tasks.add(best_task)
        if task_is_pickup(best_task):
            picked_orders.add(task_order_id(best_task))
        current_point_idx = point_to_task[best_task]
    return chrom


# ---------------------------------------------------------------------------
# Hàm thích nghi (Fitness / Evaluation)
# ---------------------------------------------------------------------------

def evaluate(
    chrom: List[int],
    dist_matrix: List[List[float]],
    point_to_task: dict,
    start_idx: int = 0,
) -> float:
    """
    Tính tổng quãng đường đi: start → task_1 → task_2 → … → task_2n.

    Dùng distance matrix đã tính sẵn để tra cứu O(1) cho mỗi cặp.
    Giá trị nhỏ hơn = nhiễm sắc thể tốt hơn (tối thiểu hóa).
    """
    total = 0.0
    prev = start_idx
    for t in chrom:
        nxt = point_to_task[t]
        total += dist_matrix[prev][nxt]
        prev = nxt
    return total


def fitness(distance: float, eps: float = 1e-6) -> float:
    """Chuyển khoảng cách → fitness (càng xa → fitness càng thấp)."""
    return 1.0 / (distance + eps)


# ---------------------------------------------------------------------------
# Các toán tử di truyền (Genetic Operators)
# ---------------------------------------------------------------------------

def tournament_select(
    population: List[List[int]],
    distances: List[float],
    k: int,
    rng: random.Random,
) -> List[int]:
    """
    Chọn lọc giải đấu (Tournament Selection):
    Chọn ngẫu nhiên k cá thể, giữ lại cá thể có quãng đường nhỏ nhất.
    """
    contenders = rng.sample(range(len(population)), k)
    best = min(contenders, key=lambda i: distances[i])
    return population[best][:]


def order_crossover(parent1: List[int], parent2: List[int],
                    rng: random.Random) -> List[int]:
    """
    Lai ghép thứ tự (Order Crossover – OX):
      1. Chọn ngẫu nhiên một đoạn [a, b] từ parent1, sao chép vào con.
      2. Điền các gene còn thiếu theo thứ tự xuất hiện trong parent2.

    Đầu ra CHƯA đảm bảo ràng buộc thứ tự → cần gọi precedence_repair() sau.
    """
    size = len(parent1)
    a, b = sorted(rng.sample(range(size), 2))
    child: List[Optional[int]] = [None] * size
    slice_genes = set(parent1[a:b + 1])
    child[a:b + 1] = parent1[a:b + 1]
    # Điền các gene không có trong đoạn [a,b], theo thứ tự parent2
    fill_iter = (g for g in parent2 if g not in slice_genes)
    for i in range(size):
        if child[i] is None:
            child[i] = next(fill_iter)
    return [g for g in child if g is not None]  # type: ignore


def swap_mutation(chrom: List[int], rng: random.Random) -> List[int]:
    """
    Đột biến hoán đổi (Swap Mutation):
    Chọn ngẫu nhiên 2 vị trí và hoán đổi giá trị.
    Sau đột biến cần gọi precedence_repair().
    """
    chrom = chrom[:]
    if len(chrom) < 2:
        return chrom
    i, j = rng.sample(range(len(chrom)), 2)
    chrom[i], chrom[j] = chrom[j], chrom[i]
    return chrom


# ---------------------------------------------------------------------------
# Vòng lặp chính của GA (Main GA Loop)
# ---------------------------------------------------------------------------

def run_ga(
    grid: List[List[int]],
    start: Point,
    orders: List[Order],
    config: GAConfig = GAConfig(),
    progress_cb: Optional[Callable[[int, float], None]] = None,
) -> GAResult:
    """
    Chạy thuật toán di truyền để tìm thứ tự nhiệm vụ pickup-delivery tối ưu.

    Quy trình:
      1. Xây dựng danh sách điểm (start + 2n pickup/dropoff) và distance matrix.
      2. Khởi tạo quần thể: 50% biến thể tham lam + 50% ngẫu nhiên hợp lệ.
      3. Vòng lặp tiến hóa:
         a. Bảo toàn cá thể ưu tú (elitism).
         b. Chọn cha mẹ bằng giải đấu → lai ghép OX → đột biến swap → sửa ràng buộc.
         c. Ghi nhận best/mean/worst mỗi thế hệ.
         d. Dừng sớm nếu không cải thiện sau `early_stop_gen` thế hệ liên tiếp.
      4. Trả về lộ trình tốt nhất dưới dạng danh sách tọa độ (x, y).

    Tham số:
        grid        : Bản đồ 2D (0=trống, 1=vật cản) đã inflate.
        start       : Tọa độ xuất phát (x, y).
        orders      : Danh sách các đơn hàng.
        config      : Tham số GA (xem GAConfig).
        progress_cb : Callback(gen, best_dist) gọi mỗi thế hệ (tùy chọn).

    Trả về:
        GAResult chứa nhiễm sắc thể tốt nhất, lộ trình, quãng đường, lịch sử.
    """
    rng = random.Random(config.seed)
    n_orders = len(orders)
    if n_orders == 0:
        return GAResult([], [start], 0.0, 0, [])

    # ===== BƯỚC 1: Xây dựng danh sách điểm và distance matrix =====
    points: List[Point] = [start]
    point_to_task: dict = {}     # ánh xạ: task_index → index trong `points`
    for k, o in enumerate(orders):
        points.append(o.pickup)
        point_to_task[2 * k] = len(points) - 1
        points.append(o.dropoff)
        point_to_task[2 * k + 1] = len(points) - 1
    start_idx = 0

    # Chọn phương pháp tính khoảng cách
    if config.distance_method == "octile":
        # Nhanh: chỉ dùng Octile (không xét vật cản) — phù hợp Bước 1 (GA-only)
        dist_matrix = build_distance_matrix_octile(points)
    else:
        # Chính xác: dùng A* trên bản đồ có vật cản
        dist_matrix = build_distance_matrix(grid, points)

    # ===== BƯỚC 2: Khởi tạo quần thể =====
    population: List[List[int]] = []
    n_greedy = config.pop_size // 2     # 50% cá thể dựa trên tham lam
    n_random = config.pop_size - n_greedy  # 50% cá thể ngẫu nhiên

    # Cá thể tham lam gốc (nearest neighbor)
    base_greedy = greedy_chromosome(start_idx, n_orders, dist_matrix, point_to_task)
    population.append(base_greedy)
    # Các biến thể đột biến từ cá thể tham lam
    for _ in range(n_greedy - 1):
        c = swap_mutation(base_greedy, rng)
        c = precedence_repair(c)
        population.append(c)
    # Cá thể ngẫu nhiên hợp lệ
    for _ in range(n_random):
        population.append(random_valid_chromosome(n_orders, rng))

    # Đánh giá quần thể ban đầu
    distances = [evaluate(c, dist_matrix, point_to_task, start_idx)
                 for c in population]
    n_elite = max(1, int(config.pop_size * config.elitism_ratio))

    # ===== BƯỚC 3: Vòng lặp tiến hóa =====
    history: List[float] = []
    history_mean: List[float] = []
    history_worst: List[float] = []
    best_idx = min(range(len(population)), key=lambda i: distances[i])
    best_dist = distances[best_idx]
    best_chrom = population[best_idx][:]
    stagnation = 0      # Đếm số thế hệ liên tiếp không cải thiện
    gens_run = 0

    for gen in range(config.max_gen):
        gens_run = gen + 1

        # --- Bảo toàn cá thể ưu tú (Elitism) ---
        sorted_idx = sorted(range(len(population)), key=lambda i: distances[i])
        new_pop = [population[i][:] for i in sorted_idx[:n_elite]]

        # --- Sinh sản (Reproduction) ---
        while len(new_pop) < config.pop_size:
            # Chọn 2 cha mẹ bằng giải đấu
            p1 = tournament_select(population, distances, config.tournament_k, rng)
            p2 = tournament_select(population, distances, config.tournament_k, rng)
            # Lai ghép OX
            if rng.random() < config.crossover_rate:
                child = order_crossover(p1, p2, rng)
            else:
                child = p1[:]
            # Đột biến hoán đổi
            if rng.random() < config.mutation_rate:
                child = swap_mutation(child, rng)
            # Sửa ràng buộc pickup trước delivery
            child = precedence_repair(child)
            new_pop.append(child)

        # Thay thế quần thể và đánh giá lại
        population = new_pop
        distances = [evaluate(c, dist_matrix, point_to_task, start_idx)
                     for c in population]

        # --- Ghi nhận thống kê thế hệ ---
        gen_best_idx = min(range(len(population)), key=lambda i: distances[i])
        gen_best = distances[gen_best_idx]
        gen_mean = sum(distances) / len(distances)
        gen_worst = max(distances)
        history.append(gen_best)
        history_mean.append(gen_mean)
        history_worst.append(gen_worst)

        # --- Cập nhật cá thể tốt nhất toàn cục ---
        if gen_best < best_dist - 1e-9:
            best_dist = gen_best
            best_chrom = population[gen_best_idx][:]
            stagnation = 0
        else:
            stagnation += 1

        # Callback tiến độ (nếu có)
        if progress_cb:
            progress_cb(gen, best_dist)

        # --- Dừng sớm nếu bế tắc ---
        if stagnation >= config.early_stop_gen:
            break

    # ===== BƯỚC 4: Xây dựng lộ trình tọa độ =====
    best_route = [start] + [task_point(t, orders) for t in best_chrom]

    return GAResult(
        best_sequence=best_chrom,
        best_route=best_route,
        total_distance=best_dist,
        generations_run=gens_run,
        history=history,
        history_mean=history_mean,
        history_worst=history_worst,
    )


# ---------------------------------------------------------------------------
# Mở rộng đường đi chi tiết (Path Expansion via A*)
# ---------------------------------------------------------------------------

def expand_full_path(grid: List[List[int]], route: List[Point]) -> List[Point]:
    """
    Chuyển lộ trình cấp cao (danh sách waypoint) thành đường đi chi tiết
    từng ô trên lưới, bằng cách gọi A* giữa các cặp waypoint liên tiếp.

    Đầu vào:
        grid  : Bản đồ đã inflate (0=trống, 1=cấm).
        route : [start, wp1, wp2, …, wp_{2n}] — output của GA.

    Đầu ra:
        Danh sách liên tục các (x, y) mà robot đi qua (bao gồm start và cuối).
        Mỗi bước liền kề cách nhau đúng 1 ô (4-hướng) hoặc √2 (8-hướng).

    Lỗi:
        RuntimeError nếu bất kỳ đoạn nào không tìm được đường A*.
    """
    full: List[Point] = []
    for i in range(len(route) - 1):
        seg = astar(grid, route[i], route[i + 1])
        if seg is None:
            raise RuntimeError(
                f"Không tìm được đường A* giữa {route[i]} và {route[i + 1]}")
        if i == 0:
            full.extend(seg)
        else:
            full.extend(seg[1:])  # Bỏ ô đầu (trùng ô cuối đoạn trước)
    return full
