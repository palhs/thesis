# Module 07 — `pbft/` (đào sâu · giao thức đầu tiên)

> Giao thức đồng thuận **đầu tiên** thay cho `BroadcastNode` giả. ~40–45 phút.
> Đây là **đỉnh chặng 2**: PBFT n=4 thật chạy qua trọn 5 tầng lõi → sinh
> `event_type="decided"` → 1 dòng CSV. Module đào sâu ⇒ có đủ: trace & dự đoán +
> chạy thật + **Phòng thủ**.

## 0. Vì sao tồn tại — và nối với phòng thủ

PBFT (Practical Byzantine Fault Tolerance) là **baseline safety-first** của cả
luận văn: góc "an toàn tuyệt đối, trả giá bằng chi phí bản tin `O(n²)`" trong bản
đồ 3 họ (Module 00). Mọi so sánh về latency/throughput (RQ1) và ngưỡng chịu lỗi
đối kháng (RQ4) đều lấy PBFT làm mốc.

Từ M06 ta đã có đường ống 5 tầng lõi chạy `BroadcastNode` giả: mỗi node phát *một
vòng* `n·(n−1)` bản tin phẳng rồi im, **không bao giờ decide**. Module này **thay
ruột node** bằng một FSM (finite-state machine — máy trạng thái hữu hạn) PBFT
thật. Kết quả: "một vòng phẳng" biến thành **chuỗi 3 pha** pre-prepare → prepare →
commit, mỗi pha chốt tại **quorum `2f+1`**, và CSV mọc ra `event_type="decided"`.
Đường ống 5 tầng **GIỮ NGUYÊN** — chỉ ruột node đổi (đóng câu mang từ M06).

Điểm chống lưng phòng thủ (2 điểm "gai" nhất, neo bài báo gốc):
1. **An toàn = giao của hai quorum.** Hai quorum `2f+1` bất kỳ trong tập `3f+1`
   luôn cắt nhau ở ≥ `f+1` node ⇒ ≥ 1 node trung thực trong giao ⇒ không thể có
   hai giá trị mâu thuẫn cùng chốt. An toàn **không phụ thuộc synchrony**.
2. **View-change = cơ chế hồi sinh liveness** khi primary (node dẫn) hỏng/chậm —
   và là phần *đắt nhất* (`O(n³)`). Đây là chỗ delay cắn PBFT.

## 1. Đọc gì, theo thứ tự

1. `wiki/algorithms/pbft.md` — hợp đồng giao thức (3 pha, safety argument,
   view-change, simulator mapping). **Đọc trước khi mở code.** Đặc biệt §Safety
   argument và §Behaviour under adversarial conditions (threshold break).
2. `src/pbft/instance.py` (51 dòng) — data-plane per-`(view,seq)`: enum 4 trạng
   thái `IDLE→PRE_PREPARED→PREPARED→COMMITTED`, hai dict đếm phiếu `prepares`/
   `commits`, hai hàm đếm phiếu-khớp-digest. Đọc **đầu tiên**: hiểu "một instance"
   trước khi hiểu node lái nhiều instance.
3. `src/pbft/messages.py` (80 dòng) — 6 payload dataclass frozen (pre-prepare,
   prepare, commit, view-change, new-view, reply). Chỉ là túi dữ liệu trên dây.
4. `src/pbft/digest.py` (21 dòng) — blake2b 32-byte, KHÔNG dùng `hash()`
   (process-stable ⇒ replay byte-identical). Cùng kỷ luật hash như per-Node seed.
5. `src/pbft/node.py` (512 dòng) — FSM chính. Đọc theo **luồng đời một request**:
   `_propose` → `_handle_pre_prepare`/`_accept_pre_prepare` → `_broadcast_prepare`/
   `_check_prepare_quorum` → `_accept_prepare` → commit tương tự → `_accept_commit`
   (`_emit_decided`) → `_send_reply`/`_record_reply`. Sau đó nhánh view-change:
   `_arm_view_change_timer` → `_on_view_change_timeout` → `_initiate_view_change` →
   `_handle_view_change` (f+1 catch-up) → `_check_new_view_quorum` → `_enter_new_view`.
6. `src/pbft/viewchange.py` (56 dòng) — 2 hàm thuần (`collect_evidence`,
   `compute_reissue`) tách khỏi node để unit-test cô lập.
7. `src/pbft/summarise.py` (98 dòng) — reducer T40: records → 1 dict metric.
   **Đóng câu tồn đọng `tps ∝ n`** ở dòng 66-68.
8. Test (đặc tả chạy được): `tests/pbft/test_happy_path.py` (3 pha trọn),
   `tests/pbft/test_quorum_thresholds.py` (ranh giới `2f+1`, degenerate small-n),
   `tests/integration/test_pbft_consensus.py` (e2e qua `build_run`, có kịch bản B
   view-change). Helper: `tests/pbft/_helpers.py`.

Bài báo gốc (đọc **đúng đoạn**, không cày cả bài):
`raw/castro-practicalbft.pdf` §4.2 (predicate prepared/committed-local), §4.5.1
Safety (giao quorum), §4.4 + §4.5.2 Liveness (backoff + f+1 catch-up). Trích
chương-câu ở §6 Phòng thủ dưới.

## 2. Mục tiêu khi đọc (trả lời được là đạt)

- `f = (n−1)//3` và quorum `2f+1`. Với n=4 → f=1, quorum=3. **Vì sao `3f+1` chứ
  không phải `2f+1` node tổng?** (giao hai quorum phải chừa ≥1 node trung thực.)
- Một instance đi `IDLE→PRE_PREPARED→PREPARED→COMMITTED`. **Mỗi mũi tên cần điều
  kiện gì?** (accept pre-prepare / đủ `2f+1` prepare / đủ `2f+1` commit.)
- **Decision B**: mọi replica (kể cả primary) tự broadcast PREPARE/COMMIT *và*
  tự ghi phiếu mình. Vì sao phải tự-ghi? (`Network.broadcast` loại người gửi.)
- **Decision C**: phiếu tới *trước* PRE-PREPARE vẫn được đếm lùi. Cơ chế nào cho
  phép? (`setdefault` tạo Instance rỗng; `matching_*` trả 0 khi `digest is None`.)
- **Decision G**: `decided` phát **một lần mỗi seq** dù request bị reissue qua
  view-change. Chốt ở đâu? (`self._decided_seqs` set.)
- View-change timer: delay `= vc_delay · 2^view`. **Vì sao nhân đôi mỗi view?**
- **f+1 catch-up**: node chưa hết giờ vẫn nhảy vào view-change nếu thấy `f+1`
  node khác đã muốn. Vì sao ngưỡng đúng bằng `f+1`?

## 3. Idiom Python sẽ gặp (gloss)

- `dict.setdefault(key, default)` — trả value nếu key có; nếu chưa, chèn
  `default` rồi trả nó. `self.inst.setdefault((v,s), Instance(...))`: "lấy
  instance `(v,s)`, chưa có thì tạo rỗng". Là mấu chốt Decision C (đếm phiếu lùi).
- `@dataclass(frozen=True)` — payload bất biến, không sửa sau khi tạo (khớp kỷ
  luật reproducibility). `Instance` thì **không** frozen (state đổi tại chỗ).
- `Enum` (`InstanceState`) — 4 hằng có tên; so bằng `is` (`state is COMMITTED`),
  không so `==` số. Đọc rõ ý đồ hơn magic number.
- `set` cho idempotence — `self._decided_seqs`, `self._new_view_installed`,
  `self._finalized_seqs`: "đã làm việc X cho khóa này chưa?" — `if k in s: return`.
- `tuple` làm `timer_id` — `("view_change", view, seq)` / `("vc_escalate", nv)`.
  Timer_id phức hợp để hủy đúng cái (nhớ lazy-tombstone của M01). `_on_timer` rẽ
  bằng `isinstance(timer_id, tuple) and timer_id[0] == ...`.
- `2 ** view` — luỹ thừa; exponential backoff.
- `sum(1 for d in dict.values() if d == self.digest)` — đếm-có-điều-kiện idiom;
  ở `matching_prepares` đếm phiếu **khớp digest** (phiếu sai digest không tính).
- `dict[src] = digest` last-write-wins — một src vote lại thì đè phiếu cũ (seam
  cho equivocation T53). Keyed by `src` ⇒ một src spam nhiều lần vẫn tính **1**.

## 4. Khái niệm gloss (đồng thuận)

- **primary / view** — *primary* = node dẫn của một *view* (một lượt lãnh đạo).
  Luật `primary = view mod n` (Decision D): view 0→node 0, view 1→node 1... Đổi
  view = đổi primary, xoay vòng.
- **quorum `2f+1` / ngưỡng `f = ⌊(n−1)/3⌋`** — số phiếu tối thiểu chốt một pha.
  BFT cần `n ≥ 3f+1`: chịu `f` node Byzantine (nói dối/ác ý, không chỉ chết).
  Ví dụ n=4, f=1: chịu đúng 1 kẻ phản.
- **giao hai quorum (safety)** — hai tập `2f+1` trong `3f+1` node giao nhau ở
  `(2f+1)+(2f+1)−(3f+1) = f+1` node. `f` kẻ xấu tối đa ⇒ ≥1 trung thực trong giao
  ⇒ nó từ chối vote cho giá trị thứ hai ⇒ chỉ một giá trị chốt được. **Không cần
  synchrony** — đúng ngay cả khi mạng trễ/mất/đảo tuỳ ý.
- **threshold break** — khi kẻ xấu > `f`: giao **vẫn** ≥`f+1` node, nhưng có thể
  *toàn Byzantine*; kẻ equivocate (nói hai lời) vote cả hai giá trị ⇒ hai giá trị
  cùng chốt ⇒ **vỡ an toàn**. (Không phải do quorum rời nhau — điểm tinh tế wiki
  §threshold break nhấn, dùng cho detector T55.)
- **three-phase commit** — pre-prepare (primary gán seq, phát request), prepare
  (mọi replica xác nhận thấy pre-prepare — chốt *thứ tự*), commit (chốt *đã-đủ-
  người-thấy-thứ-tự*). Hai vòng quorum vì một vòng không đủ bắc cầu qua view-change.
- **committed-local vs decided** — replica *commit locally* khi đủ `2f+1` COMMIT
  (nó tự thực thi). Trong sim, mỗi replica commit-local phát `pbft_committed`
  + `decided`; `decided` gộp một-lần-mỗi-seq. **Client finality** (T70) đi thêm 1
  hop: `f+1` REPLY khớp → `pbft_client_finalized` (> commit latency).
- **view-change** — hồi sinh liveness: replica hết giờ mà chưa commit →
  broadcast VIEW-CHANGE(v+1, evidence); primary mới của v+1 gom `2f+1` VIEW-CHANGE
  → phát NEW-VIEW re-anchor request prepared-chưa-commit → 3 pha chạy lại. Giá:
  `O(n³)` bản tin. Backoff `2^view` để chu kỳ đồng-view giãn theo cấp số nhân đến
  khi có việc chốt được (§4.5.2 bài báo).
- **spurious view-change** — delay > timeout ⇒ view-change *dù primary trung
  thực*. Lãng phí traffic, giết throughput. Đây là knob chính chống delay (RQ1).

## 5. Grill "trace & dự đoán"

> Sau mỗi câu: **dự đoán trước**, rồi ta **CHẠY THẬT** để chấm. Suite:
> `PYTHONPATH=src:tests/pbft python3 -m unittest <mod> -v` hoặc
> `PYTHONPATH=src:tests/integration python3 -m unittest test_pbft_consensus -v`.

**G1 — quorum tối thiểu.** n=4, một non-primary (node 1) nhận PRE-PREPARE hợp lệ
rồi nhận **2** peer PREPARE (thành 2f=2 phiếu peer). `matching_prepares()` = ? và
state = ? Rồi thêm 1 PREPARE nữa (peer thứ 3): giờ state = ?

<details><summary>ĐÁP ÁN</summary>

Sau pre-prepare, node **tự ghi phiếu mình** (Decision B) ⇒ đã có 1. +2 peer = **3**
phiếu... khoan: `_broadcast_prepare` tự ghi 1, cộng 2 peer = 3 = quorum. Nhưng đề
cho "2 peer PREPARE" *sau* self ⇒ `matching_prepares()=3`, `2f+1=3` ⇒ **PREPARED
ngay**. Nếu chỉ 1 peer (self+1=2=2f): còn PRE_PREPARED, chưa đủ. Xem
`test_quorum_thresholds.py::test_2f_prepares_is_insufficient` (2f *tổng* kể cả
self là chưa đủ) vs `test_2f_plus_1_prepares_tips_to_prepared`. **Bẫy: self-vote
luôn được ghi trước** — đếm phiếu peer phải trừ 1 khỏi quorum.
</details>

**G2 — phiếu tới trước pre-prepare (Decision C).** n=4, node 1 nhận **3 PREPARE
từ peer** cho `(0,0)` *trước khi* thấy PRE-PREPARE. Ngay lúc đó `matching_prepares()`
= ? Sau đó PRE-PREPARE tới: chuyện gì xảy ra tức thì?

<details><summary>ĐÁP ÁN</summary>

`_handle_prepare` dùng `setdefault` tạo `Instance(0,0)` rỗng, ghi 3 phiếu vào
`inst.prepares`. Nhưng `matching_prepares()` trả **0** vì `inst.digest is None`
(chưa biết digest để so khớp). Khi PRE-PREPARE tới, `_accept_pre_prepare` đặt
`inst.digest`, rồi gọi `_check_prepare_quorum` — giờ 3 peer khớp + self = 4 ≥ 3 ⇒
**PREPARED ngay lập tức** (và cascade sang broadcast COMMIT). Đây là lý do dòng
`self._check_prepare_quorum(inst, t)` cuối `_accept_pre_prepare` (comment: "buffered
PREPAREs may suffice"). Cơ chế: phiếu đếm-lùi.
</details>

**G3 — decided một-lần-mỗi-seq (Decision G).** n=4, instance `(0,0)` đã COMMITTED
và phát `decided`. Một COMMIT thứ 4 (thừa) cho `(0,0)` tới. `decided` count = ?
Nếu sau này request-0 bị reissue thành instance `(1,0)` (view 1) và cũng đủ quorum,
`decided` cho seq 0 phát thêm lần nữa không?

<details><summary>ĐÁP ÁN</summary>

COMMIT thừa: `_check_commit_quorum` guard `inst.state is PREPARED` — instance đã
COMMITTED ⇒ **no-op**, `decided` vẫn = 1
(`test_commit_after_committed_does_not_refire_decided`). Reissue `(1,0)`: instance
*khác* (khác view) sẽ COMMITTED, nhưng `_accept_commit` kiểm `if inst.seq not in
self._decided_seqs` — seq 0 đã trong set ⇒ **không phát `decided` lần hai**. Sim
thực thi mỗi seq đúng một lần dù đi qua nhiều view. **Bẫy: "decided" khoá theo
*seq*, không theo *instance* `(view,seq)`.**
</details>

**G4 — view-change backoff.** n=4, `vc_delay=10`, node ở view 0. Timer view-change
cho instance `(0,0)` fire sau bao lâu? Nếu escalate lên view 1, timer kế fire sau
bao lâu (tính từ lúc arm)?

<details><summary>ĐÁP ÁN</summary>

`_arm_view_change_timer`: `delay = vc_delay · 2^view`. View 0 → `10·2^0 = 10`.
View 1 → `10·2^1 = 20`. Nhân đôi mỗi view (§4.5.2 bài báo: "waits 2δ before
starting view change for view v+2"). Lý do: nếu view mới cũng nghẽn, cho nó *nhiều
thời gian hơn* — chu kỳ đồng-view giãn cấp số nhân tới khi có việc chốt được, chặn
view-change-storm. Kịch bản B integration test tuned quanh đúng biên này:
`D < vc_delay < 2D` ⇒ view 0 timer (=vc_delay) fire trước commit, view 1 timer
(=2·vc_delay) sống sót ⇒ đúng một lần recovery.
</details>

**G5 — tps ∝ n (đóng câu tồn đọng M00/M06).** n=4, honest, workload 1 request trên
node 0. Có bao nhiêu record `decided`? `summarise.py` tính `tps` thế nào ⇒ vì sao
tps tỉ lệ n?

<details><summary>ĐÁP ÁN</summary>

Mỗi node trong n=4 commit-local instance `(0,0)` ⇒ mỗi node phát 1 `decided` ⇒
**4 record `decided`** (integration `test_every_node_decides_seq0` khẳng định 4).
`summarise.py:66` `tps = len(decided)/result.now` = 4/now. Với cùng 1 request
nhưng n=7 → 7 record → tps=7/now. **`tps` đếm decided *per-node*, không per-block**
⇒ tỉ lệ thẳng n. Đây chính là "misnomer" đã bắt ở M00: đại lượng này KHÔNG phải
throughput ứng dụng (goodput mới là). Xem lại `goodput(meta, n_opportunities, now)`
dòng 80-81 — `n_opportunities` = số *instance decided phân biệt* = 1, đúng nghĩa
"một request".
</details>

**G6 — an toàn khi quorum vẫn giao (khái niệm, không chạy).** n=4, f=1. Kẻ tấn công
muốn hai giá trị A và B cùng chốt ở seq 0. Cần mỗi giá trị `2f+1=3` prepare. Vì sao
với ≤1 node xấu điều này bất khả, còn với 2 node xấu thì được — dù hai quorum *luôn*
giao nhau ở ≥ f+1 node?

<details><summary>ĐÁP ÁN</summary>

Hai quorum 3-node trong tập 4: giao ≥ `3+3−4 = 2 = f+1`. Với 1 node xấu: giao 2
node chứa ≥1 **trung thực**; node đó chỉ vote một giá trị cho `(view,seq)` (guard
"không prepare giá trị thứ hai") ⇒ giá trị kia thiếu 1 phiếu ⇒ **không đủ 3**. Với
2 node xấu: giao 2 node có thể là **đúng 2 kẻ xấu**; chúng equivocate — vote A cho
quorum này, vote B cho quorum kia ⇒ **cả A và B đủ 3** ⇒ vỡ an toàn. Điểm tinh tế
(wiki §threshold break): cái vỡ **không** phải "quorum rời nhau" (chúng vẫn giao) —
mà là "honest-vetoer" biến mất khỏi giao. Detector T55 phải soi *equivocation sống
sót trong giao*, không soi *quorum rời*.
</details>

## 6. Phòng thủ (câu hội đồng dễ hỏi — trả lời mẫu, neo nguồn)

**PT1 — "Vì sao đúng `3f+1`? Sao không `2f+1` hay `3f`?"**
Cần đồng thời: (a) chốt được khi `f` node im/chậm ⇒ quorum ≤ `n−f`; (b) hai quorum
bất kỳ giao ở ≥1 node trung thực ⇒ `2·quorum − n ≥ f+1`. Ghép hai điều kiện với
quorum `= 2f+1` ⇒ `n ≥ 3f+1`. Neo: `raw/castro-practicalbft.pdf` §4.5.1 —
*"Since there are 3f+1 replicas, [any two quorums] must intersect in at least one
replica that is not faulty"*; và `wiki/algorithms/pbft.md` §Safety argument +
`wiki/concepts/quorum-arithmetic`. Anchor số: n=4 chịu đúng 1 kẻ phản.

**PT2 — "An toàn có cần mạng đồng bộ không?"**
Không. An toàn giữ dưới **trễ/mất/đảo tuỳ ý** — chỉ **liveness** cần GST (Global
Stabilisation Time — mốc sau đó mạng bó trễ bằng Δ). Neo: `wiki/algorithms/pbft.md`
§Safety argument dòng cuối (*"Safety is independent of synchrony... Only liveness
depends on GST"*) + bài báo §3 (partial synchrony), §4.5.1 vs §4.5.2. Đánh đổi
nêu rõ: đây là chỗ PBFT *mua* an toàn bằng việc **không** đảm bảo tiến triển khi
mạng còn loạn.

**PT3 — "View-change tốn kém thế nào, và khi nào nó phản tác dụng?"**
`O(n³)` bản tin ở PBFT cổ điển — phần đắt nhất. Phản tác dụng = **spurious
view-change**: delay > timeout ⇒ đổi lượt dẫn dù primary trung thực, đốt traffic,
giết throughput dưới delay giật cục. Chính vì thế timeout là **load-bearing** và
là knob chống-delay chính. Neo: bài báo §4.4 + §6 (bảng complexity), wiki
§View change + §Behaviour under network delay + §Weaknesses ("Timeout calibration
is load-bearing"). Đây là hạt giống enhancement adaptive-timeout (T57, đã descope
— nói thẳng nếu hỏi sâu).

**PT4 — "Backoff `2^view` và f+1 catch-up để làm gì?"**
Hai cơ chế liveness từ §4.5.2 bài báo: (a) *timer nhân đôi mỗi view* — *"ensure
this period increases exponentially until some operation executes"* — chặn
view-change-storm; (b) *f+1 catch-up* — *"if a replica receives a set of f+1 valid
view-change messages... it sends a view-change message... even if its timer has not
expired"* — kéo node tụt hậu vào cuộc, và (mặt kia) một node xấu **không** ép nổi
view-change vì cần ≥ `f+1` node muốn (≥1 trung thực). Neo code: `node.py`
`_arm_view_change_timer` (dòng 374) và `_handle_view_change` (dòng 393,
`seen >= self.f + 1`).

**PT5 — "Kết quả PBFT của bạn tin được ở đâu, giả định nào bạn *không* chứng minh?"**
Tin được: honest correctness, liveness, và **equivocating-primary** (conflicting
PRE-PREPARE, chặn ở quorum PREPARE) — đều exercise thật. **Ranh giới mô hình
(nói thẳng)**: sim không mang chữ ký; VIEW-CHANGE evidence là *assertion trần*,
không phải prepared-certificate mật mã ⇒ *safety chống evidence giả* được **giả
định by construction, không chứng minh**; adversary catalog cố ý **không** có năng
lực forge-evidence. Neo: `wiki/algorithms/pbft.md` §Simulator mapping ("Trusted
view-change evidence — modeling boundary"). Đây là caveat = rào chắn phạm vi, không
phải lỗ hổng ẩn.

## 7. Giải thích lại (Feynman) + ghi sổ

Tự nói to, không nhìn code, ~2 phút:
1. Một request đi từ `_propose` tới `decided` qua những trạng thái/quorum nào?
2. Vì sao mọi replica phải **tự ghi phiếu mình** và phiếu-đến-sớm vẫn đếm được?
3. `decided` khoá theo gì để chỉ phát một lần?
4. Hai điểm gai phòng thủ: giao-quorum (an toàn) và view-change (liveness+giá).

Hổng chỗ nào → quay lại §4. Xong: cập nhật `progress.md` (điểm 1–5, đã thông, còn
mờ) + đóng câu tồn đọng `tps ∝ n`.
