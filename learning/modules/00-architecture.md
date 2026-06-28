# Module 00 — Định hướng theo spine luận văn (claims-first)

> **Không đọc code buổi này.** Mục tiêu: nạp *bản đồ luận điểm* trước, để mọi buổi
> sau bạn luôn biết mình đang đọc engine để **bảo vệ điều gì**. ~30–40 phút.

## 0. Vì sao có buổi này

Lộ trình đọc code đi bottom-up, nhưng *neo theo luận điểm* (Câu 1 buổi grill). Nếu
nhảy thẳng vào `scheduler` mà chưa biết RQ4 là gì, bạn sẽ đọc như đọc thư viện
ngẫu nhiên. Buổi này dựng cái "đỉnh" để các buổi sau ngước nhìn.

## 1. Đọc gì, theo thứ tự

1. `wiki/concepts/problem-statement.md` — tên đề tài, 3 khoảng trống tạo động lực, 4 mục tiêu, phạm vi (in/out), giả định.
2. `wiki/concepts/research-questions.md` — **RQ1–RQ5**, metric chính + biến độc lập mỗi câu.
3. `wiki/concepts/key-findings.md` — **10 phát hiện F1–F10** + bản đồ RQ→finding. *Đây là trái tim — đọc kỹ nhất.*
4. `wiki/concepts/system-design.md` (+ `system-design-protocols.md`) — 5 tầng hợp thành hệ chạy; "một cell + seed → một dòng CSV".
5. `wiki/diagrams/runtime/macro.md` — 6 phase: init → workload → run loop → stop → flush → output.
6. Lướt `drafts/ch4_results.md` §4.1 + `drafts/ch5_synthesis.md` §5.1, §5.3 — để thấy kết quả tổng **"không họ nào thắng tất"**.

## 2. Mục tiêu khi đọc (trả lời được là đạt)

- RQ1–RQ5 mỗi câu hỏi *gì*, đo bằng *metric nào*?
- Kể được ít nhất 4 phát hiện headline (gợi ý: F1 chi phí truyền tin hai chế độ, F2 latency phẳng theo `n`, F3 Snowman phơi nhiễm trễ, F4 thứ hạng kháng-mất-gói PBFT ≥ Snowman > FFG).
- "Một dòng CSV" ứng với cái gì?
- 5 tầng code là gì, tầng nào chống lưng RQ nào (bảng dưới)?
- "No family dominates" nghĩa là gì, cho **một** ví dụ đảo ngược (inversion)?

## 3. Bản đồ neo: tầng code → RQ/phát hiện (cái "đỉnh" để ngước nhìn)

| Tầng code | Chống lưng chủ yếu cho |
|-----------|------------------------|
| `scheduler` + `nodes` + `network` + `event_log` (lõi) | *Tính tái lập & hợp lệ* — nền của MỌI con số. Đếm message → RQ3. |
| `pbft` / `pos` / `snowman` (giao thức) | Bản thân *đối tượng so sánh* — mọi RQ. |
| `workload` + `common` (chạy/sweep) | RQ2 (throughput), và tính tái lập của cả chiến dịch. |
| `delay` (Họ B) | RQ1 (trễ→finality), RQ4 (kháng mất gói). |
| `adversary` (Họ C) | RQ4 (kháng tấn công: delay-emission / offline / equivocate). |
| `output` (phân tích) | Nơi *mọi tuyên bố Chương 4–5* ra đời; RQ5 (Pareto, no-dominance). |

> Bản đồ RQ→finding *chính xác* nằm trong `key-findings.md` — bảng trên chỉ để định
> hướng, đừng học thuộc thay cho trang đó.

## 4. Khái niệm gloss (gặp lần đầu)

- **L1 (Layer-1)** — blockchain nền (tự lo đồng thuận), đối lập Layer-2 chạy *trên* nó.
- **partial synchrony** (đồng bộ một phần) — mạng async một thời gian rồi mới ổn định sau mốc GST; PBFT/FFG giả định cái này.
- **ACU** (denominator chuẩn hóa) — "đơn vị đồng thuận" để so chi phí giữa các họ trên cùng mẫu số; xem `evaluation-metrics.md`.
- **Pareto frontier** — tập các lựa chọn "không cái nào bị cái khác trội hơn ở MỌI tiêu chí"; RQ5 xoay quanh nó.

## 5. Grill — nhớ spine (cuối buổi, tôi hỏi miệng)

1. RQ4 hỏi gì? Phát hiện headline của nó?
2. Một dòng trong `results/baseline/baseline.csv` ứng với gì?
3. Đi từ YAML tới một dòng CSV qua mấy phase? Kể tên theo thứ tự.
4. "No family dominates" — cho một cặp đảo ngược cụ thể.

<details><summary>ĐÁP ÁN (tự trả lời trước rồi mở)</summary>

1. RQ4 = *kháng chịu dưới lỗi/tấn công* (trễ, mất gói, adversary). Headline F4: thứ
   hạng kháng-mất-gói **PBFT ≥ Snowman > Casper FFG**, nhưng ở `n=25` PBFT/Snowman
   *hòa* (CI chồng nhau) — một crossover thật: Snowman tốt nhất khi mất gói nhẹ,
   PBFT là cái duy nhất còn sống ở 20%.
2. Một **(kịch bản, seed)**: baseline.csv = 15 kịch bản × 20 seed = 300 dòng. Một
   dòng là một lượt chạy của một giao thức ở một `n` với một seed.
3. init → workload → run loop → stop → flush → output (6 phase, `diagrams/runtime/macro`).
4. Ví dụ: PBFT *nhanh & sống* nhưng fork *không quy trách được* (unaccountable);
   Casper FFG *rẻ nhất về overhead* + lỗi *quy trách được* (slashing) nhưng mong
   manh nhất dưới mất gói; Snowman *an toàn nhất dưới equivocation* nhưng *đắt nhất
   dưới trễ*. Mỗi cái là một góc — không cái nào trội mọi trục.
</details>

## 6. Phòng thủ (câu hội đồng dễ hỏi ở mức tổng)

- **"Sao mô phỏng mà không đo testnet thật?"** → để *kiểm soát + tái lập + so sánh
  táo-với-táo* xuyên họ; đánh đổi: external validity thấp hơn. Neo: `ch1` phạm
  vi/giả định, `ch6` limitations (mô hình chỉ-trễ), nguồn [16]/[17] (tiền lệ
  đánh giá BFT bằng mô phỏng).
- **"Sao chỉ 3 giao thức, không có DAG/Narwhal?"** → 3 cái đại diện 3 góc thiết kế
  (BFT tất định / finality-gadget PoS / subsampling xác suất); Narwhal+Tusk *hoãn
  sang further-work*. Neo: `concepts/consensus-families`, `concepts/week7-decision`,
  `ch6 §6.3`.
- **"Đóng góp chính là gì?"** → một *harness hợp nhất* cho phép so sánh táo-với-táo
  + các phát hiện *no-dominance* và *kháng-chịu-đổi-bằng-latency*. Neo:
  `problem-statement`, `key-findings`.

## 7. Ghi sổ

Cập nhật `progress.md` dòng `00 · architecture`: điểm tự đánh giá, spine nào còn mờ.
Mang theo sang buổi 01 câu hỏi: *"tính tái lập (byte-identical replay) thực ra được
gì bảo chứng?"* — module `scheduler` trả lời.
