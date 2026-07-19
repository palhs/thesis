# Module 13 — `output/` (đào sâu · tầng Phân tích · đóng xương sống)

> Nơi "CSV thô mỗi dòng 1 cell" biến thành **hình Chương 4–5**. ~40–45 phút.
> Module đào sâu cuối chặng dữ-liệu, nên có đủ: trace & dự đoán + chạy thật +
> Phòng thủ. Đây là bước cuối của câu thần chú: *YAML + seed → 1 dòng CSV* →
> **nhiều seed → mean ± CI → figure**.

## 0. Vì sao tồn tại — và nối RQ/hình/chương

M11/M12 (delay/adversary) đã sinh ra file **long-format**: mỗi dòng = một cell
`(protocol, scenario, seed)`, do đường ống `_run_cell → clip → reducer →
_build_row` đẻ ra. `output/` là tầng đứng **sau** file đó, làm hai việc:

1. **Định nghĩa cột** metric mà reducer/writer dùng (`schema.py` COLUMN_ORDER +
   `metrics.py` goodput/bytes_per_acu) — hợp đồng cột của mọi dòng thô.
2. **Gộp qua seed → thống kê → vẽ**: `analysis.py`+`aggregate.py` gom 20 seed
   thành mean + 95% CI; `plots.py` vẽ metric-vs-`n`; các module họ
   (`delay_analysis`, `adversary_analysis/comparison`) tái dùng đúng helper CI +
   STYLE để ra bảng-xếp-hạng feed RQ4/RQ5.

Điểm chống lưng phòng thủ: đây là nơi "**con số của em đáng tin**" phải đứng
vững — CI đúng thống kê (Student-t, small-sample), so-sánh công bằng
(`commit_latency_ms` không phải `finality_latency_ms`), và **byte-identical** ở
tầng phân tích (mọi CSV/figure là hàm THUẦN của CSV thô đã commit). Nối:
RQ3 (overhead, Fig 4.7), RQ1/RQ4 (delay/loss ranking Fig 4.8–4.13),
RQ5 (frontier radar Fig 5.1); [[wiki/concepts/key-findings]] F2/F3.

## 1. Đọc gì, theo thứ tự

1. `wiki/concepts/output-format.md` — hợp đồng CSV chuẩn (schema ~30 cột, subset
   18 cột hôm nay, §13 Revisions về latency comparability). **Đọc trước code.**
2. `wiki/concepts/evaluation-metrics.md` §Goodput/§Overhead — mẫu số ACU, tps vs
   goodput. Đọc lướt phần đã nắm từ M07/M08.
3. Code, theo *chiều dữ liệu đi lên*:
   - `src/output/schema.py` (66 dòng) — `ScenarioMeta` + `COLUMN_ORDER`. Ngắn.
   - `src/output/metrics.py` — hai cột thuần workload (`goodput`, `bytes_per_acu`).
   - `src/output/analysis.py` — **lõi thống kê**: `aggregate`, `t_critical_975`,
     `wilson_interval`, `by_metric`. Đọc kỹ nhất.
   - `src/output/aggregate.py` — long→wide, ghi `aggregated.csv`.
   - `src/output/metrics_view.py` — view dẫn xuất pass-through (T42).
   - `src/output/plots.py` — render figure (matplotlib headless).
4. Test (đặc tả chạy được): `tests/output/test_metrics.py`,
   `test_aggregate.py`, `test_metrics_view.py`.

## 2. Mục tiêu khi đọc (trả lời được là đạt)

- **Hai ranh giới reduce**: per-trial (trong adapter M11/M12, 1 dòng/cell) vs
  across-seed (`output/aggregate`, 1 dòng/scenario). Cái nào tiêu thụ cái nào?
- `aggregate()` group theo **`run_id`** chứ không `(protocol, n)` — vì sao? (bẫy
  FFG n=4 uniform/nonuniform).
- Vì sao CI của **hầu hết** metric có bề rộng **0**, chỉ `goodput` có CI thật?
- Vì sao Student-t (`df=19, t=2.093`) chứ không normal `1.96`? Wilson dùng cho ai?
- `commit_latency_ms` vs `finality_latency_ms`: cái nào so cross-protocol, vì sao?
- Tính tái lập tầng phân tích: `metrics_view` **pass-through verbatim string** →
  điều đó bảo chứng gì mà "đọc-rồi-format-lại" không bảo chứng?

## 3. Idiom Python sẽ gặp (gloss)

- `csv.DictReader` / `csv.DictWriter(fieldnames=..., extrasaction="raise")` —
  đọc/ghi CSV theo tên cột. `extrasaction="raise"` = có key lạ thì NÉM (fail-fast);
  `"ignore"` (trong metrics_view) = bỏ cột thừa lặng lẽ khi chiếu.
- `defaultdict(list)` và `defaultdict(lambda: defaultdict(list))` — dict tự tạo
  giá trị rỗng khi truy key mới; lồng hai lớp = `[metric][protocol] → list`.
- `@dataclass(frozen=True)` — `Agg`/`ScenarioMeta` = túi dữ liệu bất biến.
- `row.setdefault(k, default)` — lấy `row[k]`, nếu chưa có thì đặt `default` rồi
  trả (dùng gom nhiều metric của cùng `run_id` vào **một** dòng wide).
- `[v for v in vals if not math.isnan(v)]` — lọc NaN TRƯỚC khi tính mean/std
  (NaN = "ô này không áp dụng", vd Snowman-param ở PBFT).
- `round(x, 6)` — chốt định dạng số để CSV byte-stable qua các lần chạy.
- `matplotlib.use("Agg")` — backend không-màn-hình (headless) → render tất định,
  không phụ thuộc GUI. Đặt TRƯỚC `import pyplot`.
- `sorted(groups.items())` / `key=lambda k: (proto, n, k)` — áp một **thứ tự toàn
  phần** để output độc-lập-thứ-tự-đọc-vào (nối trụ collect-sort của M10).

## 4. Khái niệm gloss

- **long-format vs wide-format** — long: 1 dòng/(scenario,seed), metric là cột,
  nhiều dòng cùng scenario (substrate mà sweep *append* vào). wide (`aggregated.csv`):
  1 dòng/scenario, mỗi metric nở thành `mean/ci_lo/ci_hi/cv` (feed plot/table).
- **confidence interval (CI)** — khoảng quanh mean mà ta tin (95%) chứa giá trị
  thật. Nửa-rộng `ci_half = t · sem`.
- **standard error of mean (sem)** — `std / √k`; độ lệch của *trung bình mẫu* (nhỏ
  dần khi thêm seed), khác `std` (độ tản của từng điểm).
- **Student-t** — phân phối thay normal khi mẫu NHỎ + phương sai chưa biết; tra
  `t_critical_975(df)`, `df = k−1 = 19` cho 20 seed → `t=2.093` (rộng hơn 1.96 ~7%).
- **coefficient of variation (cv)** — `std/mean·100%`; cờ-nhìn-lướt xem metric nào
  có **biến thiên theo seed thật** (goodput ~2.2%) vs **tất định** (cv=0).
- **Wilson interval** — CI cho *tỉ lệ* nhị phân `k/n` (success_rate, ε-witness);
  trung thực ở biên 0-of-n / n-of-n (normal approx sập thành điểm ở đó).
- **ACU (atomic-commit-unit)** — mẫu số chuẩn-hóa overhead: msg/byte trên "một đơn
  vị chốt", để so PBFT (per-block) với FFG (per-epoch) công bằng.
- **derived view / projection** — bản chiếu THUẦN của file gốc (đọc→chọn cột→ghi),
  không thu thập mới, không đổi định dạng ⇒ byte-identical với nguồn.

## 5. Grill — trace & dự đoán (đoán xong ta CHẠY THẬT để chấm)

> Chạy chấm: `make test-output`, hoặc một file cụ thể, vd
> `PYTHONPATH=src python3 -m pytest tests/output/test_aggregate.py -q`
> (dataset thật `results/baseline/*.csv` đã có → test real-data không skip).

1. `aggregate()` nhận 40 dòng: 20 seed `casper-ffg-n4-uniform` + 20 seed
   `casper-ffg-n4-nonuniform` (cùng protocol, cùng n=4). Ra **mấy nhóm** Agg
   cho một metric? Nếu group theo `(protocol, n)` thay vì `run_id` thì sai ở đâu?
2. Một scenario có 5 giá trị `goodput = [8,9,10,11,12]`. `mean`=? `ci_lo`, `ci_hi`
   nằm hai phía mean? Còn 5 giá trị **giống hệt** `[10,10,10,10,10]` thì `ci_half`=?
3. Một nhóm chỉ có **1** seed sống sót (k=1) sau khi lọc NaN. `std/sem/ci_half`=?
   (đọc nhánh `else` trong `aggregate`).
4. `bytes_per_acu` gặp một delivery `msg_type="TOTALLY-UNKNOWN"`. Trả NaN, 0, hay
   **ném**? Vì sao thiết kế vậy?
5. `metrics_view` chiếu `baseline.csv` (300 dòng). Ô `commit_latency_ms` trong view
   so với ô nguồn: bằng-số hay bằng-**byte**? Nếu code đọc float rồi `f"{x:.6f}"`
   lại thì test nào sẽ gãy?
6. Hai figure `throughput_vs_n` (goodput) và `decision_rate_vs_n` (tps). Đường nào
   **phẳng theo n**, đường nào **dốc lên theo n**? Con nào là "throughput thật"?

<details><summary>ĐÁP ÁN</summary>

1. **Hai nhóm** (mỗi `run_id` một mẫu 20 seed riêng). Group theo `(protocol,n)` sẽ
   **gộp** 40 dòng làm một → hỏng CẢ mean lẫn CI (trộn hai stake-distribution khác
   nhau). Docstring `aggregate` nói thẳng: group theo `run_id` "never pooled".
   (Lưu ý: `by_metric` sau đó *bỏ* nonuniform khỏi đường cong để không có 2 điểm
   trùng n, nhưng nó vẫn nằm trong `aggregated.csv`.)
2. `mean=10.0`; `ci_lo<10<ci_hi` (test `test_ci_brackets_mean`). Với 5 giá trị
   giống hệt: `std=0 ⇒ sem=0 ⇒ ci_half=0` (CI bề-rộng-0). Đây chính là vì sao hầu
   hết metric structural có CI = 0.
3. Cả ba = **0.0** — nhánh `else` khi `k≤1` (không đủ điểm tính phương sai mẫu
   `ddof=1`, `√(k−1)` sẽ chia 0). `cv` cũng = 0 (mean≠0).
4. **Ném `KeyError`** (fail-fast): `_BASE_BUDGET[mt]` không có key → một msg_type
   chưa được cấp ngân sách KHÔNG được lặng lẽ tính 0 (sẽ làm lệch overhead).
   `test_unbudgeted_msg_type_raises` chốt điều này; `TestBudgetCoverage` còn grep
   `node.py` bảo đảm mọi type 3 giao thức phát đều có trong bảng.
5. Bằng **byte** — view copy-through **string thô**, không parse-lại-format. Nếu
   đọc float rồi format lại, `test_round_trip_fidelity` (so byte-for-byte view vs
   nguồn) + `test_rebuild_matches_committed_artifact` sẽ gãy. Pass-through =
   byte-stable KHÔNG cần biết §9 float-format.
6. `goodput` **phẳng** (committed tx/finality, model không có trần capacity → không
   bão hòa); `tps` **dốc lên ∝ n** (decided-EVENT rate: mỗi node phát 1 `decided`
   → n record). goodput mới là throughput thật; tps là *misnomer/artifact* — tách
   thành hai figure để trung thực (F2). Nối thẳng câu tồn đọng từ M07.
</details>

## 6. Phòng thủ (câu hội đồng dễ hỏi về đúng phần này)

- **"Sao dùng Student-t chứ không phân phối chuẩn (z=1.96)?"** → Mẫu NHỎ (20 seed)
  + phương sai chưa biết → t bù độ bất định bằng đuôi dày hơn: `df=19 ⇒ t=2.093`,
  rộng hơn ~7%. Không có scipy — bảng critical-value nhúng sẵn, `df>30` mới rơi về
  normal. Neo: `src/output/analysis.py` docstring; `drafts/ch4_results.md` §4.2
  (statistical reliability).
- **"CI của gần hết metric ≈ 0 — có phải test/thu-thập lỗi?"** → Không: metric
  *structural* (overhead `2n`, tps, latency) là hàm tất định của `(protocol, n)`,
  **không** đụng cú rút workload ngẫu nhiên → 0 biến thiên qua seed → CI bề-rộng-0.
  Chỉ `goodput` phụ thuộc chuỗi tx Poisson (đổi theo seed) → `cv≈2.2%`, CI≈±1%. Cột
  `cv` cố ý phơi bày điều này. Neo: [[wiki/concepts/key-findings]] F2;
  `wiki/experiments/2026-06-08_baseline-cis.md` (T44).
- **"So latency giữa 3 giao thức có công bằng?"** → Dùng `commit_latency_ms` (đo
  tại COMMIT quorum, cùng nghĩa cả ba), KHÔNG `finality_latency_ms` (chỉ PBFT có
  thêm hop client-REPLY sau T70 finding #1 → lệch một-vòng, non-comparable). Neo:
  `wiki/concepts/output-format.md` §13 Revisions [2026-06-15].
- **"tps của PBFT/Snowman phồng theo n — có tô hồng không?"** → Ngược lại, đây là
  báo trung thực: tps là *decision-event rate* (mỗi node ghi `decided` → ∝ n),
  goodput (committed valid tx / finality) mới là throughput thật và nó *phẳng*. Cả
  hai lên figure tách biệt. Neo: `wiki/concepts/evaluation-metrics.md` §Goodput;
  F2.
- **"Làm sao biết hình trong luận văn đúng dữ liệu, không chỉnh tay?"** → Mọi
  CSV/figure là hàm **thuần** của CSV thô đã commit: `aggregate.write` +
  `metrics_view` byte-identical trên re-run, và test-gate
  `test_rebuild_matches_committed_artifact` / `test_write_is_byte_identical_on_rerun`
  chứng minh artifact-trên-đĩa = đúng cái code tái sinh. Không khâu tay nào chen vào.
  Neo: `src/output/aggregate.py` + `metrics_view.py` docstrings + tests.

## 7. Giải thích lại + ghi sổ

Giải thích cho tôi (Feynman) trong ~5 câu: *file long-format thô đi qua
`analysis.aggregate` thành wide `aggregated.csv` như thế nào, và vì sao chỉ
`goodput` có CI khác 0.* Rồi cập nhật `progress.md` dòng `13 · output-analysis`.

Câu mang sang **Module 14 (mock-defense)**: giờ đã đủ toàn cảnh — tầng lõi
(01–06) → giao thức (07–09) → chạy/sweep (10) → thí nghiệm B/C (11–12) → phân
tích (13). M14 gom **toàn bộ Phòng thủ còn nợ** (PBFT §6 M07, Casper §6 M08,
delay §6 M11, adversary §6 M12, + M13 ở trên) và **đọc-lại
`wiki/concepts/key-findings.md` F1–F10** với con số cụ thể, đóng cả hồ sơ.
