"""Heuristic player bots for the three doctrines. Skill profile drives reaction, dodge odds, aim error and tactics."""
import math

from .geom import unit, dist, ang_deg, perp, seg_dist


class Bot:
    def __init__(self, world, player, skill):
        self.W = world
        self.p = player
        self.sk = skill
        self.rng = world.rng
        self.next_decision = 0.0
        self.base_move = (0.0, 0.0)
        self.override_move = None
        self.strafe_sign = 1 if self.rng.random() < 0.5 else -1
        self.strafe_timer = self.rng.uniform(1.0, 2.0)
        self.seen = {}
        self.face_dir = None
        self.face_until = 0.0
        self.throw_cd = 0.0
        self.hold_cd = 0.0
        self.pickup_lock = None

    # -- utils ----------------------------------------------------------------
    def roll(self):
        return self.rng.random() < self.sk['tactic_prob']

    def decided(self, key, telegraphed=False):
        dec = self.seen.get(key)
        if dec is None:
            prob = self.sk.get('telegraph_dodge_prob', self.sk['dodge_prob']) if telegraphed else self.sk['dodge_prob']
            dec = self.rng.random() < prob
            self.seen[key] = dec
        return dec

    def toward(self, pos):
        p = self.p.pos
        return unit(pos[0] - p[0], pos[1] - p[1])

    def avoid_walls(self, mv):
        W = self.W
        p = self.p.pos
        x, y = mv
        m = 1.0
        if p[0] < m and x < 0:
            x = 0.0
        if p[0] > W.W - m and x > 0:
            x = 0.0
        if p[1] < m and y < 0:
            y = 0.0
        if p[1] > W.H - m and y > 0:
            y = 0.0
        if p[0] < 0.7:
            x += 0.6
        if p[0] > W.W - 0.7:
            x -= 0.6
        if p[1] < 0.7:
            y += 0.6
        if p[1] > W.H - 0.7:
            y -= 0.6
        return unit(x, y) if (x or y) else (0.0, 0.0)

    def surface_dist(self, tgt):
        return dist(tgt.pos, self.p.pos) - getattr(tgt, 'radius', 0.4)

    def escape_dir(self, aoes, primary):
        """Pick the direction (8 candidates) whose landing point 2.5 m away is outside the most AoEs and inside the room."""
        W = self.W
        p = self.p
        px, py = p.pos
        prad = p.hit_radius()
        best = None
        best_score = None
        base = unit(px - primary.pos[0], py - primary.pos[1])
        if base == (0.0, 0.0):
            base = (0.0, 1.0)
        for k in range(8):
            ang = 45.0 * k
            c, s_ = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            d = (base[0] * c - base[1] * s_, base[0] * s_ + base[1] * c)
            tx, ty = px + d[0] * 2.5, py + d[1] * 2.5
            if not (prad <= tx <= W.W - prad and prad <= ty <= W.H - prad):
                continue
            score = 0.0
            for a in aoes:
                if a.delay <= primary.delay + 0.6 and dist((tx, ty), a.pos) <= a.radius + prad + 0.2:
                    score += 10.0
            score += (k if k <= 4 else 8 - k) * 0.5
            if best_score is None or score < best_score:
                best_score = score
                best = d
        return best or base

    # -- per tick ---------------------------------------------------------------
    def tick(self, dt):
        W = self.W
        p = self.p
        t = W.t
        if p.dead:
            return
        it = p.intent
        it['dash'] = None
        it['skill'] = None
        it['hold'] = False
        it['override'] = None
        it['face'] = None
        self.strafe_timer -= dt
        self.throw_cd -= dt
        self.hold_cd -= dt
        if self.strafe_timer <= 0:
            self.strafe_sign = -self.strafe_sign
            self.strafe_timer = self.rng.uniform(1.0, 2.2)
        if t >= self.next_decision:
            self.next_decision = t + self.sk['decision_period']
            self.decide()
        self.threats()
        mv = self.base_move
        if self.override_move is not None and t < self.override_move[1]:
            mv = self.override_move[0]
            if p.is_melee() and self.override_move[2]:
                it['attack'] = False
        it['move'] = self.avoid_walls(mv)
        if self.face_dir is not None and t < self.face_until:
            it['face'] = self.face_dir
        p.tick_active_reflect(W)

    # -- threat response ----------------------------------------------------------
    def threats(self):
        W = self.W
        p = self.p
        t = W.t
        sk = self.sk
        react = sk['reaction']
        px, py = p.pos
        prad = p.hit_radius()
        dodge_dir = None
        urgency = 9.0
        reflect = None
        hold_time = 0.4
        cancel = False
        for pr in W.projectiles:
            if not pr.alive or pr.owner != 'enemy':
                continue
            rx, ry = pr.pos[0] - px, pr.pos[1] - py
            vx, vy = pr.vel
            vv = vx * vx + vy * vy
            if vv < 1e-6:
                continue
            rv = rx * vx + ry * vy
            if rv >= 0:
                continue
            tca = -rv / vv
            if tca > react + 0.15:
                continue
            cx, cy = rx + vx * tca, ry + vy * tca
            if math.hypot(cx, cy) > prad + pr.radius + 0.25:
                continue
            if not self.decided(id(pr)):
                continue
            if tca < urgency:
                urgency = tca
                if p.id == 'edge' and pr.reflectable and not p.vehicle and p.state == 'normal':
                    reflect = pr
                    dodge_dir = None
                else:
                    reflect = None
                    pv = perp(unit(vx, vy))
                    side = 1.0 if (cx * pv[0] + cy * pv[1]) < 0 else -1.0
                    dodge_dir = (pv[0] * side, pv[1] * side)
                    hold_time = min(0.45, tca + 0.2)
                    cancel = False
        live_aoes = [a for a in W.aoes if a.alive and a.owner == 'enemy']
        for a in live_aoes:
            d = dist(a.pos, p.pos)
            if d > a.radius + prad + 0.3 or a.delay > react + 0.5:
                continue
            if not self.decided(id(a), True):
                continue
            if a.delay < urgency:
                urgency = a.delay
                reflect = None
                dodge_dir = self.escape_dir(live_aoes, a)
                hold_time = a.delay + 0.15
                cancel = True
        for b in W.beams:
            if not b.alive:
                continue
            remaining = b.telegraph - b.elapsed
            if remaining > react + 0.5:
                continue
            if seg_dist(b.origin, b.end(), p.pos) > b.width / 2 + prad + 0.5:
                continue
            if not self.decided(id(b), True):
                continue
            if remaining < urgency:
                urgency = remaining
                reflect = None
                pv = perp(b.dir)
                rel = (px - b.origin[0], py - b.origin[1])
                side = 1.0 if (rel[0] * pv[0] + rel[1] * pv[1]) >= 0 else -1.0
                dodge_dir = (pv[0] * side, pv[1] * side)
                hold_time = remaining + 0.15
                cancel = True
        for e in W.enemies:
            if not e.alive or e.atk is None:
                continue
            kind = e.atk.get('kind')
            if kind == 'melee':
                a = e.spec['attack']
                if dist(e.pos, p.pos) > a['hit_range'] + prad + 0.4 or e.atk['t'] > react + 0.2:
                    continue
                if not self.decided(id(e.atk), True):
                    continue
                if p.id == 'knuckle' and p.hp > 0.3 * p.max_hp:
                    continue
                if e.atk['t'] < urgency:
                    urgency = e.atk['t']
                    reflect = None
                    away = unit(px - e.pos[0], py - e.pos[1])
                    if away == (0.0, 0.0):
                        away = (1.0, 0.0)
                    if p.id == 'edge' and p.dash_cd <= 0 and p.state == 'normal':
                        dodge_dir = (-away[0], -away[1])
                    else:
                        pv = perp(away)
                        dodge_dir = unit(away[0] + pv[0] * self.strafe_sign, away[1] + pv[1] * self.strafe_sign)
                    hold_time = e.atk['t'] + 0.1
                    cancel = False
            elif kind == 'telegraph' and e.behavior == 'sniper':
                remaining = e.atk['t']
                if remaining > react + 0.3:
                    continue
                if e.atk.get('locked') and e.atk.get('aim') is not None and dist(e.atk['aim'], p.pos) > prad + 0.7:
                    continue
                if not self.decided(id(e.atk), True):
                    continue
                if remaining < urgency:
                    urgency = remaining
                    reflect = None
                    pv = perp(unit(px - e.pos[0], py - e.pos[1]))
                    dodge_dir = (pv[0] * self.strafe_sign, pv[1] * self.strafe_sign)
                    hold_time = remaining + 0.15
                    cancel = False
        B = W.boss
        if B is not None and B.alive and B.state == 'telegraph' and B.cur is not None:
            tp = B.cur['type']
            remaining = B.timer
            if tp in ('fan', 'ring') and p.is_melee() and remaining <= react + 0.8:
                arm = B.cur.get('arm', 1.5)
                ds = dist(B.pos, p.pos) - B.radius - p.hit_radius()
                if 0.0 < ds <= arm + 2.5 and self.decided(('boss', B.tele_id), True):
                    to_b = unit(B.pos[0] - px, B.pos[1] - py)
                    if ds > arm - 0.4 and B.hittable_melee():
                        dodge_dir = to_b
                        hold_time = remaining + 0.3
                        cancel = False
                        urgency = min(urgency, remaining)
                        reflect = None
            if remaining <= react + 0.6 and tp in ('charge', 'sweep'):
                if self.decided(('boss', B.tele_id), True):
                    to_b = unit(B.pos[0] - px, B.pos[1] - py)
                    if tp == 'charge':
                        pv = perp(to_b)
                        dodge_dir = (pv[0] * self.strafe_sign, pv[1] * self.strafe_sign)
                        hold_time = remaining + 1.0
                    else:
                        y_lock = B.lock if B.lock is not None else py
                        dodge_dir = (0.0, 1.0 if py >= y_lock else -1.0)
                        hold_time = remaining + 0.2
                    cancel = True
                    if remaining < urgency:
                        urgency = remaining
                    reflect = None
        if reflect is not None:
            v = reflect.vel
            self.face_dir = unit(-v[0], -v[1])
            self.face_until = t + 0.3
            p.intent['attack'] = True
            p.intent['aim'] = None
        elif dodge_dir is not None:
            if W.rtype == 'rush':
                te = unit(W.exit_pos[0] - px, W.exit_pos[1] - py)
                dodge_dir = unit(dodge_dir[0] + 0.8 * te[0], dodge_dir[1] + 0.8 * te[1])
            ds = p.c['dash']
            if p.dash_cd <= 0 and ds['iframes'] > 0 and urgency <= 0.35 and p.state == 'normal' and not p.vehicle:
                p.intent['dash'] = dodge_dir
            else:
                self.override_move = (dodge_dir, t + max(0.3, hold_time), cancel)

    # -- decisions -----------------------------------------------------------------
    def decide(self):
        W = self.W
        p = self.p
        it = p.intent
        enemies = [e for e in W.enemies if e.targetable()]
        boss = W.boss if (W.boss is not None and W.boss.alive) else None
        it['attack'] = False
        it['aim'] = None
        if W.rtype == 'rush':
            self.decide_rush(enemies)
            return
        anchor = W.node['pos'] if W.node else None
        pk = self.pick_pickup(enemies)
        if not enemies and not boss:
            if pk is not None:
                self.base_move = self.toward(pk.pos)
            elif anchor is not None and dist(p.pos, anchor) > 2.0:
                self.base_move = self.toward(anchor)
            else:
                self.base_move = (0.0, 0.0)
            return
        ov = self.find_override(enemies)
        if ov is not None:
            it['override'] = ov
            d = self.surface_dist(ov)
            if p.id == 'edge':
                if d <= 4.5 and p.dash_cd <= 0 and p.state == 'normal':
                    it['dash'] = self.toward(ov.pos)
                self.base_move = self.toward(ov.pos)
            else:
                self.base_move = self.toward(ov.pos) if d > 0.6 else (0.0, 0.0)
            if p.id == 'trigger':
                tgt = self.pick_target(enemies, boss, 7.0)
                if tgt is not None and p.state != 'override':
                    it['aim'] = tgt.pos
                    it['attack'] = True
            return
        if p.id == 'trigger':
            self.decide_trigger(enemies, boss, anchor, pk)
        elif p.id == 'knuckle':
            self.decide_knuckle(enemies, boss, anchor, pk)
        else:
            self.decide_edge(enemies, boss, anchor, pk)

    def pick_target(self, enemies, boss, add_range):
        p = self.p
        W = self.W
        if W.node is not None:
            cands = [e for e in enemies if not e.dormant] or enemies
            if cands:
                return min(cands, key=lambda e: dist(e.pos, W.node['pos']) * (0.6 if e.behavior == 'melee' else 1.0))
        if boss is not None:
            if p.is_melee() and p.hp < 0.6 * p.max_hp:
                add_range = max(add_range, 7.0)
            adds = [e for e in enemies if self.surface_dist(e) <= add_range]
            if adds:
                return min(adds, key=lambda e: dist(e.pos, p.pos))
            return boss
        if not enemies:
            return None

        def w(e):
            d = dist(e.pos, p.pos)
            if e.behavior in ('sniper', 'lobber'):
                d *= 0.7
            if e.behavior in ('turret', 'beam_turret') and p.id == 'trigger':
                d *= 0.6
            if e.behavior == 'teleporter' and p.is_melee() and e.atk is None:
                d *= 0.5
            if e.dormant:
                d *= 1.5
            return d
        return min(enemies, key=w)

    def pick_pickup(self, enemies):
        p = self.p
        best = None
        bd = 7.0
        for pk in self.W.pickups:
            if not pk.alive:
                continue
            if pk.kind == 'chip' and p.chip is not None and p.chip_left > p.chip_total * 0.3:
                continue
            if pk.kind == 'charge' and p.charges >= p.charges_max:
                continue
            d = dist(pk.pos, p.pos)
            if d >= bd:
                continue
            if any((not e.dormant) and dist(e.pos, pk.pos) < 2.5 for e in enemies):
                continue
            best = pk
            bd = d
        return best

    def find_override(self, enemies):
        p = self.p
        W = self.W
        if p.vehicle is not None:
            return None
        mind = W.g['player_common']['override_min_enemy_distance']
        for e in enemies:
            if e.overridable and e.behavior == 'vehicle' and e.state == 'stunned':
                if p.hp < 0.25 * p.max_hp:
                    continue
                if any(o is not e and o.active() and dist(o.pos, e.pos) < mind for o in enemies):
                    continue
                return e
        if p.id == 'knuckle' and p.carried is None and p.c['override'].get('carry_sentry'):
            for e in enemies:
                if e.behavior in ('turret', 'beam_turret') and e.alive and not e.dormant and e.hp <= e.max_hp * p.c['override'].get('carry_hp_frac', 0.5) \
                        and e.stream_left <= 0 and e.atk is None:
                    others = sum(1 for o in enemies if o is not e and o.active() and dist(o.pos, e.pos) < 8.0)
                    if others == 0:
                        return e
        return None

    def cluster_target(self, enemies, radius, max_dist, min_count):
        p = self.p
        best = None
        bc = min_count - 1
        for e in enemies:
            if dist(e.pos, p.pos) > max_dist:
                continue
            c = sum(1 for o in enemies if dist(o.pos, e.pos) <= radius)
            if c > bc:
                bc = c
                best = e
        return best

    def incoming_count(self):
        p = self.p
        n = 0
        for pr in self.W.projectiles:
            if not pr.alive or pr.owner != 'enemy':
                continue
            rx, ry = pr.pos[0] - p.pos[0], pr.pos[1] - p.pos[1]
            if rx * pr.vel[0] + ry * pr.vel[1] < 0 and math.hypot(rx, ry) < 6.0:
                n += 1
        return n

    def anchor_move(self, anchor, to_t):
        p = self.p
        if anchor is not None:
            node = self.W.node
            r = 6.0 if node['hp'] > 0.5 * node['max_hp'] else 2.5
            if dist(p.pos, anchor) > r:
                return self.toward(anchor)
        return None

    # -- trigger ----------------------------------------------------------------------
    def decide_trigger(self, enemies, boss, anchor, pk):
        p = self.p
        it = p.intent
        tgt = self.pick_target(enemies, boss, 7.0)
        d = self.surface_dist(tgt)
        to_t = self.toward(tgt.pos)
        it['aim'] = tgt.pos
        it['attack'] = d <= p.weapon_range() + 0.5
        am = self.anchor_move(anchor, to_t)
        near_d = 4.5 if boss is None or tgt is not boss else 6.5
        if am is not None:
            self.base_move = am
        elif pk is not None and (p.chip is None or pk.kind == 'charge'):
            self.base_move = self.toward(pk.pos)
        elif d < near_d:
            self.base_move = (-to_t[0], -to_t[1])
        elif d > 8.5:
            self.base_move = to_t
        else:
            pv = perp(to_t)
            self.base_move = (pv[0] * self.strafe_sign, pv[1] * self.strafe_sign)
        if p.charges > 0 and p.skill_cd <= 0 and p.state == 'normal' and self.roll():
            c = self.cluster_target(enemies, 2.5, p.c['skill']['range'], 3)
            if c is not None:
                it['skill'] = c.pos
            elif boss is not None and dist(boss.pos, p.pos) <= p.c['skill']['range'] + boss.radius and p.charges >= 3:
                it['skill'] = boss.pos
        if p.vehicle and p.sub_cd <= 0:
            c = self.cluster_target(enemies, 2.5, p.vehicle['sub']['range'], 2)
            if c is not None:
                it['skill'] = c.pos
            elif boss is not None:
                it['skill'] = boss.pos

    # -- knuckle ----------------------------------------------------------------------
    def decide_knuckle(self, enemies, boss, anchor, pk):
        p = self.p
        it = p.intent
        tgt = self.pick_target(enemies, boss, 4.0)
        d = self.surface_dist(tgt)
        to_t = self.toward(tgt.pos)
        reach = p.c['basic']['range']
        it['aim'] = tgt.pos
        if p.vehicle:
            it['attack'] = d <= p.weapon_range()
            self.base_move = to_t if d > 6.0 else (-to_t[0], -to_t[1]) if d < 3.0 else (0.0, 0.0)
            if p.sub_cd <= 0:
                it['skill'] = tgt.pos
            return
        if p.carried:
            it['attack'] = d <= p.weapon_range()
            self.base_move = to_t if d > 6.0 else (0.0, 0.0)
            return
        am = self.anchor_move(anchor, to_t)
        if am is not None and d > 3.0:
            self.base_move = am
            return
        if pk is not None and d > 3.0:
            self.base_move = self.toward(pk.pos)
            return
        if d > 4.0 and p.dash_cd <= 0 and p.state == 'normal' and self.roll():
            it['dash'] = to_t
            self.base_move = to_t
            return
        if d > reach - 0.2:
            self.base_move = to_t
        else:
            self.base_move = (0.0, 0.0)
            it['attack'] = True
        if tgt is not boss and tgt.throwable and d <= reach and self.throw_cd <= 0 and p.state == 'normal' and self.roll():
            tt = None
            if boss is not None and not boss.hittable_melee():
                tt = boss
            else:
                others = [e for e in enemies if e is not tgt and dist(e.pos, p.pos) <= p.c['hold']['throw_range']]
                if others:
                    tt = max(others, key=lambda e: sum(1 for o in others if dist(o.pos, e.pos) <= 2.0))
                elif boss is not None and dist(boss.pos, p.pos) <= p.c['hold']['throw_range'] + boss.radius:
                    tt = boss
            if tt is not None:
                it['hold'] = True
                it['hold_dir'] = self.toward(tt.pos)
                self.throw_cd = 2.0
        if p.chip is not None and 'hold_replace' in p.chip and d > 3.0 and self.hold_cd <= 0:
            it['hold'] = True
            it['hold_dir'] = to_t
            self.hold_cd = 1.0
        n_close = sum(1 for e in enemies if dist(e.pos, p.pos) <= p.c['skill']['radius'])
        if boss is not None and dist(boss.pos, p.pos) <= p.c['skill']['radius'] + boss.radius:
            n_close += 2
        if p.charges > 0 and p.skill_cd <= 0 and p.state == 'normal' and self.roll():
            if n_close >= 3 or (p.hp < 0.4 * p.max_hp and n_close >= 2) or self.incoming_count() >= 3:
                it['skill'] = p.pos

    # -- edge -------------------------------------------------------------------------
    def decide_edge(self, enemies, boss, anchor, pk):
        p = self.p
        it = p.intent
        tgt = self.pick_target(enemies, boss, 4.0)
        d = self.surface_dist(tgt)
        to_t = self.toward(tgt.pos)
        reach = p.weapon_range()
        it['aim'] = tgt.pos
        if p.vehicle:
            it['attack'] = d <= p.vehicle['gun']['range']
            self.base_move = to_t if d > 6.0 else (-to_t[0], -to_t[1]) if d < 3.0 else (0.0, 0.0)
            if p.sub_cd <= 0:
                it['skill'] = tgt.pos
            return
        am = self.anchor_move(anchor, to_t)
        if am is not None and d > 3.0:
            self.base_move = am
            return
        if pk is not None and d > 3.0:
            self.base_move = self.toward(pk.pos)
            return
        if d > 4.5 and p.dash_cd <= 0 and p.state == 'normal' and self.roll():
            a = (p.pos[0], p.pos[1])
            b = (p.pos[0] + to_t[0] * p.c['dash']['distance'], p.pos[1] + to_t[1] * p.c['dash']['distance'])
            if any(seg_dist(a, b, e.pos) <= 1.0 for e in enemies) or (tgt is boss and d <= 7.0):
                it['dash'] = to_t
                self.base_move = to_t
                return
        if d > reach * 0.85:
            self.base_move = to_t
        else:
            self.base_move = (0.0, 0.0)
            it['attack'] = True
        if d > 1.8 and self.hold_cd <= 0 and p.state == 'normal' and self.roll():
            cone = [e for e in enemies if dist(e.pos, p.pos) <= p.c['hold']['length'] and
                    ang_deg(to_t, (e.pos[0] - p.pos[0], e.pos[1] - p.pos[1])) <= 25]
            if len(cone) >= 2 or (boss is not None and d <= p.c['hold']['length'] and len(cone) >= 1):
                it['hold'] = True
                it['hold_dir'] = to_t
                self.hold_cd = 2.5
        if p.charges > 0 and p.skill_cd <= 0 and p.state == 'normal' and self.roll():
            cone = [e for e in enemies if dist(e.pos, p.pos) <= p.c['skill']['range'] and
                    ang_deg(to_t, (e.pos[0] - p.pos[0], e.pos[1] - p.pos[1])) <= 20]
            if len(cone) >= 3 or self.incoming_count() >= 2 or (boss is not None and p.charges >= 3 and d <= 10.0):
                it['skill'] = tgt.pos

    # -- rush rooms ---------------------------------------------------------------------
    def decide_rush(self, enemies):
        p = self.p
        W = self.W
        it = p.intent
        to_exit = self.toward(W.exit_pos)
        blockers = [e for e in enemies if dist(e.pos, p.pos) <= 3.5 and
                    (to_exit[0] * (e.pos[0] - p.pos[0]) + to_exit[1] * (e.pos[1] - p.pos[1])) > 0.2 * dist(e.pos, p.pos)]
        mv = [to_exit[0], to_exit[1]]
        if blockers:
            b = min(blockers, key=lambda e: dist(e.pos, p.pos))
            rel = (b.pos[0] - p.pos[0], b.pos[1] - p.pos[1])
            side = 1.0 if rel[1] < 0 else -1.0
            mv[1] += 0.9 * side
            if abs(p.pos[1] - W.H / 2) > W.H / 2 - 1.5:
                mv[1] = (W.H / 2 - p.pos[1]) * 0.5
        self.base_move = unit(mv[0], mv[1])
        tgt = None
        if enemies:
            tgt = min(enemies, key=lambda e: dist(e.pos, p.pos) + (0.0 if e in blockers else 3.0))
        if p.id == 'trigger':
            if tgt is not None and dist(tgt.pos, p.pos) <= p.weapon_range():
                it['aim'] = tgt.pos
                it['attack'] = True
            if blockers and p.charges > 0 and p.skill_cd <= 0 and len(blockers) >= 2 and self.roll():
                it['skill'] = blockers[0].pos
        elif p.id == 'knuckle':
            if p.dash_cd <= 0 and p.state == 'normal' and self.roll() and (blockers or self.rng.random() < 0.3):
                it['dash'] = to_exit
            if tgt is not None and self.surface_dist(tgt) <= p.c['basic']['range']:
                it['aim'] = tgt.pos
                it['attack'] = True
            if len(blockers) >= 3 and p.charges > 0 and p.skill_cd <= 0 and self.roll():
                it['skill'] = p.pos
        else:
            if blockers and p.dash_cd <= 0 and p.state == 'normal' and self.roll():
                it['dash'] = to_exit
            if tgt is not None and self.surface_dist(tgt) <= p.weapon_range():
                it['aim'] = tgt.pos
                it['attack'] = True
            if len(blockers) >= 2 and p.charges > 0 and p.skill_cd <= 0 and self.roll():
                it['skill'] = (p.pos[0] + to_exit[0] * 5, p.pos[1] + to_exit[1] * 5)
