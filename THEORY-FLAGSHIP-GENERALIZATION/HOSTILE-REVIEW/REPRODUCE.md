# Reproduction and immutable research sources

Run from the repository root with Python 3.13 or a compatible version. The independent hostile checks use only standard Python and exact rational arithmetic. They exercise different conditions from the constructor replays.

~~~powershell
python THEORY-FLAGSHIP-GENERALIZATION/HOSTILE-REVIEW/check_hostile.py
~~~

The authenticated source replay uses the GitHub CLI for the declared repository, Python, the installed Z3 binding for P, and Lean 4.21.0. It reads separately published script blobs at exact commits and verifies the Git content SHA of each script before executing it on stdin. It does not alter the repository or checkout.

~~~powershell
python THEORY-FLAGSHIP-GENERALIZATION/HOSTILE-REVIEW/replay_releases.py
~~~

Both commands passed on 27 November 2026. The authenticated replay covered A's 144 matched deterministic tables and 128 continuous Bernstein cases, P's 336 raw source/fragment cases and fixed-guard refutation, and U's 1,296 count-flow metric comparisons and analytic depth-64 example. It also ran the three blind role scripts and separately pinned Lean checks. Lean checks supporting arithmetic. None of these executions tests a real deployment.

## Candidate receipt verification

These full keys and tree identifiers were independently compared to authenticated GitHub commit metadata and local Git objects. The operative documents and original seals are linked within the respective detailed reviews. [A](A-REVIEW.md) · [P](P-REVIEW.md) · [U](U-REVIEW.md)

| Role or stage | Exact commit | Exact tree |
| --- | --- | --- |
| A neutral | de86a826d9223ec1ebdd331c01f9f0adc82f5466 | b849271803db8d8d48da9a517a8a8807e57cf0b2 |
| A before-proof | b66188584a3509a96f03c561290672515d9c848f | 109780ae986783981dc3fb889fd6a2e01067faf4 |
| A proof | 95b3576a3bf65824b9e09e689aad80f6ae4f46df | c0c422b1c898b273781c8267362ed35e7bc9c428 |
| A comparison | 148074a3a0b15092830d77cad151613024e175ee | 7c5a631cf0fbf395fdd77219e481c11ceee00338 |
| P neutral | 69b137e57300fbd4af3380d254fb9ab32eee32c1 | ac2d24121371adb7bcf50e12e4d8c3f769ec9f91 |
| P before-proof | 19cd95ccfb3b0c4e4f6eb24132516a488d723f84 | c92dae7267aa141c0d9f270b17f62e015c346d47 |
| P proof | 7f8ae35278bf975c7e224fee1566233f594dce0a | 162a992ad75a5f0ffce3d66b3617d0c35c040e35 |
| P comparison | e218a1d1f9a6b9e76c8a16e2de84f447a32b8720 | 0afc7a8c02d31a1167b3816e2c42194f79078b04 |
| P fixed guard | bebeea2f1be63f89bd6a3bffb8b2651b625a06d2 | b2874eda243dd048ca3d4b0bb031b23dbfd0827f |
| U original neutral | 758ec550179f010d81327308cca9ec7e5120ae8b | 3073db0843625ce01beb8a8f16b333643958d80d |
| U final neutral scope | 3d5199852cf3550f5e3a568b75b8d8a9f6faa662 | 8ebd0d600da0f632c38a27cc8d9e6dcc6a44a4dc |
| U before-proof | e09f81e2181445eb4aad4814573a5db2cd2334cc | 69ad8c8e667758022b0356604b2b53ffcdc41477 |
| U proof | 8b1390de89c775087ccd5f1d61d6e516ca010fce | f8104cd894cdbb385aa46f6d51dc7cf25a3c1c31 |
| U grid scope | 1ba70aa1f6def4c9a557aa79bdcd0b7e058cbfc1 | b2f5a91ac3c550886f81290fa415a025d29741ab |
| U comparison | 7e6a30d865785801a67a254130380762c3d017b1 | da4957b5c2e0b256d1a415cba3dd272c65068b01 |
| U transport and comparator scope | b4ba949ab516d685324d22ba73c383572c99ea8e | b4b9be5f734700985d7f1ebb35637a65c9263714 |

The P fixed-guard addendum has blob 0e415a2aedabeff1672d855cf4303916f7e53bf8 and the amended P proof has blob 0a07236b0d0a060864b5c40fd4dfb4e74ec04b3d. The U transport addendum has blob 0102bf5c384a8001a223820f71e2e7e9f69b0a38 and the amended U proof has blob 3721647e29d523d07edea94baea68b248ba197a5. The source replay script itself names nine exact Python and Lean blobs.

The governing reconstruction, generalization, accepted X16 and accepted final flagship commits and their tree IDs independently matched the master manifest. The original PDFs are accounted for by its pinned original-artifact and reconstruction record. The exact X17 branch/tag lookup yielded no accepted reference and the governing original study is still a proposal. [Baseline manifest](../BASELINE-MANIFEST.md)
