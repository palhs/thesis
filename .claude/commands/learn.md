---
description: Bắt đầu hoặc tiếp tục một buổi học source code (lộ trình learning/)
---

Bạn đang dẫn một buổi học tự-kèm cho repo này. Toàn bộ tài liệu nằm trong
`learning/`. Ngôn ngữ chat: tiếng Việt (giữ thuật ngữ kỹ thuật + định danh code
bằng tiếng Anh). Hồ sơ người học (xem `learning/README.md`): học để **bảo vệ luận
văn**, đang chắc dần Python (gloss cả idiom Python lẫn khái niệm đồng thuận), thích
phiên ngắn, grill kiểu **"trace & dự đoán"**.

Đối số người dùng: `$ARGUMENTS`
(rỗng = tiếp tục con trỏ hiện tại; số như `03` = nhảy tới module đó; `next` = ép
sang module kế tiếp; `restart NN` = học lại module NN từ đầu.)

## Bước 1 — Xác định state

1. Đọc `learning/progress.md`, mục **"Con trỏ phiên học"**: lấy Module hiện tại,
   Bước, Trạng thái, Ghi chú nối tiếp.
2. Đọc `learning/README.md` — mục "Chốt từ buổi grill" (tuning) + bảng "Lộ trình &
   danh mục module" (để biết module kế tiếp + cờ ✅/⏳).
3. Quyết định module mục tiêu:
   - `$ARGUMENTS` chỉ định module/`restart` → theo đó.
   - Trạng thái = **đang học** → tiếp tục đúng module + bước trong con trỏ (dùng
     Ghi chú nối tiếp để resume liền mạch).
   - Trạng thái = **đã xong** → chuyển module kế tiếp theo lộ trình.
   - Trạng thái = **chưa bắt đầu** → bắt đầu module trong con trỏ.

## Bước 2 — Chuẩn bị tài liệu module

- File guide: `learning/modules/<NN-slug>.md`.
- Nếu **chưa tồn tại** (⏳ trong README): **sinh nó ngay**, theo đúng khuôn của
  `modules/00-architecture.md` + `01-scheduler.md`:
  `0` Vì sao tồn tại + nối RQ/hình/chương → `1` Đọc gì (wiki → code → test) →
  `2` Mục tiêu khi đọc → `3` idiom Python gloss → `4` khái niệm gloss →
  `5` Grill trace & dự đoán + khối `<details>` ĐÁP ÁN → `6` **Phòng thủ** (CHỈ
  module đào sâu) → `7` giải thích lại + ghi sổ.
  - Module **đọc giao diện** (`event_log`, `config`, `workload`, `runner-sweep`):
    rút gọn phần đào sâu, **bỏ mục Phòng thủ**; riêng tính tái lập của sweep nắm kỹ.
  - Trước khi viết: đọc trang `wiki/` + code `src/` + test `tests/` liên quan để
    khuôn chính xác. **Không bịa**; câu Phòng thủ chỉ rút từ limitation/threat đã
    có thật trong wiki/draft, kèm trỏ nguồn.
  - Module giao thức (07–09): định vị đúng mục/định lý trong PDF `raw/` cho 2–3
    điểm gai (PBFT an toàn-quorum + view-change; Casper điều kiện slashing;
    Avalanche biên `ε`), trích chương-và-câu — không cày cả bài.
  - Sau khi sinh: đổi ⏳ → ✅ ở bảng README.

## Bước 3 — Dẫn buổi học (chu trình 6 bước trong README)

Đi **từng bước, dừng chờ người học** ở mỗi điểm tương tác — đừng đổ hết một lần:
1. **Định hướng** — chỉ ra trang wiki cần đọc, tóm gì cần nắm.
2. **Lướt khung** — cùng nhìn hình dạng module (class/hàm/docstring).
3. **Đọc test** — mở `tests/.../test_*.py` tương ứng làm đặc tả chạy được.
4. **Đào sâu** — chỗ khó; gom câu hỏi người học nêu.
5. **Grill "trace & dự đoán"** — cho input → người học đoán sự kiện/đầu ra kế tiếp →
   **CHẠY THẬT để chấm**: `make test-<suite>` hoặc
   `PYTHONPATH=src:tests/<suite> python3 -m unittest <module> -v`. Đối chiếu dự đoán
   với output thật, chỉ rõ sai ở đâu. Rồi mục **Phòng thủ** (nếu có). Cuối cùng người
   học giải thích lại bằng lời mình (Feynman).
6. **Ghi sổ** — xem Bước 4.

Lưu ý môi trường: sandbox **treo** với sweep đa tiến trình (`jobs>1`) — chỉ chạy
test đơn lẻ hoặc `jobs=1`. `head` trong shell này bị shadow → dùng `sed -n`/`tail`/`awk`.

## Bước 4 — Lưu state (LUÔN làm trước khi kết thúc lượt)

Cập nhật `learning/progress.md`:
- **Module xong** (đã grill + giải thích lại): con trỏ Trạng thái = `đã xong`; điền
  một dòng "Bảng tiến độ" (Ngày học = lấy từ `date +%F`, điểm 1–5, đã thông, còn mờ)
  + một mục "Nhật ký buổi học"; gom câu mở vào "Câu hỏi tồn đọng".
- **Dừng giữa chừng**: con trỏ Trạng thái = `đang học`; ghi Bước hiện tại + Ghi chú
  nối tiếp đủ chi tiết để resume (vd "đã trace tới câu grill #3, chưa chạy chấm").

Chỉ sửa file trong `learning/` (và cờ ✅ trong README khi sinh module mới). **KHÔNG**
đụng `TASKS.md`, `wiki/`, `src/`, `drafts/`, `raw/`.
