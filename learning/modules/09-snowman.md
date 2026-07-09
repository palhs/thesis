# Module 09 — `snowman/` (đào sâu · giao thức thứ ba · Snowman/Avalanche)

> Giao thức đồng thuận **thứ ba**, họ khác hẳn cả PBFT lẫn Casper. ~40–45 phút.
> Đây là module **finality xác suất** — rời hẳn *quorum tất-định* (PBFT/Casper đều
> đếm phiếu tới một ngưỡng cứng) sang *tích lũy tin cậy qua lấy mẫu ngẫu nhiên*.
> Module đào sâu ⇒ đủ: trace & dự đoán + chạy thật + **Phòng thủ**.

## 0. Vì sao tồn tại — và nối với phòng thủ

Snowman là biến thể sản xuất, tuyến-tính-hóa của **Avalanche** — đại diện **họ
probabilistic-finality** (góc `A` của CAP, Module 00). Ba họ, ba sợi chỉ cơ chế:

| Họ | Cách chốt | Đơn vị đếm | Finality |
|----|-----------|-----------|----------|
| PBFT (M07) | quorum `2f+1`, tức thì mỗi block | **node** | tất-định, ngay |
| Casper (M08) | justify→finalise, mỗi epoch | **stake** | tất-định, chậm (2 epoch) |
| **Snowman (M09)** | lấy mẫu `K` peer lặp lại, gom tin cậy | **mẫu ngẫu nhiên** | **xác suất, `1−ε`** |

Điểm cốt: **không vòng nào là một quorum.** Mỗi validator hỏi ý một nhóm nhỏ `K`
peer chọn ngẫu nhiên, và xác suất mọi node trung thực hội tụ về cùng giá trị **tăng
theo hàm mũ theo số vòng** `β`. Finality là *thống kê* — muốn `1−ε` nhỏ bao nhiêu
cũng được, bằng cách **chỉnh tham số**, không phải bằng chờ một sự kiện tất-định.

Nó chống lưng: **RQ1** (latency: Snowman finalise sub-giây, gần như *không phụ thuộc
n*), **RQ2/RQ4** (chi phí truyền tin `O(K·β)` **độc lập n** — trái ngược `O(n²)`
của PBFT; ngưỡng đối kháng là *xác suất*, không phải `1/3` cứng), và mở trục mới:
**đánh đổi finality-tất-định lấy khả năng mở rộng + chịu-trễ**.

Điểm gai phòng thủ (neo bài báo gốc `raw/avalanche.pdf` + wiki):
1. **Safety là xác suất, không phải phân loại (categorical).** Tồn tại xác suất
   khác 0 rằng một trùng hợp đối kháng gây vi phạm an toàn — nhưng xác suất đó bị
   đẩy dưới mọi `ε` mục tiêu nếu `β` đủ lớn. Đây là điểm **yếu nhất** để hội đồng
   chọc: "vậy nó *có thể* fork?" Câu trả lời phải chính xác về *shape* của bảo đảm.
2. **`ε` từ đâu ra + Snowball ≠ Snowflake.** Công thức đóng `(1−α_c/K)^β` và bug
   audit finding #5 (preference = argmax(confidence) tích lũy, KHÔNG phải majority
   của một-vòng) là hai chỗ dễ hiểu sai nhất.

Đường ống 5 tầng lõi (M01–M06) **GIỮ NGUYÊN** — Module này thay ruột node bằng một
engine mới: thay FSM-per-epoch của Casper bằng **Snowball engine per-conflict-set**.

## 1. Đọc gì, theo thứ tự

1. `wiki/algorithms/avalanche.md` — hợp đồng giao thức. **Đọc trước code.** Đặc
   biệt §The subsampling cascade (Slush→Snowflake→Snowball→Avalanche→Snowman),
   §Probabilistic safety (công thức `(1−α_c/K)^β`), §Parameters (bảng `K/α_p/α_c/β`),
   và **§Revisions** (audit finding #5 — argmax-confidence, đọc kỹ, đây là mấu chốt).
2. `src/snowman/parameters.py` (28 dòng) — quy tắc **rescale** `snowman_parameters(n)`
   → `(K, α_p, α_c)`. Production giả định `n≈1000, K=20`; thesis sweep `n∈{4,7,10,
   16,25}` nên `K=min(20, n−1)`, `α_p=⌊K/2⌋+1`, `α_c=⌈0.8K⌉`. β giữ cứng = 15.
3. `src/snowman/messages.py` (33 dòng) — 3 payload frozen: `BlockAnnouncement`
   (proposer công bố block), `Query` (poller hỏi `K` peer), `QueryResponse` (peer
   trả preference hiện tại). Không trường chữ ký (sim truyền object Python).
4. `src/snowman/block.py` (115 dòng) — `Block` + `hash_block` (SHA-256 canonical);
   **`ConflictSet`** = trạng thái Snowball cho **mọi block chung một `parent_id`**
   (`members`, `confidence` = bộ gộp đơn điệu, `preference`, `counter`, `state`); và
   `Chain` (sổ chuỗi tuyến tính cho proposer). Đọc docstring `ConflictSet` kỹ.
5. `src/snowman/poll.py` (197 dòng) — trái tim. `Poll` (một vòng đang bay cho một
   block), `on_response` (ghi từng QUERY-RESPONSE, báo hiệu early-close), và
   **`close_round`** (áp trọn cập nhật Snowball 3 bước: (1) majority-vòng + α_p →
   bump confidence, đặt preference = argmax(confidence), flip khi *strictly exceed*;
   (2) α_c trên preference → counter±; (3) counter≥β → ACCEPTED). Đọc `close_round`
   **hai lần** — đây là chỗ audit #5 sửa và là ranh Snowflake/Snowball.
6. `src/snowman/node.py` (287 dòng) — FSM chính. Đọc theo **luồng đời một block**:
   `_on_start` (arm slot timer) → `_on_timer("slot")` → `_propose` (proposer round-
   robin dựng+broadcast+tự-ghi block) → `_record_announce` (link chuỗi, lazy-create
   conflict set, **arm poll đầu tiên**) → `_start_poll_round` (`rng.sample` K peer,
   gửi K QUERY) → `_handle_response` → `on_response` → `_close_and_continue`
   (`close_round`; nếu ACCEPTED → `_emit_decided`, else arm vòng poll kế).
7. Test (đặc tả chạy được):
   - `tests/snowman/test_snowball_preference.py` — argmax-confidence vs majority-vòng
     (điểm gai audit #5). **Chạy chấm ở grill.**
   - `tests/snowman/test_node_accept.py` — β=15 poll/block → `decided`, no-fork.
   - `tests/snowman/test_node_query.py` — lấy mẫu `K` peer, **tự loại mình**.
   - `tests/snowman/test_parameters.py` — quy tắc rescale.
   Helper: `tests/snowman/_helpers.py` (`make_node`/`capturers`/`kickoff`/
   `build_run_harness`).

Bài báo gốc (đọc **đúng đoạn**, không cày cả bài): `raw/avalanche.pdf`
**§7.4 Theorem 4** (an toàn xác suất): *"the probability that two nodes u and v
decide on R and B respectively is strictly < ε over all timesteps"* — đây là phát
biểu formal của "safety là xác suất". Lưu ý **phân biệt nguồn**: Theorem 4 (paper
[1]) cho *sự tồn tại* của cận `< ε`; còn công thức **đóng** `(1−α_c/K)^β` là từ
Ava docs `[ava-docs]` (§6.1 DeepDive), **không** từ paper. Nói đúng nguồn là một
điểm cộng phòng thủ.

## 2. Mục tiêu khi đọc (trả lời được là đạt)

- **Vì sao no-quorum lại an toàn?** Diễn đạt được: một vòng chỉ hỏi `K` peer (không
  đủ quorum), nhưng `β` vòng liên tiếp α_c-đồng-thuận đẩy xác suất đảo ngược xuống
  `(1−α_c/K)^β` — mũ theo β.
- **ConflictSet là gì, khóa theo gì?** Khóa theo `parent_id` — mọi block "tranh"
  cùng một khe (cùng cha) nằm chung một conflict set; Snowball chọn *một* preference
  trong đó. Baseline trung thực = **singleton** (mỗi khe một block) ⇒ không bao giờ
  flip.
- **`α_p` vs `α_c` khác gì?** α_p (thấp hơn) = ngưỡng *đổi preference*; α_c (cao hơn,
  ≈0.8K) = ngưỡng *tăng counter tin cậy*. Production tách đôi cái mà paper gốc gọi
  chung là `α`, để chỉnh độ-dao-động-preference và xác-suất-finality độc lập.
- **Vì sao audit #5 quan trọng?** preference bám **argmax(confidence tích lũy)** —
  KHÔNG lật theo majority của một vòng đơn (đó là Snowflake, vứt thông tin lịch sử).
- **`decided` bắn khi nào, mấy lần?** Khi `counter≥β` (=15) → block ACCEPTED →
  `_emit_decided` một-lần-mỗi-block-mỗi-node. n node ⇒ n record `decided`/block
  (nối `tps∝n` misnomer từ M07).

## 3. Idiom Python sẽ gặp (gloss)

- **`min(items, key=lambda kv: (-kv[1], kv[0]))`** (poll.py:127) — tìm argmax bằng
  `min` với khóa *đảo dấu*: `-count` để count lớn nhất ra "nhỏ nhất", rồi `kv[0]`
  (block_id bytes) để tie-break *lex nhỏ nhất*. Một dòng gói cả "majority + tie-break
  tất-định". bytes so sánh lex được trong Python.
- **`dict.get(k, 0) + 1` idiom accumulator** (poll.py:53-54, 133-135) — bộ đếm đơn
  điệu không cần khởi tạo trước: đọc-mặc-định-0-rồi-cộng. `confidence` và
  `agree_per_block` đều dùng.
- **`dict.setdefault(k, default)`** (node.py:188) — "lấy nếu có, tạo-rồi-lấy nếu
  chưa" nguyên tử. `conflict_sets.setdefault(parent, ConflictSet(...))` = lazy-create
  conflict set lần đầu thấy parent. So với M07 (`setdefault` tạo ô phiếu rỗng).
- **`self.rng.sample(population, k)`** (node.py:210) — lấy `k` phần tử **không lặp**,
  ngẫu nhiên nhưng **tất-định theo seed** (`self.rng` là per-node RNG seed-hóa từ
  M05). Đây là chỗ duy nhất Snowman "tung xúc xắc". Đổi seed ⇒ đổi peer set ⇒ đổi
  quỹ đạo — nhưng cùng seed ⇒ byte y hệt (reproducibility).
- **`isinstance(timer_id, tuple) and timer_id[0] == "poll"`** (node.py:104) — timer
  đa-hình: `"slot"` (str) vs `("poll", block_id)` / `("query_timeout", bid, rid)`
  (tuple). Dùng cấu trúc phân loại timer, mỗi block một poll-timer riêng.
- **`@dataclass(frozen=True)` cho `PollOutcome`** vs `@dataclass` (mutable) cho
  `Poll`/`ConflictSet` — outcome là *báo cáo* bất biến trả ra; state thì *biến đổi
  tại chỗ*. Cùng phân biệt như M04 (EventRecord frozen).

## 4. Khái niệm gloss (đồng thuận)

- **Subsampled voting (bỏ phiếu lấy mẫu con)** — thay vì hỏi *cả* mạng, mỗi vòng hỏi
  một mẫu nhỏ `K` peer chọn ngẫu nhiên. Chi phí `O(K)`/vòng, **độc lập n**. Đây là
  lý do Snowman mở rộng tới hàng nghìn node.
- **Metastability** — hệ khởi đầu ở thế cân bằng mong manh (50/50); một nhiễu ngẫu
  nhiên nhỏ được **khuếch đại** qua các vòng lấy mẫu tới khi cả mạng "sụp" về một
  phía. Tên bài báo gốc: *"through Metastability"*.
- **Confidence / preference / counter** — ba mức trạng thái Snowball:
  *confidence[b]* = tổng số vòng b là majority (đơn điệu, không giảm); *preference* =
  block confidence cao nhất (argmax); *counter* = số vòng α_c-liên-tiếp trên
  preference hiện tại (reset khi flip hoặc miss α_c). ACCEPT khi counter≥β.
- **`ε` (epsilon) — biên safety** — xác suất hai node trung thực chốt hai block mâu
  thuẫn; `< (1−α_c/K)^β`. Anchor số: `K=20, α_c=16, β=15` ⇒ `(1−0.8)^15 = 0.2^15 ≈
  3×10⁻¹¹`. Đó là "sub-giây, bất biến" của Avalanche.
- **`α_c/K` — tỉ lệ tin cậy** — phần mẫu phải đồng thuận để bump counter. Cao (0.8)
  ⇒ `1−α_c/K` nhỏ ⇒ `ε` bé. Đây là núm chỉnh safety mạnh nhất *trong một vòng*.
- **Probabilistic vs deterministic finality** — PBFT/Casper: "chốt rồi thì KHÔNG BAO
  GIỜ đảo" (categorical). Snowman: "chốt rồi thì đảo với xác suất `≤ε`" (statistical).
  Với ε≈10⁻¹¹ thì thực tế như nhau, nhưng *shape* của bảo đảm khác — điểm gai
  phòng thủ.
- **Liveness dưới bất đồng bộ** — safety KHÔNG cần synchrony; nhưng dưới trễ nặng,
  peer lấy mẫu có thể "chưa biết block" → trả "don't know" → không góp vào α-majority
  → finality **đình trệ** (không vi phạm safety). Amores-Sesar [2] chỉ ra khoảng
  liveness-degradation này bị đánh giá thấp trong treatment gốc.

## 5. Grill "trace & dự đoán"

> Luật chơi: **dự đoán trước**, rồi ta **chạy thật** để chấm. Sai chỗ nào chỉ rõ chỗ
> đó. Làm từng câu một, đừng đọc đáp án trước.

### G1 — Rescale tham số
`snowman_parameters(n)` cho `n=4`, `n=7`, `n=25` trả `(K, α_p, α_c)` là gì? Nhớ
`K=min(20, n−1)`, `α_p=⌊K/2⌋+1`, `α_c=⌈0.8K⌉`.

<details><summary>ĐÁP ÁN G1</summary>

- `n=4`: K=3, α_p=⌊3/2⌋+1=2, α_c=⌈2.4⌉=3.
- `n=7`: K=6, α_p=⌊6/2⌋+1=4, α_c=⌈4.8⌉=5.
- `n=25`: K=min(20,24)=**20**, α_p=⌊20/2⌋+1=11, α_c=⌈16⌉=16 — chạm production.

Chạy chấm: `make test-snowman` hoặc
`PYTHONPATH=src:tests/snowman python3 -m unittest test_parameters -v`.
Điểm gai: ở `n=4`, K=3 nghĩa mỗi vòng chỉ hỏi **3** peer (cả 3 peer còn lại) — mạng
bé đến mức "mẫu con" = "cả mạng trừ mình". Đó là vì sao n=4 là **degenerate boundary**
(có CSV sanity riêng, `snowman_degenerate_n4`).
</details>

### G2 — Lấy mẫu peer
Harness `n=4`. Một `snowman_poll_started` có `peers` gồm mấy phần tử? Node tự-poll
có bao giờ tự hỏi chính mình không?

<details><summary>ĐÁP ÁN G2</summary>

`len(peers) == K == 3`, và `node_id ∉ peers` (lấy mẫu từ `_peers_minus_self()` =
`range(n)` trừ chính mình). Chạy chấm:
`PYTHONPATH=src:tests/snowman python3 -m unittest test_node_query.TestQueryHarness -v`
(`test_poll_started_after_announce`).
Cơ chế: `rng.sample(self._peers_minus_self(), self.K)` — sample **không lặp** từ 3
peer, lấy đúng 3 ⇒ ở n=4 luôn là cả 3 peer (không thực sự "ngẫu nhiên" ở boundary).
</details>

### G3 — Snowflake vs Snowball (điểm gai audit #5)
ConflictSet có 2 block A, B. Chạy **5 vòng** mỗi vòng `{A:4, B:1}` với α_p=3 ⇒
confidence[A]=5, preference=A. Giờ **một vòng** `{B:4, A:1}` (B là majority của
vòng này, đạt α_p). Dự đoán: preference có flip sang B không? `out.flipped`=?
`out.new_preference`=?

<details><summary>ĐÁP ÁN G3</summary>

**KHÔNG flip.** `flipped=False`, `new_preference=A`. Vì Snowball: confidence[B] mới
lên 1, còn confidence[A]=5 — flip chỉ khi challenger **strictly exceed** đương kim.
1 < 5 ⇒ giữ A.

**Snowflake** (bug cũ) sẽ flip sang B ngay vì B là majority của *vòng này*. Đó chính
là audit finding #5: đọc dòng "if count≥α_p → update preference" là "fold vòng này
vào tally lịch sử mà preference bám theo", KHÔNG phải "ghi đè preference bằng winner
của vòng này". Chạy chấm:
`PYTHONPATH=src:tests/snowman python3 -m unittest test_snowball_preference.TestSnowflakeVsSnowballDivergence -v`
(`test_single_majority_round_does_not_flip_high_confidence_pref`).
Bẫy con: để B **thực sự** vượt A cần 6 vòng B-majority (confidence B: 1,2,3,4,5,6 —
qua mốc 5 của A ở vòng thứ 6). Tie (B=5=A) KHÔNG flip — phải strictly exceed.
</details>

### G4 — β-acceptance và `decided`
Harness `n=4`, β=15, delay≈0. Với **một** block đã announce: mỗi node phải chạy bao
nhiêu vòng poll (`snowman_poll_started`) trước khi phát `decided`? Và cả mạng phát
mấy record `decided` cho block đó?

<details><summary>ĐÁP ÁN G4</summary>

Mỗi (node, block) chạy **đúng 15** vòng poll (counter +1/vòng vì baseline singleton
luôn α_c-hit) rồi ACCEPTED → `decided`. n=4 node ⇒ **4** record `decided`/block
(mỗi node tự đạt finality cục bộ). Chạy chấm:
`PYTHONPATH=src:tests/snowman python3 -m unittest test_node_accept -v`
(`test_accepted_block_runs_exactly_beta_polls` khẳng định 15; `test_decided_...`
khẳng định mỗi node decide mọi block; `test_no_forks...` khẳng định 1 value/block).
Nối M07: 4 record/block là *cùng* lý do `tps=len(decided)/t_max ∝ n` là misnomer —
goodput đếm instance phân biệt (`n_opportunities`) mới đúng.
</details>

### G5 — Reproducibility
Chạy `build_run_harness(n=7, t_max=3.0, global_seed=42)` hai lần → so `logger.records`.
Rồi đổi seed=7. Dự đoán: seed=42 hai lần có byte y hệt? seed=42 vs seed=7 khác ở đâu
đầu tiên?

<details><summary>ĐÁP ÁN G5</summary>

seed=42 hai lần: **byte y hệt** — `rng.sample` tất-định theo seed, thứ tự dispatch
tất-định (heap key M01). seed=42 vs seed=7: khác ngay từ `snowman_poll_started`
đầu tiên có conflict (n≥5, K<n−1 ⇒ mẫu THỰC SỰ ngẫu nhiên) — `peers` khác nhau. Ở
n=4 thì peers luôn = cả 3, nên khác biệt seed **không** lộ ở peer set (chỉ ở thứ tự
response nếu delay ngẫu nhiên). Đây là cặp SameSeed/Divergence của M05, giờ ở tầng
giao thức Snowman. Chạy chấm (viết nhanh script so `[r.fields for r in records]`
hai lần, hoặc dựa `test_snowman_baseline` integration).
</details>

## 6. Phòng thủ (câu hội đồng dễ hỏi — trả lời mẫu, neo nguồn)

> Neo `wiki/algorithms/avalanche.md` + `raw/avalanche.pdf` §Theorem 4 + DeepDive
> §6.1. **Không bịa số.** Luyện thành lời ở buổi `14-mock-defense`.

- **PT1 — "Snowman *có thể* fork không? Vậy nó có an toàn không?"**
  *Có thể — với xác suất `< (1−α_c/K)^β`, khác 0 nhưng chỉnh được nhỏ tùy ý.* An
  toàn của Snowman là **xác suất, không phải phân loại** (avalanche.md §Probabilistic
  safety; paper §Theorem 4: hai node chốt R/B với xác suất strictly < ε). Với
  production `K=20,α_c=16,β=15` ⇒ `0.2^15 ≈ 3×10⁻¹¹` — dưới mọi ngưỡng quan sát
  được. Đối lập PBFT: safety **categorical**, suy ra từ giao quorum `3f+1`, xác
  suất fork = 0 tuyệt đối (nhưng đổi lại `O(n²)` và cần `n≥3f+1`).

- **PT2 — "`ε` con số kia lấy ở đâu? Bạn có tự đo được không?"**
  Công thức đóng `(1−α_c/K)^β` từ **Ava docs [ava-docs]** (DeepDive §6.1), KHÔNG
  từ paper — paper §Theorem 4 chỉ chứng minh *tồn tại* cận `<ε`. Thesis **đo empirical
  ε** bằng đếm vi phạm qua nhiều seed rồi so đường cong empirical với cận lý thuyết
  (avalanche.md §Probabilistic safety). Đây là analogue của accountable-safety check
  ở Casper — bảo đảm là thật, nhưng *shape* là xác suất, không phải categoricity.

- **PT3 — "Vì sao không đếm quorum như PBFT? Được gì, mất gì?"**
  *Được:* chi phí `O(K·β)`/validator **độc lập n** ⇒ mở rộng hàng nghìn node, và
  chịu-trễ tốt (vòng đóng khi `K` response đầu về, peer chậm không cản — avalanche.md
  §Behaviour under network delay). *Mất:* finality tất-định (chỉ còn `1−ε`), và
  **nhạy tham số**: `(K,α_p,α_c,β)` phải chọn *toàn mạng, cùng nhau*; chọn tồi làm
  xói `ε` vài bậc mà giao thức *không lộ dấu hỏng* (avalanche.md §Weaknesses).

- **PT4 — "Sybil? Ai đó tạo 10000 node ảo thì sao?"**
  Snowman **không** tự chống Sybil — lấy mẫu ngẫu nhiên *giả định* phân bố peer
  trung thực. Chống Sybil là **ngoại vi**: trên AVAX là **stake-weighted sampling**
  (avalanche.md §Model, §Weaknesses "Sybil resistance is external"). Nối M08: Casper
  đóng Sybil *bên trong* bằng đếm stake; Snowman đẩy ra ngoài engine. Sim của thesis
  dùng lấy mẫu đồng-đều (chưa stake-weighted) — một giới hạn phạm vi ghi rõ.

- **PT5 — "Dưới bất đồng bộ (trễ nặng) nó có chết không?"**
  Safety KHÔNG chết (không cần synchrony). Nhưng **liveness đình trệ**: peer chưa
  nhận block → trả "don't know" → không góp α-majority → counter không lên. Amores-
  Sesar [2] (avalanche.md §Behaviour under delay) chỉ ra khoảng liveness-degradation
  dưới bất đồng bộ worst-case bị treatment gốc [1] đánh giá thấp. Sim probe đúng khe
  này (T51 delay sweep: đo time-to-accept khi trễ tăng). Đối lập: quorum-based (PBFT)
  **stall hẳn** dưới trễ tương tự — Snowman "chậm dần" thay vì "đứng im".

## 7. Giải thích lại (Feynman) + ghi sổ

Sau grill, người học tự giải thích bằng lời mình:
1. Vì sao "không quorum" mà vẫn an toàn — vai trò `β` (mũ) và `α_c/K` (cơ số).
2. ConflictSet khóa theo `parent_id`; baseline trung thực = singleton ⇒ không flip;
   flip chỉ xảy ra khi có block cạnh tranh cùng cha (audit #5: argmax-confidence).
3. `decided` bắn khi counter≥β=15; n node ⇒ n record (nối tps∝n misnomer).
4. Một câu phòng thủ đắt nhất (PT1): "safety xác suất không phải categorical" — nói
   đúng *shape*, đúng con số `0.2^15≈3×10⁻¹¹`, đúng nguồn (Ava docs vs paper Thm 4).

Cập nhật `progress.md`: điểm 1–5, đã thông / còn mờ, gom câu mở. **Đóng câu tồn
đọng α_c/β từ M00** (giờ đã có con số + cơ chế). Ghi vào "Nhật ký buổi học".
