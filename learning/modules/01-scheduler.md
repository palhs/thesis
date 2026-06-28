# Module 01 — `scheduler/` (đào sâu)

> Bộ máy thời-gian-ảo của simulator. ~40–45 phút. Đây là module *đào sâu* đầu
> tiên, nên có đủ: trace & dự đoán + chạy thật + Phòng thủ.

## 0. Vì sao tồn tại — và nối với phòng thủ

Scheduler là **trái tim của discrete-event simulation**: thay vì chạy thời gian
thực, nó giữ một hàng đợi sự kiện và luôn xử lý **sự kiện sớm nhất kế tiếp**, nhảy
đồng hồ ảo tới đúng thời điểm đó. Không có sự kiện = không có gì xảy ra (không "chờ"
thật).

Điểm chống lưng phòng thủ: nó xử lý sự kiện theo **một thứ tự toàn phần tất định**
`(t, node_id, seq)`. Cùng `(YAML, seed)` → **chạy lại ra byte y hệt**. Đó là nền
của câu "kết quả của em đáng tin / tái lập được" — RQ nào cũng đứng trên nó.

## 1. Đọc gì, theo thứ tự

1. `wiki/concepts/simulation-design.md` + `simulation-design-runtime.md` — hợp đồng thiết kế (5 quyết định cấu trúc + hợp đồng tất định). **Đọc trước khi mở code.**
2. `src/scheduler/events.py` — các lớp sự kiện (`Delivery`, `TimerFire`, `PhaseAdvance`) + kiểu `SimTime`/`NodeId`/`TimerId`. Ngắn, đọc đầu tiên.
3. `src/scheduler/scheduler.py` — bản thân scheduler (183 dòng). Đọc theo thứ tự: `__init__` → `schedule` → `set_timer`/`cancel_timer` → `bind`/`bind_network` → `run` → `_dispatch`.
4. Test (đặc tả chạy được): `tests/scheduler/test_scheduler.py` (đơn vị), `tests/scheduler/test_e2e.py` (ping-pong end-to-end), `tests/scheduler/test_stress.py` (thứ tự dưới tải).

## 2. Mục tiêu khi đọc (trả lời được là đạt)

- Heap chứa tuple `(t, node_id, seq, event)`. **Vì sao phần tử `event` không bao giờ bị đem so sánh?**
- `schedule()` là "phễu đơn" (single funnel) — nghĩa là gì, ai cũng phải đi qua nó?
- `set_timer` + `cancel_timer` + **lazy tombstone**: hủy timer mà *không* gỡ khỏi heap thì sao vẫn đúng?
- `run()` có **3 điều kiện dừng** — thứ tự kiểm tra? cái nào thắng nếu trùng?
- `bind()` nối *một nửa* API outbound, `bind_network`/`Network.bind` nối nửa kia — "split-bind invariant" là gì?

## 3. Idiom Python sẽ gặp (gloss)

- `@dataclass` — bộ tạo class tự sinh `__init__`/`__repr__`; ở đây `RunResult` chỉ là túi dữ liệu.
- `heapq` — biến một `list` thành **min-heap** (đống nhỏ-nhất-trên-đỉnh). `heappush`/`heappop` giữ phần tử nhỏ nhất ra trước. So sánh tuple là *theo từ điển* (so `t` trước, hòa thì so `node_id`, rồi `seq`).
- `lambda` đóng biến trong `bind()` — `node.set_timer = lambda ...: self.set_timer(node.id, ...)`. Đây là **monkey-patching**: gắn thẳng hàm vào instance `node`, "đóng" (capture) `node.id` để sau này gọi không cần truyền lại id. Mẹo quan trọng — `nodes` không tự biết id mình; scheduler tiêm vào.
- `math.isfinite(t)` — chặn `nan`/`inf`. Nhớ: **mọi so sánh với `nan` đều False**, kể cả `nan < now`.
- `Literal["quiescence","deadline","predicate"]` — chỉ là chú thích kiểu, liệt kê giá trị hợp lệ.

## 4. Khái niệm gloss

- **virtual clock** (`self._now`) — đồng hồ ảo, chỉ nhảy khi pop một sự kiện; read-only với node (node nhận `t` làm tham số).
- **quiescence** — heap rỗng = hệ "lặng", không còn gì để làm → dừng tự nhiên.
- **lazy tombstone** — hủy timer chỉ xóa khỏi `registry` (O(1)); entry cũ vẫn nằm trên heap như "bia mộ", lúc pop ra mới phát hiện không khớp `seq` và bỏ qua.
- **byte-identical replay** — chạy lại cho ra *dòng sự kiện y hệt từng byte*; bằng chứng tất định.

## 5. Grill — trace & dự đoán (cuối buổi; đoán xong ta CHẠY THẬT để chấm)

> Cách chạy chấm: `make test-scheduler`, hoặc một test cụ thể, vd
> `PYTHONPATH=src:tests/scheduler python3 -m unittest tests.scheduler.test_scheduler -v`.

1. Hai sự kiện cùng `t`, cùng `node_id`. Cái nào pop ra trước, **nhờ trường nào**?
2. Trong `schedule()`, kiểm tra `math.isfinite(t)` đặt *trước* `t < self._now`. **Đảo thứ tự hai dòng đó thì input nào lọt lưới và phá heap?**
3. `set_timer(node=2, timer_id="vc")` (giả sử seq=5) → rồi `cancel_timer(2,"vc")`. Khi entry đó được pop ra trong `run()`, **chuyện gì xảy ra**?
4. `set_timer(2,"vc")` *hai lần* (seq 5 rồi 9), không hủy. Timer fire **mấy lần**, và là lần nào?
5. Heap còn 1 sự kiện ở `t=10`, và gọi `run(t_max=10)`. Trả về `stopped_by` = gì — `"deadline"` hay `"quiescence"`?
6. Pop ra một `PhaseAdvance` nhưng chưa gọi `bind_network()`. Kết quả?

<details><summary>ĐÁP ÁN</summary>

1. Nhờ **`seq`**. `seq` tăng đơn điệu *theo từng node* (`_next_seq`), nên `(t,node_id,seq)`
   là duy nhất theo cấu trúc → heapq **không bao giờ phải so tới phần tử `event`** (đó
   là lý do `event` — vốn không so sánh được — vẫn nằm trong tuple an toàn).
2. Một `t = nan`. Vì `nan < now` là **False**, nếu kiểm tra past-time chạy trước thì
   `nan` lọt qua, bị push vào heap; mọi so sánh với `nan` là False → thứ tự heap hỏng,
   phá tất định. Vì thế `isfinite` phải đứng trước.
3. **Bị tombstone**: `cancel` đã xóa khóa `(2,"vc")` khỏi `registry`, nên
   `registry.get((2,"vc"))` trả `None` ≠ 5 → `run()` tăng `n_tombstoned`, `continue`,
   *không* gọi `on_timer`.
4. **Fire đúng một lần** — lần seq=9. Lần set thứ hai ghi đè `registry[(2,"vc")] = 9`.
   Entry seq=5 pop ra trước: `get(...) == 9 ≠ 5` → tombstone. Entry seq=9: khớp → fire.
5. **`"deadline"`**. Đầu mỗi vòng lặp, điều kiện deadline (`now >= t_max`) được kiểm
   *trước* điều kiện heap-rỗng. (Lưu ý tinh: deadline so với `self._now` *hiện tại*;
   tùy `now` đã tới 10 chưa mà nó có thể pop sự kiện trước — chạy thật để thấy.)
6. **`RuntimeError`**: `_dispatch` thấy `PhaseAdvance` mà `self.network is None` → ném
   "PhaseAdvance with no network bound; call bind_network() first" (fail-fast).
</details>

## 6. Phòng thủ (câu hội đồng dễ hỏi về đúng phần này)

- **"Mô phỏng tất định thì có còn phản ánh mạng thật không?"** → Tất định là về *tái
  lập*, không phải *đơn điệu*: tính ngẫu nhiên (trễ, mất gói, chọn mẫu) vẫn có, nhưng
  do **một seed** điều khiển nên chạy lại tái hiện được. Đổi seed = một thế giới mạng
  khác; ta sweep nhiều seed rồi báo CI. Neo: `wiki/concepts/reproducibility.md`, mục
  threats-to-validity trong `drafts/ch3_methodology.md`.
- **"Sao tự viết min-heap thay vì dùng thư viện sự kiện có sẵn?"** → để *làm chủ quy
  tắc phá-hòa* (tie-break) `(t, node_id, seq)` — chính nó bảo chứng thứ tự toàn phần
  tất định; thư viện ngoài không cho kiểm soát chỗ đó. Neo: `simulation-design.md` §3
  (5 quyết định cấu trúc, D1/D2).
- **"`p_drop` / trễ là ngẫu nhiên — sao kết quả lại tái lập?"** → mọi nguồn ngẫu nhiên
  rút từ RNG seed-hóa theo node/network (xem module 03 + `concepts/reproducibility`);
  scheduler bản thân *không* có RNG. Neo: `simulation-design-runtime.md` §1.

## 7. Giải thích lại + ghi sổ

Giải thích cho tôi (Feynman) trong ~5 câu: *một vòng lặp `run()` làm gì, và vì sao
3 trường `(t,node_id,seq)` là đủ để chạy lại ra byte y hệt.* Rồi cập nhật `progress.md`
dòng `01 · scheduler`. Mang sang module 02 câu hỏi: *"node nhận được `set_timer`/`emit`
từ đâu?"* — câu trả lời là `bind()` ở đây, nhưng *phía node* trông thế nào thì module
`nodes` mới rõ.
