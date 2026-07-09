# Module 02 — `nodes/` (đào sâu)

> Lớp **validator** (`Node`): mọi node giao thức đứng trên nó. ~40–45 phút. Module
> *đào sâu* nên có đủ: trace & dự đoán + chạy thật + Phòng thủ.
>
> Nối tiếp Module 01: câu mang sang là *"node nhận `set_timer`/`emit`/`send` từ
> đâu?"* — nửa đầu đã thấy ở scheduler (`bind()` tiêm lambda). Module này nhìn từ
> **phía node**: vì sao trước khi bind, gọi `send` lại *nổ* `RuntimeError`.

## 0. Vì sao tồn tại — và nối với phòng thủ

`Node` là **API chung của một validator**. Bất kể PBFT, Casper FFG hay Snowman, mọi
node đều: có danh tính (`id`/`weight`), đi qua cùng một vòng đời (`created → running
→ halted`), nhận cùng ba hook vào (`start`/`on_message`/`on_timer`), và gọi cùng một
bộ API ra (`send`/`broadcast`/`set_timer`/`emit`). Chỉ **bộ não giao thức** (FSM —
máy trạng thái quyết định) là khác nhau, và nó nằm trong **subclass**.

Đây là **"two-layer commitment"** (cam kết hai tầng) — ý tưởng chống lưng lớn nhất
của trang `node-model.md`:

- **Tầng chung (lifecycle):** đồng nhất tuyệt đối. Cho phép scheduler lái *mọi* node
  y hệt nhau, và cho phép metric layer (T40) đếm `decided`/`halted` mà không cần biết
  giao thức nào.
- **Tầng FSM per-protocol:** *cố tình không* hợp nhất. Ép một từ vựng trạng thái
  chung lên 3 giao thức cơ chế khác nhau sẽ **phá fidelity** (vd biến vòng poll của
  Snowman thành "pha bỏ phiếu ma"). Việc so sánh chéo để dành cho **tầng metric**,
  không phải tầng FSM.

Điểm chống lưng phòng thủ: *"Sao không dùng chung một FSM cho gọn?"* — trả lời nằm ở
chính ranh giới hai tầng này (neo `node-model.md` §1). Và: mỗi node có **RNG riêng**
seed-hóa theo `(global_seed, node_id)` — đây là mảnh còn thiếu của chuỗi tất định mà
Module 01 mở ra (scheduler *không* có RNG; RNG sống ở node + network).

## 1. Đọc gì, theo thứ tự

1. `wiki/concepts/node-model.md` — hợp đồng thiết kế. **Đọc trước code.** Bốn mục
   xương sống: §1 two-layer, §3 lifecycle + halt reasons, §6 inbound hooks, §7
   outbound API + determinism surface. §4 (FSM) đọc lướt — chi tiết để dành Module
   07–09; §9 (adversary) đọc lướt — để dành Module 12.
2. `src/nodes/lifecycle.py` — hai enum (`Lifecycle`, `HaltReason`). 20 dòng, đọc đầu.
3. `src/nodes/message.py` — `Message` (frozen dataclass envelope). 15 dòng.
4. `src/nodes/node.py` — bản thân `Node` (154 dòng). Đọc theo thứ tự: `_stable_seed`
   → `__init__` (guards + RNG) → khối *inbound protected* (`_on_*` abstract) →
   khối *outbound placeholder* (raise) → khối *inbound public* (`start`/`halt`/
   `on_message`/`on_timer` — lớp guard) → `_emit_decided`.
5. Test (đặc tả chạy được): `tests/nodes/test_node.py` (đơn vị), `tests/nodes/
   test_e2e.py` (ping-pong 2 node qua scheduler thật), `_helpers.py` (`FakeNode` +
   `PingPongNode` + `LoopbackNetwork` — đọc để hiểu test dựng gì).

## 2. Mục tiêu khi đọc (trả lời được là đạt)

- **Template method:** `on_message` (public) vs `_on_message` (protected, abstract).
  Vì sao tách đôi? Lớp public *làm gì* trước khi gọi lớp protected?
- **Split-bind:** năm hàm outbound đều raise `RuntimeError` khi chưa bind. *Ai* ghi
  đè `send`/`broadcast` (→ Network)? *Ai* ghi đè `set_timer`/`cancel_timer`/`emit`
  (→ Scheduler)? (Đây là câu mang sang từ Module 01.)
- **Vòng đời đơn điệu:** `created → running → halted`. Vì sao `halted` không quay lại
  `running` được? Node đã halted nhận thêm message thì sao?
- **Halt idempotent:** halt hai lần → reason nào thắng, emit mấy lần? Vì sao harness
  cần tính chất này?
- **Guard precedence:** node đang `CREATED` bị halt thẳng (bỏ qua `RUNNING`) rồi có
  message tới → **raise hay drop?** Thứ tự hai guard trong `on_message` quyết định.
- **RNG per-node:** vì sao seed = `blake2b(f"{global_seed}:{node_id}")` chứ không phải
  `hash(...)` thuần? (Neo Revision 2026-05-19.)

## 3. Idiom Python sẽ gặp (gloss)

- **`ABC` + `@abstractmethod`** — "abstract base class". `Node(ABC)` với ba
  `@abstractmethod _on_*` ⇒ **không thể `Node(...)` trực tiếp** (raise `TypeError`);
  phải subclass và cài đủ ba hook. Đây là cách ép "tầng FSM per-protocol phải có mặt".
- **Template method pattern** — hàm *public* (`on_message`) chứa phần khung chung
  (kiểm tra lifecycle), rồi *ủy quyền* xuống hàm *protected* (`_on_message`) mà
  subclass cài. Tên có gạch dưới `_` = "nội bộ, đừng gọi từ ngoài". Scheduler gọi
  bản public; giao thức override bản protected.
- **Monkey-patching instance method** — `n.emit = lambda ...`. Gán thẳng một hàm vào
  *một instance* (không phải cả class). Đây chính là cái `bind()` làm: đè placeholder
  `raise RuntimeError` bằng lambda thật. (Đã gặp phía scheduler ở Module 01; giờ thấy
  phía node là cái *bị* đè.)
- **`typing.Protocol`** — `AdversaryProfile(Protocol)`: "structural typing" (vịt-gõ
  có kiểm kiểu). Ở đây chỉ là **khe cắm rỗng có kiểu** — T22 giữ khe `self.adversary`
  mà không ngó vào trong; T18 mới cắm chiến lược thật. `_is_protocol` = cờ runtime
  đánh dấu một class là Protocol.
- **`@dataclass(frozen=True)`** — `Message` bất biến: tạo xong không sửa field được
  (gán lại → `FrozenInstanceError`). Envelope "đông cứng" nên an toàn khi truyền qua
  mạng/nhiều node.
- **`hashlib.blake2b(...).digest()` + `int.from_bytes(...,"big")`** — băm chuỗi seed
  thành 8 byte, rồi đọc 8 byte đó thành số nguyên big-endian ⇒ một seed **ổn định
  giữa các tiến trình/máy** (khác với `hash()` bị process-randomised).
- **`is` với enum** — `self.status is Lifecycle.HALTED`: enum là singleton nên so
  bằng `is` (đồng nhất) đúng và nhanh hơn `==`.
- **`math.isfinite(weight)`** — chặn `nan`/`inf`. Nhớ bẫy: `nan < 0` là **False**,
  nên chỉ check `weight < 0` sẽ *lọt* `nan` — phải `isfinite` trước (song song đúng
  cái bẫy `isfinite` của scheduler ở Module 01).

## 4. Khái niệm gloss

- **validator** — một node tham gia đồng thuận (đề xuất/bỏ phiếu/chốt). Trong sim mỗi
  validator = một instance `Node`-subclass.
- **FSM (finite-state machine, máy trạng thái hữu hạn)** — "bộ não giao thức": tập
  trạng thái + luật chuyển (vd PBFT `idle→pre_prepared→prepared→committed`). Sống
  trong subclass, một *instance FSM cho mỗi quyết định* (mỗi `(view,seq)`, mỗi epoch,
  mỗi block).
- **lifecycle vs FSM** — hai máy trạng thái *khác nhau chồng lên nhau*: lifecycle
  (`created/running/halted`) là chung, thô; FSM là riêng, mịn. Node đang `running`
  thì FSM chạy bên trong; `halted` thì dừng tất cả.
- **halt reason** — lý do dừng: `run_end` (hết giờ, harness), `crashed` (harness tiêm
  lỗi / adversary không tham gia — Module 12), `slashed`/`exited` (chỉ Casper FFG, do
  FSM). Partition mạng **không** phải halt reason (node bị cô lập vẫn `running`; cô
  lập do network layer lo — Module 03).
- **split-bind invariant** — API ra của node bị *chẻ đôi chủ sở hữu*: **Scheduler**
  sở hữu `set_timer`/`cancel_timer`/`emit` (thời gian + quan sát); **Network** sở hữu
  `send`/`broadcast` (truyền tin). Trước khi cả hai bind xong, gọi bất kỳ hàm nào →
  `RuntimeError` fail-fast.
- **per-node RNG** — mỗi node một `random.Random` seed-hóa từ `(global_seed, node_id)`.
  Hai node khác id → hai dòng ngẫu nhiên độc lập; cùng node + cùng seed hai lần chạy →
  dòng y hệt. Đây là mắt xích tất định mà scheduler thiếu.

## 5. Grill — trace & dự đoán (cuối buổi; đoán xong ta CHẠY THẬT để chấm)

> Cách chạy chấm: `make test-nodes`, hoặc một test cụ thể, vd
> `PYTHONPATH=src:tests/nodes python3 -m unittest tests.nodes.test_node -v`.

1. Gọi thẳng `Node(0, 1.0, None, 0)` (không qua subclass). **Kết quả?** Vì trường nào
   của class chặn?
2. `FakeNode().send(1, "X", None, 0.0)` — gọi *ngay sau khi tạo*, chưa bind gì.
   **Kết quả?** Và nếu đã `sched.bind(n)` nhưng *chưa* `net.bind(n)` thì `send` chạy
   được chưa?
3. `FakeNode(weight=math.nan)`. **Raise hay nhận?** Nếu code chỉ có dòng `weight < 0`
   mà bỏ `isfinite`, `nan` có lọt không?
4. Node đang `running`. Gọi `halt(CRASHED, 9.0)` rồi `halt(RUN_END, 12.0)`. Cuối cùng
   `_halt_reason` = gì, và sự kiện `halted` được emit **mấy lần**?
5. Node vừa tạo (đang `CREATED`, *chưa* `start`). Gọi `halt(RUN_END, 7.0)`, rồi
   `on_message(msg, 8.0)`. Câu `on_message` **raise `RuntimeError` (vì chưa start) hay
   drop im lặng (vì đã halted)?** Thứ tự hai guard quyết định điều gì?
6. Chạy e2e `_run(global_seed=42, budget=4)` (ping-pong 2 node). Node **nào** đi trọn
   `decided → halted`, node nào kẹt lại? `result.stopped_by` = `"quiescence"` hay
   `"deadline"`?

<details><summary>ĐÁP ÁN</summary>

1. **`TypeError`** — `Node(ABC)` có ba `@abstractmethod` (`_on_start`/`_on_message`/
   `_on_timer`) chưa cài; Python cấm khởi tạo abstract class còn abstract method.
   Test: `test_node_is_abstract`.
2. **`RuntimeError`** ("send called before Network.bind()"). Placeholder mặc định của
   `send` chỉ raise. Và **chưa** — `sched.bind` chỉ đè `set_timer`/`cancel_timer`/
   `emit`; `send`/`broadcast` do **`Network.bind`** đè. Đây chính là split-bind: cần
   *cả hai* bên bind (đúng câu mang sang từ Module 01). Test: `test_send_raises_before_bind`.
3. **`ValueError`** (thông điệp chứa "finite"). `__init__` check `math.isfinite(weight)`
   *trước* `weight < 0`. Nếu bỏ `isfinite`: `nan < 0` là **False** ⇒ `nan` **lọt qua**
   thành weight hợp lệ (rồi phá số học ngưỡng sau này). Cùng một cái bẫy `nan` như
   scheduler grill #2. Test: `test_nan_weight_rejected`.
4. `_halt_reason = HaltReason.CRASHED` (**lần đầu thắng**); emit **đúng 1 lần**. `halt`
   thấy `status is HALTED` ở lần hai → `return` ngay, không đổi reason, không emit.
   *Vì sao harness cần:* cuối run nó **blanket-halt mọi node** bằng `RUN_END`; node nào
   đã crashed/slashed rồi phải **giữ nguyên** lý do thật. Test:
   `test_second_halt_is_noop_and_keeps_first_reason`.
5. **Drop im lặng** (không raise). Trong `on_message`, guard `if status is HALTED:
   return` đứng **trước** guard `if status is CREATED: raise`. Node bị blanket-halt từ
   `CREATED` sẽ nhảy thẳng `CREATED→HALTED` (bỏ qua `RUNNING`, vẫn đơn điệu), và bất kỳ
   message/timer trễ nào tới sau cũng phải **rơi lặng lẽ**, không được nổ. Test:
   `test_halt_from_created_skips_running_and_drops_inbound`.
6. **Node 1** đi trọn `decided→halted`. Node 0 mở màn bằng PING *không* tính là hop của
   nó, nên node 1 luôn đi trước một nhịp, chạm `budget=4` trước → emit decided+halted,
   ngừng trả lời; trao đổi lịm dần. Node 0 kẹt ở `budget-1=3` hops, **không** halt.
   `stopped_by = "quiescence"` (heap cạn, không phải chạm deadline). Test:
   `test_run_reaches_quiescence` + `test_decided_and_halted_events_emitted`.

</details>

## 6. Phòng thủ (câu hội đồng dễ hỏi về đúng phần này)

- **"Sao không hợp nhất một FSM chung cho cả ba giao thức cho dễ so sánh?"** →
  *Two-layer commitment*: tầng lifecycle *đã* hợp nhất (đủ để so sánh liveness qua
  `halted`/`decided`); nhưng ép hợp nhất *tầng FSM* sẽ **phá mechanism fidelity** — vd
  biến vòng poll subsample của Snowman thành "pha bỏ phiếu ma" không có thật. Việc làm
  cho kết quả *commensurable* (so sánh được) là của **tầng metric** (T40 output schema),
  không phải tầng FSM. Neo: `wiki/concepts/node-model.md` §1; `concepts/consensus-families`.
- **"Mỗi node một RNG riêng — thế có còn tái lập được không?"** → Có. Seed rút *tất
  định* từ `blake2b(f"{global_seed}:{node_id}")` (không phải `hash()` thuần vốn bị
  process-randomised). Hai node khác id → hai dòng độc lập; cùng `(global_seed,
  node_id)` hai lần chạy → **byte y hệt**. Đây là mắt xích tất định mà scheduler cố
  tình không giữ (scheduler không có RNG). Neo: `node-model.md` §8 + Revision
  2026-05-19; `concepts/reproducibility.md`.
- **"Vì sao chặn `node_id < 0`?"** → `-1` là **sentinel của `PhaseAdvance`** (sự kiện
  đổi pha mạng, Module 01); một node id âm sẽ *luôn sắp trước mọi node thật* ở cùng `t`
  trong khóa `(t, node_id, seq)` → xáo trộn thứ tự tất định. Guard `ValueError` chặn
  ngay khi tạo. Neo: `node-model.md` §8 Revision 2026-05-27 (T39).
- **"Validator bị cô lập mạng có phải là node đã chết (halted) không?"** → Không.
  *Partition ≠ halt*: node bị cô lập vẫn `running`, chỉ là message của nó không được
  giao — việc cô lập do **network layer** (Module 03) thực thi ở tầng giao message,
  không phải lifecycle. Halt chỉ có 4 lý do: `run_end`/`crashed`/`slashed`/`exited`.
  Neo: `node-model.md` §3.

## 7. Giải thích lại + ghi sổ

Giải thích cho tôi (Feynman) trong ~5 câu: *tại sao `Node` tách đôi thành lớp public
có guard và lớp `_`-protected do subclass cài (template method), và split-bind lấp nốt
câu "node nhận `send`/`set_timer` từ đâu" của Module 01 như thế nào.* Rồi cập nhật
`progress.md` dòng `02 · nodes`.

Mang sang **Module 03 (`network/`)**: câu hỏi *"`Network.bind` đè `send`/`broadcast`
bằng gì, và trễ/mất-gói/partition được tiêm ở đâu để node vẫn `running` mà message
không tới?"* — nửa đầu ta đã thấy phía node (placeholder bị đè); phía network trông
thế nào thì Module 03 mới rõ. Cũng để dành: RNG *network-scoped* (khác RNG per-node ở
đây) là nơi trễ/mất-gói thực sự được rút.
