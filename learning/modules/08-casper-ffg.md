# Module 08 — `pos/` (đào sâu · giao thức thứ hai · Casper FFG)

> Giao thức đồng thuận **thứ hai**, họ khác hẳn PBFT. ~40–45 phút. Đây là module
> **accountable safety / slashing** — cái mới mà PBFT *không* có. Module đào sâu ⇒
> đủ: trace & dự đoán + chạy thật + **Phòng thủ**.

## 0. Vì sao tồn tại — và nối với phòng thủ

Casper FFG (Friendly Finality Gadget) là đại diện **họ PoS-finality** trong bản đồ
3 họ (Module 00). PBFT chốt **tức thì mỗi block** bằng đếm *node*; Casper là một
**finality gadget** phủ lên một chuỗi block đang mọc, chốt **theo epoch** (mốc
nhiều slot một lần) bằng đếm **stake** (cổ phần đặt cọc), và trừng phạt kẻ gian
bằng **kinh tế** (slashing — đốt cọc) chứ không chỉ loại bằng mật mã. Nó chống
lưng RQ1 (latency: Casper chốt *chậm hơn* — 2 epoch), RQ4 (ngưỡng đối kháng đo bằng
stake), và mở một trục PBFT không có: **chi phí kinh tế của một đòn phá an toàn**.

Điểm gai phòng thủ (2 điểm, neo bài báo gốc `raw/casper.pdf`):
1. **Accountable safety = hai điều răn (Commandments) slashing.** Nếu hai checkpoint
   mâu thuẫn cùng được finalise, thì ≥ ⅓ stake **chắc chắn** đã ký một bản tin vi
   phạm *chứng minh được* → thủ phạm **quy được trách nhiệm** và bị đốt cọc. Đây là
   cái PBFT thiếu: PBFT an toàn nhưng thủ phạm **vô danh**.
2. **Two-round justify → finalise = tương tự prepare → commit của PBFT** nhưng ở
   *mức epoch*, không *mức block*. Chính đây sinh ra **điểm yếu**: finality *chậm*
   (đo bằng phút, không sub-giây).

Đường ống 5 tầng lõi (M01–M06) **GIỮ NGUYÊN** — Module này chỉ thay ruột node bằng
một FSM mới: thay vì FSM PBFT per-`(view,seq)`, giờ là FSM Casper per-**epoch**.

## 1. Đọc gì, theo thứ tự

1. `wiki/algorithms/pos.md` — hợp đồng giao thức. **Đọc trước code.** Đặc biệt
   §Two-round finalisation, §Slashing conditions, §Accountable safety, và
   §Simulator mapping (Implemented vs **Not implemented** — ranh giới phạm vi).
2. `src/pos/messages.py` (36 dòng) — 2 payload frozen (`BlockProposalPayload`,
   `AttestationPayload`) + 1 vote lồng `FFGVote(source_epoch, source_hash,
   target_epoch, target_hash)`. Chỉ là túi dữ liệu trên dây; **không** có trường
   chữ ký (§15: sim truyền object Python, không verify chữ ký).
3. `src/pos/epoch.py` (85 dòng) — `EpochFSM` (UNJUSTIFIED→JUSTIFIED→FINALISED) +
   `EpochState` (bộ gộp phiếu **một instance mỗi target epoch**) + `VoteStatus`
   (NEW/DUPLICATE/CONFLICT). Đọc `record_vote` kỹ: dedup theo attester, phân loại
   3 nhánh — đây là mấu chốt phát hiện slashing.
4. `src/pos/finality.py` (82 dòng) — hàm **thuần** `evaluate(...) → FFGTransitions`.
   Nói *nên xảy ra gì* (justify? finalise source?) mà **không** sửa gì. Test
   division-free `3·stake ≥ 2·total`. Tách rule khỏi node để unit-test cô lập
   (giống `viewchange.py` của PBFT).
5. `src/pos/node.py` (421 dòng) — FSM chính. Đọc theo **luồng đời một epoch**:
   `_on_slot` → `_propose`/`_accept_block` (dựng chuỗi + set checkpoint hash) →
   `_attest` (dựng `FFGVote <highest_justified, epoch>`, broadcast, tự-ghi) →
   `_file_ffg_vote` (phân loại NEW/DUP/CONFLICT + chạy slashing check) →
   `_run_ffg_transitions` (gọi `evaluate`, áp transition) → `_finalise`
   (`_emit_decided` một-lần-mỗi-epoch). Nhánh accountable-safety: `_check_surround`,
   `_flag_slashing`, `slashable_stake_fraction`.
6. Test (đặc tả chạy được): `tests/pos/test_node_finality.py` (ngưỡng ⅔,
   two-link finalise → decided, non-uniform stake), `tests/pos/test_slashing.py`
   (NEW/DUP/CONFLICT, double vote, surround cả hai chiều, slashable fraction).
   Helper: `tests/pos/_helpers.py` (`make_node`/`capturers`/`kickoff`).

Bài báo gốc (đọc **đúng đoạn**, không cày cả bài): `raw/casper.pdf` §3
**Figure 2 "The two Casper Commandments"** (hai điều kiện slashing) + câu ngay sau
Figure 2 (accountable-safety: *"impossible for any two conflicting checkpoints to
be finalized unless ≥⅓ of validators violate one of the Commandments"*). Trích
chương-câu ở §6 Phòng thủ dưới.

## 2. Mục tiêu khi đọc (trả lời được là đạt)

- FFG vote hình `<source, target>`. **Justified** = có supermajority link (≥⅔
  stake) từ tổ tiên đã-justified tới target. **Finalised** = target justified *và*
  có link ⅔ nữa từ target tới **con liền kề** của nó. Vì sao cần *hai* link liên
  tiếp? (tương tự prepare→commit — một vòng không đủ.)
- Ngưỡng đo bằng **stake**, không **count**. n=4 stake đều 3 → total 12, ⅔ = 8;
  test division-free là `3·stake ≥ 2·total`. **Vì sao viết vậy thay vì
  `stake/total ≥ 2/3`?** (số nguyên so khớp *chính xác*, không rounding float.)
- **Decision C** (giống PBFT): mọi node tự broadcast ATTESTATION *và* tự-ghi phiếu
  mình. Vì sao tự-ghi? (`Network.broadcast` loại người gửi.)
- **Decision F**: epoch 0 (genesis) pre-installed = FINALISED. Vì sao phải bootstrap
  sẵn? (justify chain cần một điểm neo đã-justified để link đầu tiên bám vào.)
- **Decision H**: `EpochState` lazy-create bằng `setdefault`. Vì sao? (ATTESTATION
  có thể tới *trước* checkpoint block của epoch đó.)
- **Hai điều răn slashing**: *double vote* (hai phiếu khác nhau cùng target epoch)
  và *surround vote* (`s1 < s2 < t2 < t1`). `record_vote` phân biệt DUPLICATE (vô
  hại, idempotent) với CONFLICT (slashable) thế nào?
- `decided` phát **một lần mỗi epoch** (`decided_epochs`). Một phiếu thừa trên link
  đã-đủ có re-finalise không? (không — guard `source_state is JUSTIFIED`.)

## 3. Idiom Python sẽ gặp (gloss)

- **So sánh xích (chained comparison)** — `s1 < s2 < t2 < t1` trong `_check_surround`
  là idiom Python: đọc như toán học, tương đương `s1<s2 and s2<t2 and t2<t1`,
  **đánh giá mỗi toán hạng một lần**. Đây *chính là* điều kiện surround của bài báo,
  chép thẳng.
- `dict.setdefault(key, default)` — hai chỗ: `_epoch_state` (`setdefault(epoch,
  EpochState(epoch))` = "lấy state epoch, chưa có thì tạo rỗng" — Decision H, đếm
  phiếu lùi) và `vote_history.setdefault(attester, []).append(ffg)` (gom lịch sử
  phiếu mỗi attester để check surround về sau).
- `@dataclass(frozen=True)` — `FFGVote`/`BlockProposalPayload`/`AttestationPayload`
  bất biến (kỷ luật reproducibility); `FFGTransitions` cũng frozen (chỉ chở kết
  quả). `EpochState` **không** frozen (state đổi tại chỗ).
- `Enum` + so `is` — `EpochFSM`/`VoteStatus`; `state is EpochFSM.JUSTIFIED`,
  `status is VoteStatus.CONFLICT`. Đọc rõ ý đồ, không magic number.
- `set` cho idempotence + đếm-phân-biệt — `self._slashable` (mỗi kẻ gian đếm **một
  lần** dù phạm nhiều lần), `self.decided_epochs` (finalise một-lần-mỗi-epoch).
- `sum(self.stake_table[a] for a in self._slashable)` — đếm-có-điều-kiện idiom:
  cộng stake của đúng những attester trong tập slashable ⇒ tử số của fraction.
- Khoá tuple làm dedup key — `_filed[attester] = (source_epoch, source_hash,
  target_hash)`; so **cả bộ ba** để tách DUPLICATE (bộ ba trùng khít) khỏi CONFLICT
  (cùng attester, bộ ba khác).
- `3.0 * stake >= 2.0 * total` — nhân chéo thay chia: tránh so float `x/y ≥ 2/3`.

## 4. Khái niệm gloss (đồng thuận)

- **slot / epoch / checkpoint** — *slot* = một khe thời gian (một block). *epoch* =
  một cụm cố định `slots_per_epoch` slot (sim mặc định 2). *checkpoint* = block đầu
  của mỗi epoch — chỉ checkpoint mới được justify/finalise, không phải mọi block.
- **FFG vote `<source, target>`** — một phiếu chứng thực "checkpoint *source* nên
  justify checkpoint *target*". Trong code: `FFGVote(source_epoch, source_hash,
  target_epoch, target_hash)`.
- **supermajority link (≥⅔ stake)** — link `S → T` tồn tại khi các FFG vote đại
  diện ≥ ⅔ **tổng stake** đã bỏ cho `<S,T>`. Đây là "quorum" của Casper, nhưng cân
  theo cổ phần, không theo đầu người.
- **justified vs finalised** — *justified* = có một supermajority link tới nó từ tổ
  tiên đã-justified. *finalised* = nó justified **và** có link ⅔ nữa từ nó tới con
  liền kề. Hai link liên tiếp = PoS analogue của prepare→commit. Ví dụ: link `<0,1>`
  justify epoch 1; link `<1,2>` justify epoch 2 **và** finalise epoch 1.
- **stake-weighted `3f+1`** — cùng số học giao-quorum như PBFT (§quorum-arithmetic)
  nhưng `f` đo bằng **⅓ tổng stake**, không ⅓ số node. Chịu Byzantine tới `f < ⅓`
  stake.
- **accountable safety / slashing** — cái mới của họ này. Nếu hai checkpoint mâu
  thuẫn cùng finalise, ≥⅓ stake **chứng minh được** đã vi phạm điều răn ⇒ thủ phạm
  **định danh được**, cọc bị **đốt**. PBFT an toàn nhưng *không* quy trách nhiệm cá
  nhân — đây là điểm phân biệt.
- **hai điều răn (Casper Commandments, Figure 2)** — hai kiểu vi phạm *chứng minh
  được*: (I) **double vote** — một validator ký hai phiếu khác nhau **cùng target
  epoch**; (II) **surround vote** — phiếu `<s1,t1>` *bao* phiếu khác của **chính
  nó** `<s2,t2>`: `s1 < s2 < t2 < t1`. Vi phạm một trong hai ⇒ slashed.
- **economic rationality** — giả định nền của họ: validator quý cọc hơn lợi từ tấn
  công. Slashing chỉ răn được kẻ *duy lý kinh tế*; đây là trục mới PBFT không có.
- **weak subjectivity (điểm yếu)** — node mới / offline lâu **không** bootstrap
  thuần từ chuỗi; phải tin một checkpoint gần đây từ nguồn xã hội. Không cơ chế
  on-chain nào đóng được khe này.

## 5. Grill "trace & dự đoán"

> Sau mỗi câu: **dự đoán trước**, rồi ta **CHẠY THẬT** để chấm. Suite:
> `PYTHONPATH=src:tests/pos python3 -m unittest <mod> -v`
> (`<mod>` = `test_node_finality` hoặc `test_slashing`).

**G1 — ngưỡng ⅔ đo bằng stake.** n=4, stake đều 3.0 mỗi node → total 12, ⅔ = 8.
Node 0 nhận **2** phiếu peer cho link `<0,1>` (mỗi phiếu 3.0). `epoch_states[1].state`
= ? Rồi nhận phiếu peer **thứ 3**: state = ?

<details><summary>ĐÁP ÁN</summary>

2 phiếu = 6 stake < 8 ⇒ vẫn **UNJUSTIFIED** (`test_one_vote_short_does_not_justify`).
Phiếu thứ 3: 9 ≥ 8 ⇒ `meets_supermajority(9,12)` vì `3·9=27 ≥ 2·12=24` ⇒
**JUSTIFIED** (`test_supermajority_justifies_epoch`). **Bẫy:** node 0 ở đây *không*
tự-ghi (drive off slot loop qua `_populate_chain`, chỉ nạp block; phiếu đến từ peer
1/2/3), nên cần đủ 3 phiếu peer. Đối chiếu non-uniform: stake `9,1,1,1` → **một**
phiếu từ node 0 (stake 9 > 8) đủ justify (`test_non_uniform_stake_justifies_on_stake`)
— đếm **stake**, không **đầu người**.
</details>

**G2 — hai link liên tiếp finalise + decided.** n=4. Trước: 3 phiếu peer link `<0,1>`
(justify epoch 1). Sau: 3 phiếu peer link `<1,2>`. Ngay sau vòng thứ hai:
`epoch_states[1].state` = ? `epoch_states[2].state` = ? Có bao nhiêu record `decided`,
`instance_id` = ?

<details><summary>ĐÁP ÁN</summary>

Link `<1,2>` đủ ⅔ ⇒ `evaluate` trả `justified=True`. Vì `target(2)=source(1)+1`
**và** source epoch 1 đang **JUSTIFIED** ⇒ `finalised_source=True`. Kết quả:
epoch 2 = **JUSTIFIED**, epoch 1 = **FINALISED**, phát **1** `decided` với
`instance_id=1`, `value=cps[1].hex()`
(`test_two_links_finalise_and_emit_decided`). **Bẫy:** finalise thuộc về
**source** (epoch 1), không phải target (epoch 2) — target chỉ mới justified.
</details>

**G3 — decided một-lần-mỗi-epoch.** Tiếp G2: epoch 1 đã FINALISED + phát `decided`.
Giờ một phiếu **thừa** (từ node 0) cho đúng link `<1,2>` tới. Số record `decided` =?

<details><summary>ĐÁP ÁN</summary>

`decided` vẫn = **1** (`test_decided_emitted_once_per_epoch`). Hai lớp chặn: (a)
`evaluate` guard `target_state is UNJUSTIFIED` — epoch 2 đã JUSTIFIED ⇒ trả `_NONE`,
không transition; (b) kể cả nếu tới được `_finalise`, guard `if epoch not in
self.decided_epochs`. **Bẫy:** finalise **không** re-fire vì cả rule (source phải
còn strictly JUSTIFIED) *lẫn* `decided_epochs` set cùng chặn — idempotent hai tầng.
</details>

**G4 — double vote vs duplicate.** n=4. Node 0 nhận từ attester 1 phiếu `<0→1>`
target hash `cps[1]`. Rồi nhận từ **cùng** attester 1 một phiếu nữa cùng target
epoch 1 nhưng **target hash khác** (`other`). Có `casper_slashing` không, reason gì?
Còn nếu phiếu thứ hai **trùng khít** (cùng cả 3 giá trị) thì sao?

<details><summary>ĐÁP ÁN</summary>

Khác target hash ⇒ `record_vote` thấy `_filed[1]` đã có bộ ba khác ⇒ **CONFLICT** ⇒
`_flag_slashing("double_vote", ...)`, **1** event `casper_slashing`, `reason=
"double_vote"`, `attester_idx=1`, `target_epoch=1`
(`test_double_vote_emits_slashing`). Link stake **không** bị cộng lần hai (phiếu thứ
hai không justify gì). Trùng khít ⇒ **DUPLICATE** ⇒ idempotent no-op, **0** slashing
(`test_exact_duplicate_does_not_slash`). **Bẫy:** re-delivery mạng (trùng khít) là
bình thường, **không** slash; chỉ *bộ ba khác nhau cùng target epoch* mới là double
vote.
</details>

**G5 — surround vote (so sánh xích).** n=4, chuỗi tới epoch 4. Attester 1 nộp link
**rộng** `<1,4>` rồi link **hẹp** `<2,3>`. Có slashing reason `surround_vote` không?
Nếu nộp **ngược** (hẹp trước, rộng sau)? Còn link **kề** `<1,2>` rồi `<2,3>`?

<details><summary>ĐÁP ÁN</summary>

`<1,4>` rồi `<2,3>`: `_check_surround` kiểm `s1<s2<t2<t1` = `1<2<3<4` ✓ ⇒
**surround_vote** (`test_surround_emits_slashing`). Ngược lại (`<2,3>` rồi `<1,4>`):
nhánh thứ hai `s2<s1<t1<t2` = `1<2<3<4` (với new=rộng) ✓ ⇒ vẫn phát hiện
(`test_surround_both_orderings`) — vì thế điều kiện có **hai chiều** OR. Kề
`<1,2>`,`<2,3>`: `1<2` nhưng `t1=2 < t2=3` (không bao) ⇒ **không** surround, và
target khác nhau ⇒ **không** double vote ⇒ **0** slashing
(`test_nested_non_surround_does_not_slash`). **Bẫy:** "bao" nghĩa là *một khoảng
nằm lọt hẳn trong khoảng kia*, không phải chỉ chồng lấn/kề nhau.
</details>

**G6 — accountable safety (khái niệm, không chạy).** Hai checkpoint mâu thuẫn C và
C' cùng được finalise. Vì sao điều đó *bắt buộc* kéo theo ≥⅓ tổng stake đã ký một
bản tin slashable? Và khác gì PBFT — nơi hai giá trị cùng chốt cũng cần >f node xấu?

<details><summary>ĐÁP ÁN</summary>

Mỗi finalise cần supermajority link ≥⅔ stake. Hai link cho C và C' mâu thuẫn ⇒ theo
số học giao-quorum, phần **giao** của hai tập ⅔-stake ≥ `⅔+⅔−1 = ⅓` stake; validator
trong giao đã ký cho *cả hai* checkpoint mâu thuẫn ⇒ vi phạm **double** hoặc
**surround** vote ⇒ slashable. Nên ≥⅓ stake **chứng minh được** có tội (Casper paper,
câu ngay sau Figure 2). Khác PBFT: PBFT cũng cần giao ≥ f+1 kẻ xấu, nhưng thủ phạm
**vô danh** — không có bằng chứng ký gán tội cá nhân. Casper biến "an toàn dưới
ngưỡng" thành "an toàn + **quy trách nhiệm** trên ngưỡng". **Bẫy:** accountable
safety **không** ngăn được kẻ có >⅓ stake phá an toàn — nó chỉ đảm bảo đòn phá đó
**đắt** (đốt ≥⅓ stake) và **định danh được**.
</details>

## 6. Phòng thủ (câu hội đồng dễ hỏi — trả lời mẫu, neo nguồn)

**PT1 — "Vì sao đúng *hai* điều kiện slashing? Sao không một, không ba?"**
Hai điều răn phủ đúng hai cách một validator có thể ký mâu thuẫn *chứng minh được*:
(I) **double vote** — hai phiếu khác nhau cùng target height (equivocate tại một
mốc); (II) **surround vote** — bỏ một phiếu bao/lọt trong phiếu cũ của chính nó (đảo
một checkpoint đã cam kết). Ghép hai điều kiện là **đủ và cần** để chứng minh định lý
accountable-safety: bất kỳ hai finalise mâu thuẫn nào cũng buộc ≥⅓ stake phạm *ít
nhất một* trong hai. Neo: `raw/casper.pdf` §3 **Figure 2 "The two Casper
Commandments"** — *"I. h(t1)=h(t2) ... OR II. h(s1)<h(s2)<h(t2)<h(t1)"*; và
`wiki/algorithms/pos.md` §Slashing conditions. Anchor số: n=4 stake đều → một kẻ =
3/12 = 0.25 stake slashable.

**PT2 — "Accountable safety khác gì an toàn của PBFT?"**
Cả hai dựa cùng số học giao-quorum (PBFT: giao ≥ f+1 node; Casper: giao ≥⅓ stake).
Điểm cộng của Casper là **quy trách nhiệm**: kẻ phá an toàn để lại **bằng chứng ký**
gán tội cá nhân, cọc bị đốt. PBFT an toàn nhưng thủ phạm **vô danh** — không đốt được
ai. Casper nâng Agreement từ "đảm bảo theo ngưỡng" lên "ngưỡng **+ răn đe kinh tế**".
Neo: `wiki/algorithms/pos.md` §Accountable safety +
`wiki/sources/2026-04-21_buterin-griffith-casper-ffg-2017.md` takeaway #3
(*"an adversary with >⅓ stake can violate safety, but must burn >⅓ of total stake"*).

**PT3 — "Điểm yếu lớn nhất của họ này là gì?"**
Nói thẳng hai cái. (a) **Finality chậm**: two-round justify→finalise ở *mức epoch* ⇒
time-to-finality đo bằng **phút** (Ethereum: một epoch ~6.4 phút), so với sub-giây
của PBFT. Đổi lại: chịu delay **duyên dáng** — trễ chỉ *kéo dài* finality, không phá
an toàn ("finalisation simply stalls"). (b) **Weak subjectivity**: node mới/offline
lâu phải tin một checkpoint gần đây từ nguồn xã hội — không cơ chế on-chain nào đóng
được. Neo: `wiki/algorithms/pos.md` §Weaknesses to foreground + §Behaviour under
network delay.

**PT4 — "Sim của bạn *thật sự* làm gì, và *không* làm gì?"** (ranh giới phạm vi)
**Có**: two-round FFG cân stake (justify→finalise, test division-free `3·stake ≥
2·total`), proposer chọn theo stake (T33), **phát hiện** double/surround vote (T70) +
metric `slashable_stake_fraction`. **Không** (cố ý, deferred): **không** áp phạt/đốt
cọc (chỉ *detect*, không burn); **không** báo cáo "safety-cost budget" `~α/3`;
**không** LMD-GHOST fork choice / reorg; stake_table **cố định** cả run, không rotate;
không cây checkpoint qua nhánh. Và như mọi giao thức trong sim: **không** chữ ký thật
(§15) ⇒ slashing là *detection trên vote quan sát được*, không phải verify chữ ký mật
mã. Neo: `wiki/algorithms/pos.md` §Simulator mapping (Implemented / **Not
implemented**) + ##Revisions 2026-06-04 (T70 sửa lại chính section này vì bản cũ
overclaim). Đây là caveat = rào chắn phạm vi, không phải lỗ hổng ẩn.

**PT5 — "Slashing chỉ răn được ai? Giả định nào chống lưng nó?"**
Chỉ răn kẻ **duy lý kinh tế** — giả định `economic rationality`: validator coi cọc
nặng hơn mọi lợi từ chiến lược equivocate. Kẻ *phi lý* (muốn phá bằng mọi giá) hoặc
kẻ nắm >⅓ stake sẵn sàng đốt cọc thì slashing **không** ngăn được — nó chỉ khiến đòn
phá *đắt* và *định danh được*. Ngoài ra sim **chưa** áp phạt nên trục "chi phí kinh
tế" hiện là *lý thuyết bài báo / future work*, không phải output. Neo:
`wiki/algorithms/pos.md` §Model and assumptions (Economic rationality) +
§Behaviour under adversarial conditions (Safety-cost budget — deferred).

## 7. Giải thích lại (Feynman) + ghi sổ

Tự nói to, không nhìn code, ~2 phút:
1. Một epoch đi từ ATTESTATION tới `decided` qua những trạng thái/link nào? (justify
   → finalise, hai link liên tiếp.)
2. Vì sao ngưỡng đo bằng **stake** không **count**, và vì sao viết `3·stake ≥
   2·total`?
3. Hai điều răn slashing là gì? `record_vote` tách DUPLICATE (vô hại) khỏi CONFLICT
   (slashable) thế nào?
4. Hai điểm gai phòng thủ: accountable safety (quy trách nhiệm, khác PBFT) và
   finality-chậm (đánh đổi của two-round mức epoch).

Hổng chỗ nào → quay lại §4. Xong: cập nhật `progress.md` (điểm 1–5, đã thông, còn
mờ). Câu mang sang M09 (Snowman): rời hẳn thế giới quorum-tất-định sang **finality
xác suất** (subsampled voting, biên `ε`) — con số `α_c`/`β` đang treo từ M00.
