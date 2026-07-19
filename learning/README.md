# learning — lộ trình đọc hiểu source code simulator

> Sổ tay học `src/` của thesis này, may đo cho một người: biết đọc code, đang
> chắc dần Python, học để **bảo vệ luận văn**, thích phiên ngắn và thích bị
> "quay" kiểu *trace & dự đoán*. Đây là tài liệu cá nhân — không phải wiki, không
> port sang LaTeX, không nằm trong vòng review của TASKS.md.

## Hồ sơ người học (để các buổi sau nhớ cách may đo)

| Trục | Lựa chọn | Hệ quả lên tài liệu |
|------|----------|---------------------|
| Mục tiêu | Bảo vệ luận văn | Mỗi module mở đầu bằng *tại sao tồn tại + đánh đổi + nối RQ/chương*. Nhẹ phần đọc từng dòng plumbing. |
| Nền tảng | Đang chắc dần Python | Gloss cả idiom Python (dataclass, lambda-binding, heapq, `typing.Protocol`) lẫn khái niệm đồng thuận. |
| Nhịp độ | Phiên ngắn, nhiều buổi | 1 module / buổi, ~30–45 phút. Module guide sinh *đúng lúc* (just-in-time), không viết sẵn hết. |
| Kiểu grill | Thực chiến: trace & dự đoán | Cuối mỗi buổi: cho input → bạn dự đoán sự kiện/đầu ra kế tiếp + "đổi dòng này thì hỏng đâu?". |

## Chốt từ buổi grill `/grill-me` (2026-06-25)

Năm quyết định khung, đã stress-test:

1. **Trục neo — hướng lai.** Đọc code bottom-up (nền trước), nhưng *neo theo
   luận điểm*: buổi 00 định hướng theo spine luận văn (RQ → key-findings → hình
   Ch4–5); mỗi module gắn một dòng "chống lưng cho tuyên bố / hình / RQ nào".
2. **Phạm vi — chia tầng.** *Đào sâu*: `scheduler`, `nodes`, 3 giao thức,
   `delay`, `adversary`, `output`. *Đọc giao diện* (gộp ~1–2 buổi): `event_log`,
   `config`, `workload`, `runner/sweep` — riêng *tính tái lập* (reproducibility)
   của sweep thì nắm kỹ. Điều chỉnh sau nếu thấy chậm.
3. **Trace — hai vai.** Ping-pong 2 node (nửa buổi cuối tầng lõi, module 06):
   "đường ống nối thông". PBFT n=4 thật → 1 dòng CSV (đỉnh module 07): "một kết
   quả ra đời". Mặc định mỗi buổi: **dự đoán xong CHẠY THẬT để chấm**.
4. **Phòng thủ — rải + tổng.** Mỗi module đào sâu kết bằng mục **"Phòng thủ"**
   (3–5 câu hội đồng dễ hỏi + trả lời mẫu, *neo wiki/draft, không bịa*). Buổi
   tổng cuối (`14-mock-defense.md`): tôi đóng vai hội đồng quay lại toàn bộ.
5. **Bài báo gốc — đọc có chủ đích.** PDF do người dùng tải vào `raw/` (agent
   chỉ đọc, không sửa). Mỗi giao thức: định vị đúng mục/định lý chống lưng cho
   điểm phòng thủ "gai" nhất, đọc đúng đoạn đó — *không cày cả bài*. Điểm không
   gai dùng `resources/*_DeepDive.md` + `wiki/sources/` làm proxy.

## Tư tưởng cốt lõi

Toàn bộ simulator quy về **một câu**:

> *một file cấu hình YAML + một seed (hạt giống ngẫu nhiên) → một dòng trong CSV kết quả.*

Mọi module tồn tại để phục vụ đường đi đó. Khi lạc, quay về câu này.

Code chia 5 tầng, **đọc từ dưới lên** (giao thức vô nghĩa nếu chưa nắm API `Node`
+ scheduler). Đánh đổi: phải đọc "đường ống" trước phần thú vị — ta bù bằng một
buổi **trace end-to-end** ngay sau tầng lõi để thấy thành quả sớm.

```
config (YAML→hệ thống)  ─┐
scheduler (đồng hồ ảo)   ├─ TẦNG LÕI: discrete-event simulation
nodes (validator + FSM)  │   (xử lý từng "sự kiện" theo thời gian ảo,
network (gửi tin có trễ) │    KHÔNG chạy thời gian thực)
event_log (sự kiện→CSV)  ─┘
        ↓
pbft / pos / snowman      ─ TẦNG GIAO THỨC (3 thuật toán đồng thuận)
        ↓
common (runner+sweep), workload  ─ TẦNG CHẠY (1 run → quét cả lưới)
        ↓
delay/ (Họ B), adversary/ (Họ C) ─ TẦNG THÍ NGHIỆM (sinh số liệu luận văn)
        ↓
output/ (metric, CSV, plot)  ─ TẦNG PHÂN TÍCH → hình Chương 4–5
```

## Chu trình 6 bước mỗi module (phần "khoa học")

1. **Định hướng (5')** — đọc trang hợp đồng trong `wiki/`: biết module *phải làm
   gì* trước khi xem *làm thế nào*. (nạp khái niệm đúng-lúc → đỡ lạc)
2. **Lướt khung** — đọc 1 lượt chỉ để thấy *hình dạng*: có class/hàm nào, docstring
   nói gì. Không dừng ở chi tiết.
3. **Đọc qua test** — mở `tests/.../test_*.py` tương ứng. Test là "đặc tả chạy
   được": cho bạn input/output cụ thể. Cách nhanh nhất để hiểu ý đồ.
4. **Đào sâu** — đọc lại chỗ khó, ghi câu hỏi.
5. **Grill + giải thích lại** — tôi quay bạn (trace & dự đoán); bạn đoán xong, ta
   **chạy thật** test/script tương ứng để chấm. Rồi bạn giải thích module bằng lời
   mình (kỹ thuật Feynman). Hổng chỗ nào → quay về bước 4. Module đào sâu có thêm
   mục **"Phòng thủ"** (câu hỏi hội đồng + trả lời mẫu neo wiki/draft).
6. **Ghi sổ** — cập nhật `progress.md`: gì đã thông, gì còn mờ, điểm tự đánh giá.

> Vì sao bước 5 quan trọng: *truy hồi chủ động* (active recall) nhớ lâu hơn đọc
> lại nhiều lần. Học xong không nghiệm thu rất dễ ảo tưởng đã hiểu.

## Lộ trình & danh mục module

Mỗi dòng là một file trong `modules/`. ✅ = đã viết đầy đủ; ⏳ = sinh đúng lúc khi
tới buổi đó. Cập nhật trạng thái học trong `progress.md`.

| File | Chặng | Module `src/` | Trạng thái |
|------|-------|---------------|-----------|
| `00-architecture.md`     | 0 · Bản đồ | (chỉ wiki + sơ đồ) | ✅ |
| `01-scheduler.md`        | 1 · Lõi | `scheduler/` | ✅ |
| `02-nodes.md`            | 1 · Lõi | `nodes/` | ✅ |
| `03-network.md`          | 1 · Lõi | `network/` | ✅ |
| `04-event-log.md`        | 1 · Lõi | `event_log/` | ✅ |
| `05-config.md`           | 1 · Lõi | `config/` | ✅ |
| `06-trace-end-to-end.md` | ★ Trace | xuyên tầng lõi (ping-pong) | ✅ |
| `07-pbft.md`             | 2 · Giao thức | `pbft/` | ✅ |
| `08-casper-ffg.md`       | 3 · Giao thức | `pos/` | ✅ |
| `09-snowman.md`          | 3 · Giao thức | `snowman/` | ✅ |
| `10-runner-sweep.md`     | 4 · Chạy | `common/`, `workload/` | ✅ |
| `11-delay-family-b.md`   | 5 · Thí nghiệm | `delay/` | ✅ |
| `12-adversary-family-c.md` | 5 · Thí nghiệm | `adversary/` | ✅ |
| `13-output-analysis.md`  | 6 · Phân tích | `output/` | ✅ |
| `14-mock-defense.md`     | ★ Tổng | quay lại toàn bộ (mock defense) | ⏳ |

## Nghi thức mỗi buổi (copy-paste để bắt đầu)

> "Bắt đầu buổi học module NN" → tôi (a) sinh/ mở `modules/NN-*.md`, (b) dẫn bạn
> qua bước 1–4, (c) chạy grill bước 5, (d) cùng cập nhật `progress.md`.

Khi đọc mà bí: cứ hỏi thẳng. Tôi sẽ định nghĩa thuật ngữ ở lần gặp đầu và trỏ về
trang wiki giữ phát biểu chính xác.

## Glossary tối thiểu (chi tiết để trong từng module)

- **BFT** (Byzantine Fault Tolerant) — chịu được node *nói dối/ác ý*, không chỉ node *chết*.
- **finality** — thời điểm một khối "chốt", không thể đảo ngược.
- **quorum** — số phiếu tối thiểu để ra quyết định (BFT thường cần > 2/3).
- **fault threshold f** — số node lỗi tối đa chịu được; BFT cần `n ≥ 3f+1`.
- **view-change** (đổi lượt dẫn) — đổi node dẫn dắt khi nghi nó hỏng (cơ chế hồi sinh *liveness*).
- **safety vs liveness** — *safety* = không bao giờ ra kết quả sai/mâu thuẫn; *liveness* = rốt cuộc cũng ra được kết quả.
- **discrete-event simulation** — mô phỏng bằng cách xử lý từng "sự kiện" theo *thời gian ảo*, không đợi thời gian thực.
