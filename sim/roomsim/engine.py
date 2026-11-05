"""World, entities, enemy AI and boss AI for the ROOM ZERO room simulator."""
import math
import random

from .geom import unit, dist, ang_deg, rotate, perp, seg_dist
from .player import Player
from .bots import Bot

CHIP_POOL_BY_CHAPTER = {1: ['H', 'S', 'R'], 2: ['H', 'S', 'R'], 3: ['H', 'S', 'R', 'F', 'L'],
                        4: ['H', 'S', 'R', 'F', 'L'], 5: ['H', 'S', 'R', 'F', 'L', 'C'], 6: ['H', 'S', 'R', 'F', 'L', 'C']}


class Projectile:
    __slots__ = ('pos', 'vel', 'damage', 'owner', 'radius', 'range_left', 'pierce', 'homing', 'aoe',
                 'reflectable', 'knockback', 'kind', 'src', 'clears', 'burn', 'alive', 'hit_set', 'knockdown', 'body', 'arm', 'label')

    def __init__(self, pos, vel, damage, owner, radius=0.15, range=20.0, pierce=False, homing=None, aoe=0.0,
                 reflectable=True, knockback=0.0, kind='bullet', src=None, clears=False, burn=None, knockdown=0.0, body=None, arm=0.0, label=None):
        self.arm = arm
        self.label = label
        self.pos = [pos[0], pos[1]]
        self.vel = [vel[0], vel[1]]
        self.damage = damage
        self.owner = owner
        self.radius = radius
        self.range_left = range
        self.pierce = pierce
        self.homing = homing
        self.aoe = aoe
        self.reflectable = reflectable
        self.knockback = knockback
        self.kind = kind
        self.src = src
        self.clears = clears
        self.burn = burn
        self.alive = True
        self.hit_set = set()
        self.knockdown = knockdown
        self.body = body


class AoE:
    __slots__ = ('pos', 'radius', 'delay', 'damage', 'owner', 'src', 'knockdown', 'alive', 'label')

    def __init__(self, pos, radius, delay, damage, owner, src=None, knockdown=0.0, label=None):
        self.label = label
        self.pos = (pos[0], pos[1])
        self.radius = radius
        self.delay = delay
        self.damage = damage
        self.owner = owner
        self.src = src
        self.knockdown = knockdown
        self.alive = True


class Beam:
    """Telegraphed line attack. Direction tracks the player until lock_at, fires at telegraph end."""
    __slots__ = ('origin', 'dir', 'telegraph', 'lock_at', 'length', 'width', 'damage', 'src', 'alive', 'locked', 'elapsed', 'label')

    def __init__(self, origin, direction, telegraph, lock_at, length, width, damage, src, label=None):
        self.label = label
        self.origin = (origin[0], origin[1])
        self.dir = direction
        self.telegraph = telegraph
        self.lock_at = lock_at
        self.length = length
        self.width = width
        self.damage = damage
        self.src = src
        self.alive = True
        self.locked = False
        self.elapsed = 0.0

    def end(self):
        return (self.origin[0] + self.dir[0] * self.length, self.origin[1] + self.dir[1] * self.length)


class Pickup:
    __slots__ = ('pos', 'kind', 'chip', 'alive')

    def __init__(self, pos, kind, chip=None):
        self.pos = (pos[0], pos[1])
        self.kind = kind
        self.chip = chip
        self.alive = True


class Enemy:
    def __init__(self, world, spec, pos):
        g = world.P['global']
        self.spec = spec
        self.id = spec['id']
        self.tier = spec.get('tier', 'grunt')
        self.pos = [pos[0], pos[1]]
        self.radius = spec.get('radius', 0.4)
        sc = world.scaling
        self.max_hp = spec['hp'] * sc['hp']
        self.hp = self.max_hp
        self.speed = spec.get('speed', 0.0) * sc['speed']
        self.dmg_mult = sc['dmg']
        self.behavior = spec.get('behavior', 'melee')
        self.state = 'spawning'
        self.timer = g['spawn']['telegraph_time']
        self.cooldown = world.rng.uniform(0.4, 1.5)
        self.cannon_cd = world.rng.uniform(1.5, 3.0)
        self.facing = (-1.0, 0.0)
        self.knockdown = 0.0
        self.kb_vel = [0.0, 0.0]
        self.alive = True
        self.dormant = False
        self.atk = None
        self.burn = None
        self.burst_left = 0
        self.burst_timer = 0.0
        self.stream_left = 0.0
        self.stream_timer = 0.0
        self.repo_left = 0.0
        self.repo_dir = (0.0, 0.0)
        self.teleport_timer = spec.get('teleport_every', 0.0) * world.rng.uniform(0.3, 1.0)
        self.overridable = spec.get('overridable', False)
        self.throwable = spec.get('throwable', False)
        self.shield_arc = spec.get('shield_arc_deg', 0.0)
        self.shield_hp = spec.get('shield_hp', 0.0) * sc['hp']
        self.shield_max = self.shield_hp
        self.shield_down = 0.0
        self.flying = spec.get('flying', False)
        self.stunned_used = False

    # -- queries ---------------------------------------------------------
    def targetable(self):
        return self.alive and self.state not in ('spawning', 'thrown')

    def active(self):
        return self.targetable() and not self.dormant and self.state != 'stunned' and self.knockdown <= 0

    # -- damage ----------------------------------------------------------
    def wake(self, world, chain=False):
        if not self.dormant:
            return
        self.dormant = False
        if chain:
            r = world.rules['tpose_chain_range']
            for e in world.enemies:
                if e is not self and e.alive and e.dormant and dist(e.pos, self.pos) <= r:
                    e.dormant = False

    def take_damage(self, world, amount, melee=False, from_pos=None, knockback=0.0, knockdown=0.0):
        if not self.targetable():
            return False
        if self.shield_arc and self.shield_down <= 0 and not melee and from_pos is not None and self.state != 'stunned' and self.knockdown <= 0 and not self.dormant:
            to_src = (from_pos[0] - self.pos[0], from_pos[1] - self.pos[1])
            if ang_deg(self.facing, to_src) <= self.shield_arc / 2:
                world.m['blocked'] += 1
                if self.shield_max > 0:
                    self.shield_hp -= amount
                    if self.shield_hp <= 0:
                        self.shield_down = self.spec.get('shield_down_time', 3.0)
                        self.shield_hp = self.shield_max
                return False
        if self.dormant:
            self.wake(world, chain=True)
        self.hp -= amount
        world.m['dmg_dealt'] += amount
        resist = self.spec.get('knockback_resist', False)
        if knockback and not resist:
            d = unit(self.pos[0] - from_pos[0], self.pos[1] - from_pos[1]) if from_pos else self.facing
            self.kb_vel[0] += d[0] * knockback * 5.0
            self.kb_vel[1] += d[1] * knockback * 5.0
        if knockdown and not resist:
            self.knockdown = max(self.knockdown, knockdown)
            self.atk = None
            self.burst_left = 0
            self.stream_left = 0.0
        if self.hp <= 0:
            self.die(world, melee)
        return True

    def die(self, world, melee=False):
        if not self.alive:
            return
        self.alive = False
        world.on_enemy_killed(self, melee)

    # -- helpers ---------------------------------------------------------
    def move_dir(self, world, d, dt, mult=1.0):
        if self.speed <= 0:
            return
        self.pos[0] += d[0] * self.speed * mult * dt
        self.pos[1] += d[1] * self.speed * mult * dt
        world.clamp(self.pos, self.radius)

    def pick_target(self, world):
        p = world.player
        node = world.node
        if node is not None and node['hp'] > 0 and self.behavior == 'melee':
            dn = dist(self.pos, node['pos'])
            dp = dist(self.pos, p.pos)
            if dn < dp:
                return node['pos'], 'node'
        return p.pos, 'player'

    def fire_bullet(self, world, aim, a):
        d = unit(aim[0] - self.pos[0], aim[1] - self.pos[1])
        if d == (0.0, 0.0):
            d = self.facing
        d = rotate(d, world.rng.uniform(-a['spread_deg'] / 2, a['spread_deg'] / 2))
        world.spawn_proj(self.pos, d, a['proj_speed'], a['damage'] * self.dmg_mult, 'enemy', src=self,
                         range=24.0, reflectable=self.spec.get('reflectable', True), start_offset=self.radius + 0.2)

    def rotate_toward(self, to_t, dt):
        rate = self.spec.get('turn_rate_deg', 90.0) * dt
        ang = ang_deg(self.facing, to_t)
        if ang <= rate:
            self.facing = to_t
        else:
            cross = self.facing[0] * to_t[1] - self.facing[1] * to_t[0]
            self.facing = rotate(self.facing, rate if cross > 0 else -rate)

    # -- update ----------------------------------------------------------
    def update(self, world, dt):
        if not self.alive:
            return
        if self.state == 'spawning':
            self.timer -= dt
            if self.timer <= 0:
                self.state = 'idle'
                if world.modifier == 'tpose':
                    self.dormant = True
            return
        if self.state == 'thrown':
            return
        p = world.player
        if self.dormant:
            if dist(self.pos, p.pos) <= world.rules['tpose_wake_range']:
                self.wake(world, chain=True)
            return
        if self.burn:
            dps, tleft = self.burn
            self.hp -= dps * dt
            world.m['dmg_dealt'] += dps * dt
            self.burn = (dps, tleft - dt) if tleft > dt else None
            if self.hp <= 0:
                self.die(world, False)
                return
        if self.kb_vel[0] or self.kb_vel[1]:
            self.pos[0] += self.kb_vel[0] * dt
            self.pos[1] += self.kb_vel[1] * dt
            self.kb_vel[0] *= 0.82
            self.kb_vel[1] *= 0.82
            if abs(self.kb_vel[0]) + abs(self.kb_vel[1]) < 0.1:
                self.kb_vel = [0.0, 0.0]
            world.clamp(self.pos, self.radius)
        if self.shield_down > 0:
            self.shield_down -= dt
        if self.knockdown > 0:
            self.knockdown -= dt
            return
        if self.state == 'stunned':
            self.timer -= dt
            if self.timer <= 0:
                self.state = 'idle'
            return
        frac = self.spec.get('stun_hp_frac')
        if frac and not self.stunned_used and self.hp <= frac * self.max_hp:
            self.stunned_used = True
            self.state = 'stunned'
            self.timer = self.spec['stun_time']
            self.atk = None
            self.burst_left = 0
            return
        self.cooldown -= dt
        self.cannon_cd -= dt
        tpos, tkind = self.pick_target(world)
        d = dist(self.pos, tpos)
        to_t = unit(tpos[0] - self.pos[0], tpos[1] - self.pos[1])
        if to_t == (0.0, 0.0):
            to_t = self.facing
        beh = self.behavior
        a = self.spec.get('attack', {})
        rng = world.rng

        if beh == 'melee':
            if self.shield_arc:
                self.rotate_toward(to_t, dt)
            else:
                self.facing = to_t
            if self.atk:
                self.atk['t'] -= dt
                if self.atk['t'] <= 0:
                    reach = a['hit_range'] + (0.0 if tkind == 'node' else p.hit_radius())
                    if dist(self.pos, tpos) <= reach:
                        world.hit_target(tkind, a['damage'] * self.dmg_mult, self)
                    self.atk = None
                    self.cooldown = a['cooldown']
                return
            if d > a['range'] + (0.0 if tkind == 'node' else p.hit_radius() - 0.4):
                self.move_dir(world, to_t, dt)
            elif self.cooldown <= 0:
                self.atk = {'kind': 'melee', 't': a['windup']}

        elif beh == 'ranged':
            self.facing = to_t
            if self.burst_left > 0:
                self.burst_timer -= dt
                if self.burst_timer <= 0:
                    self.fire_bullet(world, p.pos, a)
                    self.burst_left -= 1
                    self.burst_timer = a['burst_gap']
                    if self.burst_left == 0:
                        self.cooldown = a['cooldown']
                return
            if self.atk:
                self.atk['t'] -= dt
                if self.atk['t'] <= 0:
                    self.atk = None
                    self.burst_left = a['burst']
                    self.burst_timer = 0.0
                return
            if d > self.spec['stop_range']:
                self.move_dir(world, to_t, dt)
            elif d < self.spec.get('retreat_range', 0.0):
                self.move_dir(world, (-to_t[0], -to_t[1]), dt, 0.6)
            if self.cooldown <= 0 and d <= self.spec['fire_range']:
                self.atk = {'kind': 'telegraph', 't': a['telegraph']}

        elif beh == 'sniper':
            self.facing = to_t
            if self.atk:
                self.atk['t'] -= dt
                if not self.atk['locked'] and self.atk['t'] <= a['telegraph'] - a['lock_at']:
                    self.atk['locked'] = True
                    self.atk['aim'] = (p.pos[0], p.pos[1])
                if self.atk['t'] <= 0:
                    aim = self.atk.get('aim') or (p.pos[0], p.pos[1])
                    dv = unit(aim[0] - self.pos[0], aim[1] - self.pos[1])
                    world.spawn_proj(self.pos, dv, a['proj_speed'], a['damage'] * self.dmg_mult, 'enemy', src=self,
                                     range=30.0, start_offset=self.radius + 0.2)
                    self.atk = None
                    self.cooldown = a['cooldown']
                    self.repo_left = a['reposition']
                    pv = perp(to_t)
                    self.repo_dir = pv if rng.random() < 0.5 else (-pv[0], -pv[1])
                return
            if self.repo_left > 0:
                step = self.speed * dt
                self.repo_left -= step
                self.move_dir(world, self.repo_dir, dt)
                return
            if d < self.spec['min_range']:
                self.move_dir(world, (-to_t[0], -to_t[1]), dt)
            elif d > self.spec['max_range']:
                self.move_dir(world, to_t, dt)
            elif self.cooldown <= 0:
                self.atk = {'kind': 'telegraph', 't': a['telegraph'], 'locked': False, 'aim': None}

        elif beh == 'lobber':
            self.facing = to_t
            if self.atk:
                self.atk['t'] -= dt
                if self.atk['t'] <= 0:
                    world.aoes.append(AoE((p.pos[0], p.pos[1]), a['aoe_radius'], a['flight'], a['damage'] * self.dmg_mult, 'enemy', src=self))
                    self.atk = None
                    self.cooldown = a['cooldown']
                return
            if d < self.spec['min_range']:
                self.move_dir(world, (-to_t[0], -to_t[1]), dt)
            elif d > self.spec['max_range']:
                self.move_dir(world, to_t, dt)
            if self.cooldown <= 0 and d <= self.spec['max_range'] + 1.0:
                self.atk = {'kind': 'telegraph', 't': a['telegraph']}

        elif beh == 'turret':
            self.rotate_toward(to_t, dt)
            if self.stream_left > 0:
                self.stream_left -= dt
                self.stream_timer -= dt
                if self.stream_timer <= 0:
                    dv = rotate(self.facing, rng.uniform(-a['spread_deg'] / 2, a['spread_deg'] / 2))
                    world.spawn_proj(self.pos, dv, a['proj_speed'], a['damage'] * self.dmg_mult, 'enemy', src=self,
                                     range=24.0, start_offset=self.radius + 0.2)
                    self.stream_timer = a['shot_gap']
                if self.stream_left <= 0:
                    self.cooldown = a['cooldown']
                return
            if self.cooldown <= 0 and d <= self.spec['fire_range'] and ang_deg(self.facing, to_t) <= self.spec['aim_tolerance_deg']:
                self.stream_left = a['stream_time']
                self.stream_timer = 0.0

        elif beh == 'beam_turret':
            self.rotate_toward(to_t, dt)
            if self.atk:
                self.atk['t'] -= dt
                if self.atk['t'] <= 0:
                    self.atk = None
                return
            if self.cooldown <= 0 and d <= self.spec['fire_range'] and ang_deg(self.facing, to_t) <= self.spec['aim_tolerance_deg']:
                world.beams.append(Beam(self.pos, to_t, a['telegraph'], a['lock_at'], a['beam_length'], a['beam_width'],
                                        a['damage'] * self.dmg_mult, self))
                self.atk = {'kind': 'beam', 't': a['telegraph']}
                self.cooldown = a['cooldown'] + a['telegraph']

        elif beh == 'teleporter':
            self.facing = to_t
            self.teleport_timer -= dt
            if self.atk:
                self.atk['t'] -= dt
                if self.atk['t'] <= 0:
                    self.atk = None
                return
            if self.teleport_timer <= 0:
                lo, hi = self.spec['teleport_range']
                for _ in range(12):
                    ang = rng.uniform(0, 360)
                    r = rng.uniform(lo, hi)
                    dv = rotate((1.0, 0.0), ang)
                    cand = [p.pos[0] + dv[0] * r, p.pos[1] + dv[1] * r]
                    if world.inside(cand, self.radius):
                        self.pos = cand
                        break
                self.teleport_timer = self.spec['teleport_every']
                self.cooldown = self.spec.get('materialize', 0.6)
                return
            if self.cooldown <= 0:
                world.beams.append(Beam(self.pos, to_t, a['telegraph'], a['lock_at'], a['beam_length'], a['beam_width'],
                                        a['damage'] * self.dmg_mult, self))
                self.atk = {'kind': 'beam', 't': a['telegraph']}
                self.cooldown = a['cooldown']

        elif beh == 'vehicle':
            self.facing = to_t
            cannon = self.spec.get('cannon')
            if cannon and self.cannon_cd <= 0 and d <= 14.0:
                delay = cannon['telegraph'] + d / cannon['proj_speed']
                world.aoes.append(AoE((p.pos[0], p.pos[1]), cannon['aoe_radius'], delay, cannon['damage'] * self.dmg_mult, 'enemy', src=self))
                self.cannon_cd = cannon['cooldown']
            if self.burst_left > 0:
                self.burst_timer -= dt
                if self.burst_timer <= 0:
                    self.fire_bullet(world, p.pos, a)
                    self.burst_left -= 1
                    self.burst_timer = a['burst_gap']
                    if self.burst_left == 0:
                        self.cooldown = a['cooldown']
                return
            if self.atk:
                self.atk['t'] -= dt
                if self.atk['t'] <= 0:
                    self.atk = None
                    self.burst_left = a['burst']
                    self.burst_timer = 0.0
                return
            if d > self.spec['stop_range']:
                self.move_dir(world, to_t, dt)
            if self.cooldown <= 0 and d <= self.spec['fire_range']:
                self.atk = {'kind': 'telegraph', 't': a['telegraph']}


class Boss:
    def __init__(self, world, spec, pos):
        self.spec = spec
        self.display = spec['display']
        self.pos = [pos[0], pos[1]]
        self.radius = spec['radius']
        self.max_hp = spec['hp'] * world.boss_hp_mult
        self.hp = self.max_hp
        self.base_speed = spec.get('speed', 0.0)
        self.contact = spec.get('contact_damage', 0)
        self.phases = spec['phases']
        self.phase_idx = 0
        self.patterns = list(spec['patterns'])
        self.defs = spec['pattern_defs']
        self.state = 'rest'
        self.timer = 2.0
        self.cur = None
        self.cur_name = None
        self.queue = []
        self.flying = spec.get('flying', False)
        self.landed = False
        self.keep_range = spec.get('keep_range')
        self.charge_vel = (1.0, 0.0)
        self.charge_speed = 0.0
        self.charge_left = 0.0
        self.charge_hit = False
        self.lock = None
        self.alive = True
        self.contact_cd = 0.0
        self.telegraph_total = 0.0
        self.tele_id = 0
        self.summon_uses = {}
        self.moved = False
        self.id = 'boss:' + spec['display']
        self.throwable = False

    def phase(self):
        return self.phases[self.phase_idx]

    def smult(self):
        return self.phase().get('speed_mult', 1.0)

    def rest_time(self):
        return self.phase().get('rest', self.spec['rest'])

    def hittable_melee(self):
        return (not self.flying) or self.landed

    def targetable(self):
        return self.alive

    def take_damage(self, world, amount, melee=False, **kw):
        if not self.alive:
            return False
        if melee and not self.hittable_melee():
            return False
        self.hp -= amount
        world.m['dmg_dealt'] += amount
        if self.hp <= 0:
            self.alive = False
        return True

    def move(self, world, d, dt, sm):
        self.pos[0] += d[0] * self.base_speed * sm * dt
        self.pos[1] += d[1] * self.base_speed * sm * dt
        world.clamp(self.pos, self.radius)
        self.moved = True

    def next_pattern(self, rng):
        if not self.queue:
            self.queue = list(self.patterns)
            rng.shuffle(self.queue)
        return self.queue.pop()

    def contact_check(self, world):
        p = world.player
        if self.contact > 0 and self.contact_cd <= 0 and dist(self.pos, p.pos) <= self.radius + p.hit_radius():
            world.damage_player(self.contact * world.boss_dmg_mult, 'boss/contact', self.pos, self)
            self.contact_cd = 1.0

    def update(self, world, dt):
        if not self.alive:
            return
        p = world.player
        rng = world.rng
        frac = self.hp / self.max_hp
        while self.phase_idx + 1 < len(self.phases) and frac <= self.phases[self.phase_idx + 1]['hp_frac']:
            self.phase_idx += 1
            for name in self.phases[self.phase_idx].get('add_patterns', []):
                if name not in self.patterns:
                    self.patterns.append(name)
                    self.queue.append(name)
        sm = self.smult()
        self.contact_cd -= dt
        to_p = unit(p.pos[0] - self.pos[0], p.pos[1] - self.pos[1])
        if to_p == (0.0, 0.0):
            to_p = (1.0, 0.0)
        d = dist(self.pos, p.pos)
        dm = world.boss_dmg_mult

        if self.state == 'rest':
            self.timer -= dt
            self.moved = False
            if self.base_speed > 0:
                if self.keep_range is not None:
                    if d > self.keep_range + 1.0:
                        self.move(world, to_p, dt, sm)
                    elif d < self.keep_range - 1.0:
                        self.move(world, (-to_p[0], -to_p[1]), dt, sm)
                elif d > self.radius + p.hit_radius() + 0.5:
                    self.move(world, to_p, dt, sm)
            if self.moved:
                self.contact_check(world)
            if self.timer <= 0:
                name = self.next_pattern(rng)
                pdef = self.defs[name]
                self.cur = pdef
                self.cur_name = name
                self.state = 'telegraph'
                self.telegraph_total = pdef.get('telegraph', 0.5) / sm
                self.timer = self.telegraph_total
                self.lock = None
                self.tele_id += 1
                t = pdef['type']
                if t == 'aoe':
                    for i in range(pdef['count']):
                        if i == 0:
                            off = (0.0, 0.0)
                        else:
                            off = (rng.uniform(-pdef['scatter'], pdef['scatter']), rng.uniform(-pdef['scatter'], pdef['scatter']))
                        pos = (p.pos[0] + off[0], p.pos[1] + off[1])
                        world.aoes.append(AoE(pos, pdef['radius'], self.timer, pdef['damage'] * dm, 'enemy', src=self, label='boss/' + name))
                elif t == 'aoe_self':
                    world.aoes.append(AoE((self.pos[0], self.pos[1]), pdef['radius'] + self.radius, self.timer, pdef['damage'] * dm, 'enemy', src=self, label='boss/' + name))
                elif t == 'beam':
                    world.beams.append(Beam(self.pos, to_p, self.timer, pdef['lock_at'] / sm, pdef['length'], pdef['width'], pdef['damage'] * dm, self, label='boss/' + name))
        elif self.state == 'telegraph':
            self.timer -= dt
            pdef = self.cur
            t = pdef['type']
            if t == 'sweep' and self.lock is None and self.timer <= self.telegraph_total * 0.4:
                self.lock = p.pos[1]
            if t == 'charge' and self.lock is None and self.timer <= self.telegraph_total * pdef.get('lock_frac', 0.6):
                self.lock = to_p
            if self.timer <= 0:
                self.execute(world, pdef, to_p)
        elif self.state == 'charge':
            step = self.charge_speed * dt
            self.pos[0] += self.charge_vel[0] * step
            self.pos[1] += self.charge_vel[1] * step
            self.charge_left -= step
            hit_wall = world.clamp(self.pos, self.radius)
            if not self.charge_hit and dist(self.pos, p.pos) <= self.radius + p.hit_radius():
                world.damage_player(self.cur['damage'] * dm, 'boss/charge', self.pos, self)
                self.charge_hit = True
            if self.charge_left <= 0 or hit_wall:
                self.state = 'rest'
                self.timer = self.cur.get('post_rest', self.rest_time()) / sm
        elif self.state == 'land':
            self.timer -= dt
            if self.timer <= 0:
                self.landed = False
                self.state = 'rest'
                self.timer = self.rest_time() / sm

    def execute(self, world, pdef, to_p):
        t = pdef['type']
        sm = self.smult()
        dm = world.boss_dmg_mult
        p = world.player
        if t == 'fan':
            n = pdef['count']
            spread = pdef['spread_deg']
            for i in range(n):
                ang = (-spread / 2 + spread * i / (n - 1)) if n > 1 else 0.0
                world.spawn_proj(self.pos, rotate(to_p, ang), pdef['proj_speed'], pdef['damage'] * dm, 'enemy', src=self,
                                 range=34.0, reflectable=pdef.get('reflectable', True), start_offset=self.radius + 0.3, arm=pdef.get('arm', 1.5), label='boss/fan')
            self.state = 'rest'
            self.timer = self.rest_time() / sm
        elif t == 'ring':
            n = pdef['count']
            for i in range(n):
                world.spawn_proj(self.pos, rotate((1.0, 0.0), 360.0 * i / n), pdef['proj_speed'], pdef['damage'] * dm, 'enemy', src=self,
                                 range=34.0, reflectable=pdef.get('reflectable', True), start_offset=self.radius + 0.3, arm=pdef.get('arm', 1.5), label='boss/ring')
            self.state = 'rest'
            self.timer = self.rest_time() / sm
        elif t in ('aoe', 'aoe_self', 'beam'):
            self.state = 'rest'
            self.timer = self.rest_time() / sm
        elif t == 'charge':
            self.charge_vel = self.lock or to_p
            self.charge_speed = pdef['dash_speed'] * sm
            self.charge_left = pdef.get('max_distance', 12.0)
            self.charge_hit = False
            self.state = 'charge'
        elif t == 'sweep':
            y = self.lock if self.lock is not None else p.pos[1]
            if abs(p.pos[1] - y) <= pdef['half_width'] + p.hit_radius():
                world.damage_player(pdef['damage'] * dm, 'boss/sweep', self.pos, self)
            self.state = 'rest'
            self.timer = pdef.get('post_rest', self.rest_time()) / sm
        elif t == 'summon':
            uses = self.summon_uses.get(self.cur_name, 0)
            if uses < pdef.get('max_uses', 99):
                for name, cnt in pdef['enemies'].items():
                    for _ in range(cnt):
                        world.spawn_enemy(name, near=self.pos, near_radius=self.radius + 2.5)
                self.summon_uses[self.cur_name] = uses + 1
                if uses + 1 >= pdef.get('max_uses', 99) and self.cur_name in self.patterns:
                    self.patterns.remove(self.cur_name)
            self.state = 'rest'
            self.timer = self.rest_time() / sm
        elif t == 'land':
            self.landed = True
            self.state = 'land'
            self.timer = pdef['duration']


class World:
    def __init__(self, P, room, chapter, char_id, skill, seed, difficulty='normal'):
        self.P = P
        self.room = room
        self.chapter = chapter
        self.rng = random.Random(seed)
        g = P['global']
        self.g = g
        self.rules = g['room_rules']
        self.W, self.H = g['room_sizes'][room.get('size', 'standard')]
        self.dt = g['sim_dt']
        self.t = 0.0
        ci = chapter - 1
        sc = g['chapter_scaling']
        dif = g['difficulty'][difficulty]
        self.scaling = {'hp': sc['enemy_hp_mult'][ci] * dif['enemy_hp_mult'],
                        'dmg': sc['enemy_dmg_mult'][ci] * dif['enemy_dmg_mult'],
                        'speed': sc['enemy_speed_mult'][ci]}
        self.boss_hp_mult = dif['enemy_hp_mult']
        self.boss_dmg_mult = dif['enemy_dmg_mult']
        self.chip_pool = CHIP_POOL_BY_CHAPTER[chapter]
        prog = g.get('progression_assumption', {})
        lvl = prog.get('levels_by_chapter', [0] * 6)[ci] if not dif.get('modules_disabled') else 0
        self.player_mods = {'hp_bonus': lvl * prog.get('hp_per_level', 0), 'dmg_mult': 1.0 + lvl * prog.get('dmg_mult_per_level', 0.0),
                            'dash_cd_mult': 1.0 + lvl * prog.get('dash_cd_mult_per_level', 0.0), 'ammo_mult': 1.0 + lvl * prog.get('ammo_mult_per_level', 0.0),
                            'charges_bonus': int(lvl * prog.get('charges_per_level', 0.0))}
        skill_cfg = dict(g['bot_skill'][skill])
        growth = g.get('skill_growth_per_chapter', 0.0) * ci
        for key in ('dodge_prob', 'telegraph_dodge_prob'):
            if key in skill_cfg:
                skill_cfg[key] = min(0.95, skill_cfg[key] + growth)
        self.skill_cfg = skill_cfg
        self.enemies = []
        self.projectiles = []
        self.aoes = []
        self.beams = []
        self.pickups = []
        self.spawn_queue = []
        self.stagger_queue = []
        self.stagger_timer = 0.0
        self.boss = None
        self.node = None
        self.modifier = room.get('modifier')
        self.rtype = room['type']
        self.m = {'kills': 0, 'dmg_dealt': 0.0, 'blocked': 0, 'spawned': 0, 'node_dmg': 0.0, 'wall_dmg': 0.0}
        self.done = False
        self.success = False
        self.death = False
        self.fail_reason = None
        self.exit_pos = (self.W - 1.0, self.H / 2)
        self.player = Player(self, char_id, (2.0, self.H / 2))
        self.bot = Bot(self, self.player, self.skill_cfg)
        self.waves = [dict(w) for w in room.get('waves', [])]
        self.wave_idx = 0
        self.wave_timer = 0.0
        self.pending = False
        self.spawn_timer = 0.0
        self.spawn_ticks = 0
        self.late_count = 0
        self.deletion_x = None
        for i, chip in enumerate(room.get('crates', [])):
            y = self.H * 0.25 if i % 2 == 0 else self.H * 0.75
            self.pickups.append(Pickup((self.W * 0.35 + i * 2.5, y), 'chip', chip))
        for i in range(room.get('charges', 0)):
            self.pickups.append(Pickup((self.W * 0.5 + i * 1.5, self.H * 0.5 + (i % 2) * 2.0 - 1.0), 'charge'))
        if self.rtype == 'boss':
            self.boss = Boss(self, P['bosses'][room['boss']], (self.W * 0.7, self.H / 2))
            for name, cnt in room.get('adds', {}).items():
                for _ in range(cnt):
                    self.spawn_enemy(name)
        elif self.rtype == 'defend':
            self.node = {'pos': (self.W / 2, self.H / 2), 'hp': float(room['node_hp']), 'max_hp': float(room['node_hp']),
                         'radius': self.rules['defend_node_radius']}
            self.player.pos = [self.W / 2 - 2.0, self.H / 2]
        elif self.rtype == 'rush':
            if self.modifier == 'deletion_wall':
                self.deletion_x = -3.0
        else:
            if self.modifier == 'tpose':
                merged = {}
                for w in self.waves:
                    for k, v in w.items():
                        merged[k] = merged.get(k, 0) + v
                self.waves = [merged]
            if self.waves:
                self.spawn_wave(self.waves[0])
                self.wave_idx = 1

    # -- geometry helpers ---------------------------------------------------
    def clamp(self, pos, r):
        hit = False
        if pos[0] < r:
            pos[0] = r
            hit = True
        elif pos[0] > self.W - r:
            pos[0] = self.W - r
            hit = True
        if pos[1] < r:
            pos[1] = r
            hit = True
        elif pos[1] > self.H - r:
            pos[1] = self.H - r
            hit = True
        return hit

    def inside(self, pos, r):
        return r <= pos[0] <= self.W - r and r <= pos[1] <= self.H - r

    def near_wall(self, pos, r):
        return pos[0] < r or pos[0] > self.W - r or pos[1] < r or pos[1] > self.H - r

    # -- spawning -------------------------------------------------------------
    def spawn_point(self, near=None, near_radius=2.0, interior=False):
        p = self.player.pos
        mind = self.g['spawn']['min_distance_from_player']
        rng = self.rng
        for _ in range(20):
            if near is not None:
                ang = rng.uniform(0, 360)
                dv = rotate((1.0, 0.0), ang)
                r = rng.uniform(1.0, near_radius)
                cand = [near[0] + dv[0] * r, near[1] + dv[1] * r]
                self.clamp(cand, 0.6)
            elif interior:
                cand = [rng.uniform(1.0, self.W - 1.0), rng.uniform(1.0, self.H - 1.0)]
            elif self.rtype == 'rush':
                x = min(self.W - 0.8, max(0.8, p[0] + rng.uniform(6.0, 14.0)))
                cand = [x, 0.8 if rng.random() < 0.5 else self.H - 0.8]
            else:
                side = rng.random()
                if side < 0.35:
                    cand = [self.W - 0.8, rng.uniform(0.8, self.H - 0.8)]
                elif side < 0.5:
                    cand = [0.8, rng.uniform(0.8, self.H - 0.8)]
                elif side < 0.75:
                    cand = [rng.uniform(0.8, self.W - 0.8), 0.8]
                else:
                    cand = [rng.uniform(0.8, self.W - 0.8), self.H - 0.8]
            if dist(cand, p) >= (mind if near is None else 2.5):
                return cand
        return cand

    def spawn_enemy(self, name, near=None, near_radius=2.0):
        spec = self.P['enemies'][name]
        alive = sum(1 for e in self.enemies if e.alive)
        if alive >= self.g['spawn']['max_concurrent']:
            self.spawn_queue.append(name)
            return None
        interior = self.modifier == 'tpose'
        pos = self.spawn_point(near, near_radius, interior)
        e = Enemy(self, spec, pos)
        if spec.get('speed', 0.0) == 0.0 and near is None and not interior:
            # static turrets stand a little off the wall
            e.pos[0] = min(max(e.pos[0], 2.0), self.W - 2.0)
            e.pos[1] = min(max(e.pos[1], 2.0), self.H - 2.0)
        self.enemies.append(e)
        self.m['spawned'] += 1
        return e

    def spawn_wave(self, wave):
        names = []
        for name, cnt in wave.items():
            names += [name] * cnt
        self.rng.shuffle(names)
        if self.g['spawn'].get('stagger', 0.0) <= 0:
            for n in names:
                self.spawn_enemy(n)
            return
        # first enemy now, the rest trickle in
        if names:
            self.spawn_enemy(names.pop(0))
        self.stagger_queue.extend(names)

    # -- projectile / damage API --------------------------------------------
    def spawn_proj(self, pos, d, speed, damage, owner, src=None, range=20.0, start_offset=0.5, **kw):
        pr = Projectile((pos[0] + d[0] * start_offset, pos[1] + d[1] * start_offset), (d[0] * speed, d[1] * speed), damage, owner,
                        src=src, range=range, **kw)
        self.projectiles.append(pr)
        return pr

    def hit_target(self, kind, dmg, src):
        if kind == 'node':
            self.node['hp'] -= dmg
            self.m['node_dmg'] += dmg
        else:
            self.damage_player(dmg, src.id, src.pos, src)

    def damage_player(self, amount, src_id, from_pos, src_obj=None):
        self.player.take_damage(self, amount, src_id, from_pos, src_obj)

    def on_enemy_killed(self, e, melee):
        self.m['kills'] += 1
        p = self.player
        if melee and p.id == 'knuckle':
            p.heal(p.c['passive']['heal_on_melee_kill'])
        pk = self.g['pickups']
        tier = e.tier if e.tier in pk['chip_drop_chance'] else 'grunt'
        if self.rng.random() < pk['chip_drop_chance'][tier]:
            self.pickups.append(Pickup(e.pos, 'chip', self.rng.choice(self.chip_pool)))
        elif self.rng.random() < pk['charge_drop_chance'][tier]:
            self.pickups.append(Pickup(e.pos, 'charge'))

    # -- main loop -------------------------------------------------------------
    def step(self):
        dt = self.dt
        self.t += dt
        self.bot.tick(dt)
        self.player.update(self, dt)
        if self.done:
            return
        for e in self.enemies:
            e.update(self, dt)
        if self.boss:
            self.boss.update(self, dt)
        self.update_projectiles(dt)
        self.update_aoes(dt)
        self.update_beams(dt)
        self.update_pickups()
        self.update_spawning(dt)
        self.update_rules(dt)
        self.check_end()

    def update_projectiles(self, dt):
        p = self.player
        prad = p.hit_radius()
        alive_list = []
        for pr in self.projectiles:
            if not pr.alive:
                continue
            if pr.homing is not None:
                tgt = pr.homing
                if getattr(tgt, 'alive', False):
                    want = unit(tgt.pos[0] - pr.pos[0], tgt.pos[1] - pr.pos[1])
                    spd = math.hypot(pr.vel[0], pr.vel[1])
                    cur = unit(pr.vel[0], pr.vel[1])
                    nx = cur[0] + (want[0] - cur[0]) * min(1.0, 4.0 * dt)
                    ny = cur[1] + (want[1] - cur[1]) * min(1.0, 4.0 * dt)
                    nd = unit(nx, ny)
                    pr.vel = [nd[0] * spd, nd[1] * spd]
                else:
                    pr.homing = None
            step = math.hypot(pr.vel[0], pr.vel[1]) * dt
            pr.pos[0] += pr.vel[0] * dt
            pr.pos[1] += pr.vel[1] * dt
            pr.range_left -= step
            if pr.arm > 0:
                pr.arm -= step
                if pr.arm > 0 and pr.owner == 'enemy':
                    alive_list.append(pr)
                    continue
            out = not (0.0 <= pr.pos[0] <= self.W and 0.0 <= pr.pos[1] <= self.H)
            if pr.kind == 'body':
                e = pr.body
                e.pos[0], e.pos[1] = pr.pos[0], pr.pos[1]
                hit_wall = self.clamp(e.pos, e.radius)
                for o in self.enemies:
                    if o is e or not o.targetable() or id(o) in pr.hit_set:
                        continue
                    if dist(o.pos, pr.pos) <= o.radius + 0.5:
                        pr.hit_set.add(id(o))
                        o.take_damage(self, pr.damage, melee=True, from_pos=pr.pos, knockdown=pr.knockdown)
                if self.boss and self.boss.alive and id(self.boss) not in pr.hit_set and dist(self.boss.pos, pr.pos) <= self.boss.radius + 0.5:
                    pr.hit_set.add(id(self.boss))
                    self.boss.take_damage(self, pr.damage, melee=False)
                    pr.range_left = 0.0
                if hit_wall or pr.range_left <= 0:
                    pr.alive = False
                    hold = p.c['hold']
                    e.state = 'idle'
                    e.knockdown = hold.get('land_knockdown', 1.0)
                    if hit_wall:
                        self.m['wall_dmg'] += 1
                        if hold.get('wall_kill') and e.tier == 'grunt':
                            e.die(self, melee=True)
                        else:
                            e.take_damage(self, hold.get('wall_damage', 30), melee=True)
                    continue
                alive_list.append(pr)
                continue
            if out:
                pr.alive = False
                if pr.aoe > 0 and pr.owner == 'player':
                    self.explode(pr)
                continue
            if pr.owner == 'enemy':
                if p.iframes <= 0 or True:
                    if dist(pr.pos, p.pos) <= prad + pr.radius:
                        self.damage_player(pr.damage, pr.label or (pr.src.id if pr.src is not None else 'proj'), pr.pos, pr.src)
                        pr.alive = False
                        continue
            else:
                from_pos = (pr.pos[0] - pr.vel[0] * 0.1, pr.pos[1] - pr.vel[1] * 0.1)
                if pr.clears:
                    for o in self.projectiles:
                        if o.alive and o.owner == 'enemy' and dist(o.pos, pr.pos) <= pr.radius + o.radius + 0.2:
                            o.alive = False
                hit_any = False
                for e in self.enemies:
                    if not e.targetable() or id(e) in pr.hit_set:
                        continue
                    if dist(e.pos, pr.pos) <= e.radius + pr.radius:
                        if pr.aoe > 0:
                            self.explode(pr)
                            hit_any = True
                            break
                        ok = e.take_damage(self, pr.damage, melee=False, from_pos=from_pos, knockback=pr.knockback)
                        if pr.burn and ok:
                            e.burn = pr.burn
                        pr.hit_set.add(id(e))
                        hit_any = True
                        if not pr.pierce:
                            break
                if self.boss and self.boss.alive and pr.alive and id(self.boss) not in pr.hit_set:
                    if dist(self.boss.pos, pr.pos) <= self.boss.radius + pr.radius:
                        if pr.aoe > 0:
                            self.explode(pr)
                        else:
                            self.boss.take_damage(self, pr.damage)
                        pr.hit_set.add(id(self.boss))
                        hit_any = True
                if hit_any and not pr.pierce:
                    pr.alive = False
                    continue
                if pr.range_left <= 0:
                    if pr.aoe > 0:
                        self.explode(pr)
                    pr.alive = False
                    continue
            if pr.range_left <= 0:
                pr.alive = False
                continue
            alive_list.append(pr)
        self.projectiles = alive_list

    def explode(self, pr):
        pr.alive = False
        for e in self.enemies:
            if e.targetable() and dist(e.pos, pr.pos) <= pr.aoe + e.radius:
                e.take_damage(self, pr.damage, melee=False, from_pos=None)
        if self.boss and self.boss.alive and dist(self.boss.pos, pr.pos) <= pr.aoe + self.boss.radius:
            self.boss.take_damage(self, pr.damage)

    def update_aoes(self, dt):
        p = self.player
        keep = []
        for a in self.aoes:
            if not a.alive:
                continue
            a.delay -= dt
            if a.delay > 0:
                keep.append(a)
                continue
            a.alive = False
            if a.owner == 'enemy':
                if dist(a.pos, p.pos) <= a.radius + p.hit_radius():
                    self.damage_player(a.damage, a.label or (a.src.id if a.src is not None else 'aoe'), a.pos, a.src)
            else:
                for e in self.enemies:
                    if e.targetable() and dist(e.pos, a.pos) <= a.radius + e.radius:
                        e.take_damage(self, a.damage, melee=False, from_pos=None, knockdown=a.knockdown)
                if self.boss and self.boss.alive and dist(self.boss.pos, a.pos) <= a.radius + self.boss.radius:
                    self.boss.take_damage(self, a.damage)
        self.aoes = keep

    def update_beams(self, dt):
        p = self.player
        keep = []
        for b in self.beams:
            if not b.alive:
                continue
            b.elapsed += dt
            if not b.locked:
                if b.src is not None and getattr(b.src, 'alive', True):
                    b.origin = (b.src.pos[0], b.src.pos[1])
                    d = unit(p.pos[0] - b.origin[0], p.pos[1] - b.origin[1])
                    if d != (0.0, 0.0):
                        b.dir = d
                if b.elapsed >= b.lock_at:
                    b.locked = True
            if b.elapsed >= b.telegraph:
                b.alive = False
                if b.src is not None and not getattr(b.src, 'alive', True):
                    continue
                if seg_dist(b.origin, b.end(), p.pos) <= b.width / 2 + p.hit_radius():
                    self.damage_player(b.damage, b.label or (b.src.id if b.src is not None else 'beam'), b.origin, b.src)
                continue
            keep.append(b)
        self.beams = keep

    def update_pickups(self):
        p = self.player
        r = p.pickup_radius + (p.vehicle['radius'] if p.vehicle else 0.0)
        keep = []
        for pk in self.pickups:
            if not pk.alive:
                continue
            if dist(pk.pos, p.pos) <= r:
                pk.alive = False
                if pk.kind == 'chip':
                    p.set_chip(pk.chip)
                else:
                    p.charges = min(p.charges_max, p.charges + 1)
                continue
            keep.append(pk)
        self.pickups = keep

    def update_spawning(self, dt):
        if self.stagger_queue:
            self.stagger_timer -= dt
            if self.stagger_timer <= 0:
                self.spawn_enemy(self.stagger_queue.pop(0))
                self.stagger_timer = self.g['spawn'].get('stagger', 0.4)
        if self.spawn_queue:
            alive = sum(1 for e in self.enemies if e.alive)
            while self.spawn_queue and alive < self.g['spawn']['max_concurrent']:
                self.spawn_enemy(self.spawn_queue.pop(0))
                alive += 1
        if self.rtype in ('defend', 'rush'):
            if self.rtype == 'defend' and self.t >= self.room['duration']:
                return
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                self.spawn_wave(self.room['spawn_wave'])
                self.spawn_ticks += 1
                la = self.room.get('late_add')
                if la and self.t >= la['after'] and self.late_count < la.get('max', 3) and self.spawn_ticks % la.get('every', 2) == 0:
                    self.spawn_wave(la['wave'])
                    self.late_count += 1
                self.spawn_timer = self.room['spawn_every']
            return
        if self.wave_idx >= len(self.waves) or self.stagger_queue:
            return
        alive = sum(1 for e in self.enemies if e.alive)
        if not self.pending and alive <= self.g['spawn']['next_wave_when_alive_leq']:
            self.pending = True
            self.wave_timer = self.g['spawn']['wave_gap']
        if self.pending:
            self.wave_timer -= dt
            if self.wave_timer <= 0:
                self.spawn_wave(self.waves[self.wave_idx])
                self.wave_idx += 1
                self.pending = False

    def update_rules(self, dt):
        p = self.player
        if self.deletion_x is not None:
            dw = self.rules['deletion_wall']
            self.deletion_x += dw['speed'] * dt
            if p.pos[0] - p.hit_radius() < self.deletion_x:
                p.direct_damage(self, dw['dps'] * dt, 'deletion_wall')

    def check_end(self):
        p = self.player
        if p.dead:
            self.done = True
            self.death = True
            self.success = False
            return
        if self.t >= self.g['max_room_time']:
            self.done = True
            self.fail_reason = 'timeout'
            return
        if self.rtype == 'boss':
            if not self.boss.alive:
                self.done = True
                self.success = True
            return
        if self.rtype == 'defend':
            if self.node['hp'] <= 0:
                self.done = True
                self.fail_reason = 'node'
            elif self.t >= self.room['duration']:
                self.done = True
                self.success = True
            return
        if self.rtype == 'rush':
            if p.pos[0] >= self.W - 1.5:
                self.done = True
                self.success = True
            elif self.t >= self.room['time_limit']:
                self.done = True
                self.fail_reason = 'time'
            return
        if self.wave_idx >= len(self.waves) and not self.spawn_queue and not self.stagger_queue and not any(e.alive for e in self.enemies):
            self.done = True
            self.success = True

    def run(self):
        while not self.done:
            self.step()
        return self.result()

    def result(self):
        p = self.player
        par = self.room.get('par', 40)
        grade = '-'
        if self.success:
            gr = self.g['grades']
            frac = 1.0 - max(0.0, p.hp) / p.max_hp
            if self.t <= par * gr['S']['time_mult'] and frac <= gr['S']['damage_frac']:
                grade = 'S'
            elif self.t <= par * gr['A']['time_mult'] and frac <= gr['A']['damage_frac']:
                grade = 'A'
            elif self.t <= par * gr['B']['time_mult'] and frac <= gr['B']['damage_frac']:
                grade = 'B'
            else:
                grade = 'C'
        return {
            'success': self.success, 'death': self.death, 'fail': (not self.success and not self.death),
            'fail_reason': self.fail_reason, 'time': round(self.t, 2),
            'dmg_taken': round(p.dmg_taken, 1), 'dmg_frac': round(p.dmg_taken / p.max_hp, 3),
            'hp_end_frac': round(max(0.0, p.hp) / p.max_hp, 3), 'kills': self.m['kills'], 'spawned': self.m['spawned'],
            'chip_uptime': round(p.stats['chip_time'] / max(self.t, 1e-6), 3), 'skill_uses': p.stats['skill_uses'],
            'dash_uses': p.stats['dash_uses'], 'throws': p.stats['throws'], 'reflects': p.stats['reflects'],
            'overrides': p.stats['overrides'], 'vehicle_dmg': round(p.vehicle_dmg, 1), 'blocked': self.m['blocked'],
            'dmg_by_src': {k: round(v, 1) for k, v in p.dmg_by_src.items()}, 'grade': grade,
            'node_hp_frac': (round(self.node['hp'] / self.node['max_hp'], 3) if self.node else None),
        }
