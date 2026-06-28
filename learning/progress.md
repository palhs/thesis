# Sổ theo dõi tiến độ

> Cập nhật ở bước 6 mỗi buổi. Điểm tự đánh giá 1–5 (1 = chưa thông, 5 = giải
> thích trôi chảy + trace được không cần nhìn code).

## Con trỏ phiên học (state — `/learn` đọc & ghi vào đây)

- **Module hiện tại:** 01 · scheduler
- **Bước trong module:** 1 (định hướng)
- **Trạng thái:** chưa bắt đầu <!-- chưa bắt đầu | đang học | đã xong -->
- **Buổi gần nhất:** 2026-06-29 (Module 00 · architecture — đã xong)
- **Ghi chú nối tiếp:** Mở Module 01. Mang theo câu từ buổi 00: "tính tái lập (byte-identical replay, CV=0 ở mọi metric cấu trúc) thực ra được gì bảo chứng?" — scheduler trả lời.

## Bảng tiến độ

| Module | Ngày học | Điểm grill (1–5) | Đã thông | Còn mờ / câu hỏi mở |
|--------|----------|------------------|----------|---------------------|
| 00 · architecture | 2026-06-29 | 4 | Spine RQ1–5; tps(decided/window, misnomer)≠goodput(committed_tx/window); 3-family map + 3 sợi chỉ cơ chế (leader+view-change / slashing-accountable / subsampling); B(network)≠C(adversary); BLS gộp chữ ký O(n)→O(1) bytes | Con số từng F (để re-read sau Module 09); α_c/β chính xác của Snowman; cơ chế tps∝n đọc thẳng summarise.py |
| 01 · scheduler | | | | |
| 02 · nodes | | | | |
| 03 · network | | | | |
| 04 · event-log | | | | |
| 05 · config | | | | |
| 06 · trace end-to-end | | | | |
| 07 · pbft | | | | |
| 08 · casper-ffg | | | | |
| 09 · snowman | | | | |
| 10 · runner-sweep | | | | |
| 11 · delay (Họ B) | | | | |
| 12 · adversary (Họ C) | | | | |
| 13 · output-analysis | | | | |
| 14 · mock-defense | | | | |

## Nhật ký buổi học

<!-- Mỗi buổi 1 mục. Ví dụ:
### [2026-06-25] Module 01 · scheduler
- Thông: vòng lặp run(), thứ tự 3 điều kiện dừng, lazy-tombstone.
- Mờ: vì sao seq per-node đủ để không bao giờ so sánh tới phần tử event.
- Theo dõi tiếp: xem lại khi học set_timer trong nodes.
-->

### [2026-06-29] Module 00 · architecture
- Thông: spine luận văn (RQ1–RQ5 + 10 finding); "YAML+seed → 1 dòng CSV";
  5 tầng code; throughput/goodput (tự bắt được tps là misnomer, mở
  `src/pbft/summarise.py:67` xác nhận `tps=len(decided)/result.now` đếm
  per-node ⇒ ∝n); 3 sợi chỉ cơ chế của 3 họ; B(network, vô ý) vs C(adversary,
  có chủ đích, nhắm φ-fraction); BLS aggregation.
- Cách học: tự đọc + tóm từng họ (A,B tự tóm; C mình walk-through). Active
  recall tốt — bắt được nhiều term lệch (tps name, window/block ≠ latency).
- Mờ: con số cụ thể từng F (kế hoạch: đọc-lại key-findings SAU Module 09).
- Phòng thủ đã luyện: tps-misnomer; B≠C (network vs adversary, kèm ví dụ
  Snowman loss-ok nhưng offline-chết); caveat = rào chắn phạm vi.

## Câu hỏi tồn đọng (gom để hỏi cả cụm)

- Cơ chế *chính xác* khiến `tps ∝ n` (mỗi instance phát ~n record "decided"):
  đọc thẳng `src/pbft/summarise.py` để xác nhận — Module 07/13.
- α_c (alpha) và β của Snowman: ngưỡng/số vòng poll chính xác — Module 09.
- Đọc-lại `wiki/concepts/key-findings.md` SAU Module 09 để các con số F1–F10
  "click" ngược (đã hiểu cốt, chưa thuộc số).
