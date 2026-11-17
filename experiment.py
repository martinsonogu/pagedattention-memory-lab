"""Small, reproducible allocation-mechanism experiment, not vLLM throughput reproduction."""
import argparse, csv, math, random
from pathlib import Path


def fixed_allocation(length, maximum):
    if not 0 <= length <= maximum: raise ValueError('invalid length')
    return maximum if length else maximum  # reserve maximum at admission, including empty prompt


def paged_allocation(length, block_size):
    if length < 0 or block_size < 1: raise ValueError('invalid parameters')
    return math.ceil(length / block_size) * block_size


def admit(lengths, budget, strategy, maximum, block_size):
    allocated = used = count = 0
    for length in lengths:
        required = fixed_allocation(length, maximum) if strategy == 'fixed' else paged_allocation(length, block_size)
        if allocated + required > budget:
            continue
        allocated += required
        used += length
        count += 1
    return dict(admitted=count, used_slots=used, allocated_slots=allocated,
                unused_slots=allocated-used, unused_fraction=(allocated-used)/allocated if allocated else 0)


def run(seed=20261117, trials=500, requests=100, maximum=2048, budget=32768, blocks=(8,16,32,64)):
    rng = random.Random(seed)
    rows=[]
    for trial in range(trials):
        # Clearly synthetic lengths, not measured production traces.
        # Mixture of short, medium, and long requests; clamp to maximum.
        lengths=[]
        for _ in range(requests):
            category=rng.random()
            if category < .6: length=rng.randint(32, 256)
            elif category < .9: length=rng.randint(257, 1024)
            else: length=rng.randint(1025, maximum)
            lengths.append(length)
        for name,block in [('fixed',0)]+[('paged',b) for b in blocks]:
            result=admit(lengths,budget,name,maximum,block)
            rows.append(dict(trial=trial,seed=seed,strategy=name,block_size=block,requests=requests,
                             maximum=maximum,budget=budget,**result))
    return rows


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default='results.csv');p.add_argument('--seed',type=int,default=20261117)
    p.add_argument('--trials',type=int,default=500);args=p.parse_args()
    rows=run(seed=args.seed,trials=args.trials)
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    for name,block in [('fixed',0),('paged',8),('paged',16),('paged',32),('paged',64)]:
        group=[r for r in rows if r['strategy']==name and r['block_size']==block]
        print(f'{name:5} block={block:2} admitted={sum(r["admitted"] for r in group)/len(group):.2f} '
              f'unused_fraction={sum(r["unused_fraction"] for r in group)/len(group):.3%}')
    print(f'Wrote {len(rows)} rows to {out}')
if __name__=='__main__': main()
