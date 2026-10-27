# Ticket 20 operator capacity experiments, historical

Status: HISTORICAL, superseded by the OPEN store-architecture decision. The reviewer withdrew the512KiB/128-request hard-quota design after sizing diagnostics and maximal accepted records. Policy imperatives inside this preserved experiment log are past proposals, NOT current requirements or permission to implement. The measurements retain their stated fixture/scope limits; a small-store timing pass is not a scalability claim.

Current decision: [Store architecture options](TICKET-20-STORE-DECISION.md). Current wires: [Operator contract](TICKET-20-OPERATOR-ROUTES.md).

## K6 benchmark and concurrency proof, required before activation

The two original holds are explicitly (a) snapshot+allowlist projection+canonical scope/hash/token while engine/catalog remain held, (b) WHOLE create, including that capture plus parent/producer checks and ALL existing prepare_request packet/reserve/brief/enqueue/queued persistence. Timing only put_packet or splitting nested reentrant spans does not measure (b). Peer require_active wait is a separate latency measurement. Both were proposed <=0.300s.

### Observed baseline, existing path FAILS the proposed budget

Reviewer-requested spike executed2026-10-25 from an ignored .audit-tmp script against unchanged product3f40912. Real MessageStore/ArtifactStore/catalog/queue/private-brief IO, real fsync/default atomic_json, fixture-supported managed binding with controlled process/native observations only.100 existing imported lineages,10 of them with exact524288-byte heads;10 distinct revisions, so lineage count stays100 while requests/index grow. Each packet has1000 real stored messages starting id0, exact2097152 canonical bytes, Unicode/CRLF, scope sha2561c69d2a89d37aafee3f8ea5dec4f1f892ec60592964d361b4e281556a9f8d2bf. Source acquisition is a prototype detached copy of already allowlisted rows, not the not-yet-built snapshot/allowlist or run-projection helper. No API/provider/network/native execution. Thus these are design measurements, not K6 acceptance or a bound for the unimplemented builder.

| Sample | snapshot hold s | whole-create hold s |
| --- | --- | --- |
|1|0.041512|0.411677|
|2|0.041037|0.440929|
|3|0.039318|0.470061|
|4|0.039396|0.503954|
|5|0.040400|0.552584|
|6|0.039841|0.561640|
|7|0.040310|0.604775|
|8|0.040493|0.653826|
|9|0.040108|0.684326|
|10|0.040841|0.684864|

Peer maximum require_active wait0.677207s. Outermost acquisition waits0.000005-0.000709s were recorded separately. All ten whole-create samples exceed0.300s; snapshot-only does not. The snapshot prototype measures copy/projection/scope hashing, not producer/token/run-helper validation, so it is not acceptance of full hold(a). Whole-create includes current producer/parent/audit token work and existing durable prepare steps. Receipt and script retained locally in .audit-tmp/ticket20_operator_spike.{json,py}, shellc11e87d9 exit0. Exit0 means measurement completed, NOT a passing timing gate. Cleanup joined peer and invoked fixture shutdown/temp cleanup; the shell is stopped. The accepted source/count/parent caps remain unchanged. **The one-hold mechanism is rejected; the timing contract is NOT cleared.**

### Reviewed phase split, prototype still FAILS publication budget

Reviewer ACCEPTED the split with M1-M4, preserving packet -> reserve -> brief -> enqueue. The accepted structural phases replace the earlier proposal that staged a secret-bearing brief before a request:

1. Capture/project/validate under engine/catalog. SessionStore lock is released before MessageStore. Build exact packet/audit/token and verify parent/current producer/head; no durable write.
2. Stage ONLY the immutable packet OUTSIDE engine/catalog. Add a separate unguarded root-bound store staging API; guarded put_packet and existing prepare_request stay unchanged. Use the same private created-object receipt semantics as import: created vs reused, uncertain I/O receipt null, count only this invocation's objects still unreferenced under the store metadata lock. Orphans are reported, never deleted and never counted as created requests/versions. Stage after replay/classification check, never overwrite.
3. Short reserve boundary: re-capture/recompute source/token and recheck Stop/run state, channel, producer, parent/pending CAS. Fresh scope.sha256 AND byte_length must equal the staged scope (and full scope fields must agree); difference =>409 artifact_preview_stale with staged orphan report. A private same-invocation plan may skip reading the2MiB packet during reserve ONLY after verifying its root-bound file fingerprint (mtime_ns,size), as accepted for import plans. Full _persist index validation/real fsync remain. Persist PREPARED then release boundary: this is creation's durable linearization point.
4. Private brief put-once OUTSIDE the boundary, AFTER reservation. No brief with a seal secret is created without a durable request. Stop may cancel the prepared request during this phase; a brief then grants nothing because publication rechecks state. Existing after-reserve/before-brief and after-brief/before-enqueue recovery seams remain.
5. Separate publication boundary: re-read exact request, require still prepared/uncancelled, recheck current producer/channel/head, existing coordinator-authorized enqueue and queued mark. Stop between reserve/publish sees PREPARED and cancels without enqueue. No ledger callback into owners, raw paths closed, no cross-invocation eligibility cache. Incomplete publication reports actual durability/current row, never blind retry. The existing prepare_request and guarded put_packet stay byte-for-byte unchanged; recovery/resume retain their existing path.

Private staged-plan stat checking shares import's limitation: mtime_ns+size is not a cryptographic proof against an out-of-process writer deliberately restoring both; put-once internal writes plus final metadata/CAS checks remain the accepted protection. No new persisted schema, operation journal or public capability flag. Exact plan/receipt/error signatures await review/freeze. On failed stage/reserve, the eventual error projection must include counted orphan metadata (objects/bytes, or null with staging_io_unconfirmed); it may never claim a new request from staging alone.

### Phased prototype result, retained failure

Ran the reviewed phases against unchanged product6da23f7 in an ignored script, with the same100-lineage/10-revision,2097152-byte/1000-message,524288-byte-parent shape as the first spike. Real fsync/default writer, same source hash; controlled supported managed observations only. Prototype uses the existing reserve_request with a PRIVATE instance-local _packet reuse patch ONLY during reserve, verifying exact staged stat first; _persist/full-index validation are unmodified. Publication uses the REAL coordinator validate_enqueue and full packet re-read (no authorization bypass). The unguarded packet stage is a script-local call to existing _put_bytes plus private receipt/stat construction, not a product API. Capture still uses a prototype batch copy of known allowlisted selected-channel rows; no final operator builder/run helper/auth/race/crash acceptance exists yet.

An Event-controlled peer attempts require_active inside each measured hold and concurrently during the two outside phases. Hold timing includes peer-attempt synchronization and every nested operation; peer completion is awaited outside the boundary before the next phase, and total wall includes that scheduling. This isolates per-phase waits; it does not prove fairness for an implementation that immediately re-acquires without giving a waiting peer progress. The final real benchmark must also exercise consecutive phases without this rendezvous and retain the every-wait bound.

| Sample | capture hold s | packet stage wall s (outside) | reserve hold s | brief wall s (outside) | publish hold s | total wall s |
| --- | --- | --- | --- | --- | --- | --- |
|1|0.082033|0.042633|0.122113|0.003345|0.184881|0.436507|
|2|0.074288|0.042224|0.135028|0.002840|0.205187|0.461302|
|3|0.075719|0.042860|0.147657|0.002655|0.220363|0.490816|
|4|0.078272|0.043473|0.166095|0.002846|0.244147|0.536391|
|5|0.075144|0.042295|0.176339|0.002758|0.250716|0.548811|
|6|0.079496|0.043690|0.195944|0.002845|0.261608|0.584967|
|7|0.073763|0.043661|0.217611|0.002957|0.275277|0.615032|
|8|0.074319|0.042258|0.219318|0.003146|0.295678|0.636390|
|9|0.076586|0.043340|0.236379|0.002971|0.327580|0.688397|
|10|0.075008|0.042861|0.272222|0.003280|0.319327|0.714254|

| Sample | peer wait capture s | peer wait packet stage s | peer wait reserve s | peer wait brief s | peer wait publish s |
| --- | --- | --- | --- | --- | --- |
|1|0.082491|0.030331|0.122492|0.000686|0.185335|
|2|0.074880|0.030546|0.135484|0.000776|0.205682|
|3|0.076183|0.030414|0.148113|0.000748|0.220806|
|4|0.078762|0.031306|0.166520|0.000836|0.244578|
|5|0.075592|0.030534|0.176725|0.000713|0.251231|
|6|0.079903|0.019966|0.196326|0.000900|0.262006|
|7|0.074229|0.031135|0.218087|0.000685|0.275757|
|8|0.074783|0.030025|0.219783|0.000741|0.296216|
|9|0.077064|0.031274|0.236840|0.000886|0.327973|
|10|0.075458|0.030654|0.272690|0.000838|0.319730|

**FAIL:** publication samples9/10 hold0.327580/0.319327s, peer waits0.327973/0.319730s exceed0.300s. Maximum capture0.082033s, reserve0.272222s; total create wall0.436507-0.714254s. Do not round0.327580 down to the threshold, discard the late samples, reset index between samples or call this a K6 pass. Receipt retains every phase/acquisition duration, all50 peer waits, total wall, source hash, fsync_mocked:false and persist_validation_bypassed:false in .audit-tmp/ticket20_operator_phased_spike.json; script adjacent. Tracked shella1bcfec2 exit0 means measurement completed only. Script asserts successful fixture cleanup, absent temp root and joined peer; no shell/native/provider resources remain.

### Accepted invocation evidence extension and passing DESIGN prototype

Reviewer accepted invocation-scoped packet evidence for coordinator validate_enqueue. It is private context-local state created during ONE operator create invocation, cleared in finally. It never enters the HTTP body, envelope, ledger or persisted schema, nor another thread/request, claim, poll, admission, recovery or resume. At the pre-ledger hook it is usable only when root, staged-file stat(mtime_ns,size), full scope including digest/length, and frozen audit all match this invocation; ANY absence/mismatch falls back to the existing full packet read. All request/live producer/channel/brief/envelope checks and _persist whole-index validation remain. Claim-time get_brief/get_delivery ALWAYS fully read and validate the packet before generation, even on a plan publication. A same-size/mtime-restored external edit can evade the publication stat check but MUST be caught by that full claim-time hash check; this residual is stated, not treated as a cryptographic stat proof.

Two sequential ignored prototype runs on unchanged productac30259 used the same growing-index100-lineage/10-revision,2MiB/1000-message/id0/UnicodeCRLF/512KiB-parent shape with real fsync. The script uses ContextVars around reserve and the validate_enqueue packet read only; existing checks and final index validation execute. It asserts cleared context after each use and default context in the peer. These assertions are not the full evidence-isolation/fallback/tamper regression suite, which remains root-owned before implementation acceptance. No product API or source/test file changed. The final builder/run-preset/strict HTTP work is still absent: these are selected-channel mechanism measurements, not final K6 or component clearance.

The isolated run Event-aligns a peer with each phase; the FAIRNESS run has a second thread repeatedly call require_active immediately, with NO wait-for-peer-completion rendezvous, pause or yield between main-thread phases. The peer records every wait, including calls spanning adjacent phases. Total wall is reported independently; no nested phase is relabeled as a whole-create hold.

#### Isolated run, ten samples

| Sample | capture hold s | packet stage wall s (outside) | reserve hold s | brief wall s (outside) | publish hold s | total wall s |
| --- | --- | --- | --- | --- | --- | --- |
|1|0.079236|0.043870|0.131276|0.003421|0.146748|0.406294|
|2|0.078637|0.046132|0.148299|0.003042|0.166895|0.444560|
|3|0.075122|0.043967|0.156665|0.003154|0.177101|0.457624|
|4|0.073768|0.042295|0.172445|0.003068|0.193133|0.486288|
|5|0.073979|0.043017|0.186143|0.003003|0.204222|0.512124|
|6|0.074009|0.041836|0.209214|0.003188|0.222751|0.552710|
|7|0.074363|0.042273|0.224466|0.002911|0.237690|0.583240|
|8|0.074136|0.043275|0.235080|0.003126|0.251758|0.608777|
|9|0.073857|0.042311|0.241458|0.003130|0.286883|0.649086|
|10|0.073549|0.043817|0.267801|0.003076|0.283688|0.673602|

Every recorded peer require_active wait in seconds, in completion order (raw precision, no discarded records):

```json
[0.07973340002354234,0.03163069998845458,0.1317190999398008,0.0007260000566020608,0.1472952999174595,0.07909240003209561,0.021512300008907914,0.14879929996095598,0.0007810000097379088,0.16726809996180236,0.07558990002144128,0.03107969998382032,0.15724730002693832,0.0007409999379888177,0.1774738000240177,0.07424760004505515,0.029817100032232702,0.17290000000502914,0.0009215000318363309,0.19357620005030185,0.07434249995276332,0.030921500059776008,0.18669979996047914,0.0007686000317335129,0.20485490001738071,0.0744942999444902,0.029270999948494136,0.20969639997929335,0.0008001999231055379,0.2232912000035867,0.07483370008412749,0.03056400001514703,0.22494270000606775,0.0007012999849393964,0.23807570000644773,0.07451780000701547,0.03144279995467514,0.23551269993185997,0.0007946999976411462,0.2521372999763116,0.07430570002179593,0.03008830000180751,0.24183020007330924,0.0007535999175161123,0.2873052000068128,0.07399359997361898,0.031136700068600476,0.26830390002578497,0.0007697000401094556,0.2842020000098273]
```

Peer calls=50, maximum hold=0.286882700s, maximum peer wait=0.287305200s.

#### Fairness run, ten samples

| Sample | capture hold s | packet stage wall s (outside) | reserve hold s | brief wall s (outside) | publish hold s | total wall s |
| --- | --- | --- | --- | --- | --- | --- |
|1|0.077561|0.043057|0.126435|0.003447|0.143935|0.397782|
|2|0.076496|0.045251|0.142976|0.003180|0.160783|0.432594|
|3|0.074622|0.043828|0.155609|0.003631|0.176505|0.457789|
|4|0.073316|0.044105|0.170377|0.003692|0.192060|0.487145|
|5|0.077355|0.051296|0.192721|0.003359|0.205808|0.534221|
|6|0.073934|0.042909|0.205719|0.003073|0.218025|0.547319|
|7|0.074096|0.044382|0.214158|0.003536|0.234013|0.573900|
|8|0.075184|0.042656|0.248696|0.003398|0.248400|0.621956|
|9|0.075580|0.043092|0.244847|0.003482|0.287293|0.657900|
|10|0.080319|0.044125|0.260046|0.003214|0.287088|0.678716|

Every recorded peer require_active wait in seconds, in completion order (raw precision, no discarded records):

```json
[0.0004611000185832381,0.00038920005317777395,0.0003274999326094985,0.0003823000006377697,0.1080591999925673,0.00044490001164376736,0.00039760000072419643,0.0003988000098615885,0.0003237000200897455,0.0003765999572351575,0.00033199996687471867,0.00032240001019090414,0.0065876999869942665,0.0004328000359237194,0.0006976999575272202,0.00040719995740801096,0.00040520005859434605,0.0003499999875202775,0.0003095000283792615,0.000560399959795177,0.0004905000096186996,0.0004024999216198921,0.00039080006536096334,0.12728980008978397,0.000622799969278276,0.0005193999968469143,0.0005653999978676438,0.00037219992373138666,0.0003192999865859747,0.0003602000651881099,0.0003174000885337591,0.00031409994699060917,0.0003105999203398824,0.14453659998252988,0.000345399952493608,0.0003515999997034669,0.0003942999755963683,0.10815149999689311,0.00045009993482381105,0.000407799961976707,0.0004093999741598964,0.0004088999703526497,0.00036100007127970457,0.00033430010080337524,0.00032190000638365746,0.006978200050070882,0.0006108999950811267,0.0005471999756991863,0.0005058000097051263,0.000519599998369813,0.0004285998875275254,0.00035069999285042286,0.00032650004141032696,0.00042619998566806316,0.0004456000169739127,0.00034330005291849375,0.00034060003235936165,0.00035550002939999104,0.143901800038293,0.0006313999183475971,0.0005209000082686543,0.0003989000106230378,0.00031969998963177204,0.0003295999485999346,0.00048719998449087143,0.00032049999572336674,0.00033059995621442795,0.16132489999290556,0.00034879997838288546,0.00032679992727935314,0.00031999999191612005,0.10610109998378903,0.0004417999880388379,0.0004026999231427908,0.00038790004327893257,0.0004336999263614416,0.00045119994319975376,0.00045000005047768354,0.00656360003631562,0.0004091999726369977,0.00047369999811053276,0.00039249996189028025,0.00035149999894201756,0.00032220000866800547,0.00035880005452781916,0.0003228000132367015,0.0003325999714434147,0.0004056999459862709,0.00034559995401650667,0.00032650004141032696,0.00031949998810887337,0.15641869988758117,0.0004844000795856118,0.0005314000882208347,0.00047229998745024204,0.00034330005291849375,0.00037949997931718826,0.00033799989614635706,0.0004051000578328967,0.0004533999599516392,0.00046749995090067387,0.1770979999564588,0.0004205999430269003,0.00033439998514950275,0.0003250000299885869,0.10496599995531142,0.0005071000196039677,0.0004143000114709139,0.0003931999672204256,0.0004409999819472432,0.0004311000229790807,0.00043649994768202305,0.006922699976712465,0.00048159994184970856,0.0005189999938011169,0.00034439994487911463,0.0003234000178053975,0.00032380002085119486,0.00030890002381056547,0.00031969998963177204,0.00043080002069473267,0.0003198999911546707,0.0003133999416604638,0.0003197999903932214,0.17115489998832345,0.000539399916306138,0.00047109997831285,0.0006046999478712678,0.0004104999825358391,0.00032920006196945906,0.0003347999881953001,0.0004708000924438238,0.0004230000777170062,0.00039599998854100704,0.192695900099352,0.0004205000586807728,0.0004121999954804778,0.11552660004235804,0.00046580005437135696,0.000408399966545403,0.00039770000148564577,0.0003988000098615885,0.0003282000543549657,0.0003261000383645296,0.0067659999476745725,0.0006258999928832054,0.00048559997230768204,0.0004285000031813979,0.0003541000187397003,0.00032049999572336674,0.00032510003075003624,0.0003208999987691641,0.0003306999569758773,0.00031589996069669724,0.00034060003235936165,0.00036239996552467346,0.0003309999592602253,0.00033329997677356005,0.0003432999365031719,0.19354940007906407,0.000555400038138032,0.00045350007712841034,0.0005175000987946987,0.00039240007754415274,0.0004165999125689268,0.00039379997178912163,0.00035880005452781916,0.00032359990291297436,0.0003215000033378601,0.2063695000251755,0.0003402000293135643,0.0003263000398874283,0.0003421000437811017,0.10452749999240041,0.0004827999509871006,0.0003942999755963683,0.00038709992077201605,0.0003829000052064657,0.0003743999404832721,0.00033870001789182425,0.006371999974362552,0.0005945999873802066,0.0006546999793499708,0.00038049998693168163,0.0003421999281272292,0.00039409997407346964,0.0003209999995306134,0.00031160004436969757,0.00032760004978626966,0.0004120999947190285,0.00031839997973293066,0.00031409994699060917,0.0003138999454677105,0.2066542999818921,0.0004627000307664275,0.0003795999800786376,0.0004374999552965164,0.00034769997000694275,0.00041039998177438974,0.00043919996824115515,0.0004062999505549669,0.00039409997407346964,0.21857280004769564,0.0004396000877022743,0.00040460005402565,0.10534829995594919,0.0005193999968469143,0.0004667999455705285,0.0003931999672204256,0.000485299970023334,0.00046170002315193415,0.006605600006878376,0.0008599000284448266,0.000588199938647449,0.0005765999667346478,0.00037260004319250584,0.0003355999942868948,0.0003192999865859747,0.000319099985063076,0.0003573000431060791,0.0004032999277114868,0.0003261000383645296,0.0003209999995306134,0.00031560007482767105,0.0003160000778734684,0.2149904000107199,0.0006164000369608402,0.0005272999405860901,0.00045149994548410177,0.00037260004319250584,0.0003228000132367015,0.0003443000605329871,0.0003421000437811017,0.00031969998963177204,0.0003266999265179038,0.0003256000345572829,0.23459849995560944,0.0003397000255063176,0.00032750004902482033,0.0003231000155210495,0.10588489996735007,0.00036720000207424164,0.00033950002398341894,0.0003298999508842826,0.00032540003303438425,0.0003336999798193574,0.0003369000041857362,0.0003295999485999346,0.00031269993633031845,0.006513700005598366,0.0004588000010699034,0.0005052000051364303,0.0003353999927639961,0.0003124999348074198,0.00030860002152621746,0.0003200999926775694,0.00033249997068196535,0.00032759993337094784,0.0005889000603929162,0.0003589000552892685,0.24958810000680387,0.0005749000702053308,0.0005900000687688589,0.000461899908259511,0.00034360005520284176,0.00035180000122636557,0.00034909998066723347,0.00032540003303438425,0.00031859998125582933,0.0003151999553665519,0.24901360005605966,0.00041390000842511654,0.000394499977119267,0.10616139997728169,0.0004539999645203352,0.00040579994674772024,0.0003532000118866563,0.0003499999875202775,0.0003333999775350094,0.00032279989682137966,0.0003231000155210495,0.006388899986632168,0.0006177999312058091,0.0005849000299349427,0.0004288000054657459,0.0003584000514820218,0.00032490002922713757,0.0003339000977575779,0.00031130004208534956,0.0003256000345572829,0.0003605000674724579,0.000344799947924912,0.00034629995934665203,0.0003229000139981508,0.24574819998815656,0.0006567999953404069,0.0005308000836521387,0.00048530008643865585,0.0004100000951439142,0.0003499999875202775,0.00034200004301965237,0.00034359993878751993,0.00031749997287988663,0.00041259999852627516,0.2878871000139043,0.0003429000498726964,0.00032789993565529585,0.00032600003760308027,0.11134669999592006,0.0005783999804407358,0.0004494000459089875,0.0003953000996261835,0.0004081000806763768,0.0003312000771984458,0.00032439990900456905,0.0068805000046268106,0.0005817000055685639,0.00045489997137337923,0.00044689991045743227,0.00037510006222873926,0.0003375000087544322,0.00033579999580979347,0.0003233000170439482,0.00032430002465844154,0.0003630999708548188,0.00042619998566806316,0.00038320000749081373,0.00033850001636892557,0.0003344999859109521,0.26095889997668564,0.0006422000005841255,0.0006767000304535031,0.00042729999404400587,0.0003394000232219696,0.0003974999999627471,0.00032620003912597895,0.0003247999120503664,0.000354300020262599]
```

Peer calls=338, maximum hold=0.287292600s, maximum peer wait=0.287887100s.

The isolated maximum hold/peer wait is0.286882700/0.287305200s. Consecutive-phase fairness maximum is0.287292600/0.287887100s across338 peer calls; every measured hold AND recorded wait is<=0.300s in both runs. The remaining margin is small and is NOT permission to waive the final real-builder benchmark. Total wall isolated0.406294-0.673602s, fairness0.397782-0.678716s. All prior one-hold and first-split failures remain above. The full receipts include acquisitions, per-phase labels, source hash and orphan counts in ignored ticket20_operator_evidence_spike-{isolated,fairness}.json; script adjacent. Tracked isolatedbce8bd2b and fairness148719f1 both exit0; both assert temp root removed and peer joined. Source hash remains1c69d2a89d37aafee3f8ea5dec4f1f892ec60592964d361b4e281556a9f8d2bf. No native/provider/network or final operator acceptance claim.

Reviewer pre-authorized fallback IF the real-builder publish hold or fairness later fails: split publication into enqueue and queued-mark boundaries. The queued mark must then no-op/refresh when a worker has already claimed and activated, never fail active->queued. Before relying on this fallback, root must add Event tests for claim-between-enqueue-and-mark and crash-between-them. This fallback was NOT needed, implemented or measured in the passing prototype; it does not silently change the primary five-phase design.

Required additional root gates for evidence: test_packet_evidence_is_invisible_to_other_thread_and_after_invocation; test_publication_evidence_mismatch_falls_back_to_full_packet_read (root/stat/scope/audit/absence each); test_same_size_mtime_packet_tamper_refused_before_generation; test_nonplan_enqueue_resume_and_recovery_keep_full_packet_validation. No evidence reuse on get_brief/get_delivery. Every mismatch preserves today's full-read outcome rather than inventing a new failure/refusal solely from a missing plan.

Required eventual root gate remains test_capped_source_snapshot_and_create_boundary_holds_with_peer_require_active. Named phases are snapshot, reserve recheck+commit, publish+queued mark; total wall is separate. The FINAL gate is now AT the finite byte/request ceiling and requires the30ms margin stated below, for selected-channel AND run-projection modes with exact source/parent caps and real fsync. The earlier ten-growing-index measurements above remain historical design evidence, never a final capacity proof. A full create total can exceed0.300s only by releasing the boundary between these phases; every individual hold and peer wait still meets the stricter ceiling test.

Separately test1001 messages/2097153 bytes no durable request/brief/enqueue, consistent capture under edit/delete/Stop, stale token/parent CAS races, prepared Stop in the stage-to-publish gap, crash at each phase, stage failure/orphans and stored replay never reading changed chat. Source cap does not promise every model can consume the context; existing wrapper refusals stay visible. These future tests/implementation remain blocked pending mechanism and exact payload review.

Reviewer-required root red-first gates for the split are explicit: test_stop_between_reserve_and_publish_cancels_prepared_without_dispatch (Event-interleaved actual Stop); test_crash_after_packet_stage_before_reserve_reports_orphan (no brief/request/queue); test_crash_after_reserve_before_brief_recovers and test_crash_after_brief_before_enqueue_recovers (existing prepared recovery); test_source_change_before_reserve_refuses_preview_stale; test_split_create_matches_prepare_request_stored_state (same audit, equivalent durable row/packet/brief/queue semantics); test_concurrent_same_request_create_has_one_winner_and_one_replay. Stage receipt created/reused/unknown-I/O accounting, foreign-root/stat tamper and all unchanged recovery/Stop suites remain required. These are planned tests, not executed prototype coverage. The accepted enqueue-evidence extension adds the strict negative authority tests named above before implementation acceptance.

## Finite creation capacity, G1 choice (a), PROPOSED measured ceiling

Choose a finite measured admission ceiling for this ticket, not incremental _persist validation. New limits are GLOBAL per ArtifactStore/data directory: MAX_CREATE_REQUESTS=128 total saved requests and MAX_CREATE_INDEX_BYTES=524288 accounted bytes, whichever is reached first. Count ALL local/imported/live/terminal requests, including revisions and failed/cancelled attempts. Never count only live rows or pretend export frees capacity. No purge, automatic eviction, schema migration or deletion is added. Bodies/packets live separately; copied source refs and version provenance consume index space, so a source-heavy store can fill the byte ceiling well before128 attempts. Existing larger stores/imports remain storage-valid and readable; they simply cannot admit NEW authoring requests under this ceiling. Read/library/download/immutable replay/cancel/Stop/settlement and existing explicit recovery remain available. This is a NEW creation-admission rule, not a new validator cap on retained artifacts or a promise about latency of every existing recovery path.

Index byte definition is EXACT existing atomic_json encoding length: len(json.dumps(candidate_index,ensure_ascii=True,allow_nan=False).encode('utf-8')), with default separators and NO newline, matching persisted index.json. Account INDEX_HEADROOM_BYTES=256 for timestamp/reason representation growth. For a new audit construct prospective prepared and actual queued/queued_behind_review candidates without writing, take the larger encoded length plus256, and require<=524288; require prospective request count<=128. Pure sizing/metadata reads release their store lock before another owner call. No body reads or weakened/full-index delta validator. The256 is explicit accounted overhead, never fabricated as stored bytes. The actual queued candidate is recomputed again before publication. Exact-ceiling admission is inclusive; one byte/request over refuses.

Check capacity before staging a NEW request (after full audit is known), inside the reserve boundary against current index/CAS, and inside publication before enqueue against the latest queued candidate. An early current-count/current-size failure may refuse before capture/staging. A change between phases can produce a recorded PREPARED capacity refusal without enqueue; return current row and needs_resume:true. Do not roll back or claim a new queue record. Immutable same-id replay is checked FIRST and remains200 even when creation capacity is now full. Preview tokens remain audit-only; capacity is independently rechecked, not a new field in the immutable audit or token. No public switch raises the limits.

CapacityProjection EXACT = {limits:{index_bytes:524288,requests:128},headroom_bytes:256,current:{index_bytes:nonnegative_int,requests:nonnegative_int},projected:{index_bytes:nonnegative_int|null,requests:nonnegative_int},fits:bool|null}. current.index_bytes is the actual current encoding size; projected.index_bytes is max prospective prepared/queued encoding BEFORE adding headroom. fits means projected.index_bytes+256<=limit AND projected.requests<=128. projected.requests is current+1 for a new id, unchanged for a replay. If no verified producer exists to construct an exact audit, projected.index_bytes:null and fits:null unless the count/current bytes already prove failure (fits:false). No guessed estimate is labeled exact. Every Preview carries capacity. Known capacity failure makes Preview.available:false, reason:artifact_store_capacity,preview_token:null, regardless of producer state; otherwise an unavailable producer keeps its existing capability reason. ProducerChoice itself describes producer eligibility only. AvailabilityReason=CapabilityReason|artifact_store_capacity, where CapabilityReason remains exactly artifact_capability_missing|runtime_unverified|producer_unavailable|unmanaged_producer|capability_binding_changed.

The table's typed store_capacity409 is the only new admission refusal. Its error body adds CapacityProjection and, only after saved effects, the existing guarded durability/current-row/dispatch/resume/staging fields. Fixed UI/preview disclosure code artifact_store_capacity expands to the fixed text in the table, plus the reader's finite-capacity explanatory text from CHANNELS.md. Capacity is never reset by channel delete or export. Retained packet/brief orphans do not consume the indexed-request counter; diagnostics still report them and backups/lifecycle ignore them.

### Capacity measurement and margin

The earlier ten-growing-index pass is INSUFFICIENT for unbounded creation and does not set this ceiling. The design now enforces a boundary on prospective retained metadata. Candidate grid tested on this Windows host:2MiB accounted/128 requests pilot fails max hold0.376639s/peer0.347092s;1MiB/128 requests pilot0.245172s, initial ten without capacity-check cost max0.257505s/peer0.239295s. Once the prospective-size check itself was INCLUDED in capture/reserve/publication,1MiB ten-run sample2 reserve0.439543s/peer0.440551s FAILS, and samples4/10 also miss the30ms margin (0.286913/0.274949s). Those runs are retained, never averaged or reclassified as passing. The512KiB ceiling is the largest ACCEPTED candidate in this tested power-of-two grid, a conservative rounded ceiling, not a claim to a mathematical maximum byte on all machines.

Selected ceiling test: TEN independent fresh stores EACH at128 post-create requests (127 prior requests/versions across100 lineages), exact524032 persisted index bytes+256 accounted headroom=524288, exact2097152-byte/1000-message Unicode/CRLF/id0 packet,512KiB parent, real fsync and full _persist validation. Fill the prior index primarily with valid packet-ref structures copied into imported audit/version provenance, not just an easy blob string. The final current audit is byte-padded with valid bounded instruction text for exact size. The prospective size/count check is actually timed in EACH capture/reserve/publication; no exclusion of admission cost. Immediate-loop peer contention has no per-phase rendezvous. Setup is outside timing; producer receipt is renewed through the actual current-boot heartbeat path after long setup, using the existing explicit process observation double and real wall time.

| Sample | capture hold s | reserve hold s | publish hold s | max peer wait s | total create wall s |
| --- | --- | --- | --- | --- | --- |
|1|0.087259|0.162143|0.174239|0.163002|0.474277|
|2|0.096894|0.171868|0.175987|0.172776|0.497133|
|3|0.087761|0.166140|0.179299|0.167065|0.485154|
|4|0.089837|0.198905|0.210282|0.200055|0.550161|
|5|0.086850|0.162505|0.178016|0.163487|0.479050|
|6|0.088485|0.168734|0.173776|0.169657|0.484889|
|7|0.086905|0.160238|0.173036|0.161080|0.471995|
|8|0.089745|0.166080|0.178904|0.167065|0.486263|
|9|0.095472|0.177774|0.179391|0.179042|0.506630|
|10|0.090377|0.162251|0.176586|0.163134|0.480792|

All 364 recorded ceiling-run peer waits in seconds, flattened in sample/completion order (no discarded waits):

```json
[0.0003868999192491174,0.0003486999776214361,0.00033009995240718126,0.0003146999515593052,0.0003261000383645296,0.11804319999646395,0.0004352000541985035,0.00041859992779791355,0.0004619000246748328,0.0005756999598816037,0.00042910000775009394,0.00033199996687471867,0.006688099936582148,0.0005516000092029572,0.00043709995225071907,0.0003358999965712428,0.0003415999235585332,0.00035740004386752844,0.0003407999174669385,0.0003217000048607588,0.00042399996891617775,0.0003963999915868044,0.000408699968829751,0.0003981000045314431,0.16300229995977134,0.0006012999219819903,0.0007027999963611364,0.0004741000011563301,0.0003917999565601349,0.0003494999837130308,0.0003576999297365546,0.00032870005816221237,0.0003386999014765024,0.0003397000255063176,0.00039249996189028025,0.0003386999014765024,0.00034030003007501364,0.00034289993345737457,0.0005082000279799104,0.1280286000110209,0.00044059997890144587,0.0003945999778807163,0.00039059994742274284,0.0003497999859973788,0.00031500007025897503,0.00030990003142505884,0.0003154999576508999,0.007104899967089295,0.00047339999582618475,0.000430900021456182,0.00040339992847293615,0.00033900002017617226,0.0003330999752506614,0.00035989994648844004,0.0003157999599352479,0.0003829000052064657,0.0004070999566465616,0.00033029995393007994,0.0003198999911546707,0.0003285000566393137,0.17277640011161566,0.000632300041615963,0.00038769992534071207,0.0004932000301778316,0.000586699927225709,0.00035089999437332153,0.0003565000370144844,0.0004974000621587038,0.0003693000180646777,0.0004520999500527978,0.0004897000035271049,0.0003869000356644392,0.0003445000620558858,0.0003333000931888819,0.0003309000749140978,0.0003440000582486391,0.11827580002136528,0.0004425999941304326,0.00043590005952864885,0.00044780003372579813,0.0004184999270364642,0.00034719996619969606,0.00035910005681216717,0.00032460002694278955,0.00036079995334148407,0.006759600015357137,0.000498299952596426,0.00043450004886835814,0.0006025999318808317,0.00037240004166960716,0.00034190004225820303,0.00031479995232075453,0.0003136000595986843,0.00032590003684163094,0.00035450002178549767,0.0003679998917505145,0.0003758000675588846,0.0003205999964848161,0.0003152000717818737,0.1670648999279365,0.0005158999701961875,0.0005433999467641115,0.0005667000077664852,0.0004794999258592725,0.0003453000681474805,0.0003986000083386898,0.000498599954880774,0.00041390000842511654,0.00041360000614076853,0.0004997999640181661,0.00041229999624192715,0.00040769996121525764,0.000319099985063076,0.12010890000965446,0.00044239999260753393,0.00040309992618858814,0.00039309996645897627,0.0003893000539392233,0.0003128000535070896,0.00031079992186278105,0.000327100045979023,0.0064471999648958445,0.0003906999481841922,0.0006693999748677015,0.0004771000239998102,0.0003385999007150531,0.0003565000370144844,0.00031269993633031845,0.00038780004251748323,0.0004686999600380659,0.00038839993067085743,0.00040040002204477787,0.0003952999832108617,0.20005519990809262,0.0007582999533042312,0.000651499954983592,0.0006816999521106482,0.0006057999562472105,0.00037540006451308727,0.0005021000979468226,0.00048639997839927673,0.0003828000044450164,0.0003624999662861228,0.0004959000507369637,0.0003388000186532736,0.00032270001247525215,0.00034090003464370966,0.0003252000315114856,0.11788849998265505,0.0004328000359237194,0.0004039999330416322,0.0003988000098615885,0.0004328000359237194,0.0003861000295728445,0.00031349994242191315,0.0003114000428467989,0.006526999990455806,0.00041909993160516024,0.0004956999327987432,0.00040550006087869406,0.0003451999509707093,0.00033329997677356005,0.0003124999348074198,0.0003111000405624509,0.0003375000087544322,0.0004029000410810113,0.00045579997822642326,0.00045139994472265244,0.00040529994294047356,0.1634870000416413,0.0006472999230027199,0.0003798999823629856,0.0004854999715462327,0.000458099995739758,0.00033900002017617226,0.0003681998932734132,0.0004513000603765249,0.0004430999979376793,0.00040500005707144737,0.0003380000125616789,0.00045139994472265244,0.0003782999701797962,0.00032379990443587303,0.00042910000775009394,0.1198426999617368,0.0004585999995470047,0.00041909993160516024,0.00039499998092651367,0.000408699968829751,0.00034579995553940535,0.0003226000117138028,0.006585799972526729,0.0005276999436318874,0.00041290000081062317,0.0005379000212997198,0.00037670007441192865,0.0003618999617174268,0.0003322999691590667,0.00031209993176162243,0.00032130000181496143,0.00046140002086758614,0.0005221999017521739,0.0004085999680683017,0.0004064000677317381,0.16965709999203682,0.0007554000476375222,0.000533499987795949,0.0006019000429660082,0.0004202999407425523,0.0003429999342188239,0.0003128000535070896,0.0003127999370917678,0.0003093000268563628,0.00031489995308220387,0.00030720001086592674,0.0003024999750778079,0.0003090999089181423,0.0003195999888703227,0.00044840003829449415,0.0004113999893888831,0.00041459989733994007,0.0003866000333800912,0.00033359997905790806,0.0003225000109523535,0.00032810005359351635,0.0003285000566393137,0.11877709999680519,0.00042860000394284725,0.0004010000266134739,0.0003893999382853508,0.000394799979403615,0.0005550000350922346,0.00036940001882612705,0.0068443999625742435,0.00047690002247691154,0.00036880001425743103,0.00042360008228570223,0.00035690004006028175,0.00031759997364133596,0.00031949998810887337,0.0003263000398874283,0.0003325000870972872,0.00033409998286515474,0.00038680003490298986,0.00033650000113993883,0.00031649996526539326,0.00032789993565529585,0.16107999999076128,0.0006667999550700188,0.0004784000338986516,0.0004417001036927104,0.00036910001654177904,0.00036529998760670424,0.00046419992577284575,0.00044059997890144587,0.00040819996502250433,0.000395099981687963,0.00033379998058080673,0.0003268999280408025,0.00034929998219013214,0.00032460002694278955,0.12062780000269413,0.00044760003220289946,0.0004016000311821699,0.00032190000638365746,0.00033519999124109745,0.00032919994555413723,0.00031670008320361376,0.0003152000717818737,0.0067804999416694045,0.0005801999941468239,0.0004184999270364642,0.000556000042706728,0.00037349993363022804,0.00033009995240718126,0.00033000006806105375,0.000313500058837235,0.00031589996069669724,0.00038380001205950975,0.0004493999294936657,0.0004467000253498554,0.00043080002069473267,0.16706460004206747,0.0005071000196039677,0.0005037999944761395,0.0004368999507278204,0.000431500026024878,0.0003727000439539552,0.00035039999056607485,0.00037869997322559357,0.0003408000338822603,0.0003405000315979123,0.000341600039973855,0.000395399983972311,0.0003568000392988324,0.0003424000460654497,0.00034419994335621595,0.0003375000087544322,0.12735829991288483,0.0005255000432953238,0.000457499991171062,0.00043350004125386477,0.00043130002450197935,0.00033249997068196535,0.00032190000638365746,0.00789410003926605,0.0005528000183403492,0.00044840003829449415,0.0005154000828042626,0.000354900024831295,0.00040579994674772024,0.0003304000711068511,0.00031860009767115116,0.00033000006806105375,0.0003287999425083399,0.0003355999942868948,0.00032240001019090414,0.0003301999531686306,0.00033820001408457756,0.1790418999735266,0.0005109000485390425,0.0005162999732419848,0.0005323999794200063,0.0004896000027656555,0.00036200007889419794,0.0003746000584214926,0.0004200999392196536,0.00035630003549158573,0.00044759991578757763,0.0004518999485298991,0.00040199991781264544,0.0004067000700160861,0.000328000052832067,0.12098739994689822,0.00043299992103129625,0.0004151000175625086,0.00033189996611326933,0.00031070003751665354,0.00031940010376274586,0.00032350001856684685,0.000314100063405931,0.007058000075630844,0.0006911000236868858,0.0004646000452339649,0.0005428000586107373,0.00044350000098347664,0.000505700008943677,0.00040579994674772024,0.00033850001636892557,0.00034899997990578413,0.0004390999674797058,0.0004013000288978219,0.0003458999563008547,0.00033379998058080673,0.163134399917908,0.00045080005656927824,0.0005150000797584653,0.0005589999491348863,0.0005705999210476875,0.0004225000739097595,0.0004187000449746847,0.000381199992261827,0.0003546999068930745,0.0003626999678090215]
```

Measured maximum hold=0.210282400s, maximum peer wait=0.200055200s; observed margin=0.089717600s under the absolute0.300s line. Freeze REQUIRED_MARGIN_SECONDS=0.030 for final ceiling K6, so every hold AND peer wait must be<=0.270s at the stated ceiling, not merely under0.300s. Both timing and margin pass for these ten design samples. Raw per-phase/acquisition/all-peer records are retained in .audit-tmp/ticket20-capacity-512k-sample-01..10.json and ticket20_capacity_512k_ten.json; scripts adjacent. Trackede3a8374d exit0 includes successful temp-root/peer cleanup assertions in every child run. The preceding ten without size checks (3f804db0), checked1MiB failure (99e13976),2MiB pilot(50b1c871), and the first pilot's expired-fixture-heartbeat ERROR(38c43b7d) remain distinct. The heartbeat ERROR was corrected by renewing the actual fixture receipt/heartbeat after long setup; no clock/liveness/persistence was faked or bypassed.

These are selected-channel DESIGN prototype numbers on real files, not operator implementation or final K6 acceptance. Final test_capped_source_snapshot_and_create_boundary_holds_with_peer_require_active MUST run ten samples PER stated source mode/parent shape AT the512KiB/128-request ceiling, including actual allowlist/lazy encoding/capacity checks, with per-hold/per-peer margin>=0.030s and all raw samples/wall times retained. The final real run-preset builder may add cost; failure lowers the proposed ceiling or returns to mechanism review, never raises/omits the bound. Root tests exact ceiling vs byte+1/request129 before any stage/reserve/enqueue, preview refusal/counter disclosures, capacity changes after reserve, same-id replay/recovery at capacity and imports of larger history remaining readable. No helper owns these gates.


## Why the hard-quota design was withdrawn

The independent reviewer withdrew it after the following existing-schema probes. These are metadata/storage sizing only, not operator/native/provider acceptance. Numeric values used in the diagnostic graph are already within the proposed integer<=2**63-1 bound; timestamps use a positive23-character JSON float. The graph passes existing _validate_index. Its conservative schema-accepted upper bound does not assert that all retained-body/max-byte combinations are naturally reachable under the8MiB object budget. A second body-free1024-row graph with128 groups8 each, no overflow summaries, byte_count0 and normal100.0 timestamps is545920 bytes and also validates, so the conclusion does not depend on retained body files or summary reachability.

```json
{
  "kind": "design metadata-only sizing, not persistence/native proof",
  "diagnostic_rows": 1024,
  "groups": 256,
  "rows_per_group": 4,
  "dispatch_summaries": 256,
  "global_summaries": 1,
  "longest_reason": "source_packet_unavailable",
  "numeric_int_bound": 9223372036854775807,
  "float_json_width": 23,
  "actual_float_repr": "1.2345678901234567e-100",
  "base_empty_index_bytes": 130,
  "max_row_json_bytes": 580,
  "max_group_summary_json_bytes": 417,
  "global_summary_json_bytes": 384,
  "diagnostics_full_index_bytes": 749818,
  "diagnostic_growth_reserve_bytes": 749688,
  "capacity_remaining_after_fixed_reserve": -225400,
  "schema_validation": "existing _validate_index PASS; all numeric fields within proposed bound",
  "scope": "schema-accepted conservative upper bound, not proof all retained-body combinations reachable under 8MiB object budget",
  "index_sha256": "dc2f5453becb7f32cc5cb9e1325b6bef77c7f8088bfd7f4dac4c391490ce2104"
}
```

Existing real temp-store reserve/queued/commit_version sizing (same content caps, two independent lineages per shape; cleanup asserts removed root):

```json
{
  "kind": "existing-store schema/byte sizing, no operator or managed runtime claim",
  "rows": [
    {
      "shape": "ordinary_ascii",
      "packet_bytes": 2097152,
      "messages": 1000,
      "instruction_utf8_bytes": 32768,
      "format_utf8_bytes": 512,
      "uid_utf8_bytes_max": 10,
      "all_labels_at_most256_utf8": true,
      "sizes": [
        {
          "requests": 1,
          "queued_index_bytes": 146670,
          "fulfilled_index_bytes": 293110,
          "version_growth": 146440,
          "fits_512KiB_plus256": true
        },
        {
          "requests": 2,
          "queued_index_bytes": 439654,
          "fulfilled_index_bytes": 586096,
          "version_growth": 146442,
          "fits_512KiB_plus256": false
        }
      ]
    },
    {
      "shape": "maximum_escaped_fields",
      "packet_bytes": 2097152,
      "messages": 1000,
      "instruction_utf8_bytes": 32768,
      "format_utf8_bytes": 512,
      "uid_utf8_bytes_max": 256,
      "all_labels_at_most256_utf8": true,
      "sizes": [
        {
          "requests": 1,
          "queued_index_bytes": 1823747,
          "fulfilled_index_bytes": 3647264,
          "version_growth": 1823517,
          "fits_512KiB_plus256": false
        },
        {
          "requests": 2,
          "queued_index_bytes": 5470885,
          "fulfilled_index_bytes": 7294404,
          "version_growth": 1823519,
          "fits_512KiB_plus256": false
        }
      ]
    }
  ]
}
```

An independent pure observation probe accepts confirmed_model=600000 ASCII x bytes with confirmation_reason=api_response (600062-byte observation JSON), below MAX_RESULT_RECORD_BYTES3178496 but above the withdrawn524288-byte index limit. _number also accepts a309-digit positive integer before the proposed correction. No code was changed to produce these results. The architecture choice remains OPEN in the decision memo.
