# Module 10 · runner + sweep — 1 run → cả lưới run

> Chặng 4 · Chạy · `src/common/` + `src/workload/`. Module **đọc-giao-diện**,
> **FAST LANE** (bạn đang gấp): bỏ đào sâu từng nhánh, bỏ mục Phòng thủ. Chỉ
> nắm **hai hình dạng cửa ngõ** (`run_to_completion`, `run_grid`) và **một tính
> chất phải thuộc lòng**: sweep *byte-identical qua jobs / resume / thứ tự hoàn
> thành*. Đó là điều duy nhất hội đồng có thể đâm vào ở tầng này.
>
> Cần chi tiết hơn về đâu? Dừng tôi lại, ta đào chỗ đó. Mặc định: lướt.

---

## 0. Vì sao module này tồn tại (30 giây)

**Một câu** của simulator: *một YAML + một seed → một dòng CSV.* Tầng lõi
(M01–05) dựng được **một** run. Nhưng luận văn cần **cả lưới** run: 3 protocol ×
nhiều n × nhiều timeline × nhiều seed = hàng trăm–nghìn dòng CSV. Module này là
**cầu nối một-run → nhiều-run**, đúng hai file:

| File | Vai | Câu trả lời |
|------|-----|-------------|
| `common/runner.py` | chạy **một** run tới hết | "cho `RunHandle` đã dựng, chạy scheduler tới stop và trả log ra sao?" |
| `common/sweep.py`  | lái **cả lưới** run | "cho danh sách cell độc lập, chạy song song + resume + gom lại *tất định* ra sao?" |
| `workload/generator.py` | sinh tải giao dịch | "mỗi cơ hội đề xuất khối, node nhét bao nhiêu tx, nội dung gì — *tất định*?" |

**Nối RQ/chương:** `run_grid` là hạ tầng dưới **mọi** bảng số Chương 4–5 (sweep
Họ B delay, Họ C adversary). Tính *byte-identical* của nó chính là lý do bạn
được phép nói "PBFT breakpoint ở delay X" như một **sự thật đo được** chứ không
phải một lần chạy may rủi ([[concepts/sweep-harness]] §1, `[[concepts/reproducibility]]`).
Đây là reproducibility contract nối tiếp từ M05, giờ ở quy mô *lưới*.

---

## 1. Đọc gì (thứ tự, ~15')

1. **Wiki hợp đồng:** `wiki/concepts/sweep-harness.md` — đọc §1 (cell), §3
   (sidecar/resume), §4 (collect = bước tạo thứ tự), §6 (song song). Đây là đặc
   tả. (§9 tiered là mở rộng chống OOM — lướt.)
2. **Code** (tổng < 15KB):
   - `common/runner.py` (~44 dòng) — 1 hàm `run_to_completion`. Đọc hết, nhanh.
   - `common/sweep.py` (~270 dòng) — `run_grid` + đám helper. **Đừng** đọc từng
     helper; nắm *bốn trụ* ở §4 dưới.
   - `workload/generator.py` (~114 dòng) — `generate_batches`. Nắm *một RNG,
     một thứ tự rút*.
3. **Test** (đặc tả chạy được): `tests/common/`, `tests/workload/`. Trái tim là
   test khẳng định `jobs=1` và `jobs>1` cho **cùng** kết quả.

---

## 2. Mục tiêu khi đọc (checklist tự hỏi)

- **`run_to_completion`**: `t_max=None` vs `t_max=<float>` khác nhau chỗ nào, và
  vì sao PBFT dùng cái đầu còn Casper/Snowman dùng cái sau.
- **Cell abstraction**: một "cell" là gì, ba hàm thuần trên cell (`run_cell`,
  `cell_key`, `param_fingerprint`) mỗi cái làm gì.
- **Induction-over-the-grid**: phát biểu được *bằng lời* tại sao đổi `jobs`, cắt
  giữa chừng rồi resume, hay thứ tự worker hoàn thành **không** đổi được một dòng.
- **Resume validity rule**: sidecar được tái dùng *chỉ khi* ba thứ khớp — kể tên.
- **`commit_hash` resolve một lần**: vì sao ở cha, vì sao **không** trong worker.
- **Workload determinism**: vì sao một RNG rút *theo thứ tự* + blake2b seed ⇒ tái lập.

---

## 3. Idiom Python cần gloss

- **`multiprocessing.Pool` + `spawn` + "module-level only"** — trên macOS, Pool
  con khởi động bằng `spawn`: tiến trình con **import lại** module rồi mới chạy,
  KHÔNG kế thừa bộ nhớ cha. Hệ quả: mọi hàm băng qua ranh giới Pool
  (`run_cell`, `cell_key`, `param_fingerprint`, `_worker`) phải là **hàm cấp
  module** (pickle được bằng *tên*), và mỗi cell là **tuple thuần**. Closure/
  lambda **không** pickle được → nổ. Đây là lý do cả file cấm closure băng biên
  (`sweep.py` docstring dòng 10–15).
- **`os.replace(tmp, path)`** — đổi tên *nguyên tử* trên cùng filesystem: hoặc
  thấy file cũ, hoặc thấy file mới hoàn chỉnh, không bao giờ thấy file *rách*.
  Ghi ra `tempfile.mkstemp(dir=cùng-thư-mục)` trước rồi `os.replace`, nên một cú
  crash để lại "sidecar đủ hoặc không có" — không có nửa vời (`_write_sidecar`).
  (`dir=` cùng chỗ để tránh `EXDEV` — rename xuyên-filesystem thất bại.)
- **`imap_unordered(_worker, pending, chunksize=1)`** — trả kết quả *ngay khi
  xong*, không theo thứ tự nộp (`unordered` = nhanh hơn, khỏi chờ đứa chậm).
  `chunksize=1` = mỗi lần giao 1 cell → giới hạn *số* run đang giữ trong RAM ≈
  `jobs`. Thứ tự lộn xộn KHÔNG hại vì bước collect sẽ sort lại (§4).
- **`mp.get_context("spawn")`** — ép start-method `spawn` tường minh (đừng phụ
  thuộc mặc định OS). `pool.terminate()` trong `finally` = dọn worker sạch khi
  Ctrl-C.
- **`*,` (keyword-only)** — trong `run_grid(..., *, checkpoint_dir, ...)`, dấu
  `*` bắt mọi tham số sau nó phải gọi bằng **tên**. Chống lộn thứ tự đống config.
- **nested `tuple(...)` bất biến** — `generate_batches` trả `tuple[tuple[bytes]]`
  thay list: bất biến (không ai sửa lén) + so sánh bằng `==` trực tiếp trong test.
- **blake2b + domain tag** — `blake2b(b"workload:" + seed)` băm *ổn định xuyên
  tiến trình* (khác `hash()` bị `PYTHONHASHSEED` ngẫu hóa); tag `workload:` tách
  dòng RNG này khỏi dòng network/node (cùng seed, khác dòng). Bạn đã gặp đúng
  idiom này ở `_network_seed` (M03) và `_stable_seed` (M05).
- **Knuth's Poisson** (`_batch_size`) — nhân dồn các số ngẫu nhiên `[0,1)` cho
  tới khi tích tụt dưới `e^{-mean}`; số lần nhân = mẫu Poisson. `constant` thì
  KHÔNG rút RNG (chỉ `round(rate*interval)`) — nhớ điểm này ở grill.

---

## 4. Bốn trụ của `run_grid` (nắm cái này là nắm module)

Toàn bộ tính *byte-identical* dựng trên **bốn** ý, không hơn:

1. **`run_cell` thuần.** Một cell → một `row` dict, hàm *tất định* của đối số:
   không wallclock, không state chia sẻ chéo-cell. ⇒ chạy ở đâu, lúc nào, cũng ra
   một `row`.
2. **Sidecar có vân tay + luật resume.** Mỗi cell xong ghi 1 file JSON
   `<cell_key>.json` chứa `{schema_version, commit_hash, param_fingerprint, row}`.
   Tái dùng **chỉ khi cả ba** `schema_version` **và** `commit_hash` **và**
   `param_fingerprint` khớp run hiện tại; lệch bất kỳ → coi như **vắng → tính
   lại**. ⇒ CSV cuối luôn *một* commit_hash đồng nhất, không lẫn dòng cũ.
3. **`commit_hash` resolve MỘT lần ở cha**, phát qua `run_constants`; worker chỉ
   *đọc*, không tự hỏi git. Nếu worker tự resolve, việc nó ghi file sẽ làm bẩn
   cây git *giữa sweep* → dòng thì `<hash>`, dòng thì `<hash>-dirty`. Đây là
   *đầu vào provenance duy nhất* của một row; mọi thứ khác là hàm thuần của cell.
4. **Collect = sort theo `cell_key`.** Xong lưới, đọc sidecar *mọi* cell được
   yêu cầu, `sort(key=cell_key)`, trả rows. Bước này **độc lập thứ tự**
   `imap_unordered` và thứ tự `os.scandir`. Đây là chỗ *áp lại thứ tự toàn phần*
   — grid to/nhỏ, song song mấy job, cắt-resume ở đâu, đều không xê được một dòng.

> **Induction-over-the-grid** (câu thần chú để nói với hội đồng): *mỗi cell là
> hàm thuần ghi file riêng (base case tất định); collect sort lại theo khóa toàn
> phần (inductive step độc-lập-thứ-tự) ⇒ cả lưới byte-identical bất kể jobs,
> resume, hay thứ tự hoàn thành.*

`git dirty` ⇒ `commit_hash = <hash>-dirty` ⇒ vân tay lệch ⇒ **resume vô hiệu,
tính lại cả lưới**. Nên chạy sweep production từ **cây git sạch** ([[concepts/sweep-harness]] §3).

---

## 5. Grill "trace & dự đoán" (fast — 3 câu)

Trả lời trong đầu TRƯỚC khi mở `<details>`. Rồi ta **chạy thật** chấm.

Chạy suite (sandbox: chỉ test lẻ / `jobs=1` — `jobs>1` **treo** trong sandbox này):
```
make test-common        # hoặc: PYTHONPATH=src:tests/common python3 -m unittest discover -s tests/common -v
make test-workload      # workload/generator
```

### H1 — `t_max` quyết stop condition
`run_to_completion(handle)` (không truyền `t_max`) và `run_to_completion(handle,
t_max=500.0)` khác nhau chỗ nào? Vì sao đường-thật PBFT dùng cái đầu, Casper/
Snowman dùng cái sau? Nếu Snowman gọi cái đầu thì sao?

<details><summary>ĐÁP ÁN</summary>

`t_max=None` → `scheduler.run()` chạy tới **quiescence** (hết sự kiện). PBFT
đường-honest tự cạn việc sau khi decide → dừng sạch. `t_max=<float>` →
`scheduler.run(t_max=...)` dừng ở **deadline**. Casper/Snowman **không có
quiescence tự nhiên** (đề xuất/bỏ phiếu vô hạn theo epoch/vòng), nên phải cắt
bằng deadline; gọi `None` cho Snowman → chạy *mãi không dừng* (hoặc tới khi hàng
đợi cạn theo cách không mong muốn). `run_to_completion` chỉ *gắn logger → chạy →
trả `(RunResult, EventLogger)`*; không hook adversary (T18), không xuất CSV (T40).
</details>

### H2 — Induction: jobs không đổi kết quả
Cùng lưới, chạy `run_grid(..., jobs=1)` rồi xóa checkpoint chạy lại
`jobs=4`. Hai CSV có byte-identical không? *Trụ nào* trong §4 bảo đảm điều đó?
Nếu ai đó đổi `run_cell` để nhét `time.time()` vào row thì trụ nào gãy?

<details><summary>ĐÁP ÁN</summary>

**Có, byte-identical.** Bảo đảm bởi **trụ 1** (`run_cell` thuần ⇒ mỗi cell cho
cùng row bất kể tiến trình nào tính) + **trụ 4** (collect sort theo `cell_key`
⇒ thứ tự `imap_unordered` lộn xộn được áp lại thành thứ tự toàn phần). `jobs`
chỉ đổi *lịch chạy*, không đổi *nội dung* hay *vị trí* dòng. Nhét `time.time()`
→ **trụ 1 gãy** (`run_cell` không còn thuần: phụ thuộc wallclock) → hai lần chạy
khác nhau → induction sụp. Đây đúng lý do "timing chỉ ra stderr, không bao giờ
vào row/sidecar" (§7 wiki).
</details>

### H3 — Workload: constant vs poisson rút RNG
`generate_batches` với `arrival_process="constant"` và với `"poisson"`, cùng
`global_seed`. Cái nào tiêu thụ RNG? Nếu bạn chèn thêm một cell *trước* nó trong
sweep, batch của cell này có đổi không? Vì sao?

<details><summary>ĐÁP ÁN</summary>

**`constant` KHÔNG rút RNG** — `round(offered_rate*interval)`, thuần số học.
**`poisson` rút** — Knuth nhân dồn `rng.random()`. Nhưng dù poisson: batch của
một cell **không** đổi khi chèn cell khác, vì RNG của workload seed *chỉ* từ
`_workload_seed(global_seed)` **của chính cell đó** (blake2b, domain tag
`workload:`), độc lập hoàn toàn với các cell khác trong lưới. Đây là điều kiện
"`run_cell` thuần, không state chia sẻ chéo-cell" (trụ 1). Mỗi cell là ốc đảo
tất định; sweep chỉ gom chúng lại.
</details>

---

## 6. Giải thích lại + ghi sổ (Feynman, 3 câu)

Nói bằng lời bạn, không nhìn code:

1. **Hai cửa ngõ**: `run_to_completion` (một run tới stop; `t_max` chọn
   quiescence vs deadline) và `run_grid` (cả lưới); `run_cell` thuần là gạch nối.
2. **Induction-over-the-grid** một hơi: cell thuần (base) + collect-sort (step)
   ⇒ byte-identical qua jobs/resume/thứ tự. Kèm *cái giá*: cấm closure băng Pool,
   commit_hash resolve một lần, cây git phải sạch.
3. **Workload tái lập**: một RNG blake2b-seed rút *theo thứ tự*, mỗi cell một ốc
   đảo — vì sao chèn/đổi thứ tự cell không nhiễu.

Rồi cập nhật `progress.md`: bảng tiến độ (điểm 1–5, đã thông / còn mờ) + nhật ký.
Câu mở dự kiến mang sang **M11 (delay · Họ B)**: `run_grid` là hạ tầng — M11 xem
*ai gọi* nó (adapter delay: cell = `(protocol, timeline, n, seed)`, `run_cell` =
`runner → clip → row`).
