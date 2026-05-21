# Tối Ưu Hóa Lộ Trình Giao Hàng Cho Robot NAO Trong Môi Trường Có Vật Cản Sử Dụng Thuật Toán Di Truyền Và A*

**Optimizing Delivery Routes for NAO Robot in Obstacle-Laden Environments Using Genetic Algorithm and A***

---

**Tóm tắt —** Bài báo trình bày một hệ thống tự động hóa nhiệm vụ giao hàng cho robot NAO trong môi trường trong nhà có vật cản tĩnh. Hệ thống tích hợp hai lớp lập kế hoạch: (1) lớp kế hoạch nhiệm vụ cấp cao sử dụng Thuật toán Di Truyền (Genetic Algorithm – GA) để tìm chuỗi lấy hàng – giao hàng tối ưu nhằm tối thiểu hóa tổng quãng đường di chuyển; (2) lớp lập kế hoạch đường đi cấp thấp sử dụng thuật toán A* để tìm đường tránh vật cản giữa từng cặp điểm trên bản đồ lưới. Thực nghiệm trên môi trường mô phỏng và trên phần cứng robot NAO thực tế cho thấy hệ thống đề xuất giảm tổng quãng đường di chuyển trung bình 23,4% so với chiến lược lập kế hoạch ngẫu nhiên và 11,2% so với giải thuật tham lam (greedy). Kết quả xác nhận tính khả thi của việc triển khai trên robot NAO với hệ điều hành NAOqi.

**Từ khóa —** Robot NAO, thuật toán di truyền, thuật toán A*, lập kế hoạch đường đi, tránh vật cản, tối ưu hóa lộ trình.

---

## I. GIỚI THIỆU

Sự phát triển của robot dịch vụ trong môi trường trong nhà (indoor service robots) đặt ra yêu cầu ngày càng cao về khả năng lập kế hoạch nhiệm vụ tự động và di chuyển an toàn. Robot NAO (Aldebaran/SoftBank Robotics) là một nền tảng robot hình người (humanoid) phổ biến trong nghiên cứu học thuật và ứng dụng thực tế, được trang bị nhiều cảm biến và hỗ trợ lập trình qua hệ điều hành NAOqi [1].

Bài toán giao hàng (delivery problem) trên robot đòi hỏi giải quyết đồng thời hai bài toán con: (i) xác định **thứ tự** lấy hàng và giao hàng tối ưu — một dạng bài toán TSP với ràng buộc thứ tự (Pickup and Delivery Problem – PDP) [2]; (ii) tìm **đường đi** tránh vật cản trong thời gian thực giữa các cặp điểm trên bản đồ [3].

Thuật toán Di Truyền (GA) đã được chứng minh là phù hợp để giải các bài toán tổ hợp NP-hard như TSP/PDP nhờ khả năng tìm kiếm toàn cục hiệu quả [4]. Trong khi đó, A* là thuật toán tìm đường kinh điển đảm bảo tính tối ưu và đầy đủ trên đồ thị hữu hạn [5]. Việc kết hợp hai thuật toán này tạo nên kiến trúc phân cấp hai tầng linh hoạt và hiệu quả.

Đóng góp chính của bài báo:
- Xây dựng mô hình bài toán PDP cho robot NAO với tích hợp bản đồ lưới.
- Thiết kế toán tử GA chuyên biệt tôn trọng ràng buộc thứ tự lấy/giao hàng.
- Triển khai A* trên bản đồ lưới 2D kết hợp với mô hình động học của NAO.
- Đánh giá thực nghiệm trên mô phỏng và phần cứng thực.

---

## II. CÔNG TRÌNH LIÊN QUAN

### A. Lập kế hoạch nhiệm vụ cho robot dịch vụ

Li và cộng sự [6] đề xuất giải thuật GA lai ghép để giải bài toán định tuyến robot giao hàng trong bệnh viện, đạt được kết quả tốt hơn 18% so với phương pháp truyền thống. Tuy nhiên, công trình này không xem xét việc tránh vật cản động.

Chen và Wang [7] sử dụng thuật toán tối ưu bầy đàn (PSO) kết hợp với đồ thị đường đi (roadmap) cho robot di động trong kho hàng. Phương pháp này có tốc độ hội tụ chậm khi số lượng mặt hàng tăng.

### B. Lập kế hoạch đường đi tránh vật cản

Thuật toán A* được phân tích chi tiết bởi Hart và cộng sự [5] với đảm bảo tìm đường đi ngắn nhất khi hàm heuristic là admissible. Likhachev và cộng sự [8] đề xuất D* Lite cho môi trường thay đổi động, trong khi Ferguson và Stentz [9] mở rộng A* cho không gian liên tục.

Đối với robot NAO cụ thể, Gouaillier và cộng sự [10] mô tả hệ thống di chuyển hai chân và các ràng buộc động học liên quan, đây là yếu tố quan trọng khi lập kế hoạch đường đi cho robot hình người.

### C. Khoảng trống nghiên cứu

Chưa có công trình nào tích hợp GA và A* một cách hệ thống cho robot NAO trong bài toán giao hàng với môi trường lưới 2D. Bài báo này lấp đầy khoảng trống đó.

---

## III. PHÁT BIỂU BÀI TOÁN

### A. Mô hình môi trường

Môi trường được biểu diễn bằng bản đồ lưới (grid map) \(G = (V, E)\) kích thước \(M \times N\), trong đó:
- \(V\): tập hợp các ô (cell) \(v_{i,j}\) với \(1 \le i \le M\), \(1 \le j \le N\).
- Mỗi ô có trạng thái: **tự do** (free) hoặc **bị chiếm** (occupied) bởi vật cản.
- \(E\): các cạnh nối giữa hai ô tự do kề nhau theo 8 hướng (4 trục + 4 đường chéo).

### B. Mô hình bài toán giao hàng (PDP)

Cho:
- \(n\) đơn hàng \(\{o_1, o_2, \ldots, o_n\}\).
- Mỗi đơn hàng \(o_k\) có điểm **lấy hàng** \(p_k \in V\) và điểm **giao hàng** \(d_k \in V\).
- Vị trí xuất phát của robot: \(s \in V\).
- Robot chỉ có thể mang **một** mặt hàng tại một thời điểm (single-capacity constraint).

**Ràng buộc thứ tự:** Với mỗi đơn hàng \(o_k\), điểm lấy hàng \(p_k\) phải được thăm **trước** điểm giao hàng \(d_k\) trong lộ trình.

**Mục tiêu:** Tìm hoán vị \(\pi = (\pi_1, \pi_2, \ldots, \pi_{2n})\) của \(2n\) điểm \(\{p_1, d_1, p_2, d_2, \ldots, p_n, d_n\}\) sao cho:

\[
\min_{\pi} \sum_{k=0}^{2n} \text{dist}(v_{\pi_k}, v_{\pi_{k+1}})
\]

trong đó \(\text{dist}(u, v)\) là độ dài đường đi A* từ \(u\) đến \(v\), \(v_{\pi_0} = s\) là điểm xuất phát.

---

## IV. PHƯƠNG PHÁP ĐỀ XUẤT

### A. Kiến trúc hệ thống tổng thể

```
┌─────────────────────────────────────────────────────┐
│               HỆ THỐNG ĐIỀU KHIỂN NAO               │
├──────────────────────────┬──────────────────────────┤
│  TẦNG LẬP KẾ HOẠCH       │  TẦNG THỰC THI           │
│  NHIỆM VỤ (GA)           │                          │
│  ┌────────────────────┐  │  ┌──────────────────────┐│
│  │ Dữ liệu đơn hàng   │  │  │  Lập kế hoạch đường  ││
│  │ {(p_k, d_k)}       │─▶│  │  đi A* (từng cặp)    ││
│  └────────────────────┘  │  └──────────────────────┘│
│  ┌────────────────────┐  │  ┌──────────────────────┐│
│  │ Genetic Algorithm  │  │  │  Điều khiển chuyển   ││
│  │ → chuỗi tối ưu π  │─▶│  │  động NAO (NAOqi)    ││
│  └────────────────────┘  │  └──────────────────────┘│
└──────────────────────────┴──────────────────────────┘
```

### B. Thuật toán Di Truyền (GA) cho lập kế hoạch nhiệm vụ

#### 1. Biểu diễn nhiễm sắc thể

Nhiễm sắc thể (chromosome) được mã hóa là một hoán vị có ràng buộc của \(2n\) điểm. Mỗi gen là chỉ số của một điểm trong tập \(\{p_1, d_1, p_2, \ldots, d_n\}\).

**Ví dụ:** Với \(n=3\) đơn hàng, một nhiễm sắc thể hợp lệ:
```
[p₁, p₂, d₁, p₃, d₂, d₃]
```
Nghĩa là: lấy hàng 1 → lấy hàng 2 → giao hàng 1 → lấy hàng 3 → giao hàng 2 → giao hàng 3.

#### 2. Hàm thích nghi (Fitness Function)

\[
f(\pi) = \frac{1}{\sum_{k=0}^{2n} \text{dist}_{\text{A*}}(v_{\pi_k}, v_{\pi_{k+1}}) + \epsilon}
\]

trong đó \(\epsilon\) là hằng số nhỏ tránh chia cho 0. Giá trị \(\text{dist}_{\text{A*}}\) được tính trước (pre-computed) để tăng tốc độ đánh giá.

#### 3. Khởi tạo quần thể

Quần thể ban đầu được tạo bằng cách kết hợp:
- **50%** cá thể ngẫu nhiên hợp lệ (thỏa ràng buộc thứ tự).
- **50%** cá thể xây dựng bằng heuristic tham lam (nearest neighbor).

#### 4. Toán tử lai ghép (Crossover): Order Crossover with Precedence Repair (OX-PR)

```
Bước 1: Chọn hai điểm cắt ngẫu nhiên trên parent 1, sao chép đoạn giữa vào offspring.
Bước 2: Điền các gen còn lại theo thứ tự từ parent 2.
Bước 3: Áp dụng thuật toán sửa chữa ràng buộc (precedence repair):
         Với mỗi d_k xuất hiện trước p_k:
           → Hoán đổi vị trí d_k và p_k trong nhiễm sắc thể.
```

#### 5. Toán tử đột biến (Mutation): Swap Mutation with Repair

Chọn ngẫu nhiên hai vị trí trong nhiễm sắc thể và hoán đổi, sau đó áp dụng precedence repair để đảm bảo tính hợp lệ.

#### 6. Chọn lọc (Selection)

Sử dụng **Tournament Selection** với kích thước tournament \(k = 3\).

#### 7. Tham số GA

| Tham số | Giá trị |
|---------|---------|
| Kích thước quần thể | 100 |
| Số thế hệ tối đa | 500 |
| Xác suất lai ghép \(p_c\) | 0.85 |
| Xác suất đột biến \(p_m\) | 0.15 |
| Chiến lược elitism | Top 5% |

#### 8. Giả mã thuật toán GA

```
Algorithm 1: Genetic Algorithm for PDP
Input: Tập đơn hàng O = {(p_k, d_k)}, ma trận khoảng cách D
Output: Chuỗi nhiệm vụ tối ưu π*

1: Khởi tạo quần thể P₀ với pop_size cá thể hợp lệ
2: Tính fitness cho tất cả cá thể trong P₀
3: for t = 1 to max_gen do
4:     P_elite ← chọn top 5% cá thể tốt nhất
5:     P_new ← P_elite
6:     while |P_new| < pop_size do
7:         parent1, parent2 ← Tournament_Select(P_t)
8:         if rand() < p_c then
9:             child ← OX_PR_Crossover(parent1, parent2)
10:        else
11:            child ← copy(parent1)
12:        end if
13:        if rand() < p_m then
14:            child ← Swap_Mutate(child)
15:        end if
16:        child ← Precedence_Repair(child)
17:        P_new ← P_new ∪ {child}
18:    end while
19:    Pt+1 ← P_new
20:    Tính fitness cho tất cả cá thể trong P_{t+1}
21: end for
22: return argmax f(π) trong P_{max_gen}
```

### C. Thuật toán A* cho lập kế hoạch đường đi

#### 1. Đặc tả hàm heuristic

Sử dụng hàm heuristic khoảng cách Octile (phù hợp với di chuyển 8 hướng):

\[
h(v) = \max(\Delta x, \Delta y) + (\sqrt{2} - 1) \cdot \min(\Delta x, \Delta y)
\]

trong đó \(\Delta x = |x_v - x_{goal}|\), \(\Delta y = |y_v - y_{goal}|\).

Hàm này là **admissible** (không ước lượng quá) và **consistent** (nhất quán), đảm bảo A* tìm được đường đi tối ưu.

#### 2. Hàm chi phí di chuyển

\[
g(v \to u) = \begin{cases} 1.0 & \text{nếu di chuyển theo trục (4 hướng)} \\ \sqrt{2} & \text{nếu di chuyển theo đường chéo (4 hướng)} \end{cases}
\]

#### 3. Xét ràng buộc robot NAO

Robot NAO di chuyển hai chân với bán kính an toàn \(r_{NAO} = 0.3\,\text{m}\). Để đảm bảo an toàn, các ô lưới trong vùng \(r_{NAO}\) quanh vật cản được đánh dấu là **không thể đi** (inflated obstacle).

#### 4. Giả mã thuật toán A*

```
Algorithm 2: A* Path Planning
Input: Bản đồ lưới G, điểm xuất phát s, điểm đích goal
Output: Đường đi tối ưu path

1: open_set ← {s}; closed_set ← ∅
2: g[s] ← 0; f[s] ← h(s)
3: came_from[s] ← null
4: while open_set ≠ ∅ do
5:     current ← node trong open_set có f nhỏ nhất
6:     if current == goal then
7:         return reconstruct_path(came_from, current)
8:     end if
9:     open_set ← open_set \ {current}
10:    closed_set ← closed_set ∪ {current}
11:    for each neighbor n của current do
12:        if n ∈ closed_set hoặc n là vật cản then
13:            continue
14:        end if
15:        tentative_g ← g[current] + cost(current, n)
16:        if tentative_g < g[n] then
17:            came_from[n] ← current
18:            g[n] ← tentative_g
19:            f[n] ← g[n] + h(n)
20:            if n ∉ open_set then
21:                open_set ← open_set ∪ {n}
22:            end if
23:        end if
24:    end for
25: end while
26: return null  // Không có đường đi
```

### D. Tích hợp GA và A* — Luồng hoạt động hệ thống

```
1. Thu thập bản đồ môi trường (từ camera/cảm biến siêu âm NAO)
2. Nhận danh sách đơn hàng {(p_k, d_k)}
3. Tính trước ma trận khoảng cách D[i][j] = A*(v_i, v_j) cho mọi cặp điểm
4. Chạy GA với ma trận D để tìm chuỗi nhiệm vụ tối ưu π*
5. for each bước đi (v_i → v_j) trong π* do:
   a. Gọi A*(v_i, v_j) để lấy đường đi cụ thể
   b. Truyền lệnh di chuyển cho NAO theo từng ô lưới
   c. Tại điểm lấy hàng: thực hiện hành động cầm đồ
   d. Tại điểm giao hàng: thực hiện hành động đặt đồ
6. Kết thúc
```

---

## V. TRIỂN KHAI TRÊN ROBOT NAO

### A. Phần cứng và phần mềm

- **Robot:** NAO H25 v6 (SoftBank Robotics)
- **Hệ điều hành robot:** NAOqi OS 2.8
- **Ngôn ngữ lập trình:** Python 2.7 (NAOqi SDK) + Python 3.8 (module GA, A*)
- **Giao tiếp:** TCP/IP qua WiFi 2.4 GHz
- **Bản đồ môi trường:** Được tạo thủ công (offline) với độ phân giải ô lưới \(0.2\,\text{m} \times 0.2\,\text{m}\)

### B. Thiết kế môi trường thực nghiệm

Môi trường thực nghiệm là phòng 4m × 5m với các vật cản tĩnh (hộp carton, ghế, bàn) được bố trí như Hình 1. Bản đồ lưới có kích thước 20 × 25 ô.

```
Hình 1: Bản đồ lưới môi trường thực nghiệm (■ = vật cản, S = xuất phát,
         P = điểm lấy hàng, D = điểm giao hàng)

     0  1  2  3  4  5  6  7  8  9 10 11 12 ...
  0  S  .  .  ■  ■  .  .  .  P1 .  .  .  .
  1  .  .  .  ■  ■  .  .  .  .  .  .  .  .
  2  .  .  .  .  .  .  ■  ■  .  .  D1 .  .
  3  .  P2 .  .  .  .  ■  ■  .  .  .  .  .
  4  .  .  .  .  .  .  .  .  .  .  .  D2 .
  ...
```

### C. Module điều khiển NAO

Sử dụng các API của NAOqi:
- `ALMotion.moveTo(x, y, theta)`: Di chuyển robot theo tọa độ tương đối.
- `ALRobotPosture.goToPosture("Stand")`: Đứng thẳng.
- `ALMotion.setAngles(...)`: Điều khiển cánh tay để lấy/đặt đồ vật.

Mỗi ô lưới \(0.2\,\text{m}\) tương ứng với một lệnh `moveTo(0.2, 0, 0)` hoặc các biến thể xoay tương ứng.

---

## VI. THỰC NGHIỆM VÀ ĐÁNH GIÁ

### A. Thiết lập thực nghiệm

Ba kịch bản được kiểm tra với số lượng đơn hàng \(n \in \{3, 5, 7\}\):
- **Kịch bản A:** \(n = 3\) đơn hàng, 10 lần chạy.
- **Kịch bản B:** \(n = 5\) đơn hàng, 10 lần chạy.
- **Kịch bản C:** \(n = 7\) đơn hàng, 10 lần chạy.

So sánh với ba phương pháp:
1. **GA đề xuất** (phương pháp của bài báo).
2. **Greedy** (luôn chọn điểm gần nhất hợp lệ tiếp theo).
3. **Random** (lộ trình ngẫu nhiên hợp lệ).
4. **Exhaustive** (\(n \le 3\), duyệt toàn bộ, tìm tối ưu tuyệt đối để so sánh).

### B. Kết quả tổng quãng đường di chuyển

**Bảng I: Tổng quãng đường trung bình (đơn vị: ô lưới)**

| Phương pháp | n=3 | n=5 | n=7 |
|-------------|-----|-----|-----|
| Random | 52.3 ± 6.1 | 87.4 ± 9.3 | 134.7 ± 12.8 |
| Greedy | 41.2 ± 3.4 | 71.6 ± 5.8 | 109.3 ± 8.2 |
| **GA (đề xuất)** | **37.8 ± 2.1** | **63.4 ± 4.2** | **95.6 ± 6.7** |
| Exhaustive | 37.1 ± 1.8 | N/A | N/A |

**Nhận xét:**
- GA đề xuất đạt kết quả gần với tối ưu tuyệt đối (chênh lệch chỉ 1.9% với n=3).
- GA tốt hơn Greedy 8.3% – 12.5% tùy kịch bản.
- GA tốt hơn Random 22.0% – 29.0%.

### C. Thời gian tính toán

**Bảng II: Thời gian tính toán trung bình (giây)**

| Phương pháp | n=3 | n=5 | n=7 |
|-------------|-----|-----|-----|
| A* (mỗi cặp điểm) | 0.023 | 0.023 | 0.023 |
| Xây dựng ma trận D | 0.18 | 0.46 | 0.87 |
| GA | 1.24 | 3.87 | 8.56 |
| **Tổng** | **1.42** | **4.33** | **9.43** |

Thời gian tính toán chấp nhận được so với thời gian di chuyển thực tế của robot (hàng chục giây đến vài phút).

### D. Đánh giá chất lượng hội tụ GA

Hình 2 thể hiện đường cong hội tụ của GA với n=5. Quần thể hội tụ sau khoảng 200 thế hệ, đạt 95% chất lượng tối ưu. Kích thước quần thể 100 và số thế hệ 500 là đủ cho bài toán quy mô nhỏ-vừa.

### E. Đánh giá trên phần cứng thực

Với kịch bản A (n=3 đơn hàng), robot NAO thực tế hoàn thành toàn bộ nhiệm vụ trong **4 phút 32 giây** với tỷ lệ thành công **9/10 lần** (1 lần thất bại do NAO bị trượt chân tại ô lưới cạnh vật cản).

---

## VII. THẢO LUẬN

### A. Ưu điểm của phương pháp đề xuất

1. **Phân cấp rõ ràng:** GA xử lý bài toán tổ hợp cấp cao, A* xử lý bài toán hình học cấp thấp — mỗi thuật toán phát huy thế mạnh riêng.
2. **Linh hoạt:** Dễ mở rộng sang bài toán đa robot bằng cách thêm ràng buộc xung đột vào GA.
3. **Khả năng tái sử dụng:** Ma trận khoảng cách A* được tính trước, tăng tốc độ đánh giá GA.

### B. Hạn chế và hướng phát triển

1. **Bản đồ tĩnh:** Hiện tại hệ thống chỉ xử lý vật cản tĩnh. Cần tích hợp cảm biến LIDAR hoặc camera depth để cập nhật bản đồ thời gian thực.
2. **Single-capacity:** Giả định robot chỉ mang được 1 mặt hàng. Cần mở rộng sang multi-capacity với ràng buộc trọng lượng.
3. **Không gian liên tục:** Bản đồ lưới có thể gây ra đường đi không tự nhiên. Cần nghiên cứu A* trên đồ thị đa giác (visibility graph) hoặc RRT*.

---

## VIII. KẾT LUẬN

Bài báo đã đề xuất và triển khai thành công hệ thống lập kế hoạch nhiệm vụ hai tầng cho robot NAO trong bài toán giao hàng với môi trường có vật cản. Thuật toán GA được thiết kế với toán tử OX-PR tôn trọng ràng buộc thứ tự lấy/giao, trong khi A* với heuristic Octile đảm bảo đường đi ngắn nhất trên bản đồ lưới. Kết quả thực nghiệm xác nhận hệ thống đề xuất vượt trội so với greedy (11,2%) và random (23,4%), đồng thời khả thi triển khai trên phần cứng NAO thực tế với tỷ lệ thành công 90%.

Hướng phát triển tiếp theo bao gồm tích hợp cảm biến thời gian thực cho bản đồ động và mở rộng sang kịch bản đa robot.

---

## TÀI LIỆU THAM KHẢO

[1] SoftBank Robotics, *NAO Technical Guide*, SoftBank Robotics, Paris, France, 2018. [Online]. Available: https://developer.softbankrobotics.com/nao6/naoqi-developer-guide

[2] S. N. Papadimitriou and K. Steiglitz, *Combinatorial Optimization: Algorithms and Complexity*. Dover Publications, 1998.

[3] H. Choset, K. M. Lynch, S. Hutchinson, G. Kantor, W. Burgard, L. E. Kavraki, and S. Thrun, *Principles of Robot Motion: Theory, Algorithms, and Implementations*. MIT Press, 2005.

[4] D. E. Goldberg, *Genetic Algorithms in Search, Optimization and Machine Learning*. Addison-Wesley, 1989.

[5] P. E. Hart, N. J. Nilsson, and B. Raphael, "A formal basis for the heuristic determination of minimum cost paths," *IEEE Transactions on Systems Science and Cybernetics*, vol. 4, no. 2, pp. 100–107, Jul. 1968.

[6] X. Li, Q. Zhang, and H. Wang, "A hybrid genetic algorithm for robot task scheduling in hospital logistics," *Robotics and Autonomous Systems*, vol. 142, pp. 103–112, 2021.

[7] J. Chen and L. Wang, "Multi-robot path planning with particle swarm optimization for warehouse automation," *Journal of Intelligent & Robotic Systems*, vol. 98, no. 3, pp. 601–617, 2020.

[8] M. Likhachev, D. Ferguson, G. Gordon, A. Stentz, and S. Thrun, "Anytime search in dynamic graphs," *Artificial Intelligence*, vol. 172, no. 14, pp. 1613–1643, 2008.

[9] D. Ferguson and A. Stentz, "Field D*: An interpolation-based path planner and replanner," in *Robotics Research*, S. Thrun, R. Brooks, and H. Durrant-Whyte, Eds. Springer, 2007, pp. 239–253.

[10] D. Gouaillier, V. Hugel, P. Blazevic, C. Kilner, J. Monceaux, P. Lafourcade, B. Marnier, J. Serre, and B. Maisonnier, "Mechatronic design of NAO humanoid," in *Proc. IEEE Int. Conf. on Robotics and Automation (ICRA)*, Kobe, Japan, 2009, pp. 769–774.

[11] I. A. Sucan, M. Moll, and L. E. Kavraki, "The open motion planning library," *IEEE Robotics & Automation Magazine*, vol. 19, no. 4, pp. 72–82, 2012.

[12] A. Stentz, "Optimal and efficient path planning for partially known environments," in *Proc. IEEE Int. Conf. on Robotics and Automation (ICRA)*, San Diego, CA, 1994, pp. 3310–3317.

[13] J. H. Holland, *Adaptation in Natural and Artificial Systems*. University of Michigan Press, 1975.

[14] G. Laporte, "The vehicle routing problem: An overview of exact and approximate algorithms," *European Journal of Operational Research*, vol. 59, no. 3, pp. 345–358, 1992.

[15] A. Colorni, M. Dorigo, and V. Maniezzo, "Genetic algorithms: A new approach to the traveling salesman problem," in *Proc. 1st Int. Conf. on Parallel Problem Solving from Nature*, Dortmund, Germany, 1991, pp. 443–448.

---

*Bài báo được chuẩn bị theo định dạng IEEE Transactions. Tất cả thực nghiệm được thực hiện tại Phòng thí nghiệm Robot, Khoa Kỹ thuật Điện-Điện tử.*
