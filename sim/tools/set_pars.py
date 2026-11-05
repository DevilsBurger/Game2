#!/usr/bin/env python3
"""Derive room par times from an expert-skill results JSON and write them into stages.json.

Rule: combat-like rooms  par = ceil(expert p50 * 1.15 / 5) * 5 (min 20)
      rush rooms         par = ceil(expert p50 * 1.2)
      defend rooms       par = duration (fixed by design)
      boss rooms         par = ceil(expert p50 * 1.15 / 10) * 10
Expert p50 is the median over the three characters' medians, so no doctrine is favoured.
"""
import json
import math
import statistics
import sys


def main(results_path, stages_path):
    agg = json.load(open(results_path, encoding='utf-8'))['aggregate']
    per_room = {}
    for key, a in agg.items():
        ch, room, char, skill = key.split('|')
        if skill != 'expert':
            continue
        per_room.setdefault(room, []).append(a['time_p50'])
    S = json.load(open(stages_path, encoding='utf-8'))
    changed = []
    for c in S['chapters']:
        for r in c['rooms']:
            if r['type'] == 'service':
                continue
            if r['type'] == 'defend':
                new = r['duration']
            else:
                if r['id'] not in per_room:
                    continue
                p50 = statistics.median(per_room[r['id']])
                if r['type'] == 'rush':
                    new = int(math.ceil(p50 * 1.2))
                elif r['type'] == 'boss':
                    new = int(math.ceil(p50 * 1.15 / 10.0) * 10)
                else:
                    new = max(20, int(math.ceil(p50 * 1.15 / 5.0) * 5))
            if r.get('par') != new:
                changed.append((r['id'], r.get('par'), new))
                r['par'] = new
    json.dump(S, open(stages_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    for rid, old, new in changed:
        print('%s: par %s -> %s' % (rid, old, new))
    print('%d rooms updated' % len(changed))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
