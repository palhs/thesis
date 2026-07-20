# Sổ theo dõi tiến độ

> Cập nhật ở bước 6 mỗi buổi. Điểm tự đánh giá 1–5 (1 = chưa thông, 5 = giải
> thích trôi chảy + trace được không cần nhìn code).

## Con trỏ phiên học (state — `/learn` đọc & ghi vào đây)

- **Module hiện tại:** 14 · mock-defense (★ buổi tổng — module CUỐI lộ trình)
- **Bước trong module:** 5 (Grill — VÒNG A đã mở; đã hỏi A1/A2/A3, ĐANG CHỜ người học trả lời để chấm)
- **Trạng thái:** đang học
- **Ghi chú nối tiếp (M14):** Guide đã sinh đủ 7 mục: §3 **bộ số neo** (baseline
  1000/5000ms · 94.8/79.6tps · overhead 2n/1.15n/2Kβ · W=480/guard5%/worst4.00% ·
  t=2.093 · f*=0.40/0.20@n10/0.33@n25 · conflicting=229 · Snowman 12.2–12.6s ≈12–13×),
  §5 mock defense **3 vòng** (A: số & F1–F10 nhanh · B: 20 câu Phòng thủ tồn đọng,
  quay ngược M12→M11→M08→M07 · C: 5 câu cấp-luận-văn C1 vì-sao-mô-phỏng / C2
  ba-trên-bốn-họ / C3 một-giao-thức-đại-diện-cả-họ / C4 đóng-góp-thật-sự / C5
  sửa-một-giới-hạn), §6 ngân hàng 20 PT rút gọn, §7 Feynman tổng 3 bài nói.
  Nguyên tắc xuyên buổi: **khai báo giới hạn trước khi bị hỏi; caveat = rào chắn
  phạm vi, không phải lỗ hổng ẩn**; câu mạnh nhất có dạng "Có, và em công khai điều
  đó — đây là chỗ nó được ghi". Nguồn đã nạp sẵn: key-findings F1–F10 + bảng
  RQ→finding, ch6_conclusion §6.2 (6 gạch limitations) + §6.3, §6 của guide
  07/08/11/12. **CẢNH BÁO đã nạp**: `SESSION-HANDOFF-2026-07-20-key-findings-audit.md`
  — F6 sai cả ba (cơ chế = proposer-lottery *không* phải stake-margin; luật =
  `(1−φ)²` không phải `(1−φ)`; metric = `success_rate` nhị phân "epoch 1 có
  finalise không" *không* phải sustained throughput → RQ2 phải trích
  `throughput_ratio`) và F8 headline "Snowman most delay-tolerant" **SAI**, mâu
  thuẫn F10 (đúng: PBFT #1 ở 1.0×, Snowman #2 ở 62× — inversion là *intra*-protocol
  "kiên nhẫn vô hạn: đức tính trước chậm, tử huyệt trước im lặng"); thêm 2 caveat
  chưa nằm ở tầng findings: dose asymmetry (`ref` FFG=0.1s ⇒ m=10 là đòn yếu 10×)
  và ô 62× bị clip **88.9%**. §3 bộ-số-neo của guide 14 vẫn chép headline F8 cũ —
  quay bằng BẢN ĐÃ SỬA. TIẾN ĐỘ VÒNG A: đã hỏi A1 (Snowman n=16 = 14.1× PBFT, vì
  sao) / A2 (CV=0 có phải bug) / A3 (F8 inversion — câu bẫy, chấm theo bản sửa).
  CHƯA làm: chấm A1–A3, 7 câu A còn lại, vòng B (20 câu), vòng C (5 câu), Feynman tổng.
- **Kế tiếp:** (không còn — M14 là module cuối; xong M14 là đóng lộ trình `learning/`)
- **Buổi gần nhất:** 2026-07-20 (Module 14 · mock-defense — mở buổi, sinh guide, đang ở bước 1)
- **Ghi chú cũ (M13 — đã xong):** M13 `output/` (tầng Phân tích) XONG — module đào-sâu
  đóng chặng dữ-liệu. Trục xương sống: đây là tầng đứng SAU file long-format thô
  (M11/M12 đẻ ra), kéo lên thành hình Ch4–5. NẮM CHẮC: **hai ranh-giới-reduce đừng
  lẫn** — per-trial (adapter M11/M12 `summarise.py`, 1 dòng/cell) vs across-seed
  (`output/aggregate`, 20 seed/scenario → 1 dòng wide). Chuỗi trách-nhiệm 5-file:
  **khai-báo** (`schema.py`: `ScenarioMeta` thẻ-căn-cước + `COLUMN_ORDER`, KHÔNG
  tính gì) → **điền** (reducer `summarise.py` + `csv.py`) → **gộp** (`analysis.py`:
  `aggregate()` group theo `run_id` → mean + `ci_half=t·sem`; `by_metric` pivot cho
  plot) → **ghi** (`aggregate.py` long→wide `aggregated.csv`) → **vẽ** (`plots.py`,
  matplotlib headless). Nhánh phụ `metrics_view.py` = chiếu pass-through verbatim
  string (T42, byte-identical, KHÔNG parse-format-lại). **Student-t + Wilson dạy
  từ đầu** (người học chưa học 2 distribution): CI = mean ± t·sem; std chia k−1
  (Bessel); sem=std/√k (thêm seed → √k → CI hẹp, muốn chắc gấp đôi phải ×4 seed);
  t nở-cho-mẫu-nhỏ (df=19→t=2.093, dùng z=1.96 sẽ hẹp giả 6.4%); Wilson cho tỉ-lệ
  0/1 (success_rate/ε), trung-thực-ở-biên (20/20→[0.839,1.0] không phải [1,1]).
  **CI≈0 KHÔNG bug**: metric structural (latency/tps/overhead) tất định theo
  (protocol,n) → cùng/khác seed y hệt → std=0 → CI bề-rộng-0; CHỈ `goodput` phụ
  thuộc chuỗi tx Poisson theo seed (cv≈2.27%). Byte-identical tầng phân tích: CẢ
  output/ là hàm THUẦN của CSV thô (0 RNG/0 wallclock — ngẫu nhiên chết ở thượng
  nguồn simulator); ngoại lệ tinh: figure PDF không byte-hệt do matplotlib nhét
  CreationDate → "PDF tracked, PNG regenerable", cái tất-định là NỘI DUNG số không
  phải byte-file. ĐÃ CHẠY CHẤM: `make test-output` (2 FAIL ở `test_explain.py` —
  casper-ffg n=4 theory-vs-measured lệch 14.6%, NGOÀI phạm vi M13); ba file M13
  `test_aggregate/test_metrics/test_metrics_view` 33/33 xanh qua
  `PYTHONPATH=src python3 -m unittest tests.output.*` (pytest bị path-collision
  `tests/output/__init__.py`→dùng unittest hoặc make). Grill G1–G6 tự-lực phần lớn:
  G1 group-run_id-không-pool (đúng); G2 CI hai-phía + identical→ci_half=0 (đúng
  mean, học công thức tại chỗ); G3 k=1→else-branch std=sem=ci_half=0 né chia-0
  (suýt, nói "âm" thực ra =0); G4 unbudgeted→KeyError fail-fast KHÔNG NaN (suýt,
  đoán NaN → dạy NaN=thiếu-hợp-lệ vs exception=lỗi-phải-sửa); G5 pass-through byte
  + test_round_trip_fidelity gãy nếu reformat (đúng, số thật commit_latency .9f
  `5000.000001000`≠.6f); G6 goodput phẳng 94.82 vs tps dốc 3.8→23.75∝n artifact
  (đúng, đóng câu M07). **Phòng thủ §6 (5/5) luyện NGAY trong buổi** (Student-t,
  CI≈0, commit-vs-finality-latency, tps-artifact, byte-identical) → M13 KHÔNG nợ.
- **Ghi chú cũ (M10):** M10 `common/`+`workload/` XONG (bản FAST-LANE theo yêu cầu người học đang gấp; guide `10-runner-sweep.md` đã sinh, bỏ đào-sâu + bỏ Phòng thủ, dồn reproducibility). Nắm chắc: HAI cửa ngõ — `run_to_completion(handle, t_max)` (một run, `t_max=None`→**quiescence**=hết-việc-hàng-đợi-rỗng hợp PBFT-honest, `t_max=<float>`→**deadline**=hết-giờ bắt-buộc cho Casper/Snowman vì chúng chạy vô tận không tự dừng) và `run_grid` (cả lưới). BỐN TRỤ byte-identical: (1) `run_cell` thuần no-wallclock-no-cross-cell; (2) sidecar vân tay, resume CHỈ khi schema+commit_hash+param_fingerprint đều khớp; (3) commit_hash resolve MỘT lần ở cha (worker tự resolve→bẩn cây giữa sweep→lẫn dòng dirty), cây git bẩn→resume vô hiệu; (4) collect=sort theo cell_key áp lại thứ tự toàn phần độc-lập-thứ-tự-worker. Câu thần chú: cell-thuần(base)+collect-sort(step)⇒induction-over-the-grid. Workload: một RNG blake2b `"workload:"+seed` rút THEO THỨ TỰ, mỗi cell ốc-đảo (constant KHÔNG rút RNG=round(rate×interval); poisson rút=Knuth). Đã CHẠY CHẤM: test_runner (t_max_none_quiescence ‖ t_max_float_deadline tách biệt, byte_identical), test_generator (constant_is_exact vs poisson_mean_in_tolerance, same/different-seed), test_sweep jobs=1 (CollectOrder/ResumeSkip/StaleGuards/NoTimingLeak). LƯU Ý sandbox: test_sweep có class jobs>1 (JobsEquivalence/Tiered/JobsClamp/WorkerException) — TREO trong sandbox, né; chỉ chạy class jobs=1. Mở Module 11 `delay/` (Họ B) — module ĐÀO SÂU (CÓ Phòng thủ trở lại), *ai gọi* run_grid: adapter delay, cell=`(protocol,timeline,n,seed)`, run_cell=`runner→clip→row`. Guide `11-delay-family-b.md` chưa sinh (⏳). CÒN NỢ: Phòng thủ PBFT PT1–PT5 (M07) + Casper PT1–PT5 (M08) → dồn `14-mock-defense`. ĐẾN HẠN vẫn treo: đọc-lại `wiki/concepts/key-findings.md` (F1–F10).
- **Ghi chú cũ (M09):** M09 `snowman/` (Snowman/Avalanche) XONG — giao thức đào sâu thứ BA, đóng chặng giao thức. Nắm chắc: **no-quorum** (mỗi vòng chỉ hỏi K peer, khuếch đại metastability → hội tụ); **hai bộ đếm TÁCH BIỆT** — confidence[b] (α_p nuôi, tích lũy đơn điệu, → preference=argmax, quyết *hướng*) vs counter (α_c nuôi, α_c-liên-tiếp trên preference, → ACCEPT tại β, quyết *chốt*); counter CHỈ đo `agree[preference]` nên α_c của kẻ-không-phải-preference bị vứt; audit #5 = Snowball (argmax-confidence, flip khi *strictly exceed*, tie giữ đương kim) ≠ Snowflake (flip theo majority-vòng); biên safety `ε≤(1−α_c/K)^β` (cơ số α_c/K, mũ β) — công thức đóng từ Ava docs `[ava-docs]`, Theorem 4 (raw/avalanche.pdf) chỉ cho *tồn tại* cận; rescale `K=min(20,n−1)`; n=4 degenerate (α_c=K, unanimity, LOẠI khỏi bảng RQ). Mở Module 10 `common/`+`workload/` — module ĐỌC-GIAO-DIỆN (bỏ Phòng thủ, NHẤN reproducibility của sweep). Guide `10-runner-sweep.md` chưa sinh (⏳) — sinh đúng lúc. LƯU Ý sandbox: sweep `jobs>1` TREO trong Claude Code sandbox → chỉ chạy `jobs=1` in-sandbox. CÒN NỢ: Phòng thủ PBFT PT1–PT5 (M07) + Casper PT1–PT5 (M08) chưa luyện thành lời → dồn `14-mock-defense` (Snowman PT1–PT5 ĐÃ luyện buổi này, không nợ). ĐẾN HẠN: đọc-lại `wiki/concepts/key-findings.md` (F1–F10) giờ M09 xong.
- **Ghi chú cũ (M07):** Chặng 2 khởi động — M07 `pbft/` XONG (đỉnh chặng 2 đạt: PBFT n=4 thật → 4 record `decided` → CSV, qua `build_run` trọn 5 tầng). Mở Module 08 `pos/` (Casper FFG) — giao thức ĐÀO SÂU thứ hai, module accountable-safety/slashing. Guide `08-casper-ffg.md` chưa sinh (⏳) — sinh đúng lúc, CÓ mục Phòng thủ. Khuôn giao thức (roles.md §Bài-báo-gốc): định vị đúng điều kiện SLASHING trong PDF `raw/` (Casper: hai slashing condition — no-double-vote + no-surround-vote) làm điểm gai, trích chương-câu, KHÔNG cày cả bài; proxy: `resources/*_DeepDive.md` + `wiki/algorithms/` + `wiki/sources/`. Câu mang từ M07: PBFT là baseline "an toàn ngay lập tức, quorum 2f+1, view-change O(n³) đắt"; đối chiếu Casper — finality *chậm hơn* (2 epoch) nhưng có *accountable safety* (chứng minh được AI vi phạm để phạt), khác hẳn PBFT (an toàn nhưng không quy-trách-nhiệm cá nhân). CÒN NỢ M07: chưa luyện mục Phòng thủ PBFT (PT1–PT5 trong guide 07 §6) — để dành cho buổi ôn `14-mock-defense`.

## Bảng tiến độ

| Module | Ngày học | Điểm grill (1–5) | Đã thông | Còn mờ / câu hỏi mở |
|--------|----------|------------------|----------|---------------------|
| 00 · architecture | 2026-06-29 | 4 | Spine RQ1–5; tps(decided/window, misnomer)≠goodput(committed_tx/window); 3-family map + 3 sợi chỉ cơ chế (leader+view-change / slashing-accountable / subsampling); B(network)≠C(adversary); BLS gộp chữ ký O(n)→O(1) bytes | Con số từng F (để re-read sau Module 09); α_c/β chính xác của Snowman; cơ chế tps∝n đọc thẳng summarise.py |
| 01 · scheduler | 2026-07-03 | 4 | Vòng `run()` (deadline→quiescence→pop→tombstone-nếu-TimerFire→sink→dispatch→predicate); `(t,node_id,seq)` = thứ tự toàn phần tất định (t=khi nào, node_id=phá hòa chéo-node, seq=phá hòa trong-node + số phiên bản timer); lazy tombstone (cancel/re-register O(1), heap tự dọn khi pop, so seq-heap vs registry); 3 Event → 3 handler (Delivery→on_message, TimerFire→on_timer, PhaseAdvance→advance_phase, node_id=−1); replay y hệt = input tất định (seed→net_rng) + thứ tự xử lý tất định (heap key) | Đã chạy chấm 2 test (re-register fire-once, deadline overshoot-by-one) — đều khớp dự đoán. Còn nhẹ: split-bind phía node (→M02); phase timeline map với synchrony test do experiment-matrix quyết (→M10) |
| 02 · nodes | 2026-07-05 | 4 | Two-layer (shared lifecycle + FSM per-protocol); template method (public có guard lifecycle → ủy quyền `_on_*` do subclass cài; `Node(ABC)` không tạo được, `TypeError`); split-bind (Scheduler tiêm timer/cancel/emit, Network tiêm send/broadcast; lambda closure ôm sẵn `node.id`); halt idempotent (reason đầu thắng, chống blanket RUN_END xóa lịch sử); bẫy `nan` (isfinite trước `<0`); virtual-time = cộng-số-không-đợi-thật, latency = hiệu tọa độ `t` | 6/6 grill đã chạy chấm (sai #1 abstract; bắt được lỗi giảng sai của tôi ở #5 — guard loại-trừ-nhau, drop do `status=HALTED` chứ không do thứ tự `if`). Còn nhẹ: khe `self.adversary` (opaque, →M12); FSM cross-instance state mỗi protocol (→M07–09) |
| 03 · network | 2026-07-05 | 4 | Đường ống 5 bước `_try_deliver` (resolve→drop coin→partition→delay→schedule) + kế toán RNG "xé vé" (drop coin luôn xé 1 tờ kể cả p_drop=0; partition tất định không xé; thứ tự drop-trước-partition ghim để đổi topology không lệch RNG); Delivery = entry heap `(t_sent+delay, dst, seq)`, pop→`_on_message`; delay đông cứng lúc submit (`phases[_phase_idx]` đọc tại submit, advance_phase không hồi-tố); `net_rng` blake2b network-scoped ≠ RNG per-node; PhaseAdvance node_id=−1 sort-first hiện thực half-open `[t_start,t_end)`; Network=hạ tầng *trung thực* (B) ≠ adversary tầng Node (C); 3 dataclass init ở `config/loader.py` (production) từ YAML, kiểm 2 tầng (`__post_init__`/`validate_timeline`) trước t=0 | Câu #3 grill đảo dấu kết luận `sorted` (nhớ cơ chế, sai chiều — sorted *chống* đổi); lý do "honest infrastructure" ban đầu chưa nói được (đã vá: quy-trách-nhiệm sạch + tái dùng nền + khớp giả định BFT) |
| 04 · event-log | 2026-07-05 | 4 | event_sink = con trỏ hàm (`logger.sink`) gán phase 4 → loose coupling; hai chỗ gọi→hai shape (emit tuple `("emit",type,fields)` seq=−1 / typed transport `Delivery`/`TimerFire`/`PhaseAdvance` seq thật, Phase node_id=−1); `sink` phân loại: emit soi *cấu trúc* (tuple+len3+[0]=="emit"), transport soi *kiểu*, else fail-fast (no silent drop); 5 hằng event-type; EventRecord frozen 5 trường, 4 scalar đóng cứng + `fields` mở (extensibility, phục vụ T28+); logger THỤ ĐỘNG (no sched ref/file handle/RNG)⇒reproducibility; hai chân determinism (thứ tự record=dispatch + sorted-key `repr`); copy-in (`dict(fields)`) bảo vệ chiều vào; một dòng CSV Delivery thành hình (đóng câu mang từ M03) | Feynman #2 đảo thứ tự nhẹ (tưởng buffer *rồi* check *rồi* sort — thực ra check ở `sink`/cửa vào, sort ở `to_csv`/cửa ra); H5 sót `decided` ở PingPong (node emit_decided *rồi mới* halt) — đã vá; `repr` vs `json` (giữ tuple) là loose, chưa cần thuộc |
| 05 · config | 2026-07-06 | 4 | Ranh giới loader(text→`Config`, thuần validate, không seed)/factory(`Config`+seed+node_factory→`RunHandle`, dựng); `Config` frozen = mắt xích tái lập; 6-phase bootstrap + vì sao phase5(`network.start`) trước phase6(`node.start`) — node broadcast lúc start, mạng chưa mở→`_guard_started` RuntimeError; single seed surface (1 int→blake2b→net_rng + per-Node rng, scheduler no RNG, blake2b vì `hash()` random/tiến-trình); dependency injection `node_factory` (build_run mù protocol); cặp SameSeed(bắt nhiễu)/Divergence(bắt seed-chết) kẹp nhau; 4 cổng cross-field (n∈[1,10000]/t_max hữu hạn dương/n_runs≥1/partition NodeId∈range(n)); 3 khoang opaque adversary(T18)/protocol_knobs(T28+)/workload(T41)—đóng khe `self.adversary` M02 | byte-identical vs "tương đương thống kê" ban đầu chỉ nói "audit", chưa bật lý do phân-biệt-regression-vs-trôi (đã vá); opaque round-trip: đoán key sai (gộp value làm key) — round-trip verbatim GIỮ cả `strategy`+`fraction` |
| 06 · trace end-to-end | 2026-07-06 | 4 | Đường ống trọn 5 tầng lõi qua harness thật `build_and_run` (6-phase bootstrap tường minh); ping-pong n=4 seed=42 delay-hằng=10 → 12 Delivery (`n·(n−1)`) cùng t=10, quiescence, events_processed=12; entry heap Delivery=`(t,dst,seq)` ⇒ record `node_id=dst` (src nằm trong fields); `sink` hai `isinstance` lọc event-heap, `("emit",…)` tuple trần rớt cả hai; ordering scramble `fired[0]=(100,0,'early1')` phơi cả 3 trường tie-break; byte-identical CSV cùng seed / phân kỳ khác seed ở quy mô 5 tầng; `_dispatch` rẽ HAI nhánh `_on_message` ‖ `event_sink` | event_type là chuỗi thường `"delivery"` KHÔNG phải `"decided"` (giả BroadcastNode không decide→M07) và không phải tên lớp; seq đánh số từ 1 không phải 0; broadcast là API *outbound* (inbound=`_on_message`) — hai slip thuật ngữ đã vá |
| 07 · pbft | 2026-07-06 | 4 | Mô hình `(view,seq)` = tọa độ một cuộc đồng thuận đơn (seq=khe/mục-tiêu-chốt-1-lần, view=lần-thử/đổi-khi-leader-hỏng; lưới 2D, đi-ngang=seq mới ở `_propose` chỉ primary, đi-dọc=leo 4-bậc FSM); dẫn xuất `3f+1` từ HAI ràng buộc đánh nhau (chốt-khi-f-im: quorum≤n−f; giao-2-quorum≥f+1-trung-thực: 2q−n≥f+1 ⇒ ghép ra n≥3f+1, q=2f+1); FSM IDLE→PRE_PREPARED→PREPARED→COMMITTED, mỗi bậc 1 quorum `2f+1`; Decision B (mọi replica tự-broadcast+tự-ghi phiếu vì Network.broadcast loại sender); Decision C phiếu-đếm-lùi (`setdefault` tạo ô rỗng, `matching_*`=0 khi digest None, PRE-PREPARE điền digest→0 nhảy lên khớp→cascade); Decision G `decided` khoá theo *seq* không *(view,seq)* (`_decided_seqs`); digest-binding Rule5 = biến "đồng thuận trên digest" thành "trên payload" (vote bằng digest 32B để rẻ băng thông O(n²)); `tps=len(decided)/now` ∝ n (decided phát per-node → misnomer; goodput đếm instance phân biệt mới đúng); evidence-boundary (sim không chữ ký, VIEW-CHANGE evidence = assertion trần, safety-chống-forge giả-định-by-construction, adversary catalog cố ý bỏ forge-evidence; KHÔNG đụng honest-correctness/liveness/equivocating-*primary*) | CHƯA luyện Phòng thủ PBFT (PT1–PT5 §6) → dồn `14-mock-defense`; con số F1–F10 vẫn để dành SAU M09; nhánh view-change (f+1 catch-up, backoff 2^view, reissue/compute_reissue) mới trace Scenario B ở mức pass, chưa grill sâu |
| 08 · casper-ffg | 2026-07-07 | 4 | Two-round justify→finalise (link `<S,T>` làm HAI việc: justify T + finalise S nếu T=S+1 & S đang JUSTIFIED; `decided` bắn lúc FINALISED, khoá `decided_epochs`, chậm hơn justify một link); ngưỡng ⅔ cân **stake** không đếm node (chống-Sybil: node ID rẻ, stake khoá tiền thật) + `3·stake≥2·total` division-free (tránh rounding float); hai điều răn slashing = hai cơ chế TÁCH BIỆT (double-vote: `record_vote` so bộ ba `(src_epoch,src_hash,tgt_hash)` cùng-target-epoch → DUPLICATE trùng-khít vô hại vs CONFLICT khác→slash, stake KHÔNG re-count; surround: `_check_surround` chéo-epoch vs toàn `vote_history`, hai-vế-OR `s1<s2<t2<t1 or s2<s1<t1<t2` để thứ-tự-đến không ảnh hưởng kết tội); accountable safety = định danh+đốt cọc (khác PBFT thủ phạm vô danh; ≥⅓ stake giao hai link mâu thuẫn ⇒ lộ mặt); surround-attack cụ thể = revert checkpoint đã-finalised bằng link RỘNG nhảy trùm cam kết HẸP (double-spend, không dính double-vote vì khác target height); sim `slots_per_epoch=2` = tối thiểu giữ slot/epoch distinction; goodput Casper = `n_epochs×slots_per_epoch` (finalise 1 epoch chốt nhiều block ⇒ phải chuẩn hoá mới so PBFT); tx mock = `workload/generator` byte blake2b đúng size, tất định, rỗng-ngữ-nghĩa | (a) Phòng thủ Casper PT1–PT5 (§6) chưa luyện thành lời → `14-mock-defense`; (b) hai lỗ Feynman: stake vì chống-Sybil (ban đầu chỉ nói tránh-float), sim **detect-only** không đốt cọc + finality-chậm là điểm yếu (ban đầu nói "xử phạt" — overclaim); (c) α_c/β/ε của finality xác suất để dành M09 |
| 09 · snowman | 2026-07-08 | 4 | No-quorum + metastability (khuếch đại đa số nhỏ→áp đảo); hai bộ đếm tách biệt confidence(α_p→preference→*hướng*)/counter(α_c→ACCEPT tại β→*chốt*), counter chỉ đo agree[preference]; audit#5 Snowball argmax-confidence flip-khi-strictly-exceed ≠ Snowflake; ε≤(1−α_c/K)^β (cơ số α_c/K, mũ β) công thức=Ava docs / Theorem 4=chỉ tồn-tại-cận; rescale K=min(20,n−1); reproducibility (cùng seed→byte hệt); PT1–PT5 luyện xong | G1 sai α_c (quên ceil→int) + α_p n=4 (⌊3/2⌋+1=2); "15 là **sàn**, baseline đạt sàn" (nói "tối thiểu" chưa chuẩn cho singleton); G5 khác-seed lộ ở **thứ tự** peers không phải thành viên (K=n−1 buộc cả tập); slip thuật ngữ cần tránh: "Snowman KHÔNG có quorum" |
| 10 · runner-sweep | 2026-07-08 | 4 | (FAST-LANE, module đọc-giao-diện) HAI cửa ngõ `run_to_completion`(một run; `t_max=None`→quiescence=hết-việc / `<float>`→deadline=hết-giờ) + `run_grid`(cả lưới); BỐN TRỤ byte-identical: run_cell-thuần / sidecar-vân-tay-resume-3-khớp / commit_hash-1-lần-ở-cha (bẩn-cây→tính-lại) / collect-sort-cell_key-áp-thứ-tự-toàn-phần; induction-over-the-grid = cell-thuần(base)+collect-sort(step); workload 1 RNG blake2b theo-thứ-tự mỗi cell ốc-đảo (constant no-RNG / poisson Knuth); jobs chỉ đổi THỨ TỰ chạy không đổi nội dung; đã chạy chấm runner+generator+sweep(jobs=1) | **H1 hiểu NGƯỢC lúc đầu**: tưởng quiescence là "timeout" — thực ra quiescence=hết-VIỆC (hàng đợi rỗng, giao thức tự dừng) ≠ deadline=hết-GIỜ (cưỡng bức); Snowman/Casper cần t_max vì chạy vô tận không tự quiesce — điểm này PHẢI ghim cho mock-defense; H3 ban đầu sót nửa-sau (chèn cell khác KHÔNG đổi batch vì mỗi cell seed độc lập); cần visual mới vỡ ra (module hơi thiếu-context nếu chỉ đọc chay) |
| 11 · delay (Họ B) | 2026-07-08 | 3.5 | **clip.py xuất sắc (tự lực 9/9)**: MỘT luật data `t≤W` cho mọi event + lớp ghi-sổ kept/tail/late chỉ dán lên decided; A(data→mọi cột metric)≠B(stats→chỉ `clipped_fraction`+guard); tail vs late xét first-decision so W+one_round; guard 5%=biên-lai không-phải-metric; bug clip +10% vá trước commit không lọt report | Feynman yếu 3 mảnh (ôn đầu M12): (1) không vẽ được đường ống 1 cell; (2) window-denom đúng kết-luận sai cơ-chế (HAI t_max: run()-stop=528 chung vs meta.t_max=480 field; khác ở reducer chọn chia gì); (3) adapter điền BA HÀM THUẦN không phải timelines/commit_hash. HAI cặp số hay lẫn (đồng-hồ 528/480 vs ngưỡng-clip W/W+one_round) |
| 12 · adversary (Họ C) | 2026-07-08 | 4 | Họ C khác Họ B ĐÚNG hai chỗ: config (thêm trục f/m) + runners (tiêm adversary). HAI PARADIGM TIÊM: network-wrap (delay/offline, `_wrap_outbound` chung, tráo `send/broadcast` SAU build, FSM sạch tuyệt đối; delay shift `t+=mult·ref`, offline drop) vs node-subclass (equivocate, override method phát-nội-dung LÚC build vì phải fork *nội dung* — seam wrap chỉ đổi thời-điểm/có-không, không chế được payload thứ 2). ĐẢO CHIỀU CHỌN TẬP: `slow_node_ids`=high-id chừa primary (liveness attack, mọi f<1⇒k<n⇒node0 an toàn) vs `byzantine_node_ids`=low-id ôm primary (safety attack cần primary+proposer trong tập ác). mult chỉ ở DelayProfile vì delay *dosed* (f=bao-nhiêu-kẻ, m=mỗi-kẻ-mạnh-cỡ-nào); offline/equivocate nhị phân. **PARITY CRUX (tự lực rất tốt)**: n10 b=4 fork (A gom {4,6,8}+{0,1,2,3}=7, B gom {5,7,9}+byz=7)/b=3 không (chỉ B đạt 7); contiguous-split fail (honest dồn 1 phía); điều kiện fork `b>f_tol`; parity=hàm thuần(n,id) không RNG; **người học tự bật "primary chẻ đôi sự thật, honest là nạn nhân không thấy hộp thư nhau"**. Byte-identical: shift/drop/parity đều tất định → 0 RNG adversary → replay hệt → safety signal SEED-INVARIANT (f_max=bracket không cần CI). Đường ống 1 cell: cổng-fingerprint→[runner→clip→reducer→_build_row]→sidecar→collect-sort→post-pass(finality_delay_ratio cross-cell)→csv; `_run_cell` THUẦN (no wall-clock/no cross-cell). Adapter=3 hàm `_run_cell/_cell_key/_param_fingerprint` (f,m vào fingerprint, seed=identity); commit_hash=run_constants resolve-1-lần-cha (KHÔNG phải hàm adapter). clip+reducer+window-denom-fix IMPORT THẲNG từ delay/. 3 POSTURE (F7–F10/RQ4): delay PBFT≈FFG miễn-nhiễm≪Snowman nổ 49–62× (poll tuần tự β=15); offline PBFT vách sạch f*=0.40 / FFG mượt (1−f) / Snowman vách αc DƯỚI ⅓ n-dependent (0.20@n10/0.33@n25, slack K−αc); equivocate PBFT fork(b>f_tol,conflicting=229)/FFG accountable(detect+slash, links bỏ target_hash)/Snowman kháng. Finding RQ4: no-dominance, thứ hạng ĐẢO khi đổi adversary. Chạy chấm: test_equivocate+test_determinism 16/16, test_runners+test_safety 15/15 | Bù tại buổi: (1) delay PBFT là *miễn nhiễm* không phải "chậm vừa" (đoán FFG<PBFT<Snow — sai chỗ PBFT); (2) FFG-accountable ở equivocate chưa nêu (chỉ nói PBFT-safety/Snowman-liveness); (3) dòng offline bỏ trống; (4) đường ống rơi 2 trạm (reducer/_build_row + collect-sort/post-pass) & đặt fingerprint nhầm thành "trạm" thay vì "cổng gác resume". CÒN NỢ: Phòng thủ PT1–PT5 §6 CHƯA luyện thành lời → dồn `14-mock-defense`. Điểm mạnh nổi bật: parity crux tự-lực + tự bật insight "leader chẻ đôi sự thật" |
| 13 · output-analysis | 2026-07-19 | 4 | Hai ranh-giới-reduce (per-trial adapter M11/M12 vs across-seed output/aggregate); chuỗi trách-nhiệm 5-file khai-báo(schema)→điền(reducer+csv)→gộp(analysis)→ghi(aggregate)→vẽ(plots); long(20 dòng/scenario, substrate append-được)↔wide(1 dòng, mean±CI feed plot); **Student-t** CI=mean±t·sem (std÷k−1 Bessel, sem=std/√k, df=19→t=2.093, z=1.96 hẹp giả 6.4%, ×4 seed để chắc gấp đôi) + **Wilson** cho tỉ-lệ trung-thực-ở-biên; CI≈0 không-bug (structural tất-định theo (protocol,n), chỉ goodput cv≈2.27% do Poisson-theo-seed); byte-identical tầng phân-tích (output/ hàm thuần, RNG chết ở thượng-nguồn; PDF metadata caveat); group theo run_id không-pool; k=1→else-branch né chia-0; bytes_per_acu unbudgeted→KeyError fail-fast (NaN=thiếu-hợp-lệ vs exception=lỗi); metrics_view pass-through verbatim byte-hệt; tps∝n artifact vs goodput phẳng (đóng M07). Grill 6/6 chạy chấm 33/33. **Phòng thủ 5/5 luyện trong buổi** | Đã học Student-t/Wilson từ ĐẦU tại buổi (chưa từng học 2 distribution) — cần ôn lại công thức khi vào M14; G3 nói "mẫu số âm" (thực ra =0); G4 đoán NaN (thực ra KeyError). ĐẾN HẠN treo: key-findings F1–F10 số cụ thể |
| 14 · mock-defense | | | | |

## Nhật ký buổi học

<!-- Mỗi buổi 1 mục. Ví dụ:
### [2026-06-25] Module 01 · scheduler
- Thông: vòng lặp run(), thứ tự 3 điều kiện dừng, lazy-tombstone.
- Mờ: vì sao seq per-node đủ để không bao giờ so sánh tới phần tử event.
- Theo dõi tiếp: xem lại khi học set_timer trong nodes.
-->

### [2026-07-19] Module 13 · output-analysis (đào-sâu · tầng Phân tích · đóng chặng dữ-liệu)
- Thông: mở đầu bằng khung "đây là tầng ĐỨNG SAU file long-format thô (M11/M12 đẻ
  ra), kéo lên thành hình Ch4–5". Chốt **hai ranh-giới-reduce đừng lẫn**: per-trial
  (adapter `summarise.py`, 1 dòng/cell) vs across-seed (`output/aggregate`, 20 seed
  → 1 dòng wide). Dựng **chuỗi trách-nhiệm 5-file** (người học tự tổng hợp gần đúng ở
  Feynman): khai-báo(`schema.py`, KHÔNG tính)→điền(reducer+`csv.py`)→gộp(`analysis.py`)
  →ghi(`aggregate.py`)→vẽ(`plots.py`); nhánh phụ `metrics_view` pass-through. Minh
  hoạ bằng **DỮ LIỆU THẬT** `pbft-n7`: long 20 dòng-seed (latency/tps/overhead y hệt
  mọi seed, chỉ goodput nhảy) → wide 1 dòng (commit_latency cv=0 CI[x,x] vs goodput
  94.82±1.01). 
- Cách học: người học YÊU CẦU trích thẳng wiki (output-format §2 pipeline + §13
  latency Revisions + evaluation-metrics tps/goodput) — làm luôn. **Dạy Student-t +
  Wilson TỪ ĐẦU** (người học chưa từng học 2 distribution, xin ví dụ số trực quan):
  ráp CI=mean±t·sem trên đúng 20 goodput thật của pbft-n7 → khớp aggregated.csv
  [93.81,95.83]; so z=1.96 hẹp giả 6.4%; Wilson 20/20→[0.839,1.0]. Grill G1–G6 CHẠY
  THẬT chấm: G1 pool-vs-run_id trên FFG-n4 (n_runs 20 vs 40 bịa cỡ mẫu); G2
  [8..12]→CI hai-phía + [10×5]→ci_half=0; G3 k=1→else-branch; G4 unbudgeted→KeyError;
  G5 reformat .9f→.6f khác byte; G6 tps 3.8→23.75∝n vs goodput phẳng 94.82. Ba file
  test M13 33/33 xanh (unittest; pytest path-collision). LƯU Ý: `make test-output` có
  2 FAIL ở `test_explain.py` (casper-ffg n=4 theory-vs-measured 14.6%) — NGOÀI phạm
  vi M13, ghi Backlog-cá-nhân nếu cần.
- Vấp (nhẹ, đã vá tại buổi): (1) "chịu" ở câu file-nào-hàm-thuần → dạy CẢ output/ là
  hàm thuần (RNG chết thượng-nguồn) + caveat PDF-metadata; (2) G3 nói "mẫu số âm"
  (thực ra k−1=0, code né bằng nhánh else); (3) G4 đoán NaN (thực ra KeyError; NaN=
  thiếu-hợp-lệ vs exception=lỗi-phải-sửa); (4) Feynman gọi goodput "data ngẫu nhiên"
  → siết thành "phụ thuộc chuỗi tx Poisson theo seed". Điểm mạnh: G1/G2(mean)/G5/G6
  tự-lực chắc; hỏi rất đúng chỗ (xin ví dụ số cho distribution, hỏi ranh-giới schema
  vs analysis).
- Mờ/để dành: công thức Student-t/Wilson mới học — ôn lại đầu M14. **Phòng thủ §6
  (5/5) đã luyện NGAY trong buổi** (Student-t, CI≈0, commit-latency, tps-artifact,
  byte-identical) → M13 KHÔNG dồn nợ. Câu mang sang **M14 (mock-defense, ★ buổi
  tổng)**: gom Phòng thủ còn nợ M07/M08/M11/M12 + đọc-lại key-findings F1–F10 với con
  số cụ thể — đóng cả hồ sơ, toàn cảnh lõi→giao-thức→sweep→thí-nghiệm→phân-tích đã đủ.

### [2026-07-08] Module 12 · adversary Họ C (đào-sâu · đối-thủ-chủ-đích · đóng phần sinh-số-liệu)
- Thông: mở đầu bằng câu chốt "Họ C khác Họ B đúng HAI chỗ: config (trục f/m) +
  runners (tiêm adversary)". Dựng **hai paradigm tiêm**: network-wrap (delay/offline
  qua `_wrap_outbound` chung, tráo send/broadcast SAU build, FSM sạch; delay shift
  `t+=mult·ref`, offline drop) vs node-subclass (equivocate override method phát-nội
  -dung LÚC build — vì seam wrap chỉ đổi thời-điểm/có-không, KHÔNG chế được payload
  thứ 2 mâu thuẫn). Đảo-chiều chọn tập (slow=high-id chừa primary / byzantine=low-id
  ôm primary) gắn với liveness-vs-safety. mult chỉ ở DelayProfile (delay dosed; offline
  /equivocate nhị phân). **PARITY CRUX làm rất tốt, phần lớn tự lực**: trace n10 b=4
  fork (A={4,6,8}+byz=7, B={5,7,9}+byz=7) vs b=3 không-fork (chỉ B=7), contiguous-split
  fail (honest dồn 1 phía), điều kiện `b>f_tol`. Người học **tự bật ra** insight cốt
  lõi "primary chẻ đôi sự thật, honest là nạn nhân trung thực, không thấy hộp thư
  nhau". Ôn xong 3 mảnh mờ M11: đường ống 1 cell (cổng-fingerprint→[runner→clip→
  reducer→_build_row]→sidecar→sort→post-pass→csv), adapter=3 hàm thuần (không phải
  timelines/commit_hash), window-denom (2 t_max). Grill G5 3-posture + finding RQ4
  "no-dominance, hạng đảo khi đổi adversary".
- Cách học: chọn "theo thứ tự guide" rồi rẽ vào parity crux trước theo ý thích. Chạy
  chấm THẬT: test_equivocate+test_determinism 16/16 (đóng parity + byte-identical),
  test_runners+test_safety 15/15 (posture + fork-detect). Guide 12 sinh đúng lúc, CÓ
  Phòng thủ PT1–PT5.
- Vấp (bù tại buổi): (1) delay-PBFT đoán "chậm vừa" → thực ra *miễn nhiễm* (slow≤f_tol,
  7 node nhanh tự đủ quorum); (2) equivocate bỏ sót FFG-accountable (chỉ nêu PBFT-fork/
  Snowman-resist); (3) dòng offline để trống (Snowman vách αc DƯỚI ⅓ n-dependent); (4)
  đường ống rơi 2 trạm (reducer/_build_row + collect-sort/post-pass) và đặt fingerprint
  nhầm thành "trạm" thay vì "cổng gác resume". Người học hỏi rất đúng cuối buổi: "PBFT
  sao miễn nhiễm delay, nếu không đủ quorum thì sao?" → dạy điều kiện `n−k≥7⇒k≤3⇒f≤0.30`
  = biên sweep; f cao hơn thì stall thật; Snowman không hưởng vì poll lấy-mẫu-K phải đợi.
- Mờ/để dành: Phòng thủ PT1–PT5 §6 M12 (chừa-vs-ôm primary, parity không-engineer,
  byte-identical seed-invariant, cross-⅓-để-đo, FFG-model-artifact, Snowman-timeout)
  chưa luyện thành lời → dồn `14-mock-defense` cùng nợ M07/M08/M11. Câu mang sang M13
  (`output/`): từ "CSV thô mỗi dòng 1 cell" lên "reduce/aggregate/CI/plot → hình Ch4–5".

### [2026-07-08] Module 11 · delay Họ B (đào-sâu · mở chặng 5 "Thí nghiệm" · "ai gọi run_grid")
- Thông (rất chắc, tự lực): **clip.py** — mổ sâu theo yêu cầu người học ("chưa hiểu
  luật clip decided/delivery"). Chốt bằng mô hình **A ≠ B**: MỘT luật DATA (`t≤W`,
  decided/delivery/timer như nhau) + MỘT lớp GHI-SỔ chỉ dán lên decided
  (kept/tail/late). Data (A) nuôi mọi cột metric thật (latency/tps/goodput/overhead/
  safety); stats (B) chỉ nuôi 1 cột biên-lai `clipped_fraction` + guard <5%, KHÔNG
  trộn vào A → `clipped_fraction` cao chỉ *cảnh báo* chứ không *bóp méo* số. tail vs
  late: xét **first-decision của instance** so `scope_bound=W+one_round` (người học
  tự truy đúng "dùng W hay W+B?" → dạy: mẫu-số giới-hạn-bởi-105, W=100 chia kept/
  tail). Grill G1–G3 clip 9/9 tự lực; câu đố biên (delivery t=99 sống + decided
  t=110 late) đoán đúng cả hai vế A/B, chạy `test_in_window_delivery_kept_when_
  instance_late` khớp. Người học hỏi rất đúng chỗ: (a) "bug clip có lọt report
  không?" → kiểm delay.csv commit 2ef410f7, PBFT overhead=19.80/49.99=đúng 2n → vá
  TRƯỚC commit, không lọt; bug chỉ chạm tử-số-overhead không chạm latency/safety →
  F3 miễn nhiễm; zero-delay baseline làm *control* bắt artifact; (b) "A/B ảnh hưởng
  cột nào metric schema?" → dựng bảng A→cột-thật / B→`clipped_fraction`.
- Cách học: module đào sâu (guide 11 sinh đúng lúc, CÓ Phòng thủ PT1–PT5 neo
  delay-moderate §Calibration/§Window-denominator + ffg-slot-sensitivity +
  metric-reconciliation). Grill G4 (window-denom) + G5 (adapter run_grid) CHẠY THẬT
  chấm: test_window_denominator 5/5, test_sweep_equivalence jobs=1 (PerCellInvariant
  + reproduces-committed-t46) 2/2. Né class jobs>1 (treo sandbox) — chỉ chạy method
  jobs=1. `timeout` không có trên macOS.
- Vấp (đáng giá, → ôn đầu M12): Feynman cuối YẾU cả 3 mảnh ngoài-clip. (1) *không
  vẽ được* đường ống 1 cell (`run_<proto>→clip_records→reducer→_build_row→1 dòng`).
  (2) G4 window-denom: bắt đúng KẾT LUẬN (PBFT÷result.now≈528 dìm ~10%, fix về 480,
  FFG/Snowman no-op) nhưng CƠ CHẾ lệch — nói "PBFT không truyền t_max cho run()",
  thực ra cả 3 truyền `t_max=calib.t_max=528` y hệt; khác biệt ở HAI t_max phân biệt
  (`run()`-stop=528 chung ≠ `meta.t_max`=field-mẫu-số=480 harness set) + *reducer
  chọn chia đại lượng nào* (pbft/summarise.py:67 result.now vs pos/snowman
  meta.t_max). (3) G5 adapter: nói "thêm timelines và commit_hash" — SAI chỗ điền;
  đúng = BA HÀM THUẦN `_run_cell/_cell_key/_param_fingerprint` (timelines=data
  config.py; commit_hash=tiêm qua run_constants, resolve-1-lần-ở-cha); `_run_cell`
  thuần = không wall-clock + không cross-cell (người học nêu được commit_hash, thiếu
  wall-clock). HAI cặp số hay lẫn: đồng-hồ (528 chạy/480 đo) vs ngưỡng-clip (W/
  W+one_round). Đã vá tại buổi bằng bản gọn 3-mảnh.
- Mờ/để dành: Phòng thủ M11 PT1–PT5 chưa luyện thành lời → `14-mock-defense` (cùng
  PBFT/Casper nợ cũ). ĐẾN HẠN vẫn treo: key-findings F1–F10. Câu mang sang M12
  (`adversary/` Họ C): rời mạng-trung-thực(B)→đối-thủ-chủ-đích(C); adapter TÁI DÙNG
  y khuôn M11 (run_grid + clip_records giữ nguyên), chỉ đổi config (trục f/φ) +
  runners (tiêm Node.adversary) — nên ôn 3 mảnh-mờ khi mở M12 vì chúng tái xuất.

### [2026-07-08] Module 10 · runner-sweep (đọc-giao-diện · FAST-LANE · mở chặng 4 "Chạy")
- Thông: hai cửa ngõ (`run_to_completion` một-run / `run_grid` cả-lưới); bốn trụ byte-identical; induction-over-the-grid; workload tất định mỗi-cell-ốc-đảo. H2 (reproducibility qua jobs, cốt lõi) trả lời hoàn hảo ngay. Chạy chấm: 6 test runner + 6 test generator + 4 class sweep jobs=1 — tất cả xanh, khớp dự đoán.
- Mờ: **H1 đảo ngược** — quiescence bị hiểu nhầm thành "timeout"; đã vá tại buổi (quiescence=hết-việc/tự-dừng vs deadline=hết-giờ/cưỡng-bức; vì sao Snowman-Casper buộc có t_max). Cần visual (grid 4-cell + sidecar + collect-sort) mới thông — đọc chay guide chưa đủ.
- Theo dõi tiếp: ghim quiescence-vs-deadline cho `14-mock-defense`. M11 `delay/` xem *ai gọi* `run_grid` (adapter: cell=(protocol,timeline,n,seed), run_cell=runner→clip→row) — đóng vòng "hạ tầng sweep → số liệu Chương 4".

### [2026-07-08] Module 09 · snowman (giao thức đào sâu thứ BA · finality xác suất · ĐÓNG chặng giao thức)
- Thông: giao thức thứ ba, rời hẳn **quorum tất-định** (PBFT/Casper) sang **finality
  xác suất**. Dựng mô hình bằng ví dụ 10-người-biển-màu: **no-quorum** — mỗi vòng chỉ
  hỏi K peer ngẫu nhiên, lấy mẫu *phản ánh* đa số hiện tại nên đa-số-nhỏ tự **khuếch
  đại** thành áp đảo (metastability). Hai bộ đếm **TÁCH BIỆT** (chỗ người học vật lộn
  nhất, mổ 4 lượt tới khi thông): **confidence[b]** (α_p nuôi, tích lũy đơn điệu →
  preference=argmax → quyết *hướng*, rẻ, sai không sao) vs **counter** (α_c nuôi,
  α_c-liên-tiếp trên preference → ACCEPT tại β → quyết *chốt*, đắt, sai=fork). Chốt
  hiểu lầm cốt lõi: **counter CHỈ đo `agree[preference]`** — Y đủ α_c mà Y chưa cướp
  preference (qua confidence/α_p) thì phiếu α_c của Y **bị vứt**; confidence tác động
  tới chốt chỉ **gián tiếp** (chọn ai đứng vạch xuất phát + flip thì reset counter=0).
  Audit #5: Snowball (preference=argmax(confidence), flip khi *strictly exceed*, tie
  giữ đương kim) ≠ Snowflake (flip theo majority-vòng) — bug CÓ THẬT từng có trong repo.
  Biên safety `ε≤(1−α_c/K)^β` (cơ số α_c/K, mũ β) → `0.2^15≈3×10⁻¹¹`; công thức đóng
  từ **Ava docs [ava-docs]**, Theorem 4 (raw/avalanche.pdf §7.4) chỉ cho *tồn tại* cận
  `<ε`. Rescale `K=min(20,n−1)`; n=4 degenerate (α_c=K, unanimity, ε=0, LOẠI khỏi bảng RQ).
- Cách học: module đào sâu (CÓ Phòng thủ, sinh guide 09 đúng lúc, neo Theorem 4). Grill
  G1–G5 CHẠY THẬT chấm: `test_parameters` (G1: sai α_c quên ceil + α_p n=4), `test_node_
  query` (G2 đúng: K peer, tự-loại-mình), `test_snowball_preference` (G3 ĐÚNG cả 3 —
  câu khó nhất, audit #5), `test_node_accept` (G4: 4 record decided; "15 là sàn baseline
  đạt sàn" chỉnh chữ "tối thiểu"), reproducibility script n=7 (G5: cùng seed→3205 record
  byte hệt; khác seed lộ ở **thứ tự** peers KHÔNG phải thành viên vì K=n−1 buộc cả tập).
  Người học hỏi rất đúng chỗ + tự tìm ra threat-to-validity: (a) Snowflake→Snowball đổi
  gì; (b) "chọn n−1 peer thay 10% có công bằng?" → dựng cả threat-to-validity rescale
  (ghi Câu hỏi tồn đọng); (c) truy tới cùng "α_c còn ý nghĩa gì nếu đã meet α_p".
- Vấp (đáng giá): confidence/counter + α_p/α_c gộp làm một (mất 4 lượt tách bạch mới
  thông — nhưng thông thì rất chắc); G1 quên `⌈⌉` làm tròn α_c lên số nguyên + `⌊3/2⌋=1`;
  Feynman/PT slip "quorum tới chậm" (Snowman KHÔNG có quorum) + PT1 thiếu chữ "xác suất
  không phải categorical". Phòng thủ PT1–PT5 luyện XONG buổi này (không dồn 14).
- Mờ/để dành: đọc-lại key-findings.md (F1–F10) giờ M09 xong; câu mang sang M10 (runner-
  sweep) = từ "1 run→1 dòng CSV" lên "quét cả lưới n×seed→CSV thống nhất", NHẤN
  reproducibility của sweep (sandbox jobs>1 TREO → jobs=1).

### [2026-07-07] Module 08 · casper-ffg (giao thức đào sâu thứ hai · accountable safety)
- Thông: giao thức thứ hai, họ PoS-finality — khác PBFT ở 4 trục (chốt epoch không
  block, đếm stake không node, phạt kinh tế không chỉ loại mật mã, finality chậm).
  Dựng mô hình **finality gadget**: FFG vote `<source, target>` cân ⅔ **stake**; một
  link `<S,T>` làm HAI việc — justify T, và finalise S nếu `T=S+1` & S đang JUSTIFIED
  (`finality.evaluate`). `decided` bắn đúng lúc epoch → FINALISED, một-lần-mỗi-epoch
  (`decided_epochs`), luôn chậm hơn justify **một link** = nguồn gốc "finality chậm".
  Ngưỡng division-free `3·stake≥2·total` (số nguyên khớp chính xác). Accountable
  safety = hai điều răn slashing (double-vote: `record_vote` phân loại NEW/DUPLICATE/
  CONFLICT theo bộ ba cùng-target-epoch; surround: `_check_surround` chéo-epoch, hai
  vế OR để thứ-tự-đến-của-bản-tin không đổi kết tội) → thủ phạm định danh + đốt cọc,
  khác PBFT vô danh. Đóng ba câu implement-thật người học tự hỏi: (1) `slots_per_epoch
  =2` = tối thiểu giữ phân biệt slot/epoch; (2) cùng số `decided` Casper finalise
  nhiều block hơn PBFT (hệ số slots_per_epoch) ⇒ so bằng **goodput** không tps —
  `summarise.py:72 n_opportunities=n_epochs×slots_per_epoch`; (3) tx mock qua
  `workload/generator` = byte blake2b đúng size, tất định, rỗng-ngữ-nghĩa.
- Cách học: module đào sâu (có Phòng thủ, sinh guide 08 đúng lúc, neo `raw/casper.pdf`
  §3 Figure 2 "The two Casper Commandments" — `I. h(t1)=h(t2)` OR
  `II. h(s1)<h(s2)<h(t2)<h(t1)`). Grill G1/G2/G3/G4/G5 CHẠY THẬT chấm:
  `test_node_finality` 6/6, `test_slashing.TestDoubleVote` 2/2 + `TestSurroundVote`
  3/3. Dự đoán G1/G2/G4 khớp; G3 (idempotence hai lớp) "không biết" → mổ rồi chốt;
  G5(b) đoán SAI ("ngược thứ tự không bắt") — đúng bẫy: hai-vế-OR bắt cả hai chiều.
  Người học hỏi rất đúng chỗ: (a) "observe từ 1 node?" → dẫn về finality-cục-bộ mỗi
  node tự đạt ⇒ n record `decided` (nối tps∝n); (b) đòi ví dụ CỤ THỂ surround có lợi
  gì → dựng kịch bản double-spend/revert-finalised bằng link rộng nhảy trùm.
- Vấp (đáng giá): G3 idempotence (chưa thấy hai lớp chặn: `evaluate` guard
  `target UNJUSTIFIED` + `decided_epochs` set); G5(b) tưởng thứ tự đến đổi kết tội;
  Feynman #2 stake ban đầu chỉ nói "tránh float" (thiếu chống-Sybil); Feynman #4 nói
  "xử phạt" mà quên sim **detect-only** (chưa đốt cọc) + quên nửa điểm-yếu finality-chậm.
- Mờ/để dành: Phòng thủ Casper PT1–PT5 (§6) chưa luyện thành lời → `14-mock-defense`;
  câu mang sang M09 (Snowman) = rời hẳn quorum-tất-định sang **finality xác suất**
  (subsampled voting, biên `ε`, ngưỡng `α`, số vòng `β`) — đóng α_c/β treo từ M00.

### [2026-07-06] Module 07 · pbft (★ đỉnh chặng 2)
- Thông: giao thức đồng thuận đầu tiên thay ruột `BroadcastNode` giả bằng FSM PBFT
  thật. Dựng mô hình `(view, seq)` = tọa độ MỘT cuộc đồng thuận đơn: `seq`=khe sổ
  cái (thứ ta muốn chốt, thực thi 1 lần), `view`=lần thử dưới một primary
  (`primary=view mod n`, đổi khi leader hỏng). Lưới 2D: đi-ngang (seq mới) chỉ
  primary làm ở `_propose`; đi-dọc = leo 4 bậc FSM `IDLE→PRE_PREPARED→PREPARED→
  COMMITTED`, mỗi bậc chốt tại quorum `2f+1`. Tự dẫn xuất `3f+1` từ hai ràng buộc
  đánh nhau (chốt-khi-f-im ⇒ quorum≤n−f; giao-hai-quorum≥f+1-trung-thực ⇒ 2q−n≥f+1;
  ghép ⇒ n≥3f+1, q=2f+1). Decision B (tự-broadcast+tự-ghi phiếu vì broadcast loại
  sender); Decision C (phiếu đếm-lùi: `setdefault` ô rỗng + `matching_*`=0 khi
  digest None + PRE-PREPARE điền digest → cascade); Decision G (`decided` khoá theo
  seq trong `_decided_seqs`, một lần dù reissue qua view). Digest-binding Rule 5 =
  biến "đồng thuận trên digest" thành "trên payload" (prepare/commit chỉ cõng digest
  32B để rẻ băng thông O(n²)). ĐÓNG câu tồn đọng `tps ∝ n`: 1 request → mỗi node
  phát 1 `decided` → n record → `tps=len(decided)/now` phồng theo n = misnomer;
  goodput đếm instance phân biệt mới đúng.
- Cách học: module đào sâu (có Phòng thủ, sinh guide 07 đúng lúc, neo PDF §4.2/4.5.1/
  4.4/4.5.2 cho 2 điểm gai). Grill G1 (quorum tối thiểu) + G5 (tps∝n) CHẠY THẬT chấm:
  `test_happy_path` 7/7, `test_pbft_consensus` 11/11 (n4→4 decided, n7→7 decided,
  Scenario B view-change pass). Dự đoán G1/G5 khớp. Người học tự hỏi 2 câu rất
  đúng chỗ: (a) "diễn tả một `(view,seq)`" → dẫn thẳng vào mô hình lưới; (b)
  "tại sao payload phải khớp digest" → lộ lý do vote-bằng-digest + Rule 5; (c) đòi
  giải thích trọn evidence-boundary (caveat trung thực nhất của PBFT).
- Vấp (đáng giá): cascade sau đủ quorum PREPARE — đoán "gửi đi (0,1)" (tưởng mở khe
  seq mới) — thực ra leo DỌC cùng ô: PREPARED → broadcast COMMIT. Đã tách bạch
  "đi-ngang seq mới (primary/`_propose`)" vs "đi-dọc leo thang FSM (mọi replica)".
  Cuối cùng gọi đúng cặp event chốt: `PBFT_COMMITTED` + `decided`.
- Mờ/để dành: Phòng thủ PBFT (PT1–PT5) chưa luyện → `14-mock-defense`; nhánh
  view-change (f+1 catch-up, backoff `2^view`, `compute_reissue` highest-view-per-seq)
  mới ở mức Scenario B pass, chưa grill sâu; con số F1–F10 vẫn chờ sau M09.

### [2026-07-06] Module 06 · trace end-to-end (★ đóng chặng 1)
- Thông: ghép trọn 5 tầng lõi thành MỘT dòng CSV qua harness thật
  `tests/integration/_helpers.py::build_and_run` = 6-phase bootstrap viết tường
  minh. Kịch bản neo n=4 seed=42 delay-hằng=10: 12 Delivery (`n·(n−1)`) cùng
  t=10, `RunResult(quiescence, now=10, events_processed=12, tombstoned=0)`. Chốt
  M03/M04: entry heap Delivery = `(t, dst, seq)` ⇒ trong record `node_id=dst`
  (src ở `fields`); `sink` hai `isinstance` chỉ gom event-heap, `("emit",…)` tuple
  trần rớt cả hai (harness lọc emit; EventLogger THẬT thì lại ghi emit). Ordering
  scramble (TimerNode nộp `late` trước, start reversed) → `fired[0]=(100,0,'early1')`
  phơi cả 3 trường tie-break cùng lúc. Determinism quy-mô-tích-hợp: cùng seed=42
  → byte y hệt, seed=7 → khác (SameSeed/Divergence của M05 nay trọn 5 tầng).
  `_dispatch` rẽ HAI nhánh song song: `dst._on_message` (giao tin) ‖ `event_sink`
  (ghi sổ).
- Cách học: module TRACE (bỏ Phòng thủ). 10/10 test integration pass; in giá trị
  thật (4 record đầu + CSV header + fired[:3]) đối chiếu từng dự đoán. 4/5 grill
  vững ngay.
- Vấp (đáng giá): (1) event_type đoán `decided?`→`Delivery?` — thực ra chuỗi
  thường `"delivery"`; `decided` chỉ có khi FSM giao thức THẬT chốt block (→M07),
  BroadcastNode giả không bao giờ decide — đúng bẫy "trace nhầm sang giao thức khi
  còn ở tầng lõi"; và là chuỗi thường, không phải tên lớp `Delivery`. (2) seq đánh
  số từ 1 không phải 0. (3) Feynman gọi nhầm broadcast là "inbound" — thực ra
  outbound (inbound = `_on_message`); và `_dispatch` rẽ hai nhánh, ban đầu chỉ
  thấy nhánh sink. Cả ba đã vá.
- Mờ/để dành: câu mang sang M07 = thay ruột BroadcastNode giả bằng FSM PBFT thật
  → "một vòng" `n·(n−1)` phẳng thành chuỗi pre-prepare→prepare→commit quorum
  `2f+1`, CSV mọc `event_type="decided"`; đường ống 5 tầng GIỮ NGUYÊN. Đóng luôn
  câu tồn đọng `tps ∝ n` (đọc `src/pbft/summarise.py`).

### [2026-07-06] Module 05 · config
- Thông: ranh giới hai nửa — `load_config(path)→Config` (thuần text→object, kiểm
  tra, KHÔNG seed) vs `build_run(config, seed, node_factory)→RunHandle` (dựng, seed
  vào đây); `Config` frozen = mắt xích tái lập đầu tiên. 6-phase bootstrap và vì sao
  phase 5 (`network.start`) BẮT BUỘC trước phase 6 (`node.start`) — chứng minh bằng
  thí nghiệm: đảo thứ tự → node 0 broadcast lúc mạng chưa mở → `_guard_started`
  RuntimeError (network.py:101), 1 FAIL + 6 ERROR lây. Single seed surface: 1 int
  `global_seed` → blake2b → `net_rng` + per-Node `rng` (scheduler no RNG; blake2b vì
  `hash()` random mỗi tiến-trình). Dependency injection: `node_factory` quyết
  *protocol nào*, seed quyết *xúc xắc nào*, cả hai đứng ngoài YAML. 4 cổng fail-fast
  cross-field + nguyên tắc "phân tầng theo thông tin cần có" (required/leaf/cross-field).
  3 khoang opaque (adversary→T18, protocol_knobs→T28+, workload→T41) — đóng khe
  `self.adversary` để dành từ M02: config *chở* + node *nhận* cùng một blob chưa-đóng.
- Cách học: module đọc-giao-diện, bỏ Phòng thủ, nhấn reproducibility. Grill 5/5 CHẠY
  THẬT chấm — H2 và H3 dùng thí nghiệm phá-rồi-hoàn-nguyên (đảo phase 5/6; đổi
  `rng.random()`→hằng `0.5`) để THẤY test gãy đúng dự đoán. Người học tự dựng lại
  logic cặp SameSeed/Divergence ở Bước 3 trước cả khi grill. Đầu buổi tự bật đúng
  "common random numbers" khi hỏi "trùng seed giữa các file yaml sao?".
- Vấp (nhẹ): (1) Feynman ý byte-identical ban đầu chỉ nói "audit", chưa bật lý do
  gắt = phân biệt regression-thật vs run-tự-trôi (đã vá). (2) H5 opaque: đoán key
  dict sai (`{delay-emission: 0.1}` — gộp value làm key) — thực ra round-trip verbatim
  giữ nguyên cả `strategy` lẫn `fraction`; và "ai đóng" là T18 (task) không phải node.
  Cơ chế (config chở blob, chưa mở) thì nắm đúng. Bốn cổng recall lại chuẩn xác.
- Mờ/để dành: câu mang sang M06 = ghép build_run→scheduler.run→event_sink thành MỘT
  dòng CSV thật (ping-pong 2 node), đóng trọn đường ống tầng lõi.

### [2026-07-05] Module 04 · event-log
- Thông: `event_sink` = con trỏ hàm (`scheduler.event_sink = logger.sink`, phase 4)
  → loose coupling, scheduler không biết logger tồn tại; hai chỗ gọi → hai shape
  (emit tuple seq=−1 / typed transport seq thật, PhaseAdvance node_id=−1); `sink`
  4 nhánh phân loại (emit soi *cấu trúc*, transport soi *kiểu*, else fail-fast —
  no silent drop, 3 test arity ghim); EventRecord frozen 5 trường, 4 scalar đóng
  cứng + `fields` mở = extensibility surface (T28+ nhét term riêng, không migrate);
  logger THỤ ĐỘNG (no sched ref / file handle / RNG) ⇒ điều kiện reproducibility;
  hai chân determinism (thứ tự record=dispatch tất định + sorted-key `repr`); một
  dòng CSV Delivery `8.5,3,delivery,4,"{'dst':3,...}"` thành hình — ĐÓNG câu mang
  từ M03 (`event_sink` nối vào `logger.sink`).
- Cách học: grill 5/5 CHẠY THẬT chấm từng câu (H1 phân loại/arity, H2 copy-in vs
  frozen-footgun, H3 dòng CSV + phát hiện csv quote khi ô có dấu phẩy, H4 sorted
  determinism, H5 e2e 3-loại vs 5-loại). Dự đoán H1–H4 khớp hết; H5 sót `decided`.
  Đầu buổi tự bật đúng trực giác "sự kiện pop ra phải đẩy đâu cho logger" → dẫn
  thẳng vào seam. Path collision test (`src/event_log` vs `tests/event_log/`) —
  đã ghi cách chạy đúng vào con trỏ.
- Vấp (đáng giá): (1) H5 quên `decided` — node `_emit_decided` *rồi mới* `halt`,
  hai emit đi cặp (đây là cặp M13 đọc tính finality). (2) Feynman #2 đảo thứ tự:
  check ở cửa vào `sink`, sort ở cửa ra `to_csv` — hai thời điểm tách rời, buffer
  nằm im chưa sort. Đã siết lại. (3) "không biết" ở câu TimerFire cắt payload —
  gỡ bằng nguyên tắc "ghi *sự thật quan sát* không ghi *trạng thái nháp nội bộ*".
- Mờ/để dành: `repr` vs `json.dumps` (giữ tuple) — hiểu lý do, chưa cần thuộc;
  câu mang sang M05 = factory YAML→hệ thống + 4 cổng fail-fast "Watch for T27".

### [2026-07-05] Module 03 · network
- Thông: đường ống 5 bước `_try_deliver` + mô hình "xé vé số" cho RNG
  (net_rng như xấp vé in sẵn theo seed; "tiêu 1 mẫu" = xé 1 tờ; tung đồng xu
  drop ≠ trúng drop; thứ tự drop→partition→delay ghim để đổi topology partition
  không lệch dòng RNG); "gửi" = đặt lịch Delivery ở `t+delay`, pop→`_on_message`
  (đóng trọn trực giác "promise ở t+n" của chính người học đầu buổi); delay đông
  cứng lúc submit; PhaseAdvance node_id=−1 sort-first ⇒ half-open; Network trung
  thực (Họ B) vs adversary ở Node (Họ C); vòng đời Phase/3 dataclass + init site
  `config/loader.py` từ YAML, kiểm 2 tầng trước t=0.
- Cách học: hỏi rất đúng mạch (đòi giải thích lại "tiêu mẫu" bằng term đơn giản;
  bắt được nghi vấn "vừa drop vừa delay?" — đúng chỗ dễ lẫn nhất, gỡ bằng 4-số-
  phận-tin loại-trừ-nhau; truy "Phase/dataclass/Partition init ở đâu, lúc nào" →
  lộ ranh giới network-định-nghĩa-kiểu vs config-sinh-instance). Grill 5/5, chạy
  chấm thật từng câu.
- Vấp (đáng giá): grill #3 đảo dấu kết luận `sorted(registry)` — nhớ đúng cơ chế
  (thứ tự lặp ↔ ánh xạ delay) nhưng kết luận ngược; test bẫy có chủ đích, đã chỉ
  "sorted = chống đổi, forward==reverse". Feynman phần (a) "vì sao honest infra"
  chưa nói được → đã vá (quy-trách-nhiệm B≠C + tái dùng nền + khớp giả định BFT).
- Mờ/để dành: câu mang sang M04 = `event_sink` → CSV một dòng thành hình ra sao.

### [2026-07-05] Module 02 · nodes
- Thông: two-layer commitment (lifecycle chung + FSM riêng, tầng FSM được phép
  khác — ép chung sẽ phá mechanism fidelity); template method (public/guard vs
  `_`-protected/subclass, `@abstractmethod` chặn tạo `Node` trực tiếp); split-bind
  (Scheduler↔timer/emit, Network↔send/broadcast), lambda closure curry `node.id`;
  halt idempotent (blanket RUN_END không xóa CRASHED/SLASHED); guard loại-trừ-nhau
  (drop vì `status=HALTED`, không phải thứ tự `if` — tự sửa sau khi tôi giảng sai).
- Đào sâu ngoài lề (rất tốt): hỏi bật ra 3 chủ đề phòng-thủ trước cả grill —
  (1) discrete-event không có tick, thứ tuần hoàn = recurring self-timer;
  (2) virtual-time vs wallclock: metric đo SimTime cố ý, "nhảy thời gian không đợi
  thật", latency = hiệu tọa độ `t`; giá phải trả = latency-only + no capacity ceiling
  (§6.2); (3) analogy `f(config, seed)→1 dòng CSV`, common random numbers = công bằng.
- Cách học: dự đoán trước rồi CHẠY THẬT chấm (6/6). Bắt được lỗi giảng của tôi ở
  grill #5 (thứ tự guard) — active recall + không nuốt chửng lời giảng, đúng tinh thần.
- Mờ/để dành: `self.adversary` opaque (→M12); FSM cross-instance state (→M07–09).

### [2026-07-03] Module 01 · scheduler
- Thông: vòng `run()` + 3 điều kiện dừng; khóa `(t,node_id,seq)` là thứ tự
  toàn phần tất định (tự giải thích được vai trò từng trường); lazy tombstone
  (trace tay heap+registry qua kịch bản re-register, khớp code); 3 Event ↔ 3
  handler; chuỗi determinism input(seed)+order(heap key)→output byte y hệt.
- Cách học: hỏi rất đúng chỗ (đòi trace heap/registry bằng giá trị cụ thể
  trước khi grill; hỏi vì sao order theo node_id; nối PhaseAdvance với
  async→partial-sync/GST). Dự đoán grill #4 (re-register) và #5 (deadline
  overshoot) đều CHẠY THẬT khớp.
- Mờ/đã sửa: ban đầu tưởng Delivery cần registry (thực ra chỉ TimerFire) —
  đã chỉnh; Feynman đầu tiên gộp "mọi event so seq" — siết lại còn "chỉ
  TimerFire". Hai điểm này giờ chắc.
- Phòng thủ đã luyện: determinism≠đơn điệu (seed điều khiển, sweep+CI);
  tự-viết-heap vì làm chủ tie-break; RNG seed-hóa nằm ở network không ở
  scheduler; PhaseAdvance tổng quát hơn "đổi synchrony".

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

- ~~Cơ chế `tps ∝ n`~~ ✅ ĐÓNG ở M07: 1 request → mỗi node phát 1 `decided` → n
  record; `tps=len(decided)/result.now` (summarise.py:66) phồng theo n = misnomer;
  goodput đếm instance phân biệt (`n_opportunities`) mới là thông lượng thật.
- ~~α_c (alpha) và β của Snowman~~ ✅ ĐÓNG ở M09: α_p=⌊K/2⌋+1 (flip preference),
  α_c=⌈0.8K⌉ (nhích counter), β=15 (số vòng α_c-liên-tiếp → ACCEPT); rescale
  `K=min(20,n−1)`; biên `ε≤(1−α_c/K)^β` (cơ số α_c/K, mũ β).
- **[ĐẾN HẠN]** Đọc-lại `wiki/concepts/key-findings.md` (F1–F10) — M09 đã xong,
  giờ đủ nền 3 giao thức để các con số "click" ngược (đã hiểu cốt, chưa thuộc số).
- **[M09 · defense gold] Rescale Snowman ở thesis-scale có công bằng không?**
  `K=min(20,n−1)` ⇒ ở dải n∈{4,7,10,16,25} thì K≈n (KHÔNG phải ≤10% như
  production), nên Snowman MẤT tính tail-insensitive — lợi thế chịu-trễ-tại-scale
  không phô ra được (phải sweep n≈1000). Công bằng "cùng n/mạng/seed" nhưng chạy
  Snowman NGOÀI vùng thiết kế (K≪n). Giảm thiểu (metric-reconciliation.md §Snowman
  parameter rescaling): giữ α_c/K≈0.8 + β=15 cho đúng *shape* của ε; LOẠI ô n=4
  khỏi bảng RQ (degenerate: α_c=K ⇒ đòi nhất trí, ε=0 → CSV `snowman_degenerate_n4`
  riêng); GẮN CỜ n=7 (α_c/K=0.833); xuất cột `alpha_c_over_K` mọi hàng để tự
  drop/annotate. → luyện thành lời ở `14-mock-defense`.
- **[M12 · defense gold] Vì sao sweep *delay* dừng ở f=0.30, không đẩy lên 0.40 để
  thấy PBFT stall?** KHÔNG phải giấu lỗ hổng — phân công 3 sweep: delay (T51) dừng
  0.30 vì delay-emission theo catalog §3 là đòn quấy-liveness TRONG hạn ngạch ⅓; một
  node hoãn-quá-lâu ở f>⅓ = offline về vận hành, mà vách đó ĐÃ đo bằng sweep offline
  (T52, f=0.40: PBFT 61 view-changes n=10 / 151 n=25). offline+equivocate MỚI vượt ⅓
  (0.40/0.50). Ch4 §4.4.1 "PBFT immune" được rào bởi §4.4.2 (offline stall) + §4.4.4
  qualification "holds only against an adversary that spares its view-0 primary
  (§6.2)". Khe THẬT SỰ mỏng (thủ khi bị hỏi): delay f>⅓ với `m` HỮU HẠN chưa test
  literal (khác offline vì phiếu cuối cùng vẫn tới → commit-muộn hoặc view-change-hồi
  -phục); trả lời: trên ⅓ delay suy biến thành offline (m lớn) hoặc chỉ-muộn (m nhỏ,
  không phải chế-độ-hỏng-mới), vách liveness đo độc lập ở offline, bỏ để giữ ngân sách.
- **[M12 · defense gold] Casper "không fork" — có phải short-of-implementation?** ĐÚNG
  MỘT PHẦN, và được KHAI BÁO. `EpochState.links` (src/pos/epoch.py) gộp stake theo
  `source_epoch` và BỎ QUA `target_hash` → sim KHÔNG biểu diễn nổi checkpoint-fork như
  hai giá-trị-finalised mâu thuẫn → `safety_violation` FFG luôn=0. NHƯNG đây là lựa
  chọn fidelity CÓ CHỦ ĐÍCH không phải bug giấu: mô hình forked-proposal sẽ "finalise"
  GIẢ hai checkpoint dưới honest supermajority = model artifact còn TỆ hơn. Nên FFG chỉ
  mô hình **double-vote**, và đo đúng thứ PHÂN BIỆT Casper: **accountable safety =
  `max_slashable_stake_fraction`** (chạm ≥⅓ tại f=0.40). "Casper không fork" trong sim
  ≠ "Casper fork-proof" thực tế: thực tế Casper CÓ THỂ fork khi ≥⅓ stake equivocate,
  nhưng fork ĐÓ accountable (đốt được ≥⅓ cọc) — khác PBFT fork VÔ DANH. Nối M08:
  sim **detect-only** (đo slashable, chưa thật-sự-đốt cọc). Khe mỏng: "never forks"
  (Ch4 §4.4.3) đọc lố = "fork-proof"; cứu bằng cụm "never forks *but fails accountably*"
  + khai báo model-boundary ở equivocate.py docstring + adversary-model §Revisions T53.
  → luyện thành lời ở `14-mock-defense`.
