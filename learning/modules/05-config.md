# Module 05 · config — YAML → hệ thống chạy được

> Chặng 1 · Lõi · `src/config/`. Module **đọc-giao-diện**: nắm *hình dạng cửa
> ngõ* (file YAML vào, `Config` + `RunHandle` ra) và **tính tái lập**
> (reproducibility) — không cày từng nhánh coi-cút. Bỏ mục Phòng thủ.

---

## 0. Vì sao module này tồn tại

Nhớ **một câu** của cả simulator:

> *một file YAML + một seed → một dòng CSV.*

Bốn module trước (`scheduler`, `nodes`, `network`, `event_log`) là *bộ máy*.
Nhưng bộ máy đó tự nó không biết **n=4 hay n=100**, **delay 50ms hay phân
phối lognormal**, **chạy tới t_max nào**. `config/` là **cửa ngõ đầu vào**: nó
biến một file text người viết được thành các object Python đã ráp sẵn dây, sẵn
sàng cho `scheduler.run()`.

Hai nửa, hai file:

| Nửa | File | Câu hỏi trả lời |
|-----|------|-----------------|
| **Đọc** cấu hình | `loader.py` | "file YAML này có hợp lệ không, và nó *là* config gì?" (text → `Config`) |
| **Dựng** hệ thống | `factory.py` | "cho `Config` + seed này, ráp Scheduler/Network/Node ra sao?" (`Config` → `RunHandle`) |

`schema.py` = định nghĩa *hình dạng* của `Config`/`RunHandle` (dataclass đông
cứng). `__init__.py` = mặt tiền export.

**Nối RQ/chương:** module này chống lưng cho **reproducibility contract** —
điều kiện tiên quyết để MỌI con số trong Chương 4–5 đáng tin. Nếu cùng
`(YAML, seed)` mà hai lần chạy ra khác nhau, thì "PBFT latency 120ms" là nhiễu
tiến-trình chứ không phải sự thật đo được, và không verdict so-sánh nào sống
sót khi bị audit ([[concepts/reproducibility]] §1). Đây là *lý do* T27 tồn tại.

---

## 1. Đọc gì (thứ tự)

1. **Wiki hợp đồng:** `wiki/concepts/reproducibility.md` — đọc §1 (framing),
   §3 (single seed surface), §5 (build_run 6 phase), §6 (forbidden surfaces).
   Đây là *đặc tả* của module.
2. **Code** (`src/config/`, tổng ~14KB — nhỏ):
   - `schema.py` (~50 dòng) — 3 dataclass. Đọc trước: biết *cái gì* đi ra.
   - `factory.py` (~64 dòng) — `build_run`, 6-phase bootstrap. Nửa "dựng".
   - `loader.py` (~256 dòng) — `load_config`, pipeline 5 bước. Nửa "đọc".
     Đừng đọc từng `if`; nắm *5 bước* và *phễu lỗi `ConfigError`*.
3. **Test** (`tests/config/`) — đặc tả chạy được:
   - `_helpers.py` — `MINIMAL_YAML` (config mẫu tối thiểu) + `MinimalNode`.
   - `test_e2e_determinism.py` — **trái tim**: 3 claim tái lập.
   - `test_factory.py`, `test_loader.py` — cửa ngõ + fail-fast gates.

---

## 2. Mục tiêu khi đọc

Xong module này, bạn trả lời được:

- **Ranh giới** loader vs factory: cái nào đọc, cái nào dựng, `Config` ở giữa.
- **6-phase bootstrap** trong `build_run` — thứ tự và *vì sao thứ tự đó*.
- **Single seed surface**: `global_seed` là *hạt giống duy nhất*, ra khỏi đây
  thành hai dòng RNG (per-Node + per-Network). Vì sao `global_seed` KHÔNG nằm
  trong YAML.
- **`ConfigError` là phễu lỗi duy nhất** — mọi cách config sai đều fail-fast
  *trước t=0* với một locator `path: key_path: message`.
- **Ba khoang opaque** (`adversary`/`protocol_knobs`/`workload`) — vì sao còn
  là `dict` thô, ai sẽ đóng cứng chúng sau (đóng câu M02 `self.adversary`).
- **Vì sao byte-identical** chứ không "tương đương thống kê".

---

## 3. Idiom Python cần gloss

- **`@dataclass(frozen=True)`** — class chỉ-giữ-dữ-liệu, *bất biến*: gán lại
  field sau khi tạo → `FrozenInstanceError`. Dùng cho `Config`/`RunHandle` để
  config không bị lén sửa giữa run (điều kiện tái lập). Bạn đã gặp ở
  `EventRecord` (M04) và `Phase` (M03).
- **`MappingProxyType(d)`** (từ `types`) — *khung nhìn chỉ-đọc* lên một dict.
  `handle.nodes[42] = x` → `TypeError`. `build_run` bọc dict node bằng nó để
  caller không sửa được sổ node sau khi dựng (`factory.py:63`). Khác `frozen`:
  đây bọc *container*, không phải dataclass.
- **`Callable[[NodeId, int], Node]`** (type alias `NodeFactory`) — kiểu của
  *một hàm*: nhận `(node_id, global_seed)` trả `Node`. `build_run` không tự
  `import PBFTNode`; nó nhận *nhà máy node* từ ngoài (dependency injection) —
  cùng một factory dựng được PBFT, Casper, hay `MinimalNode` test.
- **`frozenset((...))`** — set bất biến, dùng cho `_REQUIRED_TOP_LEVEL` (bảng
  khóa bắt buộc). Bất biến vì nó là hằng cấu hình, không ai được sửa lúc chạy.
- **`raise ... from None`** — *nuốt* exception gốc trong chuỗi `__cause__`. Khi
  `int("x")` ném `ValueError`, loader bắt và ném `ConfigError` sạch, `from None`
  để traceback không lòi ra `ValueError` nội bộ. Mục tiêu: **một loại lỗi duy
  nhất** thoát ra (`loader.py:9-10`).
- **`set(raw) - _REQUIRED_TOP_LEVEL`** — phép trừ tập: khóa thừa = có mà không
  bắt buộc; `_REQUIRED - set(raw)` = khóa thiếu. Hai chiều bắt cả *quên khóa*
  lẫn *gõ sai tên khóa* (typo `n_run` thay `n_runs`).
- **`sorted(missing)[0]`** — báo lỗi *tất định*: nhiều khóa thiếu thì luôn báo
  khóa đầu theo bảng chữ cái, không phụ thuộc thứ tự hash của set. (Tái lập
  ngay cả trong *thông báo lỗi*.)

---

## 4. Khái niệm cần gloss

- **Reproducibility (tái lập) byte-identical** — cùng `(YAML, seed)` → hai lần
  chạy cho stream `event_sink` **giống nhau từng byte**, không phải "gần bằng".
  Vì sao gắt vậy: nếu chỉ "tương đương thống kê" thì một regression trong số
  của protocol A không phân biệt được với "run tự trôi" ([[concepts/reproducibility]]
  §1). Giá phải trả nhỏ: `blake2b` seed + lặp `sorted` ở hai hot path.
- **Single seed surface** — `global_seed: int` là **đầu vào ngẫu nhiên duy
  nhất**. Từ nó suy ra hai dòng RNG bằng `blake2b` (băm ổn-định-liên-tiến-trình):
  `_stable_seed(seed, node_id)`→`Node.rng` (mỗi node một dòng),
  `_network_seed(seed)`→`net_rng` (cả run một dòng). Scheduler **không giữ
  RNG**. Vì sao `blake2b` chứ không `hash()`: Python bật `hash()` ngẫu-nhiên-
  hóa mỗi tiến trình → replay xuyên máy sẽ vỡ.
- **Vì sao `global_seed` KHÔNG trong YAML** — YAML mô tả *một điểm cấu hình*
  (n, delay, adversary…); seed là *trục lặp lại* trực giao. Harness bên ngoài
  đánh số seed 0…n_runs−1 và bơm vào. Cùng một YAML + nhiều seed = nhiều mẫu
  của *cùng* một điểm. Và **common random numbers**: cùng seed cho cả 3
  protocol ⇒ so sánh công bằng (cùng "vận rủi" mạng) ([[concepts/experiment-matrix]] §7).
- **Six-phase bootstrap** — thứ tự ráp *bắt buộc* (`factory.py:29-40`):
  `Scheduler()` → `Network(...)` → (mỗi node: tạo→register→bind sched→bind net)
  → `bind_network` → `network.start()` → (mỗi node `start(t=0)` theo thứ tự
  node_id). **Vì sao thứ tự này**: `network.start()` phải chạy *trước* mọi
  `node.start()` vì node có thể `broadcast` ngay lúc start — mạng chưa mở thì
  ném lỗi (đúng cái `test_network_started_before_any_node_started` bắt).
- **Ba khoang opaque** — `adversary`/`protocol_knobs`/`workload` load round-trip
  thành `dict[str,Any]`, `build_run` KHÔNG soi vào. Cố ý: hợp đồng của chúng
  còn *mở-để-sửa* (adversary→T18, protocol_knobs→T28+, workload→T41); khi task
  chủ quản landing, mỗi `dict` thay bằng một dataclass đóng cứng. Đây chính là
  khe `self.adversary` opaque bạn để dành từ **M02**.
- **Bốn cổng fail-fast cross-field** (`_validate_config`, `loader.py:229`) —
  chặn config vô nghĩa *trước t=0*: (1) `1 ≤ n ≤ 10000`; (2) `t_max` hữu hạn
  dương (chặn cả `.nan` — `isfinite` trước so sánh, đúng bẫy `nan` bạn gặp ở
  M02); (3) `n_runs ≥ 1`; (4) mọi NodeId trong partition ∈ `range(n)`. Đây là
  "Watch for T27" bạn mang từ M03/M04 — bốn cổng nằm đây.

---

## 5. Grill "trace & dự đoán"

Trả lời trong đầu (hoặc nói ra) TRƯỚC khi mở `<details>`. Sau đó ta **chạy
thật** để chấm.

Chạy suite:
```
make test-config
# hoặc lẻ:  PYTHONPATH=src:tests/config python3 -m unittest discover -s tests/config -v
```

### H1 — Ranh giới loader/factory
`load_config` trả về cái gì? `build_run` *nhận* cái gì và trả cái gì? Vẽ mũi
tên: `path` →(?)→ `Config` →(?)→ `RunHandle`. Trong hai hàm đó, cái nào cần
`global_seed`? Vì sao cái kia *không* cần?

<details><summary>ĐÁP ÁN</summary>

`load_config(path) -> Config`. `build_run(config, global_seed, node_factory)
-> RunHandle`. `path` →`load_config`→ `Config` →`build_run(+seed,+factory)`→
`RunHandle`. **Chỉ `build_run` cần seed** — vì seed là đầu vào *runtime* (bơm
RNG lúc dựng), không phải thuộc tính *cấu hình*. `load_config` cố tình không
đụng seed: nó thuần đọc-YAML→object, và `global_seed` KHÔNG nằm trong YAML
(§3 wiki). Tách vậy để cùng một `Config` chạy được với nhiều seed khác nhau.
</details>

### H2 — Thứ tự 6 phase
`MinimalNode._on_start` gọi `self.broadcast("PING", ...)`. Giả sử ai đó **đảo**
phase 5 (`network.start()`) xuống *sau* vòng `node.start()` ở phase 6. Test nào
gãy, và lỗi runtime là gì?

<details><summary>ĐÁP ÁN</summary>

`test_network_started_before_any_node_started` gãy. Node 0 `start(t=0)` →
`_on_start` → `broadcast` → `Network.submit_*` *trước khi* `network.start()`
chạy → `RuntimeError` ("submit before start"). Đây là lý do phase 5 phải đứng
trước phase 6: mạng phải "mở cửa" trước khi node đầu tiên có cơ hội gửi tin.
(Chạy chấm: test này *pass* ở code hiện tại vì thứ tự đúng — nó chứng minh
bằng việc build **không** ném RuntimeError.)
</details>

### H3 — Single seed flows
`TestSeedDivergence` chạy `build_run` với seed=42 và seed=43, khẳng định hai
stream **khác nhau**. `MinimalNode._on_start` làm gì tạo ra khác biệt đó? Nếu
`MinimalNode` broadcast `{"r": 0.5}` *hằng số* thay vì `self.rng.random()`,
test này còn pass không? Test *SameSeed* thì sao?

<details><summary>ĐÁP ÁN</summary>

`_on_start` broadcast `{"r": self.rng.random()}` — một mẫu từ per-Node RNG
đã seed từ `global_seed`. Seed khác → `Node.rng` khác → `r` khác → stream khác.
Nếu đổi thành hằng `0.5`: **`TestSeedDivergence` GÃY** (hai seed cho stream
*giống* nhau, `assertNotEqual` thất bại) — vì không còn gì phụ thuộc seed để
phân kỳ. **`TestSameSeed` vẫn PASS** (hằng số thì tất nhiên byte-identical).
Cặp test này bắt hai lỗi ngược nhau: SameSeed bắt *nhiễu* (phải giống), 
Divergence bắt *seed chết* (seed không chảy tới RNG).
</details>

### H4 — Fail-fast gate nào
Với mỗi config sai dưới đây, `load_config` fail ở **bước nào** (4.2 required /
4.3-4.4 leaf / 4.5 cross-field) và `key_path` báo gì?
(a) thiếu khóa `t_max`; (b) `n: 100000`; (c) `kind: triangular` trong delay;
(d) partition `groups: [[0,1],[99]]` với `n=4`.

<details><summary>ĐÁP ÁN</summary>

- (a) **4.2 required-key** → `key_path="t_max"`, "missing required top-level key".
- (b) **4.5 cross-field** → `key_path="n"`, "must be in [1, 10000]". (Parse/coerce
  ok — `100000` là int hợp lệ; chỉ *ngưỡng lành mạnh* bắt.)
- (c) **4.3-4.4 leaf-construct** → `DelayDist(kind="triangular")` ném `ValueError`
  trong `__post_init__`, loader bọc thành `ConfigError` key_path
  `network.phases[0].delay`, message chứa "triangular".
- (d) **4.5 cross-field** → `network.phases[0].partitions[0]`, "NodeId 99 not in
  range(n)=4". (Leaf construct *chấp nhận* 99 — Partition không biết n; chỉ
  cross-field, nơi biết cả n lẫn partition, mới bắt được.)

Điểm cốt: fail-fast phân *tầng theo thông tin cần có* — required biết-tên-khóa,
leaf biết-giá-trị-một-ô, cross-field biết-cả-config.
</details>

### H5 — Opaque round-trip
`adversary: { strategy: delay-emission, fraction: 0.1 }` trong YAML. Sau
`load_config`, `cfg.adversary` là gì? `build_run` có đọc `strategy` không? Ai
sẽ biến `dict` này thành dataclass đóng cứng, và điều đó nối với khe nào bạn để
dành từ Module 02?

<details><summary>ĐÁP ÁN</summary>

`cfg.adversary == {"strategy": "delay-emission", "fraction": 0.1}` — round-trip
verbatim (`test_opaque_sections_round_trip`). `build_run` **không** đọc — nó chỉ
`dict(raw["adversary"])` rồi giao vào `Config`, không introspect. Task **T18**
(binding adversary) sẽ thay `dict` bằng dataclass typed. Đây nối thẳng khe
`self.adversary` **opaque** bạn để dành ở M02: config *chở* blob adversary,
node *nhận* nó, nhưng cả hai tầng đều chưa mở nó ra — chờ Family C (M12).
</details>

---

## 6. Giải thích lại + ghi sổ

Feynman bằng lời bạn (không nhìn code):

1. **Đường đi một câu**: từ `path` file YAML tới `RunHandle` sẵn-chạy, đi qua
   những trạm nào, `Config` đông cứng ở đâu, seed nhập vào ở đâu.
2. **Vì sao byte-identical đáng giá** và *cái giá* của nó (2 hot path sorted +
   blake2b) — nối với "mọi con số Ch4–5".
3. **Bốn cổng fail-fast** — kể tên bốn cổng và *vì sao* mỗi cổng phải ở đúng
   tầng của nó (thông tin cần có để bắt).

Rồi cập nhật `progress.md`: bảng tiến độ (điểm 1–5, đã thông / còn mờ) + một
mục nhật ký + gom câu mở. Câu mở dự kiến mang sang **M06 (trace end-to-end)**:
ghép `build_run` + `scheduler.run` + `event_sink` thành *một dòng CSV* thật với
ping-pong 2 node — đóng trọn đường ống tầng lõi.
