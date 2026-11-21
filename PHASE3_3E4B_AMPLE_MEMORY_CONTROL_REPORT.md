# Phase 3E-4B ample-memory negative control report

**CONTROL COMPLETE — INVARIANTS SATISFIED**

This is a **prospectively specified exploratory negative control**, separate
from the historical 640-control planning count. It does not change the
frozen primary experiment or establish GPU or vLLM throughput performance.
Final primary statistical inference remains unperformed.

## Frozen specification and identities

The [prospective 3E-4A decision](PHASE3_3E4A_CONTROLS_ANALYSIS_READINESS.md)
selected all 20 seeds, 20261117–20261136, from short / generation-heavy /
dense, using the exact saved 200-request workloads with M=2048. Each workload
ran sequentially with fixed, paged8, paged16 and paged32, unlimited compute,
and 409,600 token slots. Each request's rounded allocation is at most M,
and the oldest request's allocation plus protected slack is at most M.
Thus capacity covers all 200 worst-case reservations under the unchanged
rules. The primary comparator is fixed allocation at ample memory.

The [specification](phase3/research_batch/3e4b/ample_memory_control/specification.json)
was published, synced, and read back **before dispatch**. It contains the
four predictions, all 80 condition IDs and the exact reference links and
checksums. The existing research-batch manifest binds its file digest.

| Identity | Value |
| --- | --- |
| Branch and local/live origin HEAD | `phase-3-memory-aware-scheduling` · `df794b67e72740bffb6272248b9d609c8decfaea` |
| Ordered control inventory SHA-256 | `8c51537192ea23892a9f2caaa7cb9441444baa8b5095bfa168cee819d57ce9a7` |
| Prospective specification file SHA-256 | `9bf6dbebc546e0d3a321c29057cec32c45bd924f7b489f429ff24c2a8a40e4ed` |
| Approved 3E-4A report SHA-256 | `ad3fe0f36459d4403090251d86a2843a0cbe4688952f4fb4b8124c633639aefe` |
| Primary manifest SHA-256 | `17983e334c0980cbaabafa9da4fe2e9935977848475043de92db4906105a8b48` |
| Control manifest file SHA-256 | `6ca36528c01b1af6c6d95814d850ce68a2b034e5d4de3976b97c9e5049ee99fe` |
| Control manifest identity SHA-256 | `6198d22c9d16d52f994a85e908fb42a36466fdeab186e300d06ceb5190dcb8fd` |
| Frozen primary config SHA-256 | `3753af5cb496b4ba395a8f846b4871c0060407de75828e00d445206bad46d8fa` |
| Frozen analysis plan SHA-256 | `eff60269f9fa72efa552be796f432cce46ee231def9b3676999d2d565f860c93` |
| Approved v0.4 SHA-256 | `899392a7b75349e43083fe8f66ad9b290108880a501cedd630f1990c3b042af3` |
| Approved v0.5 SHA-256 | `378ea13bfbbecf63cf1135c815a4b3161245d41c02511327b2951c2675a2a7d0` |
| Environment | macOS-15.6-x86_64-i386-64bit, CPython 3.12.3 |

| Pinned source | SHA-256 |
| --- | --- |
| `phase3_experiment.py` | `2175c9f253696757d2337df6508150f6c1008ae8605cea9b01634953e292f5b4` |
| `phase3_simulator.py` | `610f978a4fb48eaf4d0c68d08a9b590828da2af22a7a7ae9e851a3957b431bec` |
| `phase3_workloads.py` | `372ea34f29086b53e50d366ad145b847e4ca00861ca056da4e43217421fb1684` |
| `PHASE3_RESEARCH_BATCH_PROTOCOL.md` | `b74171bf0577ca2b38c71bc5008b7e77271107319966abca32b1743c7b8336c8` |
| `phase3/configs/pilot.json` | `c1fac4619259bf7b059881e39c5d958fe37f4f742f54905bc43f18e600fcef25` |
| `phase3_batch.py` | `76b6cdb2ad0d0b07b32b552f7d1583de4369d48e086bf172aba6ff535b9168db` |
| `phase3_research_batch.py` | `c983a5eb3142bc5f727da0b81a0ca8cbcede7c3daf490307a4ebcf3704e6e9f7` |

Commands from the repository root:

```sh
/usr/bin/time -p python3 -B - < /tmp/phase3-3e4b-control.py
python3 -B - < /tmp/phase3-3e4b-verify.py
```

The launcher loaded saved workloads, validated and linked the 80 matching
primary records, published the prospective specification, then called
`phase3_research_batch.run_batch` for the isolated
[ample-memory control namespace](phase3/research_batch/3e4b/ample_memory_control).
The verification command rebuilt the Cartesian inventory from primary
manifest workload documents and invoked the existing resume path twice
with a guard that would fail any attempted simulator call.

## Results against the frozen predictions

**80 expected, 80 distinct, 80 valid.** Recorded workload hashes, canonical
condition IDs, provenance, schema, scientific invariants and checksums
validated. No missing, duplicate, or unexpected conditions.

| Prediction | Observed |
| --- | --- |
| Zero memory blocking and stalls | 0 nonzero blocking or stall fields across 80 records. |
| Exact request admission, first token, and completion within each seed | 0 differing fields across 12,000 request-level comparisons (20 × 3 allocator contrasts × 200 requests). |
| Exact waiting, latency and makespan within each seed | 0 differing request or aggregate fields. |
| Allocated, unused and fragmentation slot-ticks may differ | Retained and summarized separately below. |

Each entry reports the number of nonzero blocking/stall fields, differing
request timestamps, and differing waiting/latency/makespan fields for
that seed. Comparisons are exact on the stored values. Each linked
constrained reference uses the same workload and allocator at budget 2048
with unlimited compute. These 80 existing rows were validated and linked
without rerunning or counting them as new control results.

| Seed | Blocking / timestamps / waiting-latency-makespan | Constrained fixed | Constrained paged8 | Constrained paged16 | Constrained paged32 |
| ---: | --- | --- | --- | --- | --- |
| 20261117 | 0 / 0 / 0 | [fixed](phase3/research_batch/3e3/primary/condition-d08bdc234a8b2c3e244228eaf2a262758155bb644fd95733d36f0bcb4e548a75.json) | [paged8](phase3/research_batch/3e3/primary/condition-d69dc38e7ca538b5d5e4d5d53ee5c43409a57249f47783e80eae4bdab548752f.json) | [paged16](phase3/research_batch/3e3/primary/condition-002c17a107e62d6c295cc9b1aa04c08cafbd1ca16cdd209e44d7f87b58588ff0.json) | [paged32](phase3/research_batch/3e3/primary/condition-fc879108dc251fcc64015959c11acbea8d31e452d88fb41b461391a820bcc247.json) |
| 20261118 | 0 / 0 / 0 | [fixed](phase3/research_batch/3e3/primary/condition-076a0f35a14f440446326c1adb7f19f794adc988a52c05b4938be483c28ac202.json) | [paged8](phase3/research_batch/3e3/primary/condition-0e4344b227b9db2449d132601a72a3c6deb3fecc4f004eb470923401a3c19c70.json) | [paged16](phase3/research_batch/3e3/primary/condition-7b5ea47632a903bf46b831dddcc597a897ee95307556142f9ce6099bbadc1c71.json) | [paged32](phase3/research_batch/3e3/primary/condition-3141273d339e7214b89ebb40713ea9236a163872a66139a71a6f0b1bf5811e80.json) |
| 20261119 | 0 / 0 / 0 | [fixed](phase3/research_batch/3e3/primary/condition-7078e38c2cbb094b7f59cdda1aceffb52850889f63a78b2a0b024bd16bed7d10.json) | [paged8](phase3/research_batch/3e3/primary/condition-15749ace79cb572ae4dd20f3cf1267887a1fad16a42861cda55b965971430d34.json) | [paged16](phase3/research_batch/3e3/primary/condition-571f619d665214c6a17b688f11fb75d7c6362c812302de2ce9b810e29ff697f3.json) | [paged32](phase3/research_batch/3e3/primary/condition-55be0b84e160497d482895443b67feb44f400dd1abe054c34e407c9d33f55fea.json) |
| 20261120 | 0 / 0 / 0 | [fixed](phase3/research_batch/3e3/primary/condition-d31a488eb61d8f50cce6448ad8aa25832dcda539184f05b6172701fc6ea80b4b.json) | [paged8](phase3/research_batch/3e3/primary/condition-ccf4e0f7a62cd43e878da8db8631e45805ae1dff40d4a2d33162ea203ecfa230.json) | [paged16](phase3/research_batch/3e3/primary/condition-cad8b96684e833e3b7b15153edce60a225587235754f02c27f590719162741db.json) | [paged32](phase3/research_batch/3e3/primary/condition-61364c3423eecc586b699caddc4843ef0ec21c3f7804a88d043bcb3c91a6ffdb.json) |
| 20261121 | 0 / 0 / 0 | [fixed](phase3/research_batch/3e3/primary/condition-e0cff8d3277d6e0ecd819869b29e416131350f7e34c6f97444be7f1168e10e1c.json) | [paged8](phase3/research_batch/3e3/primary/condition-9002d2402dfa5da8d653d105f61eb157ba515367cfb9de1de570f99a6c37b32f.json) | [paged16](phase3/research_batch/3e3/primary/condition-1cd167582fe1b68c81fad15e5cbd095ccd6cf44f261510f842b3501cd8db1c79.json) | [paged32](phase3/research_batch/3e3/primary/condition-4aee2f651010a5921b8316da8266cca71ccd9681cf6db75044c2e24085c8ee32.json) |
| 20261122 | 0 / 0 / 0 | [fixed](phase3/research_batch/3e3/primary/condition-6497e369c7ea84685fdadeb7c1702d468ec711b15c21ebaf1b5ba5850d70e1f5.json) | [paged8](phase3/research_batch/3e3/primary/condition-74614248b2bb83e99bf29cbce7cb8a09e6aae972b083fb9686f61753c189e787.json) | [paged16](phase3/research_batch/3e3/primary/condition-398e8a79499019aac8135855543f3e971922ed745811f2b77c99793e361acd08.json) | [paged32](phase3/research_batch/3e3/primary/condition-e4237803e87d4be71565226ad5166f7afe34a1831e78c9d0e26d1b2b4d710a3a.json) |
| 20261123 | 0 / 0 / 0 | [fixed](phase3/research_batch/3e3/primary/condition-71eee12a26f9b23512a744cda40a0f22b1478254f1aa2952a1158e8efb27f7b6.json) | [paged8](phase3/research_batch/3e3/primary/condition-9400e2d5913144af55c7f4153aa713b8dbd54ad94099c6836662ad1742fec7ad.json) | [paged16](phase3/research_batch/3e3/primary/condition-ca5542fae9bec115b4aa094a0a89b1a6ff5e8fe3e9656fbb6315f21c9ced4e7d.json) | [paged32](phase3/research_batch/3e3/primary/condition-0f130dbffe711168241246dd4ad60b8292618ebbba2964c04622f0209c3e5228.json) |
| 20261124 | 0 / 0 / 0 | [fixed](phase3/research_batch/3e3/primary/condition-d6f375258e20a69a4f5ca6bc3c04516e72969d64d941126f2d725a1da16518f8.json) | [paged8](phase3/research_batch/3e3/primary/condition-1e958f7f5dc7d5162a697d14bfb3587b680c5ff94753cbe47418dd5a0ef27015.json) | [paged16](phase3/research_batch/3e3/primary/condition-dc958d21a5259db5ccefab3c3b6a2fbebb9b49a12bcbe753169e4725d726db73.json) | [paged32](phase3/research_batch/3e3/primary/condition-0c959b870ae33cece5c4537adb40975a9c47e9a22abfffc67b0facc6643aaa37.json) |
| 20261125 | 0 / 0 / 0 | [fixed](phase3/research_batch/3e3/primary/condition-7991d7dd1f113ece2246f8d6c7ff4db279624481338d756ed567a2bf6dad0821.json) | [paged8](phase3/research_batch/3e3/primary/condition-bd71972cda95e7eee6ab128444ccb2de4a9667f8515bf3f5ce50a2f9cf4b7137.json) | [paged16](phase3/research_batch/3e3/primary/condition-ac3c91db2a9443eac976b1362ee0d6b846e029dd74f326790fd8a73c34f3dac1.json) | [paged32](phase3/research_batch/3e3/primary/condition-09fe8c24a88a56479921f43609b0b490a970fabb3cf0ad65324adf0ed2f5b8ad.json) |
| 20261126 | 0 / 0 / 0 | [fixed](phase3/research_batch/3e3/primary/condition-67dd50960332ca59e0de690d3050314eaa27c734a78b8767e527814d2545d46f.json) | [paged8](phase3/research_batch/3e3/primary/condition-3bd3805eb24dd5b7f94afc32b9741d031d0ebff122df6a84191106ed82416935.json) | [paged16](phase3/research_batch/3e3/primary/condition-017f56b94693c6a3599923e78ccf611cc810937de9efcf1ba4de786a1343a7a6.json) | [paged32](phase3/research_batch/3e3/primary/condition-8dc33df4d6aa07f03998c2c33afa5f32ab09105a562ef626a9f743d9cdd04144.json) |
| 20261127 | 0 / 0 / 0 | [fixed](phase3/research_batch/3e3/primary/condition-be78ce212a30857c8f4db937c827e387ccea883cebe99fac01d799d2f3981522.json) | [paged8](phase3/research_batch/3e3/primary/condition-1600125ed4cad4346a98cf175fff94b1164a7f0e9155cab55d4757ceb486e879.json) | [paged16](phase3/research_batch/3e3/primary/condition-b7f8e53c0bdb03607e47aad82134f2884a5a577f07bdd55d11a3d6ebeef1a22f.json) | [paged32](phase3/research_batch/3e3/primary/condition-22c00bc8d4492174bc478bc3a05bc06e39108cd9d618331013fa7e4d400e6cb1.json) |
| 20261128 | 0 / 0 / 0 | [fixed](phase3/research_batch/3e3/primary/condition-29f0653177ea826d1b49e282fb0d984c9f95feede137305e0e1786c3470b640f.json) | [paged8](phase3/research_batch/3e3/primary/condition-2d3e96b4bc08898006d84870398d2d1926ad66863a419d65e883a1dcfef160a0.json) | [paged16](phase3/research_batch/3e3/primary/condition-2fe09c79bb621f88d65d7f369255b21317613f8b3d023acf917f40b598113d81.json) | [paged32](phase3/research_batch/3e3/primary/condition-4844ede154bdca45582a493b8174be49cbb112f0d7f3719f5718a101fdaa5653.json) |
| 20261129 | 0 / 0 / 0 | [fixed](phase3/research_batch/3e3/primary/condition-385fcfdb367281ef98da49e6861c272790444330006138ceea6f4d62b98c527a.json) | [paged8](phase3/research_batch/3e3/primary/condition-c1b5cbc0564887f6bee681c4e81feec22193ef3d1b701fb4b78297b16dcff91d.json) | [paged16](phase3/research_batch/3e3/primary/condition-9d9bbf9550eb6c61ca5f04941715a7f95c1157782674240f37b7ed7e1b4a3df7.json) | [paged32](phase3/research_batch/3e3/primary/condition-3bcdd5458d1c3d3ace5dd02173735f4c3cc8d8461db3de1d79ee4a2e068ec1ff.json) |
| 20261130 | 0 / 0 / 0 | [fixed](phase3/research_batch/3e3/primary/condition-625b819761df8b84d25730990407549e558240d28d0560895f8c4ba19c5960af.json) | [paged8](phase3/research_batch/3e3/primary/condition-ad3678630e4493b6df3d41ea440322655bc99380a069d3c00361499d826a87aa.json) | [paged16](phase3/research_batch/3e3/primary/condition-0e5df3cad9c7f42095266d7e6ec97438811b89a661b0f3ab113d985fa8f2c356.json) | [paged32](phase3/research_batch/3e3/primary/condition-acbd394c3c77d03f752684341a57e5692b1c8e8f4757732cba709d05177d8cbc.json) |
| 20261131 | 0 / 0 / 0 | [fixed](phase3/research_batch/3e3/primary/condition-f99e1465c43387c17e1868834fba11d480e757f02319fc2bbb95b7e2422cb854.json) | [paged8](phase3/research_batch/3e3/primary/condition-6dd82b44b0e180f97b5df033f1e08c5d2c8a67dbf7f9355013f6987666dab68e.json) | [paged16](phase3/research_batch/3e3/primary/condition-b1a4ee337906d4ef28a2d04cf1b6ea6c48105901e23b907c337a379335b968e9.json) | [paged32](phase3/research_batch/3e3/primary/condition-16591c7625c42495478afbc41b789c74746774880e18d332b5d0e853038aa4e5.json) |
| 20261132 | 0 / 0 / 0 | [fixed](phase3/research_batch/3e3/primary/condition-fb0264ab5bbba19322cc0fa8de2cf46b07670827073f6a3c6f05434bd5813b2e.json) | [paged8](phase3/research_batch/3e3/primary/condition-6a7a18b9c280e36c0c2e6ed12f1258ef019bbf3985cab28ed7164ca1d4b42a92.json) | [paged16](phase3/research_batch/3e3/primary/condition-76ee682728d7e5330a3e4716e6f3719778030a6eb1b5db61272b85cafbb17147.json) | [paged32](phase3/research_batch/3e3/primary/condition-fb912e6a91ca44aba0071d100ff4e00c912ddc41c62fbd5737d1e289ba54bcc4.json) |
| 20261133 | 0 / 0 / 0 | [fixed](phase3/research_batch/3e3/primary/condition-9353f82b85da61eba5a6c88c3b27be5a43afde09bf010188f175d33747f5e03d.json) | [paged8](phase3/research_batch/3e3/primary/condition-894282a7d33d6ce12d3939cadcf5a1600902d1ca373c0fea497dd2eca5bcc1de.json) | [paged16](phase3/research_batch/3e3/primary/condition-225e03edd1512cd728f3af5f42ed9ad95f3a3400017d06cb0cc242f9ca35de8d.json) | [paged32](phase3/research_batch/3e3/primary/condition-d8864cfed631e929e01e35620cedc5117c57c3d36b1c42ce2e210602b9176c2b.json) |
| 20261134 | 0 / 0 / 0 | [fixed](phase3/research_batch/3e3/primary/condition-c86b4e067affd9db4c1719c15b88b7c2f6b7c919df6cd8bce4d94a0276a3e06b.json) | [paged8](phase3/research_batch/3e3/primary/condition-8e94ee20b0423c6fc7dbe7ab0eb58737584054c463eee6887c5c458a8db8d7ab.json) | [paged16](phase3/research_batch/3e3/primary/condition-2253ccab2ded81c2ebe59e9de484612610be6037902ed4125ecb61d4b7a321ab.json) | [paged32](phase3/research_batch/3e3/primary/condition-68b6f60b0e1cc40b40d27106110f375ffb46a316bfbc4c4aed9748d32cc9bc2e.json) |
| 20261135 | 0 / 0 / 0 | [fixed](phase3/research_batch/3e3/primary/condition-0a20175a9c341955c4e320fac4483c49b93a1d7a3135dca8392a25fe26fbd74a.json) | [paged8](phase3/research_batch/3e3/primary/condition-ab510dcbd5bbbeea933877e4ca118ee810ab9d26cf72041b12314d1669573951.json) | [paged16](phase3/research_batch/3e3/primary/condition-525b70cc155faed86df8e78b2246e65ba45d9862a24a07c1689e804bffa6297c.json) | [paged32](phase3/research_batch/3e3/primary/condition-f83ba289a3cc0e2b1a56f9eaa16fc1107887e81238d93da98d8306b4a09065d0.json) |
| 20261136 | 0 / 0 / 0 | [fixed](phase3/research_batch/3e3/primary/condition-7b53efb1f24c80e2110e3d816a605c3fc6a9543349a646bf85b2a2d841fe2920.json) | [paged8](phase3/research_batch/3e3/primary/condition-8f83b2709d17b6ba92692480b9a58bc34c9439d9e509c8e0de8739b65b22d244.json) | [paged16](phase3/research_batch/3e3/primary/condition-73240a361dcced23d8b86e5cb3812fca725e2325e52faaebf3672eb10c9485a1.json) | [paged32](phase3/research_batch/3e3/primary/condition-0967e18244691dea056db2dc78cc18841ce4c4b228131910efa2dc4be3f0f562.json) |

No prespecified timing or memory-blocking invariant was violated.

### Allocation and fragmentation

Values are pooled sums over the 20 seeded workloads per allocator.
Fragmentation is total unused allocated slot-ticks divided by total
allocated slot-ticks. It describes reservation and block rounding within
the simulator.

| Scope | Allocator | Allocated slot-ticks | Used slot-ticks | Unused slot-ticks | Unused share |
| --- | --- | ---: | ---: | ---: | ---: |
| Ample control | fixed | 718,852,096 | 40,340,732 | 678,511,364 | 94.3882% |
| Ample control | paged8 | 41,568,896 | 40,340,732 | 1,228,164 | 2.9545% |
| Ample control | paged16 | 42,971,104 | 40,340,732 | 2,630,372 | 6.1213% |
| Ample control | paged32 | 45,777,280 | 40,340,732 | 5,436,548 | 11.8761% |
| Constrained reference | fixed | 718,852,096 | 40,340,732 | 678,511,364 | 94.3882% |
| Constrained reference | paged8 | 41,568,896 | 40,340,732 | 1,228,164 | 2.9545% |
| Constrained reference | paged16 | 42,971,104 | 40,340,732 | 2,630,372 | 6.1213% |
| Constrained reference | paged32 | 45,777,280 | 40,340,732 | 5,436,548 | 11.8761% |

## Runtime, resume, and integrity

The command took **19.61 s** including baseline hashing and setup.
The research workflow took **4.775 s**; condition timers summed
to **3.518 s** (range 0.035633–0.058309 s).
One invocation dispatched 80 conditions in canonical order. No failure
records, retries, partial records, or redispatches were observed.

- Resume 1: ample_memory_control: dispatched=0 skipped=80 wall=0.752079s; all 82 JSON artifacts byte-identical.
- Resume 2: ample_memory_control: dispatched=0 skipped=80 wall=0.745806s; all 82 JSON artifacts byte-identical.

The comparison is a mechanism check on one frozen workload definition
across its 20 seeds. It supplies no claim about allocator timing when
memory or compute constrains progress, and no inference for the primary
experiment. Only the control namespace and this report were added.
All primary and pilot artifacts, scientific implementation and configs,
frozen analysis plan, approved historical v0.4/v0.5 protocols and F2
closure remained byte-identical. The index was empty. Nothing was
staged, committed or pushed.
