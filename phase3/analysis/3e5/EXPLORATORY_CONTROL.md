# Exploratory ample-memory control

Validated 80 saved conditions across all four allocators and 20 matched seeds. 0 records had a nonzero blocking/stall field or a timing difference from fixed within seed.

| Allocator | Allocated slot-ticks | Used slot-ticks | Unused slot-ticks | Pooled unused % |
|---|---:|---:|---:|---:|
| fixed | 718,852,096 | 40,340,732 | 678,511,364 | 94.3881735583 |
| paged8 | 41,568,896 | 40,340,732 | 1,228,164 | 2.95452638434 |
| paged16 | 42,971,104 | 40,340,732 | 2,630,372 | 6.1212576712 |
| paged32 | 45,777,280 | 40,340,732 | 5,436,548 | 11.8760835069 |

The pooled share uses the exact integer ratio unused over allocated slot-ticks. The historical 640-condition planning count did not define an executable suite and was never run. This check applies to the saved ample-memory fixture.

[Record-level verification](exploratory_control_checks.csv) · [Allocation accounting](exploratory_control_memory.csv)
