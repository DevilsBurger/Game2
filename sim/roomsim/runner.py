"""Run many room simulations in parallel and aggregate the metrics."""
import json
import os
import statistics
from multiprocessing import Pool

from .params import load_params, load_stages, iter_rooms
from .engine import World

_P = None
_STAGES = None


def _init(params_path, stages_path):
    global _P, _STAGES
    _P = load_params(params_path)
    _STAGES = load_stages(stages_path)


def _room_lookup(stages, room_id):
    for ch in stages['chapters']:
        for r in ch['rooms']:
            if r['id'] == room_id:
                return ch, r
    raise KeyError(room_id)


def _run_task(task):
    room_id, char, skill, seed, difficulty = task
    ch, room = _room_lookup(_STAGES, room_id)
    w = World(_P, room, ch['chapter'], char, skill, seed, difficulty)
    res = w.run()
    res.update({'room': room_id, 'chapter': ch['chapter'], 'type': room['type'], 'char': char, 'skill': skill, 'seed': seed})
    return res


def run_suite(params_path, stages_path, chapters=None, chars=('trigger', 'knuckle', 'edge'), skills=('average',),
              trials=24, difficulty='normal', procs=4, rooms=None):
    stages = load_stages(stages_path)
    tasks = []
    for ch, r in iter_rooms(stages, chapters):
        if rooms and r['id'] not in rooms:
            continue
        for c in chars:
            for s in skills:
                for i in range(trials):
                    tasks.append((r['id'], c, s, 1000 * i + hash((r['id'], c, s)) % 997, difficulty))
    if procs <= 1:
        _init(params_path, stages_path)
        results = [_run_task(t) for t in tasks]
    else:
        with Pool(procs, initializer=_init, initargs=(params_path, stages_path)) as pool:
            results = list(pool.imap_unordered(_run_task, tasks, chunksize=4))
    return results


def _pct(xs, q):
    if not xs:
        return 0.0
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def aggregate(results):
    groups = {}
    for r in results:
        key = (r['chapter'], r['room'], r['char'], r['skill'])
        groups.setdefault(key, []).append(r)
    out = {}
    for key, rs in groups.items():
        n = len(rs)
        succ = [r for r in rs if r['success']]
        times = [r['time'] for r in succ] or [r['time'] for r in rs]
        src = {}
        for r in rs:
            for k, v in r['dmg_by_src'].items():
                src[k] = src.get(k, 0.0) + v
        tot = sum(src.values()) or 1.0
        grades = {g: sum(1 for r in rs if r['grade'] == g) for g in ('S', 'A', 'B', 'C')}
        out[key] = {
            'n': n, 'type': rs[0]['type'],
            'success': sum(1 for r in rs if r['success']) / n,
            'death': sum(1 for r in rs if r['death']) / n,
            'fail': sum(1 for r in rs if r['fail']) / n,
            'time_mean': statistics.fmean(times), 'time_p50': _pct(times, 0.5), 'time_p90': _pct(times, 0.9),
            'dmg_frac_mean': statistics.fmean([r['dmg_frac'] for r in rs]),
            'hp_end_mean': statistics.fmean([r['hp_end_frac'] for r in rs]),
            'chip_uptime': statistics.fmean([r['chip_uptime'] for r in rs]),
            'skill_uses': statistics.fmean([r['skill_uses'] for r in rs]),
            'dash_uses': statistics.fmean([r['dash_uses'] for r in rs]),
            'throws': statistics.fmean([r['throws'] for r in rs]),
            'reflects': statistics.fmean([r['reflects'] for r in rs]),
            'overrides': statistics.fmean([r['overrides'] for r in rs]),
            'kills': statistics.fmean([r['kills'] for r in rs]),
            'grades': grades,
            'dmg_src_share': {k: round(v / tot, 3) for k, v in sorted(src.items(), key=lambda kv: -kv[1])},
        }
    return out


def summarize_by_char(agg):
    """Chapter x char roll-up: mean death rate, expected instances lost, mean hp lost."""
    roll = {}
    for (ch, room, char, skill), a in agg.items():
        key = (ch, char, skill)
        r = roll.setdefault(key, {'rooms': 0, 'death_sum': 0.0, 'exp_inst': 0.0, 'dmg_sum': 0.0, 'time_sum': 0.0, 'fail_sum': 0.0})
        r['rooms'] += 1
        r['death_sum'] += a['death']
        p = min(a['death'], 0.95)
        r['exp_inst'] += p / (1.0 - p)
        r['dmg_sum'] += a['dmg_frac_mean']
        r['time_sum'] += a['time_mean']
        r['fail_sum'] += a['fail']
    for k, r in roll.items():
        n = r['rooms']
        r['death_mean'] = r['death_sum'] / n
        r['dmg_mean'] = r['dmg_sum'] / n
        r['fail_mean'] = r['fail_sum'] / n
    return roll


def to_markdown(agg, stages, title='Balance run'):
    lines = ['# %s' % title, '']
    chapters = sorted({k[0] for k in agg})
    for ch in chapters:
        chd = next(c for c in stages['chapters'] if c['chapter'] == ch)
        lines.append('## Chapter %d — %s' % (ch, chd['name']))
        lines.append('')
        lines.append('| room | type | char | skill | succ% | death% | fail% | t_mean | t_p90 | dmg% | hp_end% | chip% | skill | dash | throw | refl | ovr | S/A/B/C | top damage sources |')
        lines.append('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
        order = [r['id'] for r in chd['rooms']]
        keys = sorted([k for k in agg if k[0] == ch], key=lambda k: (order.index(k[1]), ['trigger', 'knuckle', 'edge'].index(k[2]), k[3]))
        for k in keys:
            a = agg[k]
            g = a['grades']
            src = ', '.join('%s %d%%' % (s, round(v * 100)) for s, v in list(a['dmg_src_share'].items())[:3])
            lines.append('| %s | %s | %s | %s | %d | %d | %d | %.1f | %.1f | %d | %d | %d | %.1f | %.1f | %.1f | %.1f | %.1f | %d/%d/%d/%d | %s |' % (
                k[1], a['type'], k[2], k[3], round(a['success'] * 100), round(a['death'] * 100), round(a['fail'] * 100),
                a['time_mean'], a['time_p90'], round(a['dmg_frac_mean'] * 100), round(a['hp_end_mean'] * 100),
                round(a['chip_uptime'] * 100), a['skill_uses'], a['dash_uses'], a['throws'], a['reflects'], a['overrides'],
                g['S'], g['A'], g['B'], g['C'], src))
        lines.append('')
    roll = summarize_by_char(agg)
    lines.append('## Chapter roll-up (per character)')
    lines.append('')
    lines.append('| chapter | char | skill | rooms | mean death% | expected instances lost | mean dmg% of HP | mean fail% |')
    lines.append('|---|---|---|---|---|---|---|---|')
    for k in sorted(roll, key=lambda k: (k[0], ['trigger', 'knuckle', 'edge'].index(k[1]), k[2])):
        r = roll[k]
        lines.append('| %d | %s | %s | %d | %.1f | %.2f | %d | %.1f |' % (k[0], k[1], k[2], r['rooms'], r['death_mean'] * 100, r['exp_inst'], round(r['dmg_mean'] * 100), r['fail_mean'] * 100))
    lines.append('')
    return '\n'.join(lines)


def save(results, agg, stages, out_prefix, title):
    os.makedirs(os.path.dirname(out_prefix) or '.', exist_ok=True)
    with open(out_prefix + '.json', 'w', encoding='utf-8') as f:
        json.dump({'aggregate': {'|'.join(map(str, k)): v for k, v in agg.items()}, 'n_results': len(results)}, f, ensure_ascii=False, indent=1)
    md = to_markdown(agg, stages, title)
    with open(out_prefix + '.md', 'w', encoding='utf-8') as f:
        f.write(md)
    return md
