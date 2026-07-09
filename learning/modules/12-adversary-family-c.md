# Module 12 · `adversary/` — Họ C (adversarial experiment) ★ đào sâu

> Chặng 5 · Thí nghiệm, module đào-sâu thứ hai (sau `delay/` Họ B). Đây là module
> đóng phần "sinh số liệu": rời **mạng-trung-thực-nhưng-chậm** (Họ B) sang
> **đối-thủ-chủ-đích** (Họ C). Ba chiến lược tấn công gắn lên một khe duy nhất
> `Node.adversary`. Adapter sweep TÁI DÙNG y khuôn M11 — nên module này nhẹ phần
> "đường ống", nặng phần "cơ chế tấn công + vì sao byte-identical vẫn giữ".

---

## Cầu nối từ M11 (ôn 3 mảnh còn mờ — chúng tái xuất ở đây)

Con trỏ M11 ghi 3 chỗ Feynman yếu. Cả ba **quay lại nguyên si** trong M12, nên ta
đối chiếu ngay:

1. **Đường ống một cell.** M11: `run_<proto> → clip_records → reducer → _build_row
   → 1 dòng`. M12 GIỮ NGUYÊN chuỗi này (đọc `sweep.py::_run_cell`, dòng 141–148) —
   khác duy nhất: `run_<proto>` giờ tiêm thêm adversary trước khi chạy.
2. **Window-denominator (`_window_denominator_fix`).** M12 **import thẳng** từ
   `delay.sweep` (dòng 49) và gọi trong `_build_row` (dòng 96). Cùng cơ chế: HAI
   `t_max` (run() dừng ở `T_MAX=230` vs `meta.t_max=WINDOW_S=150` là mẫu-số);
   reducer PBFT chia `result.now`, FFG/Snowman chia `meta.t_max`.
3. **Adapter = BA HÀM THUẦN.** `_run_cell / _cell_key / _param_fingerprint` — y hệt
   M10/M11. `commit_hash` tiêm qua `run_constants` (resolve 1 lần ở cha); `f, m` vào
   fingerprint; `seed` là identity không phải param. `clip_records` + `run_grid_tiered`
   tái dùng nguyên khối từ Họ B.

→ **Câu chốt của cả module:** Họ C chỉ đổi HAI thứ so với Họ B — **config** (thêm
trục `f` và `m`) và **runners** (tiêm `Node.adversary`). Mọi thứ khác (clip, reducer,
sweep, byte-identical) là hạ tầng cũ.

---

## 0 · Vì sao module này tồn tại (neo RQ / hình / chương)

- **RQ4** ("mỗi giao thức chịu đối thủ ra sao?") sống ở đây. Ba sweep T51/T52/T53
  là toàn bộ bằng chứng thực nghiệm cho RQ4.
- **Ch4 §4.4** (adversarial results) + **Ch5 synthesis** (RQ5 Pareto) đọc thẳng CSV
  của module này. Finding cốt lõi: **no protocol dominates across all three
  adversaries** (F7–F10) — PBFT/FFG/Snowman đổi hạng tùy loại tấn công.
- Ba chiến lược ↔ ba trục yếu điểm khác nhau:
  - `delay-emission` (T51) — *liveness*: làm chậm, không phá đúng-sai.
  - `withhold-participation` (T52) — *liveness*: im lặng hẳn (offline).
  - `equivocate-vote` (T53) — *safety*: nói dối (ký hai bản mâu thuẫn) để ép fork.
- Neo wiki: `[[concepts/adversary-model]]` (catalog §§3–5), ba experiment page
  `2026-06-14_delayed-voters` / `2026-06-17_offline-validators` /
  `2026-06-18_equivocating-nodes`, và Revisions §T51/§T52/§T53 của adversary-model.

---

## 1 · Đọc gì (thứ tự)

**Wiki (định hướng):**
- `wiki/concepts/adversary-model.md` §§2–5 (matrix + ba capability) + §Revisions
  (T51/T52/T53 — mỗi Revision là một dòng "cơ chế đã hiện thực ra sao").

**Code (`src/adversary/`), đọc theo lớp:**
1. `select.py` — HAI hàm chọn tập tấn công: `slow_node_ids` (high-id, chừa primary)
   vs `byzantine_node_ids` (low-id, ôm primary). **Đối lập có chủ đích.**
2. `profiles.py` — ba dataclass `DelayProfile / OfflineProfile / EquivocateProfile`
   (data thuần, lấp khe `Node.adversary`; `mult` chỉ có ở Delay).
3. `inject.py` — seam **network-wrap** (delay + offline). `_wrap_outbound` dùng
   chung; delay shift `t`, offline drop. **KHÔNG sửa FSM.**
4. `equivocate.py` — seam **node-subclass** (equivocate). Ba lớp con override đúng
   các hàm phát-payload để fork. `split_recipients` (parity) là điểm gai.
5. `runners.py` — ba bảng dispatch (`RUNNERS`/`OFFLINE_RUNNERS`/`EQUIVOCATE_RUNNERS`).
   Xem ba `run_pbft*` cạnh nhau để thấy "chỉ đổi dòng inject / dòng chọn class".
6. `sweep.py` — adapter (ba hàm thuần) + `safety.py` (reducer safety cho T53).

**Test (`tests/adversary/`):** `test_select`, `test_inject`, `test_equivocate`,
`test_determinism`, `test_runners`, `test_safety`.

---

## 2 · Mục tiêu khi đọc (nắm được là xong module)

- [ ] Phân biệt **hai paradigm tiêm**: network-wrap (delay/offline, FSM sạch) vs
      node-subclass (equivocate, override emit). Nói được vì sao equivocate KHÔNG
      thể là wrap (nó *đổi nội dung* payload, không chỉ hoãn/bỏ).
- [ ] Giải thích **đảo chiều chọn tập**: high-id chừa primary (liveness attack, để
      primary còn chạy mà đo) vs low-id ôm primary (safety attack, cần primary +
      proposer nằm TRONG tập ác).
- [ ] Nói được **vì sao cả ba vẫn byte-identical**: fixed shift / drop / parity-split
      thuần hàm → **không xé một tờ RNG nào của adversary** → replay y hệt → safety
      signal seed-invariant.
- [ ] Trace **parity crux**: tại sao chia recipient theo chẵn/lẻ id, không theo
      nửa-liền-kề (contiguous) → điều kiện fork `b > f`.
- [ ] Đọc được ba **posture** kết quả (delay/offline/equivocate × PBFT/FFG/Snowman)
      và nối về RQ4 "no dominance".

---

## 3 · Idiom Python gloss (gặp trong module)

- **Factory tránh bẫy late-binding closure** (`inject.py:28` `_delayed_send`). Nếu
  viết `lambda dst,...: honest(dst,..., t+shift)` NGAY trong vòng `for nid in ids`,
  mọi closure sẽ tham chiếu cùng biến vòng lặp (bug kinh điển). Đây bọc trong một
  hàm nhận `shift` làm tham số → mỗi node giữ `shift` riêng. (M11 đã gặp ở clip; ở
  đây là ôn lại.)
- **Monkey-patch bound method** (`inject.py:61` `node.send = send_factory(node.send)`).
  Gán đè thuộc-tính-instance lên method đã bound bởi `Network.bind`. Node không biết
  mình bị bọc; FSM gọi `self.send(...)` như thường. Đây là cả linh hồn của
  "attaches at the Node level, post-build".
- **Subclass override chọn-lọc** (`equivocate.py`). `EquivocatingPBFTNode(PBFTNode)`
  chỉ override `_propose/_broadcast_prepare/_broadcast_commit`; phần FSM còn lại kế
  thừa nguyên. `super()._attest(...)` ở CasperNode = "chạy FSM trung thực TRƯỚC, rồi
  bồi thêm phiếu mâu thuẫn".
- **Dispatch-table dict** (`runners.py:156/224/296`). `RUNNERS[proto](...)` — ba
  bảng song song, cùng shape `RunTriple`. Chọn class runtime: `cls = Equivocating... if
  node_id in byz else HonestClass`.
- **`math.floor(f * n)`** (`select.py`). `⌊f·n⌋` — với mọi `f<1`, count `<n`, nên
  high-id set không bao giờ chạm node 0 (bất biến delay/offline dựa vào).

---

## 4 · Khái niệm gloss (đồng thuận / đo lường)

- **delay-emission** — hoãn phát tin `m·ref` giây (`ref` = nhịp vòng của giao thức;
  PBFT/Snowman ref=1.0s, FFG ref=0.1s). Trục **magnitude m** (2→10). Liveness-only:
  tin đến *muộn*, không sai, không mất.
- **withhold-participation (offline)** — node nhận + chạy FSM nhưng **phát rỗng** →
  không góp quorum/poll = crash-faulty im lặng. **Nhị phân**, không có m.
- **equivocate-vote** — ký hai bản tin mâu thuẫn nơi giao thức chờ một. Fork payload.
  Đây là **safety attack** duy nhất trong ba.
- **f (byzantine_fraction)** — nhân vật chính, trục sweep chung cho cả ba. `⌊f·n⌋`
  node tấn công. Grid tới/qua 1/3 (equivocate tới 0.50) để *đo* vách chứ không đoán.
- **finality_delay_ratio** (headline T51) — `commit_latency(attack) / commit_latency(f=0
  control)` cùng `(proto,n,seed)`. Điền ở **post-grid pass** (`_finality_delay_ratios`)
  để mỗi `_run_cell` vẫn thuần. Control f=0 = 1.0 theo định nghĩa.
- **finalization_success_rate** (headline T52) + **f\*** (vách liveness).
- **safety triple** (headline T53): `safety_violation / conflicting_instances /
  max_slashable_stake_fraction` — tính trên stream **chưa clip**, **loại node
  Byzantine** khỏi phép so (một node ác "quyết" gì không chứng minh gì).
- **accountable safety (FFG)** — không fork mà *phát hiện + đốt cọc*. Tín hiệu trung
  thực là `max_slashable_stake_fraction` (`=⌊f·n⌋/n`), chạm ≥1/3 tại f=0.40.
- **Option-B clip** — clip **báo cáo, không chặn** ở <5% (như T47). Snowman tràn ~37%
  đuôi qua W ở m=10; đuôi đó *chính là* tín hiệu suy thoái nên không cắt.

---

## 5 · Grill "trace & dự đoán"

> Đoán TRƯỚC, rồi chạy chấm (lệnh ở cuối mục). Né mọi class `jobs>1` (treo sandbox).

### G1 — `select.py`: đảo chiều high-id / low-id
Cho `n=10, f=0.30`. (a) `slow_node_ids(10, 0.30)` = ? (b) `byzantine_node_ids(10,
0.30)` = ? (c) Vì sao delay/offline dùng (a) còn equivocate dùng (b)?

<details><summary>ĐÁP ÁN G1</summary>

`k = ⌊0.30·10⌋ = 3`.
(a) `slow_node_ids` = **(7, 8, 9)** — 3 id cao nhất, ascending. Chừa node 0 (PBFT
view-0 primary). Vì mọi `f<1` cho `k<n`, node 0 KHÔNG BAO GIỜ trong tập → primary
còn chạy, ta đo được *slow backups* làm gì (đây là delay-emission, KHÔNG phải
disrupt-leader).
(b) `byzantine_node_ids` = **(0, 1, 2)** — 3 id thấp nhất. Ôm node 0.
(c) Liveness attack (delay/offline) muốn primary còn sống để hệ vẫn tiến, đo độ
chậm. Safety attack (equivocate) CẦN primary + proposer slot nằm trong tập ác để
sản xuất PRE-PREPARE/block mâu thuẫn — nên phải ôm low-id prefix.
</details>

### G2 — hai paradigm tiêm: wrap vs subclass
`inject_delay` và `inject_offline` cùng gọi `_wrap_outbound`. Tại sao equivocate
KHÔNG dùng được `_wrap_outbound` mà phải viết subclass? Nếu cố nhét equivocate vào
seam wrap thì hỏng ở đâu?

<details><summary>ĐÁP ÁN G2</summary>

`_wrap_outbound` chỉ can thiệp *thời điểm* (shift) hoặc *có/không gửi* (drop) — nó
nhận `(dst, type, payload, t)` và chuyển tiếp/bỏ. Nó **không biết payload nên là
gì**. Equivocate phải **fork nội dung**: gửi `reqA` cho nhóm chẵn, `reqB` cho nhóm
lẻ, và tự-ghi phiếu cho một bản. Đó là **quyết định ngữ nghĩa của FSM** (primary tạo
digest, proposer tạo block), phải sống *bên trong* logic phát, nên override method
FSM (`_propose/_broadcast_prepare/...`) mới đúng chỗ. Nhét vào wrap sẽ không có ngữ
cảnh `(view, seq)` / `slot` để tạo cặp payload mâu thuẫn khớp digest.

Hệ quả kiến trúc: delay/offline giữ **honest FSM sạch tuyệt đối** (B-network wrap);
equivocate là **B-hybrid** (subclass trong `adversary/`, FSM gốc `src/{pbft,pos,
snowman}/` vẫn không đụng).
</details>

### G3 — parity crux (điểm gai sâu nhất)
Byzantine = low-id prefix `{0,1,2}` ở n=10. `split_recipients` chia peer-trừ-self
theo **chẵn/lẻ id**. (a) Vì sao KHÔNG chia nửa-liền-kề (vd {0..4} vs {5..9})?
(b) Điều kiện để hai quorum `2f+1` mâu thuẫn hình thành là gì?

<details><summary>ĐÁP ÁN G3</summary>

(a) Byzantine là prefix liền-kề {0,1,2}. Nếu split cũng liền-kề, **toàn bộ honest
suffix {3..9} rơi về MỘT phía** → phía kia không đủ honest để lập quorum thứ hai →
không fork được, PBFT chỉ *đứng hình* (stall) rồi view-change. Muốn fork thật phải
để hai phía **đều có honest**.
(b) Parity cắt NGANG: nhóm chẵn {0,2,4,6,8}, nhóm lẻ {1,3,5,7,9} — mỗi nhóm chứa cả
honest lẫn Byzantine. Mỗi honest nhận đủ `b` phiếu-fork của Byzantine. Hai quorum
`2f+1` xung đột hình thành đúng khi **`b > f`** (số Byzantine vượt ngưỡng chịu lỗi
`f_tol=⌊(n−1)/3⌋`). Đó là lý do `conflicting_instances` nhảy 0→229 giữa f=0.33 và
0.40. `split_recipients` là **hàm thuần của (n, id)** — không RNG → replay byte hệt.
</details>

### G4 — byte-identical dưới tấn công
Cả ba chiến lược đều tuyên bố "per-cell replay byte-identical". Nguồn gốc chung là
gì? Và tính chất đó cho T53 một hệ quả *phương pháp luận* gì (khác latency)?

<details><summary>ĐÁP ÁN G4</summary>

Nguồn chung: **adversary không tiêu một mẫu RNG nào**. Delay = shift bằng hằng
`m·ref` (cố định). Offline = drop (không quyết định gì). Equivocate = cặp payload
`conflicting_bytes` thuần theo key + split parity thuần theo id. Tất cả tất định →
chỉ còn RNG honest (mạng + per-node) như baseline → cùng seed cho cùng byte.

Hệ quả cho T53: **safety signal seed-invariant**. `safety_violation` không phải biến
ngẫu nhiên — nó là hàm xác định của `(protocol, n, f)`. Nên fork-cliff của PBFT
(0→1 giữa f=0.33/0.40) là **vách quyết định**, không phải "xui một seed". Đây là lý
do T54 báo cáo `f_max` dạng *bracket* `[0.33, 0.40]` chứ không cần CI qua seed cho
safety.
</details>

### G5 — ba posture kết quả (nối RQ4)
Điền bảng: mỗi (chiến lược × giao thức) → PBFT/FFG/Snowman ai chịu tốt nhất / tệ
nhất, và tại sao. Rồi phát biểu finding RQ4.

<details><summary>ĐÁP ÁN G5</summary>

| | PBFT | Casper FFG | Snowman |
|--|--|--|--|
| **delay** | **miễn nhiễm** (quorum honest đủ, 0 view-change) | latency-immune, liveness dip nhẹ (proposer overlap) | **nổ ~49–62×** (β=15 poll *tuần tự* lặp trúng responder chậm) |
| **offline** | vách 1/3 sạch (f\*=0.40) | suy thoái *mượt* ≈(1−f), chết sau 1/3 | vách αc **DƯỚI** 1/3, phụ thuộc n (f\*=0.20@n10 / 0.33@n25) |
| **equivocate** | **fork cliff** trên 1/3 (conflicting=229) | **accountable** (không fork, detect+slash) | **kháng** (all-zero, Snowball hội tụ) |

Finding RQ4: **không giao thức nào trội trên cả ba trục.** delay: PBFT≈Snowman≫FFG;
withhold: PBFT≈FFG>Snowman; equivocate: Snowman>FFG>PBFT (kháng > phạt-quy-trách >
fork-vô-danh). Mỗi giao thức non-dominated → đây chính là căng thẳng RQ4/RQ5
"rankings invert across adversaries".
</details>

**Lệnh chạy chấm** (macOS, `head` bị shadow → dùng `sed/awk`; né `jobs>1`):
```bash
# G1 (select):
make test-adversary 2>&1 | tail -5
PYTHONPATH=src:tests/adversary python3 -m unittest test_select -v
# G2/G3 (inject + equivocate):
PYTHONPATH=src:tests/adversary python3 -m unittest test_inject test_equivocate -v
# G4 (determinism — byte-identical rerun + f0==honest):
PYTHONPATH=src:tests/adversary python3 -m unittest test_determinism -v
# G5 posture (runners: control finalizes, offline threshold stall, monotone):
PYTHONPATH=src:tests/adversary python3 -m unittest test_runners test_safety -v
# adapter thuần (sweep_common — KHÔNG chạy full sweep, treo):
PYTHONPATH=src:tests/adversary python3 -m unittest test_sweep_common -v
```

---

## 6 · Phòng thủ (câu hội đồng dễ hỏi — trả lời neo wiki, không bịa)

**PT1 — "Bạn cố tình chừa PBFT primary ở delay/offline nhưng lại ôm nó ở
equivocate. Chọn tập theo ý muốn kết quả — có phải cherry-pick?"**
Không, đó là **định nghĩa của từng capability**, không phải tối ưu kết quả.
delay-emission/withhold theo catalog là tấn công *backup/voter* (spec §3/§4); nếu
làm primary chậm thì đó là *disrupt-leader* — một capability KHÁC (§6), có task
riêng (không làm). Chọn high-id để giữ đúng ranh giới đó (select.py docstring).
equivocate (§5) theo định nghĩa cần primary/proposer ký bản mâu thuẫn, nên phải ôm
low-id. Cả hai lựa chọn được *khai báo và báo cáo*, không giấu. Neo:
`[[concepts/adversary-model]]` §3/§5, `select.py`.

**PT2 — "Split recipient theo parity nghe như engineer cho ra fork. Sao không
để adversary tùy ý?"**
Parity là cách **tối thiểu-thiên-vị** để một prefix Byzantine liền-kề chạm được cả
hai phía honest — điều kiện *cần* để fork tồn tại. Nếu split liền-kề, honest dồn một
phía và PBFT chỉ stall (không fork) → ta sẽ *báo cáo nhầm* PBFT an toàn hơn thực tế.
Parity là hàm thuần `(n,id)`, giống nhau ở mọi Byzantine node (đồng-lõa không cần
liên lạc), không RNG. Kết quả fork chỉ xảy ra **đúng khi `b > f`** — khớp lý thuyết
BFT, không phải nhân tạo. Neo: `equivocate.py::split_recipients`,
`[[concepts/adversary-model]]` §Revisions T53.

**PT3 — "Sweep chạy tới f=0.40, 0.50 — vượt ngưỡng 1/3 catalog. Ngoài vùng hợp lệ?"**
Cố ý. Ta **đo** vách an toàn thay vì *suy* ra nó. Trong vùng `f≤1/3` cả ba
classification §5 giữ; qua 1/3 PBFT fork đúng như BFT tiên đoán (`b>f_tol`), FFG chạm
≥1/3 slashable tại 0.40, Snowman vẫn kháng. Cross-ngưỡng cho ta *vị trí vách*, là dữ
liệu, không phải vi phạm giả định. Neo: experiment page T53 §sweep,
`[[concepts/adversary-model]]` §Revisions.

**PT4 — "FFG 'không fork' — đó là accountable safety thật hay chỉ vì mô hình của
bạn không biểu diễn được fork?"**
Trung thực: **một phần là giới hạn mô hình, và ta khai báo nó.** `EpochState.links`
gộp stake theo `source_epoch` và **bỏ qua `target_hash`**, nên một forked-proposal
sẽ "finalise" giả hai checkpoint dưới honest supermajority = *model artifact*, không
phải safety break thật. Vì thế FFG chỉ mô hình **double-vote**, và tín hiệu trung
thực là `max_slashable_stake_fraction` (=`⌊f·n⌋/n`, chạm ≥1/3 tại f=0.40), KHÔNG phải
`safety_violation`. Đây là accountable-safety đúng nghĩa *detect + slash*, và ranh
giới fidelity được ghi rõ. Neo: `equivocate.py::EquivocatingCasperNode` docstring,
`[[concepts/adversary-model]]` §Revisions T53, `safety.py`.

**PT5 — "Bạn thêm Snowman query-timeout riêng cho offline. Không phải vá để ra kết
quả đẹp sao?"**
Ngược lại — không có nó thì sweep **không đóng nổi**. Offline node không bao giờ trả
lời, mà một poll round chỉ đóng khi đủ `α_c` đồng ý HOẶC đủ cả K phản hồi; nếu sample
trúng >`K−α_c` node im vĩnh viễn thì round treo mãi. timeout (opt-in, 15s) cho round
*đóng* để đo được vách. Và vách đó chính là finding: Snowman gãy liveness **dưới**
1/3 (f\*=0.20@n10), phụ thuộc n — *mâu thuẫn* kỳ vọng "proportional degradation" của
catalog §4, được ghi thành Revision (không giấu). Với delay (§3) responder *cuối cùng
có* trả lời nên không cần timeout. Neo: `[[concepts/adversary-model]]` §Revisions T52,
experiment page `2026-06-17_offline-validators`.

---

## 7 · Giải thích lại (Feynman) + ghi sổ

Sau grill, tự nói (không nhìn guide):
1. Họ C khác Họ B ở đúng HAI chỗ nào? (config trục f/m + runners tiêm adversary)
2. Hai paradigm tiêm + vì sao equivocate không thể là wrap.
3. Đảo chiều high-id/low-id gắn với liveness-vs-safety ra sao.
4. Một câu vì-sao-byte-identical, và hệ quả seed-invariant cho safety.
5. Parity crux: điều kiện fork `b>f`.
6. Finding RQ4 "no dominance" bằng bảng 3×3.

Rồi cập nhật `progress.md`: điểm 1–5, thông/mờ, câu mở. Nếu Phòng thủ chưa luyện
thành lời → dồn `14-mock-defense` (cùng nợ PBFT/Casper/Snowman/delay).
