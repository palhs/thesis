# Script nói — bảo vệ khóa luận (15 phút)

Deck: `slides/thesis-defense.html` · 12 slide · lõi **14:00** + ~1:30 beat phụ.
Bản này là script để HỌC THUỘC theo cấu trúc xương neo. Q&A prep làm buổi
riêng, lưu file khác — không nằm ở đây.

## Cách dùng

- **NEO** (trích trong ngoặc kép) = học thuộc **nguyên văn**. Mỗi slide có
  neo mở và neo chuyển — đó là chỗ dễ bí nhất; phần giữa nói tự do theo beat.
- **Beat** (gạch đầu dòng) = ý nói tự do, 5–10 từ gợi ý, đúng register nói:
  khung tiếng Việt, thuật ngữ tiếng Anh giữ nguyên khớp chữ trên slide.
  **Mọi con số in đậm — nói đúng tuyệt đối, không xê dịch.**
- `▶` = **một lần bấm Space**. Deck đã sửa sang chế độ bước: mỗi Space bung
  đúng một beat; hết bước thì Space tự chuyển chip/tab kế tiếp, hết chip/tab
  thì sang slide. **Toàn bộ bài chỉ dùng một phím.** Chuột chỉ cần khi Q&A
  muốn nhảy tự do giữa các chip/tab.
  - Space / → / PageDown = bước tiếp · Shift+Space / ← / PageUp = lùi bước
  - ↓ / ↑ = nhảy nguyên slide (dùng khi Q&A)
- `(cắt được)` = beat phụ. **Quy tắc cắt duy nhất: vào S8 muộn hơn 8:00 →
  bỏ toàn bộ beat (cắt được) từ đó về sau.** Không có quyết định nào khác.
- Đồng hồ ghi ở đầu mỗi slide: `vào · nói · rời`. Liếc một lần lúc chuyển slide.

---

## S1 · Title — vào 0:00 · nói 0:30 · rời 0:30

*(slide tự chạy hết animation, không cần Space giữa chừng)*

**NEO MỞ:**
> "Kính thưa hội đồng, em là Lê Ngọc Phan Anh, mã sinh viên BI12-010. Đề tài
> của em là *Performance–Security Evaluation of Layer-1 Consensus under Delay
> and Adversarial Conditions* — một nghiên cứu so sánh bằng mô phỏng, thực
> hiện dưới sự hướng dẫn của Tiến sĩ Giang Anh Tuấn."

- ba protocol — **PBFT** (vàng) · **Casper FFG** (tím) · **Snowman** (xanh) —
  ba màu này theo suốt mọi slide

**NEO CHUYỂN:**
> "Em xin bắt đầu bằng lý do đề tài này tồn tại."

`▶ → S2`

---

## S2 · Proven safe. Still halting. — vào 0:30 · nói 1:30 · rời 2:00

**NEO MỞ:**
> "Các giao thức đồng thuận Layer-1 đều có chứng minh an toàn — proven safe.
> Nhưng đây là bốn năm vận hành thực tế."

- `▶` Solana — halt toàn mạng **17 giờ, 09/2021** — rồi lặp lại
  **04/2022 · 02/2023 · 02/2024**
- `▶` Ethereum — reorg **7 block, 05/2022** · stall finality nhiều epoch
  **05/2023**
- `▶` Cosmos Hub halt **06/2024** · Sui validator crash-loop **11/2024**
- `▶` (khung chữ) — các proof KHÔNG sai; cái bị phá là **điều kiện** của
  proof: bounded delay, đủ honest validator — bị vượt thường xuyên khi
  deploy; mạng thật trộn nhiều disturbance cùng lúc → không cô lập được
  điều kiện nào gây sự cố nào

`▶` (câu hỏi lớn hiện) — **NEO CHUYỂN:**
> "Vậy: điều kiện nào phá protocol nào? Muốn trả lời cần một harness duy
> nhất, stress cả ba family theo đúng một cách. Đó là việc khóa luận này làm."

`▶ → S3`

---

## S3 · Ba thước đo không đặt cạnh nhau được — vào 2:00 · nói 0:45 · rời 2:45

**NEO MỞ:**
> "Chưa ai trả lời được câu đó, vì hôm nay ba family được đo bằng ba thước
> khác nhau."

- `▶` PBFT-style báo **throughput** — ops/s trên LAN latency thấp — không
  nói gì về finality delay
- `▶` PoS finality báo **finality delay** — **~12 phút, 2 epoch** — không
  nói gì về throughput
- `▶` Avalanche-style báo **xác suất an toàn ε** — tại MỘT bộ (K, β) cố
  định — đổi tham số là số đổi
- `▶` (punchline) — số đo rất nhiều nhưng thiết kế để không bao giờ so được;
  survey chỉ xếp số của người khác cạnh nhau; matched-harness duy nhất
  trước đây — **Gervais et al.** — chỉ cho Proof-of-Work

**NEO CHUYỂN:**
> "Không tồn tại bức tranh chung — nên em xây một cái."

`▶ → S4`

---

## S4 · The goal — 5 câu hỏi — vào 2:45 · nói 0:45 · rời 3:30

**NEO MỞ:**
> "Mục tiêu gói trong một dòng: một simulator, ba protocol, cùng một bộ
> giả định."

- `▶` **WHEN** — mạng chậm thì finality chậm bao nhiêu → RQ1
- `▶` **WHAT** — throughput ra sao khi tỉ lệ Byzantine tăng → RQ2
- `▶` **HOW MUCH** — mỗi đơn vị commit tốn bao nhiêu message → RQ3
- `▶` **WHO** — adversary nào phá protocol nào, ở property nào → RQ4
- `▶` **WHICH** — có protocol nào thắng toàn diện không → RQ5

**NEO CHUYỂN:**
> "Trước khi đo, cần thấy ba protocol này vận hành khác nhau đến mức nào."

`▶ → S5`

---

## S5 · Ba family, ba protocol — vào 3:30 · nói 2:00 · rời 5:30

*(mở vào diagram PBFT: 4 node đã hiện sẵn)*

**NEO MỞ:**
> "Mỗi family em chọn một đại diện. Thứ nhất — PBFT, family cổ điển
> leader-driven."

**PBFT** — n=4, node 3 offline (f=1):
- `▶` client gửi request cho **primary** → primary broadcast **PRE-PREPARE**
- `▶` **PREPARE all-to-all** — mọi node gửi mọi node → đây là nguồn chi phí
  **O(n²)**
- `▶` **COMMIT all-to-all** — vòng hai, y hệt
- `▶` decided khi mỗi pha đủ quorum **2f+1** — tức **3 trên 4** node khớp
  phiếu, dù 1 node chết; finality **deterministic** — đã chốt là vĩnh viễn

`▶` (deck tự chuyển chip **Casper FFG**):
> "Thứ hai — Casper FFG, lớp finality của Ethereum."
- `▶` validator (theo **stake**) gửi attestation tích lũy trên link giữa hai
  checkpoint; đủ **⅔ stake**...
- `▶` ...checkpoint **justified**
- `▶` con justified ⇒ cha **finalized** — chốt hai bước
- `▶` checkpoint mới nhất luôn pending — finality đi **sau** chain tip;
  chi phí chỉ **~1.15n** message; **slashing** → vi phạm an toàn quy được
  trách nhiệm

`▶` (deck tự chuyển chip **Snowman**):
> "Thứ ba — Snowman của Avalanche. Không có leader nào cả."
- `▶` mỗi round: poll **K peer ngẫu nhiên**; nếu ≥ **α_c** trả lời trùng →
  confidence counter **1/15**
- `▶` round sau — sample MỚI hoàn toàn → **2/15**
- `▶` đổi preference giữa chừng → counter **reset về 0** — đây là chỗ trả giá
- `▶` đủ **β = 15** round liên tiếp → **ACCEPTED**; finality **xác suất**:
  ε ≤ (1−α_c/K)^β; chi phí mỗi validator **không phụ thuộc n**

**NEO CHUYỂN:**
> "Ba cơ chế khác nhau đến mức số đo gốc của chúng không so sánh được. Muốn
> so công bằng thì mọi thứ xung quanh protocol phải giống hệt nhau — đó là
> vai trò của harness."

`▶ → S6`

---

## S6 · One harness — vào 5:30 · nói 1:15 · rời 6:45

*(mở vào: hộp config đã hiện)*

**NEO MỞ:**
> "Toàn bộ thí nghiệm chạy qua đúng một pipeline."

- (đang hiện) config gồm 5 thứ: protocol · n · timeline · adversary · seed
- `▶` hạ tầng **cố định**: scheduler chạy virtual time — deterministic ·
  network delay/loss cấu hình được · logger
- `▶` đúng MỘT chỗ swap được: **protocol slot**
- `▶` mỗi run → **một dòng kết quả**, kèm **commit_hash + seed** → tái lập
  được từng dòng
- `▶` lặp **×20 seed** mỗi cell, cho mọi run family
- `▶` hạ tầng giống hệt ⇒ khác biệt đầu ra **quy được cho protocol**
- `▶` mẫu số chung — **ACU, atomic commit unit**: 1 block PBFT ≡ 1 checkpoint
  FFG finalized ≡ 1 block Snowman accepted — mọi chi phí, mọi latency đo
  trên cùng đơn vị này

**NEO CHUYỂN:**
> "Trên harness đó, em thiết kế ba họ thí nghiệm — mỗi họ quét đúng một trục."

`▶ → S7`

---

## S7 · Ba run family — vào 6:45 · nói 0:45 · rời 7:30

**NEO MỞ:**
> "Ba run family — mỗi family quét một trục, các trục còn lại ghim cố định."

**A — Scaling** (đang mở):
- `▶` quét **n = 4 → 25**
- `▶` ghim: mạng sạch, toàn honest
- `▶` → trả lời **RQ3**

`▶` (chuyển chip **B — Delay**):
- `▶` quét timeline: baseline → uniform **100–500 ms** → heavy-tail **1–5 s**,
  thêm loss **5/10/20%**
- `▶` ghim: n ∈ {10, 25}, toàn honest
- `▶` → **RQ1**

`▶` (chuyển chip **C — Adversarial**):
- `▶` quét tỉ lệ adversary **φ = 0 → 0.30** (equivocation thêm **0.40/0.50**)
- `▶` ba hành vi: delayed-voting · silent · equivocation
- `▶` → **RQ2 · RQ4**
- (footer, đọc nhanh) mọi cell chung: Poisson **100 tx/s** · tx **512 byte** ·
  **20 seed**/cell (**30** ở các điểm sát ngưỡng của family C) · common random
  numbers → so sánh theo cặp

**NEO CHUYỂN:**
> "Đó là cách đo. Giờ đến phần chính — kết quả."

`▶ → S8`

---

## S8 · Results — 4 tab — vào 7:30 · nói 4:00 (+1:30 phụ) · rời 11:30

**⏱ ĐIỂM QUYẾT ĐỊNH DUY NHẤT: nhìn đồng hồ khi vào slide này. Muộn hơn
8:00 → bỏ mọi beat `(cắt được)` từ đây về sau.**

**NEO MỞ:**
> "Kết quả nằm trong bốn tab, theo đúng thứ tự ba run family."

**Tab A — Scaling (RQ3)** (đang mở):
- `▶` message trên mỗi ACU, **n = 25**, trục log: Casper FFG **≈29** ·
  PBFT **≈50** · Snowman **≈601**
- `▶` trend đo được khớp lý thuyết **1.15n · 2n · 2Kβ** — khoảng cách **một
  bậc độ lớn** là giá của subsampling
- `▶` (cắt được) latency phẳng theo n — PBFT & Snowman **≈1 s**, FFG **≈5 s**
  vì finality theo granularity epoch

`▶` (chuyển tab **B — Delay, RQ1**):
- `▶` slowdown so với baseline zero-delay: FFG **×1.3** · PBFT **×1.9** —
  round-bounded, trơ với hình dạng tail
- `▶` Snowman **×12–15** — mỗi round đợi peer CHẬM NHẤT trong K peer sample
- `▶` (cắt được) tail đánh vào mọi round: exponential-tail **15.3 s** vs
  uniform **12.6 s** ở n=10

`▶` (chuyển tab **B — Loss**):
- `▶` ba đường finalization rate theo loss **0 → 20%**
- `▶` ranking **PBFT > Snowman > FFG** — PBFT duy nhất còn finalize ở
  **20%** nhờ recovery path (**view-change** xoay leader); Snowman
  plateau-rồi-cliff ở **10%** (dư thừa trong round, không recovery giữa
  round); FFG sập ngay bậc **5%** (không có cả hai)
- `▶` không protocol nào fork — loss ăn **liveness**, không ăn **safety**;
  (cắt được) kẻ sống trả giá **×2–3.5** latency

`▶` (chuyển tab **C — Adversarial, RQ2+RQ4** — ma trận 3×3):
- `▶` **delayed voting**: PBFT immune, success **1.0** · FFG tụt
  **0.60–0.65** — proposer xoay vòng bị stall · Snowman sống nhưng bò —
  **×62 / ×49** chậm hơn
- `▶` **silent**: PBFT sạch tới **φ = 0.33**, cliff quorum ở **0.40** ·
  FFG decay dần tới **0.33** · Snowman đói sớm nhất — survival depth
  **φ\* = 0.10 / 0.20**
- `▶` **equivocation** (quá ⅓): PBFT **fork** deterministic ở **0.40** —
  KHÔNG quy được trách nhiệm · FFG không fork — **≥⅓ stake slashable**,
  accountable · Snowman không có fork surface — bound **ε ≈ 5×10⁻¹⁵ /
  3×10⁻¹¹**
- `▶` (legend hiện — chỉ vào màu) xanh giữ vững · vàng suy giảm · đỏ vỡ

**NEO CHUYỂN:**
> "Bốn tab — không protocol nào thắng cả bốn. Đó chính là câu trả lời RQ5."

`▶ → S9`

---

## S9 · RQ5 — không ai dominate — vào 11:30 · nói 1:00 · rời 12:30

- `▶` radar **8 trục** từ bảng 5.1 — xếp hạng ordinal, chỉ minh họa; bảng
  trong báo cáo mới là bằng chứng

`▶` — **NEO Ý LÕI (thuộc nguyên văn):**
> "Phát hiện trung tâm: cùng MỘT lựa chọn thiết kế sinh ra cả điểm mạnh lẫn
> điểm yếu của mỗi protocol."

- `▶` **Snowman** — K-peer subsampling: sống khỏe khi peer CHẬM, nhưng chết
  đói khi peer IM LẶNG — sample không tìm ra ai để hỏi
- `▶` **PBFT** — leader-quorum commit: vượt delay, loss, silence — nhưng
  quá ngưỡng equivocation thì fork không quy được trách nhiệm
- `▶` **Casper FFG** — finality theo nhịp epoch: rẻ nhất, ít nhạy delay
  nhất — nhưng sập đầu tiên dưới loss; bù lại DUY NHẤT có accountable safety

**NEO CHUYỂN:**
> "Không có người thắng — vậy dùng kết quả này thế nào? Như một bản đồ chọn."

`▶ → S10`

---

## S10 · Selection map — vào 12:30 · nói 0:40 · rời 13:10

- `▶` mối đe dọa chính là cần **quy trách nhiệm** → **Casper FFG** — slashing
  làm vi phạm an toàn có giá ≥⅓ stake
- `▶` cần **sống qua nhiễu mạng** → **PBFT** — duy nhất có recovery path
- `▶` cần **chống equivocation** → **Snowman** — không có fork surface để tấn công
- `▶` (callback) mỗi sự cố ở slide mở đầu chính là một protocol chạm
  **structural limit** của nó
- `▶` đóng góp: simulator · **3** implementation · dataset + analysis ·
  methodology — mở rộng Gervais et al. từ PoW sang các family BFT

**NEO CHUYỂN:**
> "Kết quả này đúng trong phạm vi nào — em xin nói rõ giới hạn."

`▶ → S11`

---

## S11 · Limitations & future work — vào 13:10 · nói 0:50 · rời 14:00

- `▶` **giới hạn**: cài đặt rút gọn, một đại diện mỗi family — kết luận về
  CÁC protocol này, không phải family trừu tượng · **n ≤ 25**, xa hơn là
  lập luận sensitivity · Snowman safety là analytical bound, chưa witness
  thực nghiệm · adversary chừa leader view-0 · chưa mô hình compute/bandwidth
- `▶` **hướng tiếp**: threshold signature kiểu BLS/HotStuff · mô hình
  saturation-throughput · adaptive timeout trong regime stress timeout ·
  witness thực nghiệm cho ε · mở rộng harness sang DAG family (Narwhal+Tusk)

`▶` — **NEO KẾT (thuộc nguyên văn):**
> "Đóng góp của khóa luận là một mechanism map của mặt trận
> performance–security — không phải việc gọi tên một người thắng duy nhất."

`▶ → S12`

---

## S12 · Cảm ơn — 14:00

**NEO:**
> "Em xin cảm ơn hội đồng đã lắng nghe. Em sẵn sàng nhận câu hỏi ạ."

*(Q&A: dùng ↓/↑ nhảy slide, chuột click chip/tab để mở đúng diagram/kết quả
đang được hỏi.)*

---

## Ghi chú tập luyện

- Thuộc trước: 2 neo/slide (~24 câu) + 2 neo đặc biệt (ý lõi S9, neo kết S11).
- Tập với deck mở: mỗi beat = một Space — thứ tự bấm chính là mục lục bài nói.
- Cheat sheet in tay: TRÍCH SAU khi tập xong vòng đầu — chỉ gồm những chỗ
  hay quên, không trích trước.
