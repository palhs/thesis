# Module 11 · `delay/` — Họ B (network-delay experiment) ★ đào sâu

> Chặng 5 · Thí nghiệm. Đây là module đào-sâu (CÓ mục Phòng thủ). Câu hỏi cốt
> lõi: **AI gọi `run_grid`?** — M10 dạy *cỗ máy quét lưới*; M11 là *người lái nó*
> để sinh ra dataset Chương 4. Nối thẳng M06 ("1 run → 1 dòng CSV") + M10
> ("1 lưới → CSV thống nhất") vào một *thí nghiệm thật*.

---

## 0 · Vì sao module này tồn tại (neo RQ / hình / chương)

Toàn simulator quy về: *YAML + seed → 1 dòng CSV*. Đến giờ ta đã có:
- **Tầng lõi** (M01–06): một run chạy được.
- **Tầng giao thức** (M07–09): PBFT / Casper FFG / Snowman thật.
- **Tầng chạy** (M10): `run_to_completion` (một run) + `run_grid` (cả lưới),
  tái lập byte-identical.

`src/delay/` là **tầng thí nghiệm đầu tiên** — nó *dùng* cả ba tầng dưới để trả
lời một Research Question cụ thể:

| RQ | Câu hỏi | Family B chống lưng thế nào |
|----|---------|------------------------------|
| **RQ1** | Độ trễ tới finality của mỗi họ dưới trễ mạng thực? | Cột `commit_latency_ms` theo timeline |
| **RQ4** | Xếp hạng chịu-lỗi khi mạng xấu (trễ nặng + mất gói)? | (T47 heavy + T48 ranking, xây trên harness này) |

**Finding chống lưng** (`wiki/concepts/key-findings.md`): **F3 — "Snowman delay
exposure"**. Dataset T46 cho thấy dưới `E[delay]=300 ms`:
- PBFT: `1000 → ~1950 ms` (**+0.9 s**, một round-trip mỗi phase),
- Casper FFG: `5000 → ~6350 ms` (**+27 %**, do rescale slot),
- Snowman: `1000 → 12 200–15 300 ms` (**×12–15**, β=15 vòng poll *tuần tự*).

→ Hình Chương 4 (§4.3, Figures 4.8–4.13). Đây là *bằng chứng số* cho luận điểm
"Snowman phơi nhiễm trễ nhất" xuyên suốt Ch4–Ch5.

**Đánh đổi thiết kế của module:** `src/delay/` **KHÔNG** sửa một dòng nào của
`scheduler / nodes / network / event_log`, cũng không sửa package giao thức. Nó
là **lớp orchestration mỏng** — chỉ vặn ba núm đã-có-sẵn (network `Phase`,
`slot_duration`, `t_max`). Giá phải trả: một vài *chỉnh-sửa-tại-lớp-harness*
(clip cửa sổ, window-denominator fix) phải sống ở đây thay vì trong giao thức —
đó chính là các điểm "gai" cho Phòng thủ.

---

## 1 · Đọc gì (thứ tự)

**Wiki (hợp đồng):**
- `wiki/experiments/2026-06-10_delay-moderate.md` — trang hợp đồng T46. Đọc kỹ:
  *Locked methodology*, *Buffer / clip rule*, *Calibration*, *Window denominator*.
- (tham chiếu) `wiki/concepts/experiment-matrix.md` §5 (FFG slot coherence), §6
  (workload), §7 (seeds); `wiki/concepts/metric-reconciliation.md` (Snowman rescale).

**Code (`src/delay/`) — đọc theo tầng phụ thuộc:**
1. `config.py` — hằng số + `Timeline` (2 timeline, window/buffer, FFG rescale).
2. `runners.py` — `run_pbft / run_ffg / run_snowman`: *một cell → run thật*.
3. `clip.py` — `clip_records`: lọc cửa sổ [0, W] sau khi chạy.
4. `sweep.py` — **adapter gọi `run_grid`**: cell → `_run_cell` → `_build_row`.

**Test (đặc tả chạy được):**
- `tests/delay/test_clip.py` — thuần hàm, dễ trace nhất, mở trước.
- `tests/delay/test_e2e.py` — run thật n=10 một seed, cả pipeline + determinism.
- `tests/delay/test_sweep_equivalence.py` — induction-over-the-grid cho *chính
  adapter delay* (nối thẳng M10). LƯU Ý: class `jobs>1`/`jobs=4` **TREO trong
  sandbox** → chỉ chạy phần jobs=1.

---

## 2 · Mục tiêu khi đọc (nắm được là xong module)

1. **Đường ống một cell** (đọc thuộc): `run_<proto>(timeline,n,seed)` → `records`
   → `clip_records(records, W, one_round)` → `reducer(kept)` → `_build_row` → 1 dòng.
2. **Ba núm Family B vặn** so với baseline: (a) network = timeline trễ; (b) FFG
   `slot_duration` rescale `1.0→1.2 s`; (c) horizon `t_max = W+buffer = 528 s`.
3. **Vì sao clip** — tách *run horizon* (528 s, để instance kịp finalize) khỏi
   *measurement window* W (480 s, mẫu số của rate). Clip = cắt mọi event `t>W`.
4. **Hai cạm bẫy công-bằng-đo-lường** mà harness phải tự vá: (a) overhead-inflation
   nếu chỉ clip `decided`; (b) PBFT `tps/goodput` chia sai mẫu số (`result.now`
   thay vì `window`).
5. **Adapter khớp M10**: `_cell_key / _param_fingerprint / _run_cell` đúng ba hàm
   thuần mà `run_grid` cần — Family B chỉ *điền chỗ trống* của cỗ máy M10.

---

## 3 · Idiom Python gloss (gặp trong module)

- **`@dataclass(frozen=True)`** — `Timeline`, `Calibration`, `ClipStats`: record
  bất biến. `frozen` = không gán lại field sau khi tạo → an toàn để làm khóa hash
  / broadcast qua process. Đã gặp ở M02/M05.
- **`math.inf`** — `Phase(0.0, math.inf, delay)`: pha trễ kéo dài `[0, ∞)`, tức
  "timeline một-pha, không đổi giữa chừng".
- **`math.ceil(t_max / interval) + 2`** (runners `_batches`) — sinh *dư* vài batch
  để proposer không cạn hàng giữa run. `+2` = biên an toàn.
- **`next(t for t in cfg.TIMELINES if t.name == tl_name)`** — generator + `next`:
  tra timeline theo tên, lấy phần tử đầu khớp. `_timeline_by_name`.
- **Dispatch table `RUNNERS = {"pbft": run_pbft, ...}`** — dict tên→hàm, thay
  cho `if/elif`. Đã gặp ở M06 (`_dispatch`).
- **`hashlib.blake2b(canon.encode(), digest_size=16).hexdigest()`** — vân tay
  tất định của config (không phải `hash()` random-mỗi-tiến-trình). Đúng cùng lý do
  seed dùng blake2b ở M05.
- **`repr((...))` để canonicalize** — `_param_fingerprint` băm `repr` của tuple
  config; `repr` của float trong Python 3 là decimal ngắn nhất round-trip được →
  config bằng-nghĩa cho vân tay bằng nhau.
- **Hàm module-level (không closure)** — comment trong `sweep.py` nhấn: `_run_cell`
  / `_cell_key` / `_param_fingerprint` phải ở cấp module để **pickle** được dưới
  `spawn` (macOS) khi `jobs>1`. Closure không pickle được.
- **`{r.fields.get("instance_id") for r in decided}`** — set-comprehension đếm số
  *instance phân biệt* (mẫu số goodput), khác `len(decided)` (đếm event).

---

## 4 · Khái niệm gloss (đồng thuận / đo lường)

- **Family B (Họ B)** — trục thí nghiệm "mạng trung thực nhưng khắc nghiệt": trễ,
  mất gói, phân mảnh. Đối lập Family C (adversary *có chủ đích*). Nhắc M00: **B ≠ C**.
- **Timeline** — một *phân bố độ trễ giao gói* của mạng. T46 có hai: `delay-uniform`
  (uniform[0.1, 0.5] s, mean 0.3) và `delay-exponential` (exp mean 0.3 s). **Cùng
  E[delay], khác đuôi** — đây là biến độc lập chính của RQ1.
- **Measurement window W (480 s) vs Run horizon (528 s)** — cửa sổ đo (mẫu số của
  rate; chỉ tính instance *khởi động* trong `[0,W]`) tách khỏi *thời gian chạy thật*
  (dài hơn để instance khởi-động-sát-W kịp finalize trong buffer). **Buffer = 48 s
  ≥ một vòng giao thức đầy đủ.**
- **Clip** — lọc hậu-kỳ (`clip.py`): bỏ MỌI event `t > W`. Ba tinh chỉnh: (1)
  *scope* — instance in-window ⇔ decision đầu ≤ `W + one_round`; (2) *clip decided*
  — đuôi finalize `t>W` bỏ khỏi rate nhưng instance vẫn sống (giữ latency); (3)
  *clip all* — cả delivery/timer `t>W` cũng bỏ, để tử số overhead cùng cửa sổ với
  mẫu số.
- **`clipped_fraction`** — `tail / (kept + tail)` trên các instance in-scope. Guard
  hiệu chuẩn: **< 5 %**. Worst thực tế = 4.00 % (Snowman, exponential, n=10).
- **FFG slot-coherence rule** (experiment-matrix §5) — `slot_duration ≥ 4·E[delay]`.
  E[delay]=0.3 s ⇒ FFG slot `1.0→1.2 s`. PBFT/Snowman giữ cadence gốc 1.0 s. **Chỉ
  FFG khớp với chế độ trễ** — nên độ nhạy trễ của FFG là *gián tiếp* (qua đồng hồ slot).
- **one_round latency** (probe-đo) — độ trễ một-vòng của mỗi giao thức, làm sàn
  buffer + biên scope: PBFT 2 s, FFG 7 s, Snowman 16 s. Snowman là ràng buộc *cột trói*.
- **Common random numbers** — cùng 20 seed dùng lại xuyên protocol tại mỗi
  `(timeline, n)` → so sánh công bằng (khử nhiễu seed). Đã gặp M05.

---

## 5 · Grill "trace & dự đoán"

> Quy tắc: bạn **đoán trước**, nói rõ *vì sao*, rồi ta **chạy thật** để chấm. Đừng
> mở `<details>` trước khi đoán.

### G1 — `clip.py` scope (test thuần, dễ nhất)
Cho `W=100`, `one_round=5`, stream:
```python
_decided(t=10.0,  iid=1)   # instance 1
_decided(t=110.0, iid=2)   # instance 2
```
Hỏi: `stats.in_scope_instances = ?`, `stats.late_events = ?`, và danh sách
`instance_id` của decided **được giữ** = ?

<details><summary>ĐÁP ÁN G1</summary>

`in_scope_instances = 1`, `late_events = 1`, kept ids = `[1]`.
Instance 2 có decision-đầu ở `t=110 > W+one_round = 105` → khởi động trong buffer
→ *late*, bỏ hết. (`tests/delay/test_clip.py::TestScope`.)
</details>

### G2 — bẫy "grace window" (nơi scope ≠ time-clip)
Cho `W=100`, `one_round=5`, stream chỉ có `_decided(t=103.0, iid=1)`.
Hỏi: `in_scope_instances`, `kept_events`, `tail_events` = ?
(Gợi ý: 103 nằm ở đâu so với hai ngưỡng 100 và 105?)

<details><summary>ĐÁP ÁN G2</summary>

`in_scope_instances = 1` (vì `103 ≤ 105` — instance được coi là khởi-động-trong-W),
nhưng `kept_events = 0`, `tail_events = 1` (vì bản thân event `103 > W=100` → là
đuôi bị clip). Đây là tách bạch tinh tế: **scope** quyết định instance có được
*tính* không; **time-clip** quyết định *event* có được giữ không. Một instance
in-scope vẫn có thể *không* đóng góp event nào vào cửa sổ (đóng-trọn-trong-buffer),
và khi đó latency của nó KHÔNG được ghi. (`test_first_decision_within_one_round_grace_is_in_scope`.)
</details>

### G3 — vì sao clip CẢ delivery, không chỉ decided
Cho `W=100`, `one_round=5`:
```python
_delivery(t=50.0), _delivery(t=150.0), _decided(t=50.0, iid=1)
```
Hỏi: sau clip còn **mấy** delivery? Và một câu: *nếu ta quên clip delivery ở
buffer, cột nào bị sai và sai theo hướng nào?*

<details><summary>ĐÁP ÁN G3</summary>

Còn **1** delivery (`t=50`); `t=150 > W` bị bỏ. (`test_non_decided_events_clipped_at_window`.)

Nếu quên: `consensus_msgs_per_acu` và `bytes_per_acu` (tử số đếm delivery) nhặt cả
message thời-kỳ-buffer, trong khi mẫu số `decided` chỉ trải cửa sổ W → **phồng lên
≈ 528/480 ≈ +10 %**. Đây là *artifact harness thuần*, không phải hiệu ứng trễ, vì
số message *mỗi instance* là bất biến theo trễ. Bug này đã có thật trong bản nháp
T46, bắt được bằng cách so với zero-delay baseline; vá bằng cách mở time-clip ra
mọi event, xác nhận PBFT overhead trở về đúng `2n`.
</details>

### G4 — window-denominator fix (nơi PBFT khác FFG/Snowman)
`_window_denominator_fix` chỉ chạy khi `meta.protocol == "pbft"`. Hỏi: *tại sao chỉ
PBFT?* FFG và Snowman thì sao? (Gợi ý: mẫu số throughput của mỗi reducer là gì —
`result.now` hay `meta.t_max`?)

<details><summary>ĐÁP ÁN G4</summary>

- PBFT reducer (`src/pbft/summarise.py`) chia `tps/goodput` cho **`result.now`** =
  *run horizon* (528 s).
- FFG + Snowman reducer chia cho **`meta.t_max`** — mà harness đã set `meta.t_max =
  WINDOW_S` (480 s) trong `runners._meta`. → chúng đã window-based sẵn.

Nếu không vá: mẫu số PBFT lớn hơn ~10 % → `tps/goodput` PBFT bị *dìm* giả tạo so
với FFG/Snowman, phá trục throughput cross-protocol (chính là headline của T46).
Fix re-tính PBFT `tps = len(decided)/W`, `goodput` trên số *instance phân biệt* và
mẫu số W. Là **no-op cho FFG/Snowman**. Trên zero-delay baseline không lộ vì ở đó
`result.now ≈ meta.t_max` (không có buffer). (`tests/delay/test_window_denominator.py`.)
</details>

### G5 — adapter khớp M10 (đóng vòng "ai gọi run_grid")
Nhìn `run_sweep` trong `sweep.py`. Hỏi:
(a) `commit_hash` được resolve ở đâu — trong `_run_cell` (worker) hay trong `run_sweep`
(cha)? Vì sao chỗ đó?
(b) `_run_cell` là *thuần* — nó KHÔNG được đọc gì? (kể hai thứ)
(c) Nối M10: nếu ta thêm một seed mới vào `SEEDS`, các cell cũ đã checkpoint có phải
tính lại không?

<details><summary>ĐÁP ÁN G5</summary>

(a) Resolve **một lần ở cha** (`run_sweep`: `commit_hash = _resolve_commit_hash()`),
rồi broadcast qua `run_constants`. Nếu để worker tự resolve, mỗi worker chạm git
giữa sweep → cây có thể bị đọc bẩn/lệch → lẫn provenance. (Đúng "trụ 3" của M10.)

(b) `_run_cell` không đọc **wall-clock** và không đọc **cross-cell state** (không
resolve commit_hash, không đụng row của cell khác) — chỉ `runner → clip → _build_row`
với `commit_hash` *tiêm vào*. Đây là điều kiện của per-cell invariant.

(c) **Không.** Sidecar khóa theo `_cell_key` (`proto__tl__nN__seedSS`) + vân tay
`_param_fingerprint` (không chứa seed vì seed là *identity* nằm trong filename). Cell
cũ khớp schema+commit_hash+fingerprint → resume, chỉ cell seed-mới tính. Đúng
"collect-sort theo cell_key áp thứ tự toàn phần" của M10 → thêm cell không xáo trộn.
</details>

**Lệnh chạy chấm** (sandbox-safe, jobs=1):
```bash
# G1–G3 (clip thuần):
make test-delay 2>/dev/null || PYTHONPATH=src:tests python3 -m unittest delay.test_clip -v
# hoặc trực tiếp:
PYTHONPATH=src:tests/delay python3 -m unittest test_clip -v
# G4:
PYTHONPATH=src:tests/delay python3 -m unittest test_window_denominator -v
# G5 (adapter thật, jobs=1 — KHÔNG chạy class jobs>1, treo sandbox):
PYTHONPATH=src:tests/delay python3 -m unittest test_sweep_equivalence.TestPerCellInvariant test_sweep_equivalence.TestBaseCase -v
# E2E run thật một seed (chậm hơn, ~10–20 s):
PYTHONPATH=src:tests/delay python3 -m unittest test_e2e -v
```

---

## 6 · Phòng thủ (câu hội đồng dễ hỏi — trả lời neo wiki, không bịa)

> Mỗi câu: (Q) hội đồng hỏi → (A) trả lời mẫu → (nguồn). Luyện thành *lời của bạn*.

**PT1 — "Cửa sổ W=480 s và guard 5 % là tùy tiện. Sao không W khác?"**
A: W không tùy tiện — nó *probe-derived*. `clipped_fraction ≈ one_round/W`, mà
Snowman (ràng buộc cột trói) có đuôi ≈16 s, nên giữ dưới 5 % đòi `W ≳ 16/0.05 ≈
320 s`; chọn `W=480 s` để dư biên và có `≫25` quyết định in-window mỗi giao thức.
Self-check thực đo worst = 4.00 % (Snowman/exp/n=10) — dưới guard. Buffer 48 s ≥
một vòng đầy đủ để instance sát-W kịp finalize.
*(nguồn: delay-moderate §Calibration.)*

**PT2 — "Bạn rescale FFG slot 1.0→1.2 s. Vậy có phải bạn 'knob-engineer' để FFG
trông tốt?"**
A: Rescale là **luật coherence công khai** (`slot ≥ 4·E[delay]`, experiment-matrix
§5), áp *trước* khi thấy kết quả, không phải chỉnh sau. Và ta đã kiểm chứng độ nhạy:
sweep `slot ∈ {0.5,1,2} s` cho thấy FFG finality **đúng bằng `5·slot_duration` ms**
— nên ≈6.35 s là *do calibration*, đã báo cáo minh bạch (`slot_duration_ms` là một
cột trong CSV, "reported not hidden"). Crossover slot 0.2 s là *dưới* mức thực tế.
*(nguồn: experiments/2026-06-22_ffg-slot-sensitivity; experiment-matrix §5.)*

**PT3 — "PBFT được 'sửa mẫu số' còn hai giao thức kia thì không. Không công bằng?"**
A: Ngược lại — fix là để *khôi phục* công bằng. Ba reducer viết độc lập ở ba thời
điểm; FFG/Snowman tình cờ đã chia cho `meta.t_max` (=W), PBFT chia cho `result.now`
(=horizon). Không vá thì PBFT mới bị *thiệt* ~10 %. Fix chỉ re-base PBFT về đúng
cửa sổ W mà hai giao thức kia đã dùng — nó là **no-op cho FFG/Snowman**. Ta để nó ở
lớp harness thay vì sửa package giao thức để giữ nguyên baseline byte-identical.
*(nguồn: delay-moderate §Window denominator; sweep.py `_window_denominator_fix`.)*

**PT4 — "K của Snowman ở n∈{10,25} gần bằng n, không phải ≤10 % như production.
Vậy Snowman có bị chạy ngoài vùng thiết kế không?"** (defense gold)
A: **Có, và tôi công khai điều đó.** `K=min(20,n-1)` ⇒ ở thesis-scale K≈n, nên
Snowman mất tính tail-insensitive (lợi thế chịu-trễ-tại-scale chỉ phô ra khi n≈1000).
Giảm thiểu: giữ `α_c/K≈0.8` + `β=15` cho đúng *shape* của ε; LOẠI ô n=4 khỏi bảng
RQ (degenerate: α_c=K ⇒ đòi nhất trí, ε=0); xuất cột `alpha_c_over_K` mọi hàng để
tự annotate. So sánh vẫn công bằng "cùng n/mạng/seed", chỉ là Snowman chạy K≪n
không đạt được ở quy mô này — đây là *threat-to-validity đã ghi nhận*, không phải lỗi.
*(nguồn: metric-reconciliation §Snowman parameter rescaling; key-findings; progress
"defense gold".)*

**PT5 — "Số Snowman ×12–15 có nói lên bản chất giao thức không, hay chỉ là artifact?"**
A: Nói lên bản chất. β=15 vòng poll là **tuần tự** — mỗi vòng một round-trip
query→response cỡ `2·E[delay]`, nên 15 vòng cộng ≈12 s. Đây là *chi phí xây niềm tin
tuần tự*, không phải quirk cài đặt. Bằng chứng phụ: exponential chậm hơn uniform
10–21 % (cùng E[delay]) — vì đuôi memoryless thổi phồng "chờ peer chậm nhất" mỗi vòng
rồi *cộng dồn* qua 15 vòng. Đây là cơ chế mà xếp hạng T48/T49 xoay quanh.
*Caveat trung thực:* `p_drop` trong T47 là mất-vĩnh-viễn không retransmit, nên các
đường cong là *cận trên* của độ mong manh. *(nguồn: delay-moderate §Observations;
delay-analysis §caveat.)*

---

## 7 · Giải thích lại (Feynman) + ghi sổ

Sau grill, tự nói (không nhìn guide):
1. Vẽ đường ống **một cell** từ trái sang phải, gọi tên từng hàm.
2. Phân biệt **run horizon 528 s** vs **window 480 s** — mỗi cái dùng làm gì.
3. Vì sao clip phải chạm **cả delivery**, và vì sao chỉ **PBFT** cần sửa mẫu số.
4. Adapter delay *điền chỗ trống nào* của `run_grid` (ba hàm thuần) — nối M10.

Rồi cùng cập nhật `progress.md`: điểm 1–5, đã thông / còn mờ, một mục Nhật ký.

**Câu mang sang M12** (`adversary/`, Họ C): rời **mạng trung thực** (B) sang
**đối thủ có chủ đích** (C) — cùng harness sweep, nhưng cell giờ có trục `f`/`φ`
(tỉ lệ node ác) và một `Node.adversary` được tiêm vào seam.
