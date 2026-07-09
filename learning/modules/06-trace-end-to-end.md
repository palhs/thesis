# Module 06 — trace end-to-end (★ ping-pong xuyên tầng lõi)

> Buổi ĐỈNH của chặng 1. ~40 phút. Không đào sâu 1 file, không đọc giao diện —
> đây là module **TRACE**: dựng một kịch bản ping-pong nhỏ, trace tay từng sự
> kiện pop ra khỏi heap, rồi **CHẠY THẬT để chấm**. Mục tiêu duy nhất: thấy cả
> 5 tầng lõi (config → scheduler → nodes → network → event_log) nối thông thành
> **một dòng CSV thật**. Không có mục Phòng thủ ở đây.

## 0. Vì sao tồn tại — đóng câu "YAML+seed → 1 dòng CSV"

Năm buổi qua ta mổ từng tầng riêng lẻ. Buổi này ghép chúng lại và **chạy đường
ống trọn vẹn** một lần, để câu tư tưởng cốt lõi

> *một cấu hình + một seed → một dòng trong CSV kết quả*

thôi là khẩu hiệu và trở thành thứ em tự trace được bằng tay. Neo phòng thủ: khi
hội đồng hỏi "làm sao em biết cả hệ thống chạy đúng và tái lập?", câu trả lời
không phải "em tin thế" mà là *"em trace được từng event từ `start(0.0)` tới dòng
CSV, và chạy lại ra byte y hệt"*. Đây chính là bài tập đó.

Không có FSM giao thức thật ở đây (PBFT = Module 07). Ta dùng **node tối giản**
`BroadcastNode` — start thì broadcast đúng một TOKEN, nhận thì ghi sổ, không
re-broadcast. Nhờ vậy hệ đạt **quiescence** (heap rỗng, "lặng") sau đúng *một
vòng* `n·(n−1)` deliveries — đủ nhỏ để trace tay, đủ thật để thấy cả 5 tầng.

## 1. Đọc gì, theo thứ tự

1. `wiki/concepts/simulation-design.md` §7.2 — **bảng 6-phase bootstrap** (đã gặp
   ở Module 05). Đây là xương sống buổi hôm nay; đọc lại 6 dòng bảng đó trước.
2. `tests/integration/_helpers.py` — harness `build_and_run(nodes, phases, seed)`
   + hai node tối giản `BroadcastNode` / `TimerNode`. **Đây là "run" thật** ta sẽ
   trace. Đọc kỹ hàm `build_and_run`: nó là 6-phase bootstrap viết tường minh.
3. `tests/integration/test_message_exchange.py` — kịch bản ping-pong `n∈{4,7,10}`.
   Ta lấy **n=4, constant delay=10** làm kịch bản hand-trace.
4. `tests/integration/test_ordering.py` — cùng harness nhưng dùng `TimerNode` để
   phơi bày tie-break `(t, node_id, seq)` dưới thứ tự nộp *cố tình đảo*.
5. `tests/integration/test_event_logger_integration.py` — thay sink bắt-tay bằng
   **EventLogger thật** → `logger.to_csv(path)`. Đây là mắt xích đóng câu "→ 1
   dòng CSV". Đọc `_run_with_real_logger`.

## 2. Mục tiêu khi đọc (trả lời được là đạt)

- 6-phase bootstrap trong `build_and_run`: chỉ đúng dòng code cho **từng phase**
  1–6. Vì sao `net.start()` (phase 5) đứng trước `n.start(0.0)` (phase 5 kickoff)?
- Kịch bản n=4 constant-delay: **bao nhiêu** Delivery, **tất cả** ở `t` nào, và
  `events_processed` bằng mấy? `stopped_by` = gì?
- Trong `sink`, vì sao có **hai** bộ lọc `isinstance` — một cho `deliveries`, một
  cho `dispatched`? Cái `("emit", ...)` tuple bị loại ở đâu và tại sao?
- Dòng CSV đầu tiên EventLogger nhả ra cho kịch bản n=4 trông thế nào (5 trường
  `t, node_id, event_type, seq, fields`)?
- Vì sao `logger.records` đã **tự tăng đơn điệu** theo `(t, node_id, seq)` mà
  không cần sort lại — dù `to_csv` vẫn sort? (nối M04)

## 3. Idiom Python sẽ gặp (gloss)

- **Monkey-patch qua `bind`** (nhắc lại M02/M03): `sched.bind(n)` gắn thẳng
  `n.set_timer`/`n.emit`; `net.bind(n)` gắn `n.send`/`n.broadcast`. Sau bind, gọi
  `n.broadcast(...)` là gọi lambda đã "đóng" sẵn `n.id`. Trước bind, cùng tên hàm
  đó chỉ là stub ném `RuntimeError` (fail-fast — thấy ở `node.py:86`).
- **`isinstance(ev, (A, B, C))`** — kiểm tra kiểu với *tuple các lớp* = "là một
  trong các lớp này". `sink` dùng nó để phân biệt event heap thật (`Delivery`/
  `TimerFire`/`PhaseAdvance`) với side-channel `("emit", ...)` (một `tuple` Python
  trần, không phải instance lớp nào ở trên → rớt cả hai `if`).
- **`math.inf`** trong `Phase(0.0, math.inf, ...)` — một phase phủ `[0, ∞)`, tức
  "một synchrony duy nhất, không có ranh giới phase nội bộ" → **không** PhaseAdvance
  nào được arm. Đây là lý do stream n=4 chỉ toàn Delivery.
- **`with self.subTest(n=n)`** — chạy cùng thân test cho nhiều `n`, mỗi `n` báo
  lỗi riêng. Không cốt lõi, chỉ để đọc test khỏi vấp.

## 4. Khái niệm gloss

- **Ping-pong / broadcast round** — ở đây *không* có pong: `BroadcastNode` nhận
  TOKEN nhưng **không** gửi lại (non-recursive). Nên "vòng" chỉ có một chiều: n
  node mỗi node gửi cho n−1 peer → `n·(n−1)` message, rồi tắt.
- **quiescence** (nhắc lại M01) — heap cạn ⇒ `run()` dừng với `stopped_by=
  "quiescence"`. Ở kịch bản này không đặt `t_max` hữu hạn / `stop_when`, nên
  quiescence là cách duy nhất nó dừng.
- **dispatch stream vs delivery stream** — `dispatched` = *mọi* event heap pop ra
  (ở đây = 12 Delivery). `deliveries` = riêng payload của Delivery (src,dst,type,
  t_sent,t_delivered). Với kịch bản n=4 hai stream cùng độ dài 12; khi có timer/
  phase thì dispatch dài hơn.
- **byte-identical CSV** — hai run cùng seed → `a.read_bytes() == b.read_bytes()`.
  Bằng chứng tất định *ở quy mô tích hợp* (không chỉ 1 tầng), test khẳng định ở n=7.

## 5. Grill — trace & dự đoán (đoán xong ta CHẠY THẬT để chấm)

> Cách chạy chấm:
> `PYTHONPATH=src:tests/integration python3 -m unittest test_message_exchange test_ordering test_event_logger_integration -v`
> (hoặc `make test-integration` cho cả suite). Kịch bản neo: **n=4, seed=42,
> `_CONSTANT` = một phase `[0,∞)` delay=10**.

1. **Đếm & thời điểm.** n=4, mỗi node broadcast TOKEN lúc `t=0`, delay hằng =10.
   Heap sau phase 5 chứa bao nhiêu Delivery? Chúng pop ra ở `t` = bao nhiêu?
   `result.events_processed` = ? `result.stopped_by` = ?
2. **Event đầu tiên pop.** Trong 12 Delivery cùng `t=10`, cái nào ra **trước** —
   nêu `(t, node_id, seq)` của nó — và **nhờ trường nào** phá hòa giữa các
   Delivery cùng `t`? (gợi ý: `dst` là node_id của entry heap.)
3. **Dòng CSV đầu.** Với EventLogger thật (`_run_with_real_logger`, n=4), viết ra
   **dòng CSV đầu tiên** dạng `t,node_id,event_type,seq,fields`. `event_type` là
   chuỗi gì? `node_id` của một Delivery là src hay dst?
4. **Side-channel bị loại.** `BroadcastNode` không gọi `emit`. Giả sử đổi nó để
   `_on_start` gọi thêm `self.emit("hello", {})`. Trong `build_and_run.sink`, sự
   kiện `("emit","hello",{})` rơi vào nhánh nào — `deliveries`, `dispatched`, hay
   **không** nhánh nào? Vì sao?
5. **Ordering scramble.** `test_ordering` tạo `TimerNode` theo `reversed(range(n))`
   (node n−1 start & nộp timer *trước*), và mỗi node nộp `late`(t=200) *trước*
   `early1`/`early2`(t=100). Phần tử **đầu tiên** của `fired` là gì? (cả 3 trường)
6. **Tất định.** Chạy `_run_with_real_logger(7, _UNIFORM, 42)` hai lần rồi
   `to_csv`. `a.read_bytes() == b.read_bytes()`? `_UNIFORM` là delay ngẫu nhiên —
   sao vẫn bằng nhau? Nếu run thứ hai đổi seed=7 thì byte có còn bằng?

<details><summary>ĐÁP ÁN</summary>

1. **12 Delivery** (`n·(n−1) = 4·3`), **tất cả ở `t=10`** (gửi lúc t=0 + delay
   hằng 10; delay đông cứng lúc submit — M03). `events_processed = 12`,
   `stopped_by = "quiescence"` (heap cạn sau vòng một chiều, không re-broadcast).
2. Entry heap của một Delivery là `(t_deliver, dst, seq)` (M03). Cùng `t=10`, phá
   hòa **trước hết bằng `dst`** (= node_id nhận), rồi bằng `seq`. Delivery ra đầu
   là cái tới **dst=0** với `seq` nhỏ nhất trong nhóm dst=0. (Chạy thật để đọc
   đúng src của nó — src phụ thuộc thứ tự submit_broadcast; điều chắc chắn là
   `node_id=0` đi trước mọi `node_id≥1`.)
3. `event_type = "delivery"` (một trong 5 hằng event-type, M04). Với Delivery,
   `node_id` trong record là **dst** (event xảy ra *tại* người nhận; đây là lý do
   entry heap khóa theo dst). Nên dòng đầu đại loại:
   `10.0,0,delivery,<seq>,"{'src': <s>, 'dst': 0, 'type': 'TOKEN', ...}"`.
   (Con số `seq` và `src` cụ thể để CHẠY THẬT chốt — cốt là hình dạng 5 trường +
   `event_type="delivery"` + `node_id=dst`.)
4. **Không nhánh nào.** `("emit","hello",{})` là một `tuple` Python trần, không
   phải instance `Delivery`/`TimerFire`/`PhaseAdvance` → rớt cả `if isinstance(ev,
   Delivery)` lẫn `if isinstance(ev, (Delivery,TimerFire,PhaseAdvance))`. Đúng
   *chủ ý*: `deliveries`/`dispatched` chỉ gom event heap; emit là side-channel.
   (EventLogger thật thì *có* nhận emit qua nhánh nhận-cấu-trúc-tuple — M04 — nên
   nó sẽ ghi thêm một record `emit`; nhưng harness bắt-tay ở đây lọc bỏ.)
5. `fired[0] = (100.0, 0, "early1")`. Dù node n−1 start trước và `late` nộp trước,
   dispatch theo `(t, node_id, seq)`: `t=100` thắng `t=200`; trong t=100 thì
   `node_id=0` thắng; trong node 0 thì `early1` (nộp trước → seq nhỏ hơn) thắng
   `early2`. Đây là ba trường tie-break diễn ra cùng lúc — kịch bản dựng riêng để
   phơi cả ba.
6. **Bằng nhau.** `_UNIFORM` rút từ `net_rng` seed-hóa (M03/M05): cùng seed=42 →
   cùng dãy số → cùng timing → cùng byte. Đổi run thứ hai sang **seed=7** thì dãy
   `net_rng` khác → timing khác → **byte KHÁC** (đây chính là cặp
   SameSeed/Divergence của M05, giờ ở quy mô tích hợp trọn 5 tầng).
</details>

## 6. Giải thích lại + ghi sổ

Giải thích cho tôi (Feynman) trong ~6 câu, đi dọc **một** Delivery từ đầu tới
cuối: `n.start(0.0)` → `broadcast` (Node, đã bind bởi Network) → `submit_broadcast`
→ `_try_deliver` đặt entry `(t+delay, dst, seq)` lên heap (Scheduler) → `run()`
pop nó → `_dispatch` gọi `_on_message` (Node) **và** gọi `event_sink` →
`logger.sink` biến nó thành `EventRecord` → `to_csv` in một dòng. Nêu đúng **tầng
nào làm gì** ở mỗi mũi tên. Rồi cập nhật `progress.md` dòng `06 · trace end-to-end`.

Câu mang sang **Module 07 (`pbft/`)**: kịch bản hôm nay dùng `BroadcastNode` *giả*
(nhận rồi im). Thay nó bằng FSM PBFT thật thì "một vòng" không còn là `n·(n−1)`
deliveries phẳng nữa mà là chuỗi **pre-prepare → prepare → commit** với quorum
`2f+1` — và dòng CSV bắt đầu có `event_type="decided"`. Giữ nguyên đường ống 5
tầng đã trace hôm nay; chỉ thay ruột node.
