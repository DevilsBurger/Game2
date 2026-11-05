#!/usr/bin/env python3
"""CLI: run the ROOM ZERO balance suite.

Examples:
  python3 sim/run_balance.py --chapters 1 --trials 12
  python3 sim/run_balance.py --chapters 1,2,3,4,5,6 --skills average,expert,novice --trials 24 --out sim/results/v0_full
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from roomsim.runner import run_suite, aggregate, save, to_markdown  # noqa: E402
from roomsim.params import load_stages  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--params', default=os.path.join(os.path.dirname(__file__), 'params.json'))
    ap.add_argument('--stages', default=os.path.join(os.path.dirname(__file__), 'stages.json'))
    ap.add_argument('--chapters', default='1')
    ap.add_argument('--rooms', default='')
    ap.add_argument('--chars', default='trigger,knuckle,edge')
    ap.add_argument('--skills', default='average')
    ap.add_argument('--trials', type=int, default=24)
    ap.add_argument('--difficulty', default='normal')
    ap.add_argument('--procs', type=int, default=4)
    ap.add_argument('--out', default='')
    ap.add_argument('--title', default='Balance run')
    args = ap.parse_args()
    chapters = [int(x) for x in args.chapters.split(',') if x]
    rooms = [x for x in args.rooms.split(',') if x] or None
    t0 = time.time()
    results = run_suite(args.params, args.stages, chapters, tuple(args.chars.split(',')), tuple(args.skills.split(',')),
                        args.trials, args.difficulty, args.procs, rooms)
    agg = aggregate(results)
    stages = load_stages(args.stages)
    if args.out:
        md = save(results, agg, stages, args.out, args.title)
    else:
        md = to_markdown(agg, stages, args.title)
    print(md)
    print('runs: %d, wall: %.1fs' % (len(results), time.time() - t0), file=sys.stderr)


if __name__ == '__main__':
    main()
