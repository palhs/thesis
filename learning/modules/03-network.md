# Module 03 · network — tầng gửi tin có trễ, mất gói, phân mảnh

> Chặng 1 · Lõi. Code: `src/network/` (`network.py` + `phases.py`).
> Wiki hợp đồng: [[concepts/network-model]] + [[concepts/network-model-phases]].
> Test: `tests/network/` (5 file). Chạy chấm: `make test-network`.

---

## 0. Vì sao module này tồn tại (neo luận văn)

Nhớ câu thần chú: *một YAML + một seed → một dòng CSV*. `Network` là **kênh
truyền tin giữa các node**. Node muốn nói chuyện với nhau (PBFT gửi PRE-PREPARE,
Casper gửi ATTESTATION, Snowman gửi QUERY) — tất cả đi qua đây. Nó quyết định
**tin có tới không, và tới trễ bao lâu**.

Ba núm vặn của kênh này *chính là* biến độc lập của hai họ thí nghiệm lớn:

| Núm | Cơ chế trong `Network` | Chống lưng cho |
|-----|------------------------|----------------|
| **delay** (trễ) | `DelayDist.sample()` — rút một số dương làm độ trễ | **Họ B** (Family B, delay), RQ1 (finality vs mạng), hình Ch4 §4.3 (4.8–4.13) |
| **p_drop** (mất gói) | tung đồng xu Bernoulli mỗi tin | **Họ B** loss, RQ4 (xếp hạng chịu-lỗi PBFT ≥ Snowman > FFG) |
| **partition** (phân mảnh) | vị-từ chặn giữa các nhóm | mô hình bất-đồng-bộ / GST, CAP ([[concepts/cap-theorem]]) |

Điểm cốt: **`Network` chỉ là hạ tầng *trung thực* (honest)**. Nó tiêm trễ/mất-gói
kiểu *vô ý* của mạng thật — không phải kẻ tấn công có chủ đích. Toàn bộ ngữ nghĩa
đối thủ (adversary) sống ở tầng `Node` (T18, Họ C). Đây đúng là ranh giới **B
(network, vô ý) ≠ C (adversary, có chủ đích)** bạn đã chốt ở Module 00.

Và vì đây là tầng lõi của một *discrete-event simulation*, `Network` không "gửi"
gì thật — nó **đặt lịch một `Delivery` event** vào heap của `Scheduler` ở thời
điểm `t_sent + delay`. Đó là mắt xích nối Module 01 (scheduler) với Module 02
(nodes): `Node.send` (placeholder ở M02) được `Network.bind` **đè** bằng lambda
gọi `submit_unicast` — câu hỏi mang sang từ M02 sẽ được đóng ở đây.

---

## 1. Đọc gì, theo thứ tự

1. **Wiki trước (hợp đồng):**
   - [[concepts/network-model-phases]] — trang runtime, đọc kỹ **§1** (phase),
     **§2** (delay dist), **§3** (drop), **§4** (partition), **§6** (determinism:
     RNG mạng, thứ tự lấy mẫu, bề mặt cấm). Đây là trang "phải làm gì".
   - [[concepts/network-model]] §1 — *đường ống 5 bước* (five-step pipeline).
2. **Code (làm thế nào):**
   - `src/network/phases.py` — 3 dataclass `DelayDist` / `Partition` / `Phase`
     + `validate_timeline`. Đọc trước vì `network.py` xài chúng.
   - `src/network/network.py` — class `Network`. Trái tim là `_try_deliver`
     (đường ống 5 bước) ở cuối file.
3. **Test (đặc tả chạy được):**
   - `tests/network/test_delay_dist.py` — dist hợp lệ/không, mẫu dương.
   - `tests/network/test_network.py` — wiring, phase-advance, delivery pipeline,
     determinism. **File chính** — đọc kỹ.
   - `tests/network/test_partition.py` — ngữ nghĩa chặn nhóm.
   - `tests/network/test_e2e.py` — ping-pong 2 node qua `Network` thật (tiền đề
     cho Module 06 trace end-to-end).

---

## 2. Mục tiêu khi đọc (đọc xong tự trả lời được)

- [ ] Vẽ được **đường ống 5 bước** của `_try_deliver` và nói **bước nào tiêu RNG,
      bước nào không**, theo **đúng thứ tự** (`network-model-phases.md` §6.2).
- [ ] Giải thích vì sao `Network.bind` đè `send`/`broadcast` — và lambda closure
      "ôm" cái gì (khóa câu hỏi M02).
- [ ] Nói được vì sao "gửi" = **đặt lịch `Delivery` ở `t_sent + delay`**, không
      phải gọi hàm node đích ngay.
- [ ] Chỉ ra **RNG mạng (net_rng) khác RNG per-node** ở đâu và tại sao (blake2b,
      không phải `hash()`).
- [ ] Phân biệt được **drop (Bernoulli, tiêu RNG)** vs **partition (tất định,
      không RNG)** — và vì sao thứ tự giữa chúng lại quan trọng cho tính tái lập.
- [ ] `advance_phase` đổi cái gì; vì sao `PhaseAdvance` (node_id = −1) không đua
      (race) với `Delivery` cùng `t`.

---

## 3. Idiom Python cần gloss

- **`@dataclass(frozen=True)`** (`phases.py`) — sinh tự động `__init__`,
  `__eq__`, `__hash__`; `frozen=True` = **bất biến** (gán lại field → lỗi). Vì sao
  quan trọng: `Phase`/`DelayDist` là *cấu hình*, đóng băng chống sửa nhầm giữa run.
  ⚠️ Lưu ý docstring `DelayDist`: `params` (dict) **không** được đóng băng sâu —
  đừng mutate dict sau khi tạo (validation chỉ chạy 1 lần ở `__post_init__`).
- **`__post_init__`** — hook chạy *sau* `__init__` tự-sinh của dataclass. Đây là
  chỗ `DelayDist` **fail-fast**: kind lạ / thiếu param / param ≤ 0 → `ValueError`
  *ngay lúc tạo*, trước khi bất kỳ run nào chạy.
- **`lambda dst, type, payload, t: self.submit_unicast(node.id, ...)`**
  (`network.py:58`) — hàm vô danh làm **closure**: nó *ôm sẵn* (`capture`)
  `self` (Network) và `node.id`. Nên khi node gọi `self.send(dst, ...)`, id người
  gửi đã được "curry" (dán cứng) vào — node không tự khai báo mình là ai. Cùng
  idiom bạn đã gặp ở M02 split-bind, giờ nhìn từ phía Network.
- **`type` che builtin** — tham số tên `type` shadow hàm `type()` của Python. Cố
  ý, để khớp chữ ký `node.send(dst, type, payload, t)` ở [[concepts/node-model]] §7.
  Trong phạm vi hàm đó bạn mất `type()`, nhưng ở đây không cần.
- **`hashlib.blake2b(...).digest()` → `int.from_bytes(..., "big")`** — băm chuỗi
  seed ra 8 byte tất định, đổi thành int 64-bit. Dùng thay `hash()` builtin vì
  `hash()` của `str` bị **ngẫu-nhiên-hóa theo tiến trình** (`PYTHONHASHSEED`) →
  hai tiến trình cho seed khác nhau → **phá replay byte-identical**. (Xem §6.1
  Revisions của wiki.)
- **`random.Random(seed)`** — một *instance* RNG **riêng**, không phải `random.x`
  toàn cục. Mỗi `Network` giữ `self.net_rng` độc lập → hai run song song không
  giẫm chân RNG của nhau. `.random()` = float [0,1); `.getstate()` = ảnh chụp
  trạng thái RNG (test dùng để so "đã tiêu đúng k lần rút").
- **`any(p.blocks(src, dst) for p in phase.partitions)`** — generator + `any`:
  "có *bất kỳ* partition nào chặn không?". Nhiều partition **hợp** (disjunctive):
  một chặn là đủ.
- **`sorted(self.registry)`** (broadcast) — lặp theo `NodeId` tăng dần, **không**
  theo thứ tự dict. Vì sao: mỗi người nhận tiêu *một* mẫu delay từ `net_rng`;
  thứ tự lặp cố định ⇒ ánh xạ recipient→mẫu tất định ⇒ replay được (§6.3).

---

## 4. Khái niệm cần gloss

- **phase (pha mạng)** — một khoảng thời gian `[t_start, t_end)` mà điều kiện
  mạng *cố định* (một delay-dist, một p_drop, một tập partition). Đổi điều kiện =
  sang phase mới. Cách mô phỏng "trước GST hỗn loạn → sau GST ổn định": pha 1
  heavy-tail + partition, pha 2 uniform + không partition.
- **half-open `[t_start, t_end)`** — mốc `t = t_end` thuộc phase *sau*. Nhờ vậy
  ranh giới không nhập nhằng: tin gửi đúng lúc `t_end` dùng tham số phase kế tiếp.
- **delay distribution** — phân phối sinh **độ trễ dương** theo yêu cầu. 5 loại:
  `constant` (kênh hoàn hảo, không đọc RNG), `uniform` [low,high], `normal`
  (có sàn `clip_low`), `exponential` (đuôi không-nhớ, WAN điển hình), `heavy_tail`
  (Pareto, đuôi dài — ép partial-sync, dùng cho T47). Mọi mẫu **dương ngặt**
  (`_LATENCY_FLOOR = 1e-9`) để `t_delivered > t_sent`.
- **drop model (Bernoulli global)** — mỗi tin tung một đồng xu độc lập; xác suất
  `p_drop` thì rơi *âm thầm* (không báo người gửi). `p_drop = 1` **bị cấm** — dùng
  partition phủ toàn bộ thay thế (khai báo *ai* bị cắt trung thực hơn).
- **partition (phân mảnh)** — vị-từ tất định trên `(src, dst)`: cắt liên lạc giữa
  các *nhóm rời nhau*. Node bị phân mảnh vẫn `running` (M02: "partition không phải
  lý do halt") — chỉ *lưu lượng* bị chặn. Node không thuộc nhóm nào: tự do.
- **network-scoped RNG** — RNG *cấp hệ thống*, một cái cho cả `Network`, tách hẳn
  RNG per-node (M02). Vì mạng là thực thể chung, không thuộc validator nào. Đây là
  câu "để dành" từ M02: delay/drop thực sự rút từ `net_rng` này.
- **at-most-once, no order, no retry** — kênh giao *nhiều nhất một lần* (mất là
  mất), *không đảm bảo thứ tự*, *không gửi lại*. Điều cuối là caveat lớn của Họ B:
  `p_drop` là mất *vĩnh viễn* không truyền-lại ⇒ đường cong chịu-lỗi là *chặn
  trên* của sự mong manh ([[experiments/2026-06-13_delay-analysis]] T49).

---

## 5. Grill "trace & dự đoán"

> Cách chơi: bạn **đọc input, nói to dự đoán** (event/đầu ra kế tiếp, hoặc
> pass/fail), rồi ta **CHẠY THẬT** để chấm. Mở `<details>` chỉ *sau khi* bạn đoán.

Ta đi từng câu, dừng chờ bạn ở mỗi câu. Bắt đầu câu #1.

### Grill #1 — đường ống 5 bước, ai tiêu RNG

`_try_deliver` chạy 5 bước: (1) resolve dst, (2) drop coin, (3) partition,
(4) delay sample, (5) schedule. Xét test `test_partition_drop_consumes_no_delay_sample`:
`Partition(((0,),(1,)))`, gửi 0→1 (khác nhóm → bị partition chặn). Sau lệnh gửi,
người ta so `net_rng.getstate()` với một RNG tham chiếu đã rút **đúng 1 lần**
(`ref.random()`).

**Dự đoán:** vì sao đúng *1* lần, không phải 0, không phải 2? Bước nào đã rút,
bước nào bị bỏ qua?

<details><summary>ĐÁP ÁN</summary>

Thứ tự §6.2 là **drop coin → partition → delay**. Message 0→1:
- Bước 2 (drop coin) **luôn chạy trước** và tiêu **1** mẫu RNG
  (`net_rng.random() < p_drop`), *dù* p_drop = 0 ở test này (đồng xu vẫn được
  tung, chỉ là không bao giờ "drop").
- Bước 3 (partition) chặn → `return` sớm. Partition **không đọc RNG** (hàm tất
  định của `(src,dst,phase)`).
- Bước 4 (delay sample) **không bao giờ tới** → 0 mẫu delay.

Tổng: đúng 1 lần rút. Ý nghĩa sâu: thứ tự này *cố ý* để "một tin *lẽ ra* bị
partition" **không tiêu mẫu delay** — nhờ vậy hai cấu hình chỉ khác nhau ở
topology partition vẫn giữ *nguyên trạng thái RNG*, replay không lệch.
</details>

Chạy chấm:
```
make test-network
# hoặc riêng:
PYTHONPATH=src:tests/network python3 -m unittest test_network.TestDelivery.test_partition_drop_consumes_no_delay_sample -v
```

### Grill #2 — unicast đặt lịch ở đâu

`test_unicast_schedules_one_delivery`: phase đơn, `DelayDist("constant",{"delay":10})`,
gọi `net.submit_unicast(0, 1, "PING", {"k":1}, t_sent=5.0)`.

**Dự đoán:** sau lệnh này, heap của scheduler có mấy phần tử? Phần tử đó có
`t` = ? và `node_id` = ? (nhớ khóa heap `(t, node_id, seq)` từ M01).

<details><summary>ĐÁP ÁN</summary>

1 phần tử. `t = 5.0 + 10.0 = 15.0` (t_sent + delay). `node_id = 1` = **dst**
(Delivery gắn với node *đích*, vì nó sẽ gọi `on_message` của node 1). Payload
`Message(src=0, dst=1, type="PING", ...)`, `t_sent=5.0`.

Điểm cốt: "gửi" **không** gọi `node1.on_message` ngay — nó **đặt lịch** một
`Delivery` để scheduler pop ở `t=15`. Đó là bản chất discrete-event: mọi tương
tác đi qua heap thời-gian-ảo, không có lời gọi hàm trực tiếp giữa node.
</details>

### Grill #3 — broadcast loại ai, theo thứ tự nào

`test_broadcast_reaches_registry_minus_sender`: registry = {0,1,2}, gọi
`submit_broadcast(src=1, "ANN", None, 0.0)`.

**Dự đoán:** heap có mấy Delivery, dst là những ai? Và (khó hơn) — nếu ta đăng ký
node theo thứ tự [3,2,1,0] thay vì [0,1,2,3] với delay *ngẫu nhiên*, delivery
stream có đổi không? (xem `test_broadcast_rng_consumption_independent_of_registration_order`)

<details><summary>ĐÁP ÁN</summary>

- 2 Delivery, dst = [0, 2]. Người gửi (1) bị loại (`if dst != src`).
- Thứ tự đăng ký **không** làm đổi kết quả — vì broadcast lặp `sorted(registry)`,
  *không* theo thứ tự chèn dict. Người nhận thứ k (theo id tăng dần) luôn tiêu
  mẫu delay thứ k. Nếu ai đó lỡ viết `for dst in self.registry` (bỏ `sorted`),
  *tập* người nhận vẫn đúng (test #3 gốc vẫn pass!) nhưng ánh xạ dst→delay bị
  xáo theo thứ tự đăng ký → **replay vỡ**. Đó là lý do test dùng delay *uniform*
  (stochastic): delay `constant` không đọc RNG nên không lộ được lỗi này.
</details>

### Grill #4 — tham số phase "đông cứng" lúc submit

`test_phase_parameters_baked_at_submit_time`: pha 0 delay=100 tới t=50, pha 1
delay=1. Gửi `submit_unicast(0,1,"X",None, t_sent=49.0)` **trong pha 0**, rồi
gọi `advance_phase(1)`.

**Dự đoán:** Delivery đã đặt lịch có `t` = ? Sau `advance_phase(1)`, `t` đó có bị
tính lại theo delay=1 của pha mới không?

<details><summary>ĐÁP ÁN</summary>

`t = 49 + 100 = 149.0`. Sau `advance_phase(1)`: **vẫn 149.0** — không đổi. Đường
ống đọc `self.phases[self._phase_idx]` **tại thời điểm submit** và chốt delay ngay
vào entry heap; entry đó bất biến. Đổi phase về sau *không* hồi-tố các Delivery đã
lên lịch. (Test anh em `test_active_phase_governs_delay` pin chiều ngược: một
submit *mới* sau advance mới dùng delay của pha mới.)

Đây là mô hình đúng của mạng: một gói đã "lên đường" với độ trễ của điều kiện lúc
gửi; điều kiện đổi về sau chỉ ảnh hưởng gói gửi *sau* đó.
</details>

### Grill #5 — PhaseAdvance có đua với Delivery không

`advance_phase` docstring nói `PhaseAdvance` mang `node_id = -1`
(`Scheduler.PHASE_NODE_ID`), "sorts before every real NodeId at the same t".

**Dự đoán:** giả sử tại đúng `t = 100` (ranh giới pha) có cả một `PhaseAdvance(1)`
lẫn một `Delivery` cho node 2. Scheduler pop cái nào trước? Vì sao điều đó *phải*
đúng để half-open `[t_start, t_end)` được hiện thực đúng?

<details><summary>ĐÁP ÁN</summary>

`PhaseAdvance` pop **trước**. Khóa heap là `(t, node_id, seq)` (M01); cùng `t=100`,
so `node_id`: −1 < 2, nên PhaseAdvance thắng. Kết quả: con trỏ pha nhảy sang 1
*trước khi* bất kỳ Delivery/TimerFire nào ở `t=100` được xử lý → mọi việc tại
`t=100` "thấy" pha mới. Đúng nghĩa half-open: `t_end` cũ = `t_start` mới, và
`t=100` thuộc pha *mới*. Không có −1 sort-first, sẽ có đua: một Delivery ở t=100
có thể xử lý dưới pha cũ, phá quy ước biên.

Lưu ý tinh: đây là *tại sao* chọn −1, không phải một mẹo tùy tiện — nó ghép trực
tiếp với thiết kế tie-break của Scheduler ở M01.
</details>

Chạy chấm cả suite sau khi đoán hết:
```
make test-network
```

---

## 6. Phòng thủ (câu hội đồng dễ hỏi — trả lời mẫu, neo wiki/draft)

> Rút từ limitation/threat *có thật* trong wiki/draft. Không bịa.

**H1. "Mô hình mạng của bạn chỉ có độ trễ (latency-only). Vậy bạn bỏ qua điều gì,
và nó bóp méo kết quả ra sao?"**
Đúng, đây là caveat top-1 ([[drafts/ch6_conclusion]] §6.2; [[concepts/network-model]]).
Kênh mô hình *chỉ* trễ + mất-gói + phân mảnh; **không** có băng thông hữu hạn, hàng
đợi, hay trần dung lượng. Hệ quả trực tiếp: goodput **phẳng theo n**, không bão hòa
(F2) — vì không có nút cổ chai để bão hòa. `peak_tps` bị hoãn (cần capacity model).
Ta *khai báo* rào này, không giấu: mọi kết luận throughput là "dưới mô hình
latency-only", không phải năng lực mạng thật.

**H2. "`p_drop` là mất gói vĩnh viễn, không truyền lại (no retransmission). Mạng
thật có TCP retransmit. Kết luận chịu-lỗi của bạn còn giá trị gì?"**
Chuẩn — và ta nói thẳng nó là **chặn trên của sự mong manh** (upper bound on
fragility) ([[experiments/2026-06-13_delay-analysis]] T49). Vì không có transport
gửi lại, đường cong `finalization_rate` vs loss là *tệ nhất có thể*; một protocol
có lớp truyền lại sẽ chịu tốt hơn. Điều này *không* làm hỏng xếp hạng **tương đối**
(PBFT ≥ Snowman > FFG, RQ4) vì cả ba chịu cùng một kênh — công bằng do
common-channel. Nó chỉ chặn ta phát biểu *tuyệt đối*.

**H3. "Vì sao delay/drop rút từ một RNG mạng riêng, chứ không từ RNG của node?
Có phải chỗ này dễ sai xác định tính (determinism) không?"**
Mạng là thực thể *cấp hệ thống*, không thuộc validator nào — nên nó có `net_rng`
riêng, seed hóa từ `blake2b("network:"+seed)` ([[concepts/network-model-phases]]
§6.1 + Revisions 2026-05-19). Ban đầu spec viết `hash(("network",seed))` nhưng
`hash()` của str bị `PYTHONHASHSEED` ngẫu-nhiên-hóa theo tiến trình → phá replay
cross-process; T23 sửa sang blake2b (giống fix per-node ở node-model §8). Test
`test_network_rng_is_process_stable` chốt: hai `Network` cùng seed cho *cùng*
`getstate()`.

**H4. "Thứ tự drop-rồi-partition có gì đặc biệt? Đảo lại thì sao?"**
Thứ tự **drop coin (tiêu RNG) → partition (không RNG) → delay (tiêu RNG)** được
*ghim* (§6.2). Lý do: giữ cho một tin *lẽ ra bị partition* **không** tiêu mẫu
delay. Nhờ vậy hai cấu hình chỉ khác topology partition vẫn có *cùng* dòng RNG →
so sánh chúng là so sánh sạch (chỉ khác đúng biến ta đổi). Nếu đảo, partition sẽ
"nuốt" hoặc "chừa" mẫu delay tùy cấu hình → trạng thái RNG lệch, replay và so sánh
đều hỏng. Test `test_drop_and_partition_compose_per_sampling_order` pin điều này.

**H5. "Partition và drop nhìn từ người gửi khác nhau chỗ nào? Node có biết mình bị
cô lập không?"**
**Không** — không có phản hồi người gửi (no sender feedback). Partition-drop và
Bernoulli-drop *không phân biệt được* từ phía gửi ([[concepts/network-model-phases]]
§4). Node bị phân mảnh vẫn `running` (M02: partition không phải halt reason); nó cứ
gửi, tin cứ rơi âm thầm. Đây đúng là tinh thần bất-đồng-bộ: không ai *biết chắc*
tin mất hay chỉ trễ — nền của FLP và của thiết kế timeout/view-change.

---

## 7. Giải thích lại (Feynman) + ghi sổ

Sau khi grill, tự giải thích **không nhìn code**:

1. Kể đường đi một `PING` từ `node0.send(1,...)` → tới `node1.on_message`, gọi
   tên từng bước và nói bước nào tiêu RNG.
2. Vì sao `Network` chỉ là hạ tầng *trung thực*, ranh giới với adversary ở đâu.
3. Ba núm delay/drop/partition ánh xạ sang biến độc lập họ thí nghiệm nào.
4. Một câu: vì sao đổi phase *sau khi* gửi không hồi-tố Delivery đã lên lịch.

Nếu chỗ nào ú ớ → quay lại §4/§5 chỗ đó.

**Ghi sổ** (mình sẽ cập nhật `progress.md` ở cuối buổi): điểm grill 1–5, đã thông
gì, còn mờ gì. Câu mang sang dự kiến cho Module 04 (`event_log`): *Delivery/
metric event sau khi scheduler pop được ghi ra CSV thế nào — `event_sink` (đã
thấy ở test e2e `sched.event_sink = lambda ...`) nối vào đâu?*
