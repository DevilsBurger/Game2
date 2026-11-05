"""Player character (three doctrines) for the ROOM ZERO room simulator."""
import math

from .geom import unit, dist, ang_deg, rotate, seg_dist


class Player:
    def __init__(self, world, char_id, pos):
        P = world.P
        self.P = P
        self.c = P['characters'][char_id]
        self.id = char_id
        g = P['global']['player_common']
        self.pos = [pos[0], pos[1]]
        self.radius = g['hitbox_radius']
        self.pickup_radius = g['pickup_radius']
        mods = getattr(world, 'player_mods', {'hp_bonus': 0, 'dmg_mult': 1.0, 'dash_cd_mult': 1.0, 'ammo_mult': 1.0, 'charges_bonus': 0})
        self.mods = mods
        self.max_hp = float(self.c['hp']) + mods['hp_bonus']
        self.hp = self.max_hp
        self.speed = self.c['move_speed']
        self.facing = (1.0, 0.0)
        self.state = 'normal'
        self.state_timer = 0.0
        self.attack_timer = 0.0
        self.combo_idx = 0
        self.combo_reset = 0.0
        self.active_frames = 0.0
        self.dash_cd = 0.0
        self.dash_dir = (1.0, 0.0)
        self.dash_left = 0.0
        self.dash_speed = 0.0
        self.dash_hit = set()
        self.last_dash_t = -99.0
        self.iframes = 0.0
        self.hit_iframes = g['hit_iframes']
        self.skill_cd = 0.0
        self.skill_target = None
        self.charges = g['charges_start']
        self.charges_max = g['charges_max'] + mods['charges_bonus']
        self.chip = None
        self.chip_type = None
        self.chip_left = 0.0
        self.chip_total = 0.0
        self.vehicle = None
        self.sub_cd = 0.0
        self.carried = None
        self.hold_cd = 0.0
        self.hold_dir = (1.0, 0.0)
        self.grab_target = None
        self.override_target = None
        self.orbital_timer = 0.0
        self.melee_auto_timer = 0.0
        self.dead = False
        self.dmg_taken = 0.0
        self.dmg_by_src = {}
        self.vehicle_dmg = 0.0
        self.intent = {'move': (0.0, 0.0), 'aim': None, 'attack': False, 'hold': False, 'hold_dir': None,
                       'dash': None, 'skill': None, 'override': None, 'face': None}
        self.stats = {'skill_uses': 0, 'dash_uses': 0, 'throws': 0, 'reflects': 0, 'overrides': 0, 'chip_time': 0.0, 'shots': 0}

    # -- queries ------------------------------------------------------------
    def hit_radius(self):
        return self.vehicle['radius'] if self.vehicle else self.radius

    def is_melee(self):
        return self.id in ('knuckle', 'edge')

    def attacking(self):
        return self.combo_reset > 0.0

    def weapon_range(self):
        if self.vehicle:
            return self.vehicle['gun']['range']
        if self.carried:
            return self.carried['range']
        if self.id == 'trigger':
            return (self.chip['range'] if self.chip else self.c['basic']['range'])
        b = self.c['basic']
        mult = self.chip.get('range_mult', 1.0) if self.chip else 1.0
        return b['range'] * mult

    # -- resources ----------------------------------------------------------
    def set_chip(self, chip_type):
        spec = self.P['chips'][chip_type][self.id]
        ammo = float(spec.get('ammo', spec.get('hits', 30)))
        if self.id == 'trigger':
            ammo *= self.c['passive']['chip_ammo_mult']
        ammo *= self.mods['ammo_mult']
        self.chip = spec
        self.chip_type = chip_type
        self.chip_left = ammo
        self.chip_total = ammo

    def consume_chip(self, n=1.0):
        if not self.chip:
            return
        self.chip_left -= n
        if self.chip_left <= 0:
            self.chip = None
            self.chip_type = None

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)

    def direct_damage(self, world, amount, src_id):
        if self.dead:
            return
        if self.vehicle:
            self.vehicle['hp'] -= amount
            self.vehicle_dmg += amount
            if self.vehicle['hp'] <= 0:
                self.vehicle = None
                self.iframes = 1.0
            return
        self.hp -= amount
        self.dmg_taken += amount
        self.dmg_by_src[src_id] = self.dmg_by_src.get(src_id, 0.0) + amount
        if self.hp <= 0:
            self.dead = True

    def take_damage(self, world, amount, src_id, from_pos, src_obj=None):
        if self.dead or self.iframes > 0:
            return
        if self.id == 'edge' and (world.t - self.last_dash_t) <= self.c['passive']['counter_window'] and self.state == 'dash':
            if src_obj is not None and getattr(src_obj, 'alive', False) and dist(src_obj.pos, self.pos) <= self.c['passive']['counter_range']:
                src_obj.take_damage(world, self.c['passive']['counter_damage'], melee=True, from_pos=self.pos)
            self.stats['reflects'] += 0
            return
        if self.vehicle:
            self.vehicle['hp'] -= amount
            self.vehicle_dmg += amount
            if self.vehicle['hp'] <= 0:
                self.vehicle = None
                self.iframes = 1.0
            return
        mult = 1.0
        if self.id == 'knuckle' and self.attacking():
            mult = 1.0 - self.c['basic']['dmg_reduction']
        if self.id == 'knuckle' and self.state == 'dash':
            mult = min(mult, 1.0 - self.c['dash'].get('dmg_reduction', 0.0))
        dmg = amount * mult
        self.hp -= dmg
        self.dmg_taken += dmg
        self.dmg_by_src[src_id] = self.dmg_by_src.get(src_id, 0.0) + dmg
        self.iframes = self.hit_iframes
        if self.state == 'override' and not self.c['override'].get('super_armor', False):
            self.state = 'normal'
            self.override_target = None
        if self.state == 'grab':
            self.state = 'normal'
            if self.grab_target is not None:
                self.grab_target.knockdown = 0.0
                self.grab_target = None
        if self.hp <= 0:
            self.dead = True

    # -- update -------------------------------------------------------------
    def update(self, world, dt):
        if self.dead:
            return
        it = self.intent
        self.attack_timer -= dt
        self.dash_cd -= dt
        self.skill_cd -= dt
        self.hold_cd -= dt
        self.sub_cd -= dt
        self.iframes -= dt
        self.orbital_timer -= dt
        self.melee_auto_timer -= dt
        self.active_frames -= dt
        if self.combo_reset > 0:
            self.combo_reset -= dt
            if self.combo_reset <= 0:
                self.combo_idx = 0
        if self.chip:
            self.stats['chip_time'] += dt

        # facing
        if it['face'] is not None:
            self.facing = it['face']
        elif it['aim'] is not None:
            f = unit(it['aim'][0] - self.pos[0], it['aim'][1] - self.pos[1])
            if f != (0.0, 0.0):
                self.facing = f
        elif it['move'] != (0.0, 0.0):
            self.facing = unit(*it['move'])

        if self.state == 'dash':
            self.step_dash(world, dt)
            if self.id == 'trigger' and it['attack'] and it['aim'] is not None:
                self.do_attack(world, dt)
            return
        if self.state == 'cast':
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state = 'normal'
                self.execute_skill(world)
            return
        if self.state == 'grab':
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state = 'normal'
                self.throw(world)
            return
        if self.state == 'charge':
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state = 'normal'
                self.line_hit(world)
            return
        if self.state == 'override':
            tgt = self.override_target
            if tgt is None or not tgt.alive or (tgt.behavior == 'vehicle' and tgt.state != 'stunned'):
                self.state = 'normal'
                self.override_target = None
                return
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state = 'normal'
                self.finish_override(world, tgt)
            return

        # normal state: consume intents
        if it['dash'] is not None and self.dash_cd <= 0 and not self.vehicle:
            self.start_dash(world, it['dash'])
            return
        if it['skill'] is not None and self.skill_cd <= 0:
            if self.vehicle:
                if self.sub_cd <= 0:
                    self.fire_sub(world, it['skill'])
            elif self.charges > 0:
                self.state = 'cast'
                self.state_timer = self.c['skill']['cast']
                self.skill_target = it['skill']
                return
        if it['override'] is not None and not self.vehicle and self.c['override']['kind'] == 'hold':
            tgt = it['override']
            if tgt.alive and dist(tgt.pos, self.pos) <= tgt.radius + self.radius + 0.7:
                self.state = 'override'
                self.state_timer = self.c['override']['time'] if tgt.behavior == 'vehicle' else self.c['override'].get('carry_time', 1.0)
                self.override_target = tgt
                return
        if it['hold'] and self.hold_cd <= 0 and not self.vehicle and self.is_melee():
            if self.try_hold(world, it['hold_dir'] or self.facing):
                return
        if it['attack']:
            self.do_attack(world, dt)

        mv = it['move']
        if mv != (0.0, 0.0):
            if self.vehicle:
                spd = self.vehicle['speed']
            else:
                spd = self.speed
                if self.is_melee() and self.attack_timer > 0 and self.intent['attack']:
                    spd *= self.c['attack_move_mult']
                if self.carried:
                    spd *= self.c['override'].get('carry_speed_mult', 1.0)
            self.pos[0] += mv[0] * spd * dt
            self.pos[1] += mv[1] * spd * dt
            world.clamp(self.pos, self.hit_radius())

        if self.chip and 'orbitals' in self.chip and self.orbital_timer <= 0:
            orb = self.chip['orbitals']
            self.orbital_timer = orb['interval']
            cands = [e for e in world.enemies if e.targetable() and dist(e.pos, self.pos) <= orb['range']]
            cands.sort(key=lambda e: dist(e.pos, self.pos))
            for e in cands[:orb['count']]:
                e.take_damage(world, orb['damage'], melee=False, from_pos=None)
            if world.boss and world.boss.alive and dist(world.boss.pos, self.pos) <= orb['range'] + world.boss.radius:
                world.boss.take_damage(world, orb['damage'] * orb['count'])
            self.consume_chip(0.5)

    # -- attacks ------------------------------------------------------------
    def aim_dir(self, world, aim, err_deg):
        d = unit(aim[0] - self.pos[0], aim[1] - self.pos[1])
        if d == (0.0, 0.0):
            d = self.facing
        if err_deg > 0:
            d = rotate(d, world.rng.gauss(0.0, err_deg))
        return d

    def do_attack(self, world, dt):
        it = self.intent
        aim = it['aim'] or (self.pos[0] + self.facing[0] * 5, self.pos[1] + self.facing[1] * 5)
        err = world.bot.sk['aim_error_deg']
        if self.vehicle:
            g = self.vehicle['gun']
            if self.attack_timer <= 0:
                d = self.aim_dir(world, aim, err)
                d = rotate(d, world.rng.uniform(-g['spread_deg'] / 2, g['spread_deg'] / 2))
                world.spawn_proj(self.pos, d, g['proj_speed'], g['damage'], 'player', range=g['range'], start_offset=self.vehicle['radius'] + 0.2)
                self.attack_timer = g['interval']
                self.stats['shots'] += 1
            return
        if self.carried:
            w = self.carried
            if self.attack_timer <= 0:
                d = self.aim_dir(world, aim, err)
                d = rotate(d, world.rng.uniform(-w['spread_deg'] / 2, w['spread_deg'] / 2))
                world.spawn_proj(self.pos, d, w['proj_speed'], w['damage'], 'player', range=w['range'])
                self.attack_timer = w['interval']
                w['shots'] -= 1
                if w['shots'] <= 0:
                    self.carried = None
            return
        if self.id == 'trigger':
            ma = self.c['melee_auto']
            near = None
            nd = 99.0
            for e in world.enemies:
                if e.targetable():
                    d0 = dist(e.pos, self.pos) - e.radius
                    if d0 < nd:
                        nd = d0
                        near = e
            if near is not None and nd <= ma['range'] and not near.flying:
                if self.melee_auto_timer <= 0:
                    near.take_damage(world, ma['damage'], melee=True, from_pos=self.pos)
                    self.melee_auto_timer = ma['interval']
                return
            w = self.chip if self.chip else self.c['basic']
            if self.attack_timer <= 0:
                dmg = w['damage'] * self.mods['dmg_mult']
                if self.chip and self.chip_left <= self.chip_total * self.c['passive']['last_mag_frac']:
                    dmg *= self.c['passive']['last_mag_dmg_mult']
                base = self.aim_dir(world, aim, err)
                target = None
                if w.get('homing'):
                    tl = [e for e in world.enemies if e.targetable()]
                    if tl:
                        target = min(tl, key=lambda e: dist(e.pos, self.pos))
                    elif world.boss and world.boss.alive:
                        target = world.boss
                burn = (w['burn_dps'], w['burn_time']) if 'burn_dps' in w else None
                for _ in range(w.get('pellets', 1)):
                    d = rotate(base, world.rng.uniform(-w.get('spread_deg', 0.0) / 2, w.get('spread_deg', 0.0) / 2))
                    world.spawn_proj(self.pos, d, w['proj_speed'], dmg, 'player', range=w['range'], pierce=w.get('pierce', False),
                                     homing=target, aoe=w.get('aoe_radius', 0.0), knockback=w.get('knockback', 0.0), burn=burn)
                self.attack_timer = w['interval']
                self.stats['shots'] += 1
                if self.chip:
                    self.consume_chip(1.0)
            return
        if self.attack_timer <= 0:
            self.melee_hit(world)

    def melee_hit(self, world):
        b = self.c['basic']
        chip = self.chip or {}
        idx = self.combo_idx
        dmg = b['damages'][idx] * self.mods['dmg_mult']
        rng_ = b['range'] * chip.get('range_mult', 1.0)
        arc = chip.get('arc_deg', b['arc_deg'])
        pierce_line = chip.get('pierce', False) and self.id == 'edge'
        kb = b.get('knockback_last', 0.0) if idx == len(b['damages']) - 1 else 0.0
        hit_any = False
        nearest_d = 99.0
        for e in world.enemies:
            if not e.targetable():
                continue
            d = dist(e.pos, self.pos)
            if d - e.radius < nearest_d:
                nearest_d = d - e.radius
            if d > rng_ + e.radius:
                continue
            if arc < 360 and ang_deg(self.facing, (e.pos[0] - self.pos[0], e.pos[1] - self.pos[1])) > arc / 2:
                continue
            ok = e.take_damage(world, dmg, melee=True, from_pos=self.pos, knockback=kb)
            hit_any = hit_any or ok
            if ok and 'ground_fire' in chip:
                gf = chip['ground_fire']
                e.burn = (gf['dps'], gf['duration'])
            if ok and 'fire_trail' in chip:
                ft = chip['fire_trail']
                e.burn = (ft['dps'], ft['duration'])
        B = world.boss
        if B and B.alive:
            d = dist(B.pos, self.pos)
            if d <= rng_ + B.radius and (arc >= 360 or ang_deg(self.facing, (B.pos[0] - self.pos[0], B.pos[1] - self.pos[1])) <= arc / 2):
                hit_any = B.take_damage(world, dmg, melee=True) or hit_any
        if 'hit_aoe' in chip:
            ha = chip['hit_aoe']
            for e in world.enemies:
                if e.targetable() and dist(e.pos, self.pos) <= ha['radius'] + e.radius and \
                        ang_deg(self.facing, (e.pos[0] - self.pos[0], e.pos[1] - self.pos[1])) <= ha['arc_deg'] / 2:
                    e.take_damage(world, ha['damage'], melee=True, from_pos=self.pos, knockback=ha['knockback'])
        if 'extra_ranged' in chip:
            er = chip['extra_ranged']
            world.spawn_proj(self.pos, self.facing, er['proj_speed'], er['damage'], 'player', range=er['range'], pierce=er.get('pierce', False))
        if 'per_hit_wave' in chip:
            pw = chip['per_hit_wave']
            world.spawn_proj(self.pos, self.facing, pw['speed'], pw['damage'], 'player', range=pw['range'], radius=0.4, pierce=True)
        if self.id == 'edge':
            if B and B.alive and dist(B.pos, self.pos) - B.radius < nearest_d:
                nearest_d = dist(B.pos, self.pos) - B.radius
            if nearest_d > rng_ * b.get('lunge_if_farther_than', 0.75):
                self.pos[0] += self.facing[0] * b['step']
                self.pos[1] += self.facing[1] * b['step']
                world.clamp(self.pos, self.radius)
            self.reflect_scan(world, rng_, arc)
        self.combo_idx = (idx + 1) % len(b['damages'])
        self.combo_reset = b['combo_reset']
        self.attack_timer = b['interval'] / chip.get('attack_speed_mult', 1.0)
        self.active_frames = b.get('active_frames', 0.12)
        if self.chip:
            self.consume_chip(1.0)

    def reflect_scan(self, world, rng_, arc):
        b = self.c['basic']
        mult = b.get('reflect_dmg_mult', 2.0)
        for pr in world.projectiles:
            if not pr.alive or pr.owner != 'enemy' or not pr.reflectable:
                continue
            if dist(pr.pos, self.pos) > rng_ + 0.3:
                continue
            if arc < 360 and ang_deg(self.facing, (pr.pos[0] - self.pos[0], pr.pos[1] - self.pos[1])) > arc / 2 + 10:
                continue
            spd = math.hypot(pr.vel[0], pr.vel[1])
            src = pr.src
            if src is not None and getattr(src, 'alive', False):
                d = unit(src.pos[0] - pr.pos[0], src.pos[1] - pr.pos[1])
            else:
                d = unit(-pr.vel[0], -pr.vel[1])
            pr.vel = [d[0] * spd, d[1] * spd]
            pr.owner = 'player'
            pr.damage *= mult
            pr.reflectable = False
            pr.homing = src if (src is not None and getattr(src, 'alive', False)) else None
            pr.range_left = 30.0
            self.stats['reflects'] += 1

    def tick_active_reflect(self, world):
        if self.id == 'edge' and self.active_frames > 0 and self.state == 'normal':
            b = self.c['basic']
            chip = self.chip or {}
            self.reflect_scan(world, b['range'] * chip.get('range_mult', 1.0), chip.get('arc_deg', b['arc_deg']))

    # -- dash -----------------------------------------------------------------
    def start_dash(self, world, d):
        ds = self.c['dash']
        d = unit(*d)
        if d == (0.0, 0.0):
            d = self.facing
        self.state = 'dash'
        self.dash_dir = d
        self.dash_left = ds['distance']
        self.dash_speed = ds['distance'] / ds['duration']
        self.iframes = max(self.iframes, ds['iframes'])
        cd = ds['cooldown'] * self.mods['dash_cd_mult']
        if self.chip and 'dash_cooldown_mult' in self.chip:
            cd *= self.chip['dash_cooldown_mult']
        self.dash_cd = cd
        self.last_dash_t = world.t
        self.dash_hit = set()
        self.stats['dash_uses'] += 1
        self.facing = d

    def step_dash(self, world, dt):
        ds = self.c['dash']
        step = min(self.dash_left, self.dash_speed * dt)
        self.pos[0] += self.dash_dir[0] * step
        self.pos[1] += self.dash_dir[1] * step
        self.dash_left -= step
        hit_wall = world.clamp(self.pos, self.radius)
        if ds.get('damage', 0) > 0:
            for e in world.enemies:
                if not e.targetable() or id(e) in self.dash_hit:
                    continue
                if dist(e.pos, self.pos) <= e.radius + 0.9:
                    self.dash_hit.add(id(e))
                    dmg = ds['damage']
                    if self.id == 'knuckle' and world.near_wall(e.pos, ds.get('wall_slam_range', 1.2) + e.radius):
                        dmg += ds.get('wall_slam_bonus', 0)
                    e.take_damage(world, dmg, melee=True, from_pos=self.pos, knockdown=ds.get('knockdown', 0.0))
            B = world.boss
            if B and B.alive and id(B) not in self.dash_hit and dist(B.pos, self.pos) <= B.radius + 0.9:
                self.dash_hit.add(id(B))
                B.take_damage(world, ds['damage'], melee=True)
        if self.id == 'edge' and self.c['override']['kind'] == 'dash_assassinate':
            for e in world.enemies:
                if e.alive and e.overridable and e.behavior == 'vehicle' and e.state == 'stunned' and dist(e.pos, self.pos) <= e.radius + 0.9:
                    self.finish_override(world, e)
                    break
        if self.dash_left <= 0 or hit_wall:
            self.state = 'normal'
            if self.chip and 'dash_explosion' in self.chip:
                ex = self.chip['dash_explosion']
                for e in world.enemies:
                    if e.targetable() and dist(e.pos, self.pos) <= ex['radius'] + e.radius:
                        e.take_damage(world, ex['damage'], melee=False, from_pos=None)
                if world.boss and world.boss.alive and dist(world.boss.pos, self.pos) <= ex['radius'] + world.boss.radius:
                    world.boss.take_damage(world, ex['damage'])
                self.consume_chip(1.0)

    # -- skill ----------------------------------------------------------------
    def execute_skill(self, world):
        from .engine import AoE
        sk = self.c['skill']
        tgt = self.skill_target or (self.pos[0] + self.facing[0] * 5, self.pos[1] + self.facing[1] * 5)
        self.charges -= 1
        self.skill_cd = sk['cooldown']
        self.stats['skill_uses'] += 1
        kind = sk['kind']
        if kind == 'grenade':
            d = dist(tgt, self.pos)
            if d > sk['range']:
                u = unit(tgt[0] - self.pos[0], tgt[1] - self.pos[1])
                tgt = (self.pos[0] + u[0] * sk['range'], self.pos[1] + u[1] * sk['range'])
            world.aoes.append(AoE(tgt, sk['radius'], sk['flight'], sk['damage'], 'player'))
        elif kind == 'slam':
            for e in world.enemies:
                if e.targetable() and dist(e.pos, self.pos) <= sk['radius'] + e.radius:
                    e.take_damage(world, sk['damage'], melee=True, from_pos=self.pos, knockdown=sk['knockdown'])
            if world.boss and world.boss.alive and dist(world.boss.pos, self.pos) <= sk['radius'] + world.boss.radius:
                world.boss.take_damage(world, sk['damage'], melee=True)
            if sk.get('clears_projectiles'):
                for pr in world.projectiles:
                    if pr.alive and pr.owner == 'enemy' and dist(pr.pos, self.pos) <= sk['radius']:
                        pr.alive = False
        elif kind == 'wave':
            d = unit(tgt[0] - self.pos[0], tgt[1] - self.pos[1])
            if d == (0.0, 0.0):
                d = self.facing
            world.spawn_proj(self.pos, d, sk['speed'], sk['damage'], 'player', range=sk['range'], radius=sk['width'] / 2,
                             pierce=True, clears=sk.get('clears_projectiles', False), reflectable=False)

    def fire_sub(self, world, tgt):
        from .engine import AoE
        sub = self.vehicle['sub']
        d = dist(tgt, self.pos)
        if d > sub['range']:
            u = unit(tgt[0] - self.pos[0], tgt[1] - self.pos[1])
            tgt = (self.pos[0] + u[0] * sub['range'], self.pos[1] + u[1] * sub['range'])
        world.aoes.append(AoE(tgt, sub['aoe_radius'], sub['flight'], sub['damage'], 'player'))
        self.sub_cd = sub['cooldown']
        self.stats['skill_uses'] += 1

    # -- hold attacks ---------------------------------------------------------
    def try_hold(self, world, d):
        h = self.c['hold']
        d = unit(*d)
        if d == (0.0, 0.0):
            d = self.facing
        self.hold_dir = d
        if self.id == 'knuckle':
            if self.chip and 'hold_replace' in self.chip:
                rp = self.chip['hold_replace']
                world.spawn_proj(self.pos, d, rp['proj_speed'], rp['damage'], 'player', range=rp['range'], aoe=rp['aoe_radius'])
                self.consume_chip(1.0)
                self.hold_cd = 1.0
                return True
            best = None
            bd = 99.0
            for e in world.enemies:
                if not e.targetable() or not e.throwable or e.dormant:
                    continue
                dd = dist(e.pos, self.pos) - e.radius
                if dd <= h['range'] and dd < bd:
                    bd = dd
                    best = e
            if best is None:
                return False
            self.state = 'grab'
            self.state_timer = h['grab_time']
            self.grab_target = best
            best.knockdown = max(best.knockdown, h['grab_time'] + 0.2)
            best.atk = None
            self.facing = d
            return True
        if self.id == 'edge':
            self.state = 'charge'
            self.state_timer = h['charge']
            self.facing = d
            return True
        return False

    def throw(self, world):
        from .engine import Projectile
        h = self.c['hold']
        e = self.grab_target
        self.grab_target = None
        self.hold_cd = 1.5
        if e is None or not e.alive:
            return
        e.state = 'thrown'
        e.knockdown = 0.0
        d = self.hold_dir
        pr = Projectile((self.pos[0] + d[0] * 0.8, self.pos[1] + d[1] * 0.8), (d[0] * h['throw_speed'], d[1] * h['throw_speed']),
                        h['throw_damage'], 'player', radius=0.5, range=h['throw_range'], pierce=True, kind='body', body=e,
                        knockdown=h.get('land_knockdown', 1.0), reflectable=False)
        world.projectiles.append(pr)
        self.stats['throws'] += 1

    def line_hit(self, world):
        h = self.c['hold']
        self.hold_cd = 2.0
        a = (self.pos[0], self.pos[1])
        b = (self.pos[0] + self.hold_dir[0] * h['length'], self.pos[1] + self.hold_dir[1] * h['length'])
        for e in world.enemies:
            if e.targetable() and seg_dist(a, b, e.pos) <= h['width'] / 2 + e.radius:
                e.take_damage(world, h['damage'], melee=True, from_pos=self.pos)
        B = world.boss
        if B and B.alive and seg_dist(a, b, B.pos) <= h['width'] / 2 + B.radius:
            B.take_damage(world, h['damage'], melee=True)
        if self.chip:
            self.consume_chip(1.0)

    # -- override -------------------------------------------------------------
    def finish_override(self, world, tgt):
        self.stats['overrides'] += 1
        self.override_target = None
        if tgt.behavior == 'vehicle':
            pilot = tgt.spec['pilot']
            self.vehicle = {'hp': float(pilot['hp']), 'speed': pilot['speed'], 'radius': pilot['radius'],
                            'gun': pilot['gun'], 'sub': pilot['sub'], 'name': tgt.id}
            tgt.alive = False
        else:
            a = tgt.spec['attack']
            ov = self.c['override']
            self.carried = {'shots': ov.get('carry_shots', 40), 'damage': a.get('damage', 6) * ov.get('carry_dmg_mult', 2.5),
                            'interval': ov.get('carry_interval', 0.2), 'proj_speed': a.get('proj_speed', 14.0),
                            'range': tgt.spec.get('fire_range', 10.0), 'spread_deg': a.get('spread_deg', 4.0)}
            tgt.alive = False
