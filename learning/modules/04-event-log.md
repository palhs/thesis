# Module 04 · event-log — biến dòng sự kiện thành dòng CSV

> Chặng 1 · Lõi (module **đọc-giao-diện**: nhẹ đào sâu, **không** có mục Phòng thủ).
> Code: `src/event_log/` (`event_types.py` + `logger.py`, ~130 dòng cả gói).
> Wiki hợp đồng: [[concepts/event-log-schema]].
> Test: `tests/event_log/` (`test_logger.py` + `test_e2e.py` + `test_event_types.py`).
> Chạy chấm: `make test-event_log` (hoặc `PYTHONPATH=src:tests python3 -m unittest event_log.test_logger -v`).

---

## 0. Vì sao module này tồn tại (neo luận văn)

Câu thần chú: *một YAML + một seed → **một dòng CSV***. Bốn module trước dựng
**cỗ máy chạy** (config → scheduler → nodes → network). Module này là **cái bút
ghi chép**: nó đứng bên cạnh cỗ máy, nhìn từng sự kiện trôi qua, và chép lại thành
một file CSV thô. Đây là mắt xích *"→ CSV"* của câu thần chú — nhưng mới là **CSV
thô (raw event log)**, chưa phải bảng số liệu luận văn.

Phân biệt then chốt (wiki §mở đầu):

| Tầng | File | Hạt (row) | Ai đọc |
|------|------|-----------|--------|
| **event log thô** (module này, T24) | 1 dòng / mỗi `EventRecord` | mọi sự kiện, theo thứ tự dispatch | tầng metric (T40), kiểm bất-biến |
| **CSV metric** (Module 13, T40) | 1 dòng / mỗi `(protocol, scenario, seed)` = 1 run | đã *tính* ra latency/tps/goodput | Chương 4–5 |

Nói cách khác: module này ghi lại **chuyện gì đã xảy ra** (node 3 nhận PREPARE ở
t=8.5; node 0 decided ở t=12); Module 13 mới *đếm* các dòng đó thành con số. Vì
thế nó là **substrate** — nền thô mà mọi phân tích về sau đọc lại, thay vì đâm
que đo (instrument) thẳng vào từng giao thức.

Vai trò của nó cực kỳ **thụ động (passive)** — và đây là điểm đáng nhớ nhất:

> `EventLogger` **không giữ tham chiếu scheduler, không giữ file handle, không tự
> đặt lịch event nào, và không bao giờ raise với một event hợp lệ**. Nó *chỉ quan
> sát*.

Vì sao thiết kế thụ động lại quan trọng cho luận văn: nó là điều kiện của **tính
tái lập (reproducibility)**. Logger không thêm bất kỳ nguồn bất định nào (không
RNG, không đọc đồng hồ thật, không thứ tự riêng) → hai run cùng `global_seed` cho
ra `records` **y hệt từng byte**, và CSV cũng y hệt từng byte. Đây là lời hứa
byte-identical replay bạn đã gặp ở M01–M03, giờ kéo dài tới tận file kết quả.

---

## 1. Đọc gì, theo thứ tự

1. **Wiki trước (hợp đồng):** [[concepts/event-log-schema]] — đọc kỹ 4 mục:
   *The `event_sink` seam* (hai hình dạng payload), *`EventRecord` schema* (5
   trường), *Event-type vocabulary* (5 hằng), *CSV format* (sorted-key repr).
2. **Code (làm thế nào), đọc theo đúng thứ tự này:**
   - `src/event_log/event_types.py` (~24 dòng) — **5 hằng chuỗi** + frozenset.
     Đọc trước vì `logger.py` import từ đây.
   - `src/event_log/logger.py` (~96 dòng) — `EventRecord` (dataclass 5 trường) +
     `EventLogger` (`sink` + `to_csv` + `__len__`). Trái tim là **`sink`**.
3. **Test (đặc tả chạy được):**
   - `tests/event_log/test_logger.py` — **file chính**. Từng nhánh của `sink`,
     copy-not-alias, fail-fast, sorted-key, round-trip tuple, determinism.
   - `tests/event_log/test_e2e.py` — logger cắm vào một run 2-node **thật** (đây
     chính là chỗ trả lời câu bạn mang sang từ M03: `event_sink` nối vào đâu).

---

## 2. Mục tiêu khi đọc (đọc xong tự trả lời được)

- **Cái seam:** `scheduler.event_sink = logger.sink` được gán ở **phase 4** của
  six-phase bootstrap. Scheduler gọi callback này từ **hai chỗ**, đẻ ra **hai
  hình dạng payload**. Hai chỗ đó là gì, và mỗi chỗ cho `seq` bằng bao nhiêu?
- **`sink` phân loại payload thế nào?** Bốn nhánh `if/elif` + một `else` fail-fast.
  Nhận diện emit-tuple bằng *cấu trúc* (`tuple, len==3, [0]=="emit"`), transport
  bằng `isinstance`. Vì sao phải đúng thứ tự đó?
- **Một `EventRecord`** gồm 5 trường nào; `fields` khác 4 trường scalar ra sao
  (trường mở, "extensibility surface").
- **Một dòng CSV thành hình ra sao:** header cố định + `repr(dict(sorted(...)))`
  cho ô `fields`. Vì sao sorted-key → determinism.
- Trả được **câu mang sang từ M03**: từ lúc scheduler pop một `Delivery` → dòng
  CSV `8.5,3,delivery,4,{'dst': 3, 'msg_type': 'PREPARE', 'src': 1}` — đi qua
  những bước nào.

---

## 3. Idiom Python cần gloss

- **`@dataclass(frozen=True)`** (`EventRecord`): sinh `__init__`/`__eq__`… tự động;
  `frozen=True` chặn gán lại thuộc tính → `r.t = 9.0` ném `FrozenInstanceError`.
  *Bẫy nông:* "frozen" chỉ khoá **binding của thuộc tính**, không đóng băng *ruột*
  của một dict. `r.fields["k"] = v` **vẫn chạy** (test
  `test_fields_dict_is_mutable_in_place_known_contract_limitation` ghim đúng cái
  footgun này). Frozen = "không đổi được `r.fields` trỏ sang dict khác", không phải
  "dict bên trong bất biến".
- **`dict(fields)` — copy nông (shallow copy):** `sink` lưu `dict(fields)` chứ
  không lưu thẳng `fields`. Tạo một dict **mới** cùng nội dung. Nhờ vậy caller sửa
  dict gốc *sau khi* emit cũng không làm bẩn record đã buffer (test
  `test_emit_fields_dict_is_copied_not_aliased`). "Nông" = chỉ copy tầng ngoài;
  đủ ở đây vì value là số/chuỗi/tuple bất biến.
- **`isinstance(payload, tuple) and len(payload) == 3 and payload[0] == "emit"`
  — structural typing:** không có class `EmitTuple`; emit event là một tuple trần
  3 phần tử. Nhận diện bằng *hình dạng* thay vì *kiểu*. Đây là lý do có test arity
  (2-tuple, 4-tuple đều rớt xuống `else`).
- **`repr(dict(sorted(d.items())))`:** `sorted(d.items())` → list cặp `(k,v)` sắp
  theo key; `dict(...)` dựng lại dict theo thứ tự đó; `repr(...)` in ra chuỗi
  Python-literal. Vì key đã sắp, chuỗi **không phụ thuộc thứ tự chèn** → hai run
  chèn khác thứ tự vẫn ra chuỗi y hệt.
- **`ast.literal_eval` (chỉ trong test):** đọc ngược chuỗi repr thành object Python
  *an toàn* (chỉ literal, không exec code). `repr` giữ được `tuple` (JSON thì không)
  — đó là lý do chọn `repr` chứ không `json.dumps`, để `instance_id=(2,7)` của
  PBFT/Narwhal round-trip đúng kiểu tuple (test `..._round_trips_tuple...`).
- **`Callable[[SimTime, NodeId, int, Event], None]`:** chữ ký callback — nhận
  `(t, node_id, seq, payload)`, trả `None`. Đây là "hợp đồng hàm" giữa scheduler
  và logger; scheduler chỉ cần *một hàm đúng chữ ký này*, không cần biết là logger.

---

## 4. Khái niệm cần gloss

- **event_sink seam (đường ghép chéo-thành-phần):** một callback *tuỳ chọn* trên
  Scheduler. `None` = không ghi (scheduler chạy bình thường). Gán = có người nghe.
  Đây là **điểm nối lỏng (loose coupling)**: scheduler không biết logger tồn tại,
  chỉ gọi "ai đó" qua `event_sink`. Đổi logger, thêm logger thứ hai, hay bỏ hẳn —
  scheduler không đổi một dòng.
- **Hai hình dạng payload** (nhớ kỹ — đây là *bản chất* module):
  1. **Emit tuple** `("emit", event_type, fields)` — do lambda trong
     `Scheduler.bind()` phát, mỗi lần `Node.emit(...)`. `seq = -1` (`EMIT_SEQ`):
     emit **không có** số thứ tự per-node thật. Ví dụ: `decided`, `halted`.
  2. **Typed transport event** — do vòng `Scheduler.run()` phát mỗi khi pop một
     event *không bị tombstone*. `payload` là dataclass `Delivery`/`TimerFire`/
     `PhaseAdvance` thật, `seq` là số per-node thật. `PhaseAdvance` mang
     `node_id = -1` (`PHASE_NODE_ID`) vì nó không thuộc node nào.
- **5 event-type** (`event_types.py` là *single source of truth*): `halted`,
  `decided` (emit) + `delivery`, `timer_fire`, `phase_advance` (transport). Dùng
  **hằng** thay literal để gõ sai → `NameError` ngay (fail-fast), thay vì âm thầm
  ghi sai chuỗi.
- **`fields` = bề mặt mở rộng (extensibility surface):** 4 cột scalar
  (`t,node_id,event_type,seq`) **đóng cứng, không bao giờ đổi**; mọi thứ giao thức
  cần thêm (`round`, `msg_id`, `instance_id`, `value`…) rơi vào `fields` — thêm
  khoá, **không** migrate schema. Đây là quyết định cho phép T28+ (các FSM giao
  thức) mở rộng mà không đụng logger.
- **Vì sao `TimerFire.payload` **không** được ghi:** payload timer là ruột FSM,
  có thể to; logger chỉ giữ `timer_id`. Tương tự, **không synthesize `msg_id`**:
  broadcast đã bung thành N `Delivery` *trước khi* scheduler/logger thấy, nên
  không thể gom nhóm broadcast được nữa → chỉ ghi sự thật phong bì
  `{msg_type, src, dst}`.

---

## 5. Grill — trace & dự đoán

> Cách chơi: bạn **đọc đề, đoán ra giấy/nói miệng**, rồi ta **chạy thật** để chấm.
> Đừng mở `<details>` trước khi đoán. Mình đi **từng câu một**, dừng chờ bạn.

### H1 — `sink` phân loại (nhánh nào?)
Cho 4 lời gọi `sink` này, mỗi cái rơi vào nhánh nào của `sink`, và `event_type`
của record sinh ra là gì (hoặc "raise")?

```python
logger.sink(12.0, 5, -1, ("emit", "decided", {"value": "0xab"}))
logger.sink(8.5,  3,  4, Delivery(Message(1, 3, "PREPARE", None, 4.0)))
logger.sink(1.0,  0,  1, ("emit", "x"))          # tuple 2 phần tử
logger.sink(1.0,  0,  1, "not an event")
```

<details><summary>ĐÁP ÁN H1</summary>

1. Nhánh **emit-tuple** (`tuple, len==3, [0]=="emit"`) → `event_type="decided"`,
   `fields={"value":"0xab"}`, `seq=-1`.
2. Nhánh **`isinstance(payload, Delivery)`** → `event_type="delivery"`,
   `fields={"msg_type":"PREPARE","src":1,"dst":3}` (moi từ phong bì `msg`), `seq=4`.
3. **raise `TypeError`** — là tuple nhưng `len==2`, không lọt điều kiện emit; các
   `elif isinstance` cũng trượt (không phải Delivery/TimerFire/PhaseAdvance) → rơi
   xuống `else`. (test `test_two_tuple_emit_raises_type_error`)
4. **raise `TypeError`** — string, trượt hết → `else`. (test
   `test_unknown_payload_raises_type_error`)

Mấu chốt: nhận diện emit bằng **cấu trúc**, transport bằng **kiểu**; gì không khớp
→ fail-fast, *không* âm thầm bỏ (no silent drop).
</details>

### H2 — copy hay alias?
```python
logger = EventLogger()
original = {"reason": "RUN_END"}
logger.sink(3.0, 1, -1, ("emit", "halted", original))
original["reason"] = "MUTATED"
print(logger.records[0].fields)   # ??? in ra gì
```
Và câu vặn: nếu thay vì sửa `original`, ta làm `logger.records[0].fields["x"]=9`
thì có sửa được record không?

<details><summary>ĐÁP ÁN H2</summary>

In ra `{'reason': 'RUN_END'}` — **không** phải `MUTATED`. Vì `sink` lưu
`dict(fields)` = **một dict mới** (copy nông), sửa `original` về sau không đụng
tới bản đã buffer. Chiều *vào* được bảo vệ. (test `..._copied_not_aliased`)

Câu vặn: `records[0].fields["x"]=9` **sửa được** — đây là *footgun đối xứng* ở
chiều *ra*. `EventRecord` frozen chặn `r.t=...` nhưng **không** đóng băng ruột
dict `r.fields`. Contract hiện tại pin đúng hành vi này (test
`..._mutable_in_place_known_contract_limitation`), và ghi chú "nếu thành vấn đề
thật thì bọc `MappingProxyType`". Nhớ: frozen ≠ deep-immutable.
</details>

### H3 — một dòng CSV thành hình (đóng câu mang sang từ M03)
Buffer có đúng 2 record theo thứ tự:
```python
logger.sink(12.0, 5, -1, ("emit", "decided", {"value": "0xab"}))
logger.sink(8.5,  3,  4, Delivery(Message(1, 3, "PREPARE", None, 4.0)))
logger.to_csv(out)
```
Viết ra **3 dòng** của file CSV (header + 2 dòng data), *chính xác từng ký tự* ô
`fields`. Chú ý: thứ tự dòng theo thứ tự nào? key trong `fields` sắp thế nào?

<details><summary>ĐÁP ÁN H3</summary>

```
t,node_id,event_type,seq,fields
12.0,5,decided,-1,{'value': '0xab'}
8.5,3,delivery,4,{'dst': 3, 'msg_type': 'PREPARE', 'src': 1}
```

- **Thứ tự dòng = thứ tự buffer = thứ tự `records`**, tức thứ tự `sink` được gọi
  = thứ tự dispatch của scheduler. Logger **không** tự sắp lại (ghi 12.0 *trước*
  8.5 dù t lớn hơn — vì nó tới trước trong dòng gọi). Logger không áp thứ tự riêng.
- **Ô `fields` = `repr(dict(sorted(fields.items())))`.** Ở dòng delivery, key gốc
  chèn theo `msg_type, src, dst` nhưng sorted → `dst, msg_type, src`.
- 4 cột scalar in trần (`12.0`, `5`, `decided`, `-1`).

Đây là toàn bộ hành trình câu bạn mang sang từ M03: `run()` pop `Delivery` →
gọi `event_sink(t, node_id, seq, delivery_obj)` → `sink` vào nhánh `Delivery`,
moi `{msg_type,src,dst}` từ `msg` → append `EventRecord` → `to_csv` in
sorted-key repr. `event_sink` **nối vào `logger.sink`** ở phase 4.

Cách chạy chấm nhanh (mình sẽ chạy):
`PYTHONPATH=src:tests python3 -m unittest event_log.test_logger.TestToCsv -v`
</details>

### H4 — determinism qua thứ tự chèn khác nhau
Hai logger, cùng chuỗi event, nhưng dict `fields` **chèn khác thứ tự**:
```python
la.sink(1.0, 0, -1, ("emit", "decided", {"value": "v", "n": 1}))
lb.sink(1.0, 0, -1, ("emit", "decided", {"n": 1, "value": "v"}))
```
`la.to_csv(a)` và `lb.to_csv(b)`. `a.read_bytes() == b.read_bytes()`? Vì sao?

<details><summary>ĐÁP ÁN H4</summary>

**Bằng nhau, byte-identical.** Vì ô `fields` là `repr(dict(sorted(...)))` — sắp
key trước khi in, nên `{"value","n"}` và `{"n","value"}` đều ra `{'n': 1, 'value':
'v'}`. Thứ tự chèn bị "làm phẳng". Đây là 1 trong 2 chân của determinism (chân kia:
thứ tự record = thứ tự dispatch, đã tất định bởi khoá `(t,node_id,seq)` từ M01).
(test `test_identical_event_sequences_yield_identical_csv`)

Nối luận văn: đây chính là lời hứa *cùng (YAML, seed) → CSV y hệt từng byte* —
điều kiện để sweep + CI kiểm hồi-quy được, và để hai người chạy lại ra cùng số.
</details>

### H5 — e2e: run thật đẻ ra những event-type nào?
`test_e2e.py` có 2 fixture. `PingPongNode` (`_run`, budget=4) và `TimerPingNode`
(`_run_multiphase_with_timer`, 2 phase + timer). Với **mỗi** fixture, tập
`event_type` xuất hiện trong `logger.records` gồm những gì? (5 loại khả dĩ:
delivery, timer_fire, phase_advance, decided, halted)

<details><summary>ĐÁP ÁN H5</summary>

- **`PingPongNode` (`_run`)**: `{decided, halted, delivery}` — **3 loại**. Node
  bounce PING/PONG (delivery), khi đủ budget thì `_emit_decided` + `halt`
  (decided, halted). **Không** có `timer_fire` (không ai `set_timer`) và **không**
  `phase_advance` (chỉ 1 phase `[0, inf)`, không có mốc chuyển). (test
  `test_both_event_sink_shapes_are_recorded`)
- **`TimerPingNode` (`_run_multiphase_with_timer`)**: **cả 5** —
  `{delivery, timer_fire, phase_advance, decided, halted}`. node 0 `set_timer`
  ("kickoff", fire ở t=5 → `timer_fire`), timer fire thì gửi PING (→ delivery),
  node 1 nhận thì decided+halt; và 2 phase (mốc t=50) → `phase_advance`. Fixture
  này cố ý dựng để chạm **cả 5 nhánh** `sink` trong một run thật (đóng gap L-4).
  (test `test_recorded_stream_contains_all_five_event_types`)

Bài học: 5 nhánh của `sink` không phải lúc nào cũng cùng xuất hiện — phụ thuộc
node có arm timer không, network có nhiều phase không. Đây là lý do phải có
fixture "cả 5 loại" riêng.
</details>

---

## 7. Giải thích lại (Feynman) + ghi sổ

Sau grill, tự giải thích **không nhìn code**:

1. `event_sink` là gì, được gán ở phase mấy, scheduler gọi nó từ **hai** chỗ nào,
   mỗi chỗ payload hình dạng gì và `seq` bằng mấy.
2. Kể hành trình một `Delivery`: từ `run()` pop → thành một dòng CSV cụ thể. Nói
   rõ ô `fields` được dựng thế nào.
3. Hai chân của determinism (thứ tự record + sorted-key). Vì sao logger *thụ động*
   là điều kiện của reproducibility.
4. Một câu: vì sao 4 cột scalar đóng cứng còn `fields` mở — nó phục vụ ai (T28+).

Nếu chỗ nào ú ớ → quay lại §4/§5 chỗ đó.

**Ghi sổ** (mình cập nhật `progress.md` cuối buổi): điểm grill 1–5, đã thông gì,
còn mờ gì. Câu mang sang dự kiến cho **Module 05 (`config`)**: từ file YAML thành
`Scheduler` + `Network` + list `Node` đã bind sẵn — factory dựng cả sáu phase
bootstrap ở đâu, và bốn cổng fail-fast "Watch for T27" chặn cấu hình sai *trước
t=0* là gì? ([[concepts/reproducibility]])
