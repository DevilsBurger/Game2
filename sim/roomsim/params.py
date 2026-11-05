"""Load params.json / stages.json and resolve enemy 'base' inheritance."""
import copy
import json


def _deep_merge(base, override):
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_params(path):
    with open(path, encoding='utf-8') as f:
        p = json.load(f)
    raw = p['enemies']
    resolved = {}

    def resolve(name, chain=()):
        if name in resolved:
            return resolved[name]
        if name in chain:
            raise ValueError('cyclic enemy base: %s' % name)
        spec = raw[name]
        if 'base' in spec:
            base = resolve(spec['base'], chain + (name,))
            merged = _deep_merge(base, {k: v for k, v in spec.items() if k != 'base'})
        else:
            merged = copy.deepcopy(spec)
        merged['id'] = name
        resolved[name] = merged
        return merged

    for n in raw:
        resolve(n)
    p['enemies'] = resolved
    return p


def load_stages(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def iter_rooms(stages, chapters=None, exclude=('service',)):
    for ch in stages['chapters']:
        if chapters and ch['chapter'] not in chapters:
            continue
        for r in ch['rooms']:
            if r['type'] in exclude:
                continue
            yield ch, r
