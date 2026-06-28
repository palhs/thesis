---
description: Bảng tiến độ lộ trình học source code (learning/) — đang ở đâu, còn gì
---

Read-only. **Không sửa file nào.** In một dashboard gọn về tiến độ học.

## Bước 1 — Thu thập state

- `learning/progress.md`: mục "Con trỏ phiên học" (module hiện tại, bước, trạng
  thái, buổi gần nhất) + "Bảng tiến độ" + "Câu hỏi tồn đọng".
- `learning/README.md`: bảng "Lộ trình & danh mục module" — module nào ✅ (đã có
  guide) / ⏳ (chưa).
- Liệt kê `learning/modules/` để biết file guide nào đã sinh trên đĩa.
- `raw/`: có đủ 3 PDF cho module 07+ chưa (PBFT = `castro-practicalbft.pdf`,
  Casper = `casper.pdf`, Avalanche = `avalanche.pdf`).

## Bước 2 — In báo cáo (markdown, đúng khung này)

```
## Đang ở
- Module: <NN · tên> — <trạng thái>  (bước <x> nếu đang học)
- Buổi gần nhất: <ngày, hoặc — >

## Lộ trình (✅ xong · ▶ đang học · – chưa)
| Module | Guide | Học | Điểm | Còn mờ |
|--------|-------|-----|------|--------|
| 00 architecture | ✅/⏳ | ✅/▶/– | <điểm/–> | <tóm tắt/–> |
| ... (tới 14) | | | | |

## Tiến độ
<X/14 module đã xong; gợi ý module kế tiếp>

## Papers (cần từ module 07)
- PBFT / Casper / Avalanche: <đủ / thiếu cái nào>

## Câu hỏi tồn đọng
- <gạch đầu dòng, hoặc "không có">

## Kế tiếp
- Chạy `/learn` để tiếp tục <module kế tiếp>.
```

Suy ra cột "Học": ✅ nếu dòng bảng tiến độ có điểm; ▶ nếu là module con trỏ đang ở
trạng thái "đang học"; `–` nếu trống. Chỉ quan sát — không flip trạng thái, không sửa gì.
