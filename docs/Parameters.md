# ROOM ZERO — 밸런스 파라미터 목록

> 작성일: 2026-11-05 · params.json 0.13
> 단일 소스는 `sim/params.json`이다. 이 문서는 `sim/tools/gen_docs.py`가 거기서 생성한다. 값은 시뮬레이션으로 조정한 현재 값이며, 실제 빌드에서 플레이테스트로 다시 검증해야 한다.
> 단위: 길이 m, 시간 s, 각도 °, 피해 HP. 적 수치는 1챕터 기준이며 `chapter_scaling`과 난이도 배율이 곱해진다.

## 0. 구조와 Unity 매핑 제안

| 섹션 | 내용 | Unity 제안 |
|---|---|---|
| `global` | 방·스폰·픽업·등급·챕터 배율·난이도·특수 방 규칙 | `GlobalBalanceConfig` ScriptableObject 1개 |
| `characters` | 세 교리의 기본 공격·홀드·대시·스킬·패시브·오버라이드 | `DoctrineData` ScriptableObject ×3. 플레이어 컨트롤러는 하나 |
| `chips` | 칩 6종 × 교리 3종 변환표 | `ChipData` ×6, 교리별 서브 블록 |
| `enemies` | 적 16종(상속 포함) | `EnemyData` ×16. `base`는 프리팹 베리언트로 |
| `bosses` | 보스 7기, 페이즈·패턴 | `BossData` + `BossPatternData` |
| `progression` | 메모리·모듈·숙련 | `ProgressionData` |
| 시뮬 전용 | `bot_skill`, `progression_assumption`, `skill_growth_per_chapter`, `sim_dt`, `max_room_time` | 게임에 넣지 않는다 |

## 1. 전역 (`global`)

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `room_sizes` | `{"standard": [20.0, 11.0], "large": [30.0, 16.0], "corridor": [44.0, 9.0]}` |  | 방 크기 [가로, 세로] |
| `door_transition_time` | 2 | s | 문 전환(컴파일 연출) 시간 |
| `spawn.telegraph_time` | 0.8 | s | 스폰 텔레그래프(조립 연출) 시간. 이 동안 무적·비활성 |
| `spawn.min_distance_from_player` | 6 |  | 스폰 지점의 플레이어 최소 거리 |
| `spawn.next_wave_when_alive_leq` | 2 |  | 다음 웨이브 조건: 생존 적 수 이하 |
| `spawn.wave_gap` | 1 | s | 웨이브 조건 충족 후 다음 웨이브까지 지연 |
| `spawn.max_concurrent` | 24 |  | 동시 존재 적 최대(초과분은 대기열) |
| `spawn.stagger` | 0.4 | s | 웨이브 내 적 간 스폰 간격 |
| `player_common.hitbox_radius` | 0.4 | m | 플레이어 피격 반경 |
| `player_common.pickup_radius` | 1 | m | 픽업 획득 반경 |
| `player_common.hit_iframes` | 0.4 | s | 피격 후 무적(글리치) 시간 |
| `player_common.charges_max` | 10 |  | 차지 최대 보유 |
| `player_common.charges_start` | 5 |  | 스테이지 시작 차지 |
| `player_common.instances_per_stage` | 3 |  | 스테이지당 인스턴스(목숨) |
| `player_common.override_min_enemy_distance` | 4 |  | 오버라이드 시도 시 주변 적 허용 거리(봇 판단) |
| `pickups.chip_drop_chance` | `{"grunt": 0.04, "elite": 0.5, "vehicle": 1.0}` |  | 처치 시 칩 드롭 확률(티어별) |
| `pickups.charge_drop_chance` | `{"grunt": 0.05, "elite": 0.5, "vehicle": 0.0}` |  | 처치 시 차지 드롭 확률(티어별) |
| `pickups.rescue_reward` | `{"chip": 0.5, "charges": 0.3, "memory": 0.2}` |  | 구출 보상 확률 분포 |
| `pickups.rescue_charges` | 2 |  | 구출 보상이 차지일 때 개수 |
| `grades.S.time_mult` | 1 |  | 파 배율 |
| `grades.S.damage_frac` | 0.15 |  | 허용 순 체력 손실 비율 |
| `grades.A.time_mult` | 1.3 |  | 파 배율 |
| `grades.A.damage_frac` | 0.35 |  | 허용 순 체력 손실 비율 |
| `grades.B.time_mult` | 1.7 |  | 파 배율 |
| `grades.B.damage_frac` | 0.6 |  | 허용 순 체력 손실 비율 |
| `chapter_scaling.enemy_hp_mult` | `[1.0, 1.1, 1.2, 1.3, 1.4, 1.5]` |  | 챕터별 적 HP 배율 |
| `chapter_scaling.enemy_dmg_mult` | `[1.0, 1.05, 1.1, 1.15, 1.2, 1.25]` |  | 챕터별 적 피해 배율 |
| `chapter_scaling.enemy_speed_mult` | `[1.0, 1.0, 1.0, 1.05, 1.05, 1.05]` |  | 챕터별 적 속도 배율 |
| `difficulty.assist.enemy_hp_mult` | 0.85 |  | 챕터별 적 HP 배율 |
| `difficulty.assist.enemy_dmg_mult` | 0.6 |  | 챕터별 적 피해 배율 |
| `difficulty.assist.instances` | 5 |  | 인스턴스 수 |
| `difficulty.assist.auto_target` | O |  | 자동 타겟 기본값 |
| `difficulty.normal.enemy_hp_mult` | 1 |  | 챕터별 적 HP 배율 |
| `difficulty.normal.enemy_dmg_mult` | 1 |  | 챕터별 적 피해 배율 |
| `difficulty.normal.instances` | 3 |  | 인스턴스 수 |
| `difficulty.normal.auto_target` | X |  | 자동 타겟 기본값 |
| `difficulty.hard.enemy_hp_mult` | 1.3 |  | 챕터별 적 HP 배율 |
| `difficulty.hard.enemy_dmg_mult` | 1.4 |  | 챕터별 적 피해 배율 |
| `difficulty.hard.instances` | 2 |  | 인스턴스 수 |
| `difficulty.hard.auto_target` | X |  | 자동 타겟 기본값 |
| `difficulty.arcade.enemy_hp_mult` | 1.3 |  | 챕터별 적 HP 배율 |
| `difficulty.arcade.enemy_dmg_mult` | 1.4 |  | 챕터별 적 피해 배율 |
| `difficulty.arcade.instances` | 1 |  | 인스턴스 수 |
| `difficulty.arcade.modules_disabled` | O |  | 모듈 비활성 |
| `room_rules.tpose_wake_range` | 4 |  | T포즈 적 각성 거리 |
| `room_rules.tpose_chain_range` | 3 |  | 각성 연쇄 거리 |
| `room_rules.deletion_wall.speed` | 3 | m/s | 속도 |
| `room_rules.deletion_wall.dps` | 8 | HP/s | 초당 피해 |
| `room_rules.defend_node_radius` | 0.8 |  | 수비 노드 반경 |
| `room_rules.rescue_interaction_time` | 1.5 |  | 구출 상호작용 시간 |

## 2. 캐릭터 (`characters`)

### 트리거 (건) (`trigger`)

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `hp` | 105 | HP | 체력 |
| `move_speed` | 5.5 | m/s | 이동 속도 |
| `attack_move_mult` | 1 |  | 공격 중 이동 속도 배율 |
| `basic.kind` | ranged |  | 종류 |
| `basic.damage` | 14 | HP | 피해 |
| `basic.interval` | 0.2 | s | 공격 간격 |
| `basic.proj_speed` | 25 | m/s | 투사체 속도 |
| `basic.range` | 12 | m | 사거리 |
| `basic.spread_deg` | 2 | ° | 탄 퍼짐(각도) |
| `basic.pellets` | 1 |  | 발당 탄 수 |
| `melee_auto.range` | 1.3 | m | 사거리 |
| `melee_auto.damage` | 45 | HP | 피해 |
| `melee_auto.interval` | 0.4 | s | 공격 간격 |
| `dash.distance` | 4 | m | 거리 |
| `dash.duration` | 0.2 | s | 지속 시간 |
| `dash.iframes` | 0.25 | s | 무적 시간 |
| `dash.cooldown` | 1.2 | s | 재사용 대기 |
| `dash.damage` | 0 | HP | 피해 |
| `dash.super_armor` | X |  | 슈퍼아머(경직 없음) |
| `dash.pass_through` | O |  | 적 통과 |
| `skill.kind` | grenade |  | 종류 |
| `skill.damage` | 60 | HP | 피해 |
| `skill.radius` | 2.5 | m | 반경 |
| `skill.range` | 8 | m | 사거리 |
| `skill.flight` | 0.8 | s | 비행(도달) 시간 |
| `skill.cast` | 0.2 | s | 시전 시간 |
| `skill.cooldown` | 1 | s | 재사용 대기 |
| `passive.chip_ammo_mult` | 1.25 |  | 칩 탄약 배율 |
| `passive.last_mag_frac` | 0.25 |  | 마지막 탄창 비율 |
| `passive.last_mag_dmg_mult` | 1.5 |  | 마지막 탄창 피해 배율 |
| `override.kind` | hold |  | 종류 |
| `override.time` | 3 | s | 홀드 시간 |

### 너클 (격투) (`knuckle`)

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `hp` | 140 | HP | 체력 |
| `move_speed` | 5 | m/s | 이동 속도 |
| `attack_move_mult` | 0.5 |  | 공격 중 이동 속도 배율 |
| `basic.kind` | melee_combo |  | 종류 |
| `basic.damages` | `[18, 18, 30]` | HP | 콤보 타별 피해 |
| `basic.interval` | 0.3 | s | 공격 간격 |
| `basic.range` | 1.6 | m | 사거리 |
| `basic.arc_deg` | 90 | ° | 공격 각도 |
| `basic.knockback_last` | 3 | m | 마지막 타 넉백 거리 |
| `basic.super_armor` | O |  | 슈퍼아머(경직 없음) |
| `basic.dmg_reduction` | 0.4 |  | 피해 감소율 |
| `basic.combo_reset` | 0.8 | s | 콤보 유지 시간 |
| `hold.kind` | grab_throw |  | 종류 |
| `hold.range` | 1.6 | m | 사거리 |
| `hold.grab_time` | 0.3 | s | 잡기 시간 |
| `hold.throw_speed` | 15 | m/s | 투척 속도 |
| `hold.throw_damage` | 40 | HP | 투척체 피해 |
| `hold.wall_kill` | O |  | 벽 충돌 시 일반 적 즉사 |
| `hold.wall_damage` | 30 | HP | 벽 충돌 피해(정예) |
| `hold.throw_range` | 12 | m | 투척 거리 |
| `hold.land_knockdown` | 1 | s | 착지 다운 시간 |
| `dash.distance` | 6 | m | 거리 |
| `dash.duration` | 0.3 | s | 지속 시간 |
| `dash.iframes` | 0 | s | 무적 시간 |
| `dash.cooldown` | 1.6 | s | 재사용 대기 |
| `dash.damage` | 25 | HP | 피해 |
| `dash.knockdown` | 1 | s | 다운 시간 |
| `dash.super_armor` | O |  | 슈퍼아머(경직 없음) |
| `dash.pass_through` | O |  | 적 통과 |
| `dash.wall_slam_bonus` | 30 |  | 벽 밀어붙이기 추가 피해 |
| `dash.wall_slam_range` | 1.2 |  | 벽 판정 거리 |
| `dash.dmg_reduction` | 0.5 |  | 피해 감소율 |
| `skill.kind` | slam |  | 종류 |
| `skill.damage` | 50 | HP | 피해 |
| `skill.radius` | 3.5 | m | 반경 |
| `skill.knockdown` | 1.2 | s | 다운 시간 |
| `skill.cast` | 0.4 | s | 시전 시간 |
| `skill.cooldown` | 1 | s | 재사용 대기 |
| `skill.clears_projectiles` | O |  | 적 투사체 삭제 |
| `passive.heal_on_melee_kill` | 6 | HP | 근접 처치 시 회복 |
| `override.kind` | hold |  | 종류 |
| `override.time` | 1.5 | s | 홀드 시간 |
| `override.carry_sentry` | O |  | 센트리 휴대 가능 |
| `override.carry_shots` | 60 | 발 | 휴대 센트리 탄 수 |
| `override.carry_speed_mult` | 0.8 |  | 휴대 중 이동 배율 |
| `override.super_armor` | O |  | 슈퍼아머(경직 없음) |
| `override.carry_hp_frac` | 0.5 |  | 휴대 가능 센트리 HP 비율 |
| `override.carry_dmg_mult` | 2.5 |  | 휴대 센트리 피해 배율 |
| `override.carry_interval` | 0.2 | s | 휴대 센트리 발사 간격 |
| `override.carry_time` | 1 | s | 센트리 탈취 홀드 시간 |

### 엣지 (검술) (`edge`)

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `hp` | 120 | HP | 체력 |
| `move_speed` | 5.5 | m/s | 이동 속도 |
| `attack_move_mult` | 0.7 |  | 공격 중 이동 속도 배율 |
| `basic.kind` | melee_arc |  | 종류 |
| `basic.damages` | `[15, 15, 22]` | HP | 콤보 타별 피해 |
| `basic.interval` | 0.28 | s | 공격 간격 |
| `basic.range` | 2.2 | m | 사거리 |
| `basic.arc_deg` | 120 | ° | 공격 각도 |
| `basic.step` | 0.6 | m | 타격 시 전진 거리 |
| `basic.reflect` | O |  | 반사 가능 |
| `basic.reflect_dmg_mult` | 1.5 |  | 반사탄 피해 배율 |
| `basic.active_frames` | 0.16 | s | 반사 판정 유효 시간(타당) |
| `basic.combo_reset` | 0.8 | s | 콤보 유지 시간 |
| `basic.knockback_last` | 1.5 | m | 마지막 타 넉백 거리 |
| `basic.lunge_if_farther_than` | 0.75 |  | 전진 스텝 조건(사거리 비율) |
| `hold.kind` | line |  | 종류 |
| `hold.charge` | 0.5 | s | 차지 시간 |
| `hold.length` | 8 | m | 길이 |
| `hold.width` | 1 | m | 폭 |
| `hold.damage` | 45 | HP | 피해 |
| `hold.pierce` | O |  | 관통 |
| `dash.distance` | 5 | m | 거리 |
| `dash.duration` | 0.2 | s | 지속 시간 |
| `dash.iframes` | 0.25 | s | 무적 시간 |
| `dash.cooldown` | 1.2 | s | 재사용 대기 |
| `dash.damage` | 20 | HP | 피해 |
| `dash.super_armor` | X |  | 슈퍼아머(경직 없음) |
| `dash.pass_through` | O |  | 적 통과 |
| `skill.kind` | wave |  | 종류 |
| `skill.damage` | 40 | HP | 피해 |
| `skill.range` | 14 | m | 사거리 |
| `skill.width` | 1.5 | m | 폭 |
| `skill.speed` | 18 | m/s | 속도 |
| `skill.cast` | 0.25 | s | 시전 시간 |
| `skill.cooldown` | 1 | s | 재사용 대기 |
| `skill.clears_projectiles` | O |  | 적 투사체 삭제 |
| `passive.counter_window` | 0.2 | s | 카운터 판정 시간(대시 직후) |
| `passive.counter_damage` | 30 | HP | 카운터 피해 |
| `passive.counter_range` | 3 |  | 카운터 반격 거리 |
| `override.kind` | dash_assassinate |  | 종류 |
| `override.time` | 0 | s | 홀드 시간 |

## 3. 칩 변환표 (`chips`)

같은 칩 픽업을 교리별로 다르게 해석한다. 트리거는 무기 교체, 너클·엣지는 기본 공격 변형이며 소모 단위는 각각 탄약/타격 횟수다.

### H 「헤비」

**트리거**: damage=8, interval=0.1, proj_speed=28, range=13, spread_deg=4, pellets=1, ammo=150

**너클**: extra_ranged=`{"damage": 8, "range": 8.0, "proj_speed": 22.0}`, hits=60

**엣지**: attack_speed_mult=1.6, per_hit_wave=`{"damage": 10, "range": 4.0, "speed": 16.0}`, hits=60

### S 「스캐터」

**트리거**: damage=9, interval=0.55, proj_speed=22, range=6, spread_deg=25, pellets=7, knockback=2.5, ammo=30

**너클**: hit_aoe=`{"radius": 2.5, "arc_deg": 120, "knockback": 3.0, "damage": 15}`, hits=25

**엣지**: arc_deg=360, range_mult=1.1, hits=30

### R 「로켓」

**트리거**: damage=70, interval=0.9, proj_speed=16, range=14, homing=O, aoe_radius=1.8, ammo=15

**너클**: hold_replace=`{"kind": "rocket_punch", "damage": 60, "proj_speed": 20.0, "range": 10.0, "aoe_radius": 1.8}`, hits=12

**엣지**: dash_explosion=`{"damage": 45, "radius": 2.5}`, dash_cooldown_mult=0.6, hits=10

### F 「플레임」

**트리거**: damage=6, interval=0.1, proj_speed=10, range=6, spread_deg=10, pellets=1, burn_dps=8, burn_time=2, ammo=100

**너클**: ground_fire=`{"radius": 1.5, "dps": 15, "duration": 2.5}`, hits=30

**엣지**: fire_trail=`{"radius": 1.0, "dps": 15, "duration": 2.0}`, hits=35

### L 「레이저」

**트리거**: damage=30, interval=0.35, proj_speed=60, range=16, spread_deg=0.5, pellets=1, pierce=O, ammo=60

**너클**: extra_ranged=`{"damage": 20, "range": 6.0, "proj_speed": 60.0, "pierce": true}`, hits=30

**엣지**: range_mult=2, pierce=O, hits=40

### C 「체이서」

**트리거**: damage=7, interval=0.15, proj_speed=14, range=14, spread_deg=15, pellets=1, homing=O, ammo=100

**너클**: orbitals=`{"count": 2, "damage": 8, "interval": 0.4, "range": 5.0}`, hits=50

**엣지**: orbitals=`{"count": 2, "damage": 9, "interval": 0.4, "range": 5.0}`, hits=50

## 4. 적 (`enemies`)

상속(`base`)을 풀어 쓴 값이다. 1챕터 기준.

### 더미 라이플 (`rifle`)

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `tier` | grunt |  | 티어(드롭·투척 규칙) |
| `hp` | 45 | HP | 체력 |
| `speed` | 3 | m/s | 속도 |
| `radius` | 0.4 | m | 반경 |
| `behavior` | ranged |  | 행동 유형 |
| `stop_range` | 8 | m | 접근 정지 거리 |
| `fire_range` | 10 | m | 사격 거리 |
| `retreat_range` | 3 | m | 후퇴 거리 |
| `attack.telegraph` | 0.6 | s | 텔레그래프(예고) 시간 |
| `attack.burst` | 3 |  | 점사 탄 수 |
| `attack.burst_gap` | 0.12 | s | 점사 간격 |
| `attack.damage` | 8 | HP | 피해 |
| `attack.proj_speed` | 12 | m/s | 투사체 속도 |
| `attack.spread_deg` | 6 | ° | 탄 퍼짐(각도) |
| `attack.cooldown` | 1.8 | s | 재사용 대기 |
| `throwable` | O |  | 너클 투척 가능 |
| `reflectable` | O |  | 엣지 반사 가능 |
| `score` | 100 |  | 점수 |
| `spawn_cost` | 1 |  | 스폰 예산 비용 |

### 러셔 (`rusher`)

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `tier` | grunt |  | 티어(드롭·투척 규칙) |
| `hp` | 30 | HP | 체력 |
| `speed` | 6.5 | m/s | 속도 |
| `radius` | 0.4 | m | 반경 |
| `behavior` | melee |  | 행동 유형 |
| `attack.range` | 1.2 | m | 사거리 |
| `attack.windup` | 0.35 | s | 근접 윈드업 |
| `attack.hit_range` | 1.6 | m | 근접 판정 거리 |
| `attack.damage` | 12 | HP | 피해 |
| `attack.cooldown` | 1.2 | s | 재사용 대기 |
| `throwable` | O |  | 너클 투척 가능 |
| `score` | 80 |  | 점수 |
| `spawn_cost` | 1 |  | 스폰 예산 비용 |

### 쉴더 (`shielder`)

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `tier` | grunt |  | 티어(드롭·투척 규칙) |
| `hp` | 80 | HP | 체력 |
| `speed` | 2.5 | m/s | 속도 |
| `radius` | 0.45 | m | 반경 |
| `behavior` | melee |  | 행동 유형 |
| `shield_arc_deg` | 100 | ° | 방패 보호 각도 |
| `attack.range` | 1.5 | m | 사거리 |
| `attack.windup` | 0.6 | s | 근접 윈드업 |
| `attack.hit_range` | 1.9 | m | 근접 판정 거리 |
| `attack.damage` | 15 | HP | 피해 |
| `attack.cooldown` | 2 | s | 재사용 대기 |
| `throwable` | O |  | 너클 투척 가능 |
| `score` | 150 |  | 점수 |
| `spawn_cost` | 2 |  | 스폰 예산 비용 |
| `shield_hp` | 60 | HP | 방패 내구 |
| `shield_down_time` | 3 | s | 방패 파괴 후 개방 시간 |
| `turn_rate_deg` | 150 | °/s | 회전 속도(도/초) |

### 센트리 (`sentry`)

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `tier` | grunt |  | 티어(드롭·투척 규칙) |
| `hp` | 110 | HP | 체력 |
| `speed` | 0 | m/s | 속도 |
| `radius` | 0.5 | m | 반경 |
| `behavior` | turret |  | 행동 유형 |
| `turn_rate_deg` | 90 | °/s | 회전 속도(도/초) |
| `fire_range` | 10 | m | 사격 거리 |
| `aim_tolerance_deg` | 10 | ° | 사격 허용 각도 |
| `attack.stream_time` | 1.5 | s | 스트림 지속 |
| `attack.shot_gap` | 0.25 | s | 스트림 발사 간격 |
| `attack.damage` | 5 | HP | 피해 |
| `attack.proj_speed` | 14 | m/s | 투사체 속도 |
| `attack.spread_deg` | 4 | ° | 탄 퍼짐(각도) |
| `attack.cooldown` | 1.5 | s | 재사용 대기 |
| `throwable` | X |  | 너클 투척 가능 |
| `overridable` | O |  | 오버라이드 가능 |
| `score` | 150 |  | 점수 |
| `spawn_cost` | 2 |  | 스폰 예산 비용 |

### 슈터 (`shooter`)

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `tier` | grunt |  | 티어(드롭·투척 규칙) |
| `hp` | 50 | HP | 체력 |
| `speed` | 3.5 | m/s | 속도 |
| `radius` | 0.4 | m | 반경 |
| `behavior` | sniper |  | 행동 유형 |
| `min_range` | 9 | m | 유지 최소 거리 |
| `max_range` | 14 | m | 유지 최대 거리 |
| `attack.telegraph` | 1.2 | s | 텔레그래프(예고) 시간 |
| `attack.lock_at` | 0.9 | s | 조준 잠금 시점 |
| `attack.damage` | 22 | HP | 피해 |
| `attack.proj_speed` | 30 | m/s | 투사체 속도 |
| `attack.cooldown` | 3 | s | 재사용 대기 |
| `attack.reposition` | 3 |  | 사격 후 재배치 거리 |
| `throwable` | O |  | 너클 투척 가능 |
| `score` | 200 |  | 점수 |
| `spawn_cost` | 2 |  | 스폰 예산 비용 |

### 폭탄병 (`bomber`)

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `tier` | grunt |  | 티어(드롭·투척 규칙) |
| `hp` | 45 | HP | 체력 |
| `speed` | 3 | m/s | 속도 |
| `radius` | 0.4 | m | 반경 |
| `behavior` | lobber |  | 행동 유형 |
| `min_range` | 6 | m | 유지 최소 거리 |
| `max_range` | 9 | m | 유지 최대 거리 |
| `attack.telegraph` | 0.5 | s | 텔레그래프(예고) 시간 |
| `attack.flight` | 1 | s | 비행(도달) 시간 |
| `attack.aoe_radius` | 2 | m | 폭발 반경 |
| `attack.damage` | 16 | HP | 피해 |
| `attack.cooldown` | 2.5 | s | 재사용 대기 |
| `throwable` | O |  | 너클 투척 가능 |
| `score` | 150 |  | 점수 |
| `spawn_cost` | 2 |  | 스폰 예산 비용 |

### 오염 데이터 (`zombie`) — `rusher` 상속

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `tier` | grunt |  | 티어(드롭·투척 규칙) |
| `hp` | 40 | HP | 체력 |
| `speed` | 4.5 | m/s | 속도 |
| `radius` | 0.4 | m | 반경 |
| `behavior` | melee |  | 행동 유형 |
| `attack.range` | 1.2 | m | 사거리 |
| `attack.windup` | 0.35 | s | 근접 윈드업 |
| `attack.hit_range` | 1.6 | m | 근접 판정 거리 |
| `attack.damage` | 8 | HP | 피해 |
| `attack.cooldown` | 1.2 | s | 재사용 대기 |
| `throwable` | O |  | 너클 투척 가능 |
| `score` | 60 |  | 점수 |
| `spawn_cost` | 1 |  | 스폰 예산 비용 |

### 변이체 (`brute`)

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `tier` | elite |  | 티어(드롭·투척 규칙) |
| `hp` | 160 | HP | 체력 |
| `speed` | 3.5 | m/s | 속도 |
| `radius` | 0.7 | m | 반경 |
| `behavior` | melee |  | 행동 유형 |
| `knockback_resist` | O |  | 넉백·다운 저항 |
| `attack.range` | 2 | m | 사거리 |
| `attack.windup` | 0.8 | s | 근접 윈드업 |
| `attack.hit_range` | 2.4 | m | 근접 판정 거리 |
| `attack.damage` | 20 | HP | 피해 |
| `attack.cooldown` | 2 | s | 재사용 대기 |
| `throwable` | X |  | 너클 투척 가능 |
| `score` | 400 |  | 점수 |
| `spawn_cost` | 3 |  | 스폰 예산 비용 |

### 기사 (`knight`) — `shielder` 상속

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `tier` | grunt |  | 티어(드롭·투척 규칙) |
| `hp` | 110 | HP | 체력 |
| `speed` | 2.8 | m/s | 속도 |
| `radius` | 0.45 | m | 반경 |
| `behavior` | melee |  | 행동 유형 |
| `shield_arc_deg` | 100 | ° | 방패 보호 각도 |
| `attack.range` | 1.5 | m | 사거리 |
| `attack.windup` | 0.6 | s | 근접 윈드업 |
| `attack.hit_range` | 1.9 | m | 근접 판정 거리 |
| `attack.damage` | 16 | HP | 피해 |
| `attack.cooldown` | 2 | s | 재사용 대기 |
| `throwable` | O |  | 너클 투척 가능 |
| `score` | 200 |  | 점수 |
| `spawn_cost` | 2 |  | 스폰 예산 비용 |
| `shield_hp` | 90 | HP | 방패 내구 |
| `shield_down_time` | 3 | s | 방패 파괴 후 개방 시간 |
| `turn_rate_deg` | 150 | °/s | 회전 속도(도/초) |

### 궁수 (`archer`) — `rifle` 상속

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `tier` | grunt |  | 티어(드롭·투척 규칙) |
| `hp` | 45 | HP | 체력 |
| `speed` | 3 | m/s | 속도 |
| `radius` | 0.4 | m | 반경 |
| `behavior` | ranged |  | 행동 유형 |
| `stop_range` | 9 | m | 접근 정지 거리 |
| `fire_range` | 12 | m | 사격 거리 |
| `retreat_range` | 3 | m | 후퇴 거리 |
| `attack.telegraph` | 0.8 | s | 텔레그래프(예고) 시간 |
| `attack.burst` | 1 |  | 점사 탄 수 |
| `attack.burst_gap` | 0 | s | 점사 간격 |
| `attack.damage` | 12 | HP | 피해 |
| `attack.proj_speed` | 10 | m/s | 투사체 속도 |
| `attack.spread_deg` | 3 | ° | 탄 퍼짐(각도) |
| `attack.cooldown` | 2.2 | s | 재사용 대기 |
| `throwable` | O |  | 너클 투척 가능 |
| `reflectable` | O |  | 엣지 반사 가능 |
| `score` | 120 |  | 점수 |
| `spawn_cost` | 1 |  | 스폰 예산 비용 |

### 마법사 (`mage`) — `bomber` 상속

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `tier` | grunt |  | 티어(드롭·투척 규칙) |
| `hp` | 50 | HP | 체력 |
| `speed` | 3 | m/s | 속도 |
| `radius` | 0.4 | m | 반경 |
| `behavior` | lobber |  | 행동 유형 |
| `min_range` | 7 | m | 유지 최소 거리 |
| `max_range` | 10 | m | 유지 최대 거리 |
| `attack.telegraph` | 1 | s | 텔레그래프(예고) 시간 |
| `attack.flight` | 1.4 | s | 비행(도달) 시간 |
| `attack.aoe_radius` | 1.5 | m | 폭발 반경 |
| `attack.damage` | 18 | HP | 피해 |
| `attack.cooldown` | 3 | s | 재사용 대기 |
| `throwable` | O |  | 너클 투척 가능 |
| `score` | 200 |  | 점수 |
| `spawn_cost` | 2 |  | 스폰 예산 비용 |

### 보안 드론 (`drone`) — `rusher` 상속

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `tier` | grunt |  | 티어(드롭·투척 규칙) |
| `hp` | 28 | HP | 체력 |
| `speed` | 6.5 | m/s | 속도 |
| `radius` | 0.4 | m | 반경 |
| `behavior` | melee |  | 행동 유형 |
| `attack.range` | 1.2 | m | 사거리 |
| `attack.windup` | 0.4 | s | 근접 윈드업 |
| `attack.hit_range` | 1.6 | m | 근접 판정 거리 |
| `attack.damage` | 8 | HP | 피해 |
| `attack.cooldown` | 1.2 | s | 재사용 대기 |
| `throwable` | X |  | 너클 투척 가능 |
| `score` | 100 |  | 점수 |
| `spawn_cost` | 1 |  | 스폰 예산 비용 |
| `flying` | O |  | 비행(지상 근접 불가) |

### 레이저 센트리 (`laser_sentry`) — `sentry` 상속

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `tier` | grunt |  | 티어(드롭·투척 규칙) |
| `hp` | 130 | HP | 체력 |
| `speed` | 0 | m/s | 속도 |
| `radius` | 0.5 | m | 반경 |
| `behavior` | beam_turret |  | 행동 유형 |
| `turn_rate_deg` | 90 | °/s | 회전 속도(도/초) |
| `fire_range` | 12 | m | 사격 거리 |
| `aim_tolerance_deg` | 15 | ° | 사격 허용 각도 |
| `attack.stream_time` | 1.5 | s | 스트림 지속 |
| `attack.shot_gap` | 0.25 | s | 스트림 발사 간격 |
| `attack.damage` | 20 | HP | 피해 |
| `attack.proj_speed` | 14 | m/s | 투사체 속도 |
| `attack.spread_deg` | 4 | ° | 탄 퍼짐(각도) |
| `attack.cooldown` | 2.5 | s | 재사용 대기 |
| `attack.telegraph` | 1 | s | 텔레그래프(예고) 시간 |
| `attack.lock_at` | 0.5 | s | 조준 잠금 시점 |
| `attack.beam_length` | 12 | m | 빔 길이 |
| `attack.beam_width` | 0.6 | m | 빔 폭 |
| `throwable` | X |  | 너클 투척 가능 |
| `overridable` | O |  | 오버라이드 가능 |
| `score` | 250 |  | 점수 |
| `spawn_cost` | 3 |  | 스폰 예산 비용 |
| `reflectable` | X |  | 엣지 반사 가능 |

### 디버거 (`debugger`)

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `tier` | elite |  | 티어(드롭·투척 규칙) |
| `hp` | 160 | HP | 체력 |
| `speed` | 0 | m/s | 속도 |
| `radius` | 0.45 | m | 반경 |
| `behavior` | teleporter |  | 행동 유형 |
| `teleport_every` | 4 | s | 순간이동 주기 |
| `teleport_range` | `[6.0, 8.0]` |  | 순간이동 거리 범위 |
| `attack.telegraph` | 1 | s | 텔레그래프(예고) 시간 |
| `attack.lock_at` | 0.5 | s | 조준 잠금 시점 |
| `attack.beam_length` | 12 | m | 빔 길이 |
| `attack.beam_width` | 0.6 | m | 빔 폭 |
| `attack.damage` | 22 | HP | 피해 |
| `attack.cooldown` | 3 | s | 재사용 대기 |
| `reflectable` | X |  | 엣지 반사 가능 |
| `throwable` | X |  | 너클 투척 가능 |
| `score` | 600 |  | 점수 |
| `spawn_cost` | 5 |  | 스폰 예산 비용 |
| `materialize` | 0.6 | s | 순간이동 후 무방비 시간 |

### 진압 장갑차 (`apc`)

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `tier` | vehicle |  | 티어(드롭·투척 규칙) |
| `hp` | 300 | HP | 체력 |
| `speed` | 2 | m/s | 속도 |
| `radius` | 1.2 | m | 반경 |
| `behavior` | vehicle |  | 행동 유형 |
| `stop_range` | 8 | m | 접근 정지 거리 |
| `fire_range` | 12 | m | 사격 거리 |
| `attack.telegraph` | 0.4 | s | 텔레그래프(예고) 시간 |
| `attack.burst` | 5 |  | 점사 탄 수 |
| `attack.burst_gap` | 0.1 | s | 점사 간격 |
| `attack.damage` | 8 | HP | 피해 |
| `attack.proj_speed` | 14 | m/s | 투사체 속도 |
| `attack.spread_deg` | 5 | ° | 탄 퍼짐(각도) |
| `attack.cooldown` | 2.5 | s | 재사용 대기 |
| `stun_hp_frac` | 0.25 |  | 기절 진입 HP 비율 |
| `stun_time` | 6 | s | 기절 시간 |
| `overridable` | O |  | 오버라이드 가능 |
| `throwable` | X |  | 너클 투척 가능 |
| `score` | 800 |  | 점수 |
| `spawn_cost` | 6 |  | 스폰 예산 비용 |
| `pilot.hp` | 200 | HP | 체력 |
| `pilot.speed` | 4 | m/s | 속도 |
| `pilot.radius` | 1 | m | 반경 |
| `pilot.gun.damage` | 20 | HP | 피해 |
| `pilot.gun.interval` | 0.15 | s | 공격 간격 |
| `pilot.gun.proj_speed` | 25 | m/s | 투사체 속도 |
| `pilot.gun.range` | 14 | m | 사거리 |
| `pilot.gun.spread_deg` | 3 | ° | 탄 퍼짐(각도) |
| `pilot.sub.damage` | 80 | HP | 피해 |
| `pilot.sub.aoe_radius` | 2.5 | m | 폭발 반경 |
| `pilot.sub.range` | 10 | m | 사거리 |
| `pilot.sub.flight` | 0.6 | s | 비행(도달) 시간 |
| `pilot.sub.cooldown` | 4 | s | 재사용 대기 |

### 전차 (`tank`) — `apc` 상속

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `tier` | vehicle |  | 티어(드롭·투척 규칙) |
| `hp` | 450 | HP | 체력 |
| `speed` | 1.5 | m/s | 속도 |
| `radius` | 1.5 | m | 반경 |
| `behavior` | vehicle |  | 행동 유형 |
| `stop_range` | 8 | m | 접근 정지 거리 |
| `fire_range` | 12 | m | 사격 거리 |
| `attack.telegraph` | 0.4 | s | 텔레그래프(예고) 시간 |
| `attack.burst` | 5 |  | 점사 탄 수 |
| `attack.burst_gap` | 0.1 | s | 점사 간격 |
| `attack.damage` | 8 | HP | 피해 |
| `attack.proj_speed` | 14 | m/s | 투사체 속도 |
| `attack.spread_deg` | 5 | ° | 탄 퍼짐(각도) |
| `attack.cooldown` | 2.5 | s | 재사용 대기 |
| `stun_hp_frac` | 0.25 |  | 기절 진입 HP 비율 |
| `stun_time` | 6 | s | 기절 시간 |
| `overridable` | O |  | 오버라이드 가능 |
| `throwable` | X |  | 너클 투척 가능 |
| `score` | 1200 |  | 점수 |
| `spawn_cost` | 8 |  | 스폰 예산 비용 |
| `pilot.hp` | 300 | HP | 체력 |
| `pilot.speed` | 3 | m/s | 속도 |
| `pilot.radius` | 1.3 | m | 반경 |
| `pilot.gun.damage` | 24 | HP | 피해 |
| `pilot.gun.interval` | 0.15 | s | 공격 간격 |
| `pilot.gun.proj_speed` | 25 | m/s | 투사체 속도 |
| `pilot.gun.range` | 14 | m | 사거리 |
| `pilot.gun.spread_deg` | 3 | ° | 탄 퍼짐(각도) |
| `pilot.sub.damage` | 120 | HP | 피해 |
| `pilot.sub.aoe_radius` | 2.5 | m | 폭발 반경 |
| `pilot.sub.range` | 10 | m | 사거리 |
| `pilot.sub.flight` | 0.6 | s | 비행(도달) 시간 |
| `pilot.sub.cooldown` | 4 | s | 재사용 대기 |
| `cannon.telegraph` | 1 | s | 텔레그래프(예고) 시간 |
| `cannon.damage` | 30 | HP | 피해 |
| `cannon.proj_speed` | 15 | m/s | 투사체 속도 |
| `cannon.aoe_radius` | 2 | m | 폭발 반경 |
| `cannon.cooldown` | 4 | s | 재사용 대기 |

## 5. 보스 (`bosses`)

보스 피해는 챕터 배율을 곱하지 않고 난이도 배율만 곱한다(챕터별로 직접 튠).

### 불도저 (`bulldozer`)

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `chapter` | 1 |  | 등장 챕터 |
| `hp` | 3200 | HP | 체력 |
| `radius` | 2.5 | m | 반경 |
| `speed` | 1.5 | m/s | 속도 |
| `contact_damage` | 20 | HP | 접촉 피해(밀고 들어올 때) |
| `rest` | 2.5 | s | 패턴 간 휴식 |
| `par` | 90 | s | 파 시간 |

패턴 순환: `charge, fan5, ring12`

| 페이즈 | 값 |
|---|---|
| 1 | `{"hp_frac": 1.0, "speed_mult": 1.0}` |
| 2 | `{"hp_frac": 0.5, "speed_mult": 1.25, "add_patterns": ["summon_rifle3"]}` |

| 패턴 | 정의 |
|---|---|
| `charge` | `{"type": "charge", "telegraph": 1.3, "dash_speed": 12.0, "damage": 22, "post_rest": 3.0, "max_distance": 14.0, "lock_frac": 0.4}` |
| `fan5` | `{"type": "fan", "telegraph": 0.8, "count": 5, "spread_deg": 50.0, "damage": 8, "proj_speed": 11.0}` |
| `ring12` | `{"type": "ring", "telegraph": 1.0, "count": 12, "damage": 8, "proj_speed": 8.0}` |
| `summon_rifle3` | `{"type": "summon", "telegraph": 1.0, "enemies": {"rifle": 3}, "max_uses": 2}` |

### 공격 헬기 (중간보스) (`heli`)

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `chapter` | 2 |  | 등장 챕터 |
| `hp` | 2000 | HP | 체력 |
| `radius` | 1.5 | m | 반경 |
| `speed` | 3 | m/s | 속도 |
| `flying` | O |  | 비행(지상 근접 불가) |
| `keep_range` | 7 |  | 유지 거리(비행 보스) |
| `contact_damage` | 0 | HP | 접촉 피해(밀고 들어올 때) |
| `rest` | 2.2 | s | 패턴 간 휴식 |
| `par` | 70 | s | 파 시간 |

패턴 순환: `fan5, rockets3, land, land`

| 페이즈 | 값 |
|---|---|
| 1 | `{"hp_frac": 1.0, "speed_mult": 1.0}` |
| 2 | `{"hp_frac": 0.5, "speed_mult": 1.2}` |

| 패턴 | 정의 |
|---|---|
| `fan5` | `{"type": "fan", "telegraph": 0.7, "count": 5, "spread_deg": 40.0, "damage": 9, "proj_speed": 12.0}` |
| `rockets3` | `{"type": "aoe", "telegraph": 1.2, "count": 3, "radius": 2.0, "scatter": 2.5, "damage": 20}` |
| `land` | `{"type": "land", "telegraph": 0.5, "duration": 3.5}` |

### 장갑 열차 (`armored_train`)

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `chapter` | 2 |  | 등장 챕터 |
| `hp` | 4000 | HP | 체력 |
| `radius` | 3 | m | 반경 |
| `speed` | 0 | m/s | 속도 |
| `contact_damage` | 0 | HP | 접촉 피해(밀고 들어올 때) |
| `rest` | 2.2 | s | 패턴 간 휴식 |
| `par` | 100 | s | 파 시간 |

패턴 순환: `fan9, mortar3, summon_rifle4, sweep`

| 페이즈 | 값 |
|---|---|
| 1 | `{"hp_frac": 1.0, "speed_mult": 1.0}` |
| 2 | `{"hp_frac": 0.5, "speed_mult": 1.2}` |

| 패턴 | 정의 |
|---|---|
| `fan9` | `{"type": "fan", "telegraph": 0.8, "count": 7, "spread_deg": 50.0, "damage": 9, "proj_speed": 11.0}` |
| `mortar3` | `{"type": "aoe", "telegraph": 1.3, "count": 3, "radius": 2.2, "scatter": 3.0, "damage": 18}` |
| `summon_rifle4` | `{"type": "summon", "telegraph": 1.0, "enemies": {"rifle": 2}, "max_uses": 4}` |
| `sweep` | `{"type": "sweep", "telegraph": 1.3, "half_width": 1.5, "damage": 22, "post_rest": 3.0}` |

### 클러스터 (`cluster`)

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `chapter` | 3 |  | 등장 챕터 |
| `hp` | 3600 | HP | 체력 |
| `radius` | 2 | m | 반경 |
| `speed` | 2.5 | m/s | 속도 |
| `contact_damage` | 12 | HP | 접촉 피해(밀고 들어올 때) |
| `rest` | 2 | s | 패턴 간 휴식 |
| `par` | 100 | s | 파 시간 |

패턴 순환: `charge, slam, summon_zombie6, spit5`

| 페이즈 | 값 |
|---|---|
| 1 | `{"hp_frac": 1.0, "speed_mult": 1.0}` |
| 2 | `{"hp_frac": 0.5, "speed_mult": 1.3}` |

| 패턴 | 정의 |
|---|---|
| `charge` | `{"type": "charge", "telegraph": 1.3, "dash_speed": 10.0, "damage": 22, "post_rest": 2.5, "max_distance": 12.0, "lock_frac": 0.4}` |
| `slam` | `{"type": "aoe_self", "telegraph": 1.0, "radius": 3.0, "damage": 22}` |
| `summon_zombie6` | `{"type": "summon", "telegraph": 1.0, "enemies": {"zombie": 4}, "max_uses": 4}` |
| `spit5` | `{"type": "fan", "telegraph": 0.8, "count": 5, "spread_deg": 36.0, "damage": 9, "proj_speed": 7.0}` |

### 블록 골렘 (`block_golem`)

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `chapter` | 4 |  | 등장 챕터 |
| `hp` | 4200 | HP | 체력 |
| `radius` | 2.8 | m | 반경 |
| `speed` | 1.2 | m/s | 속도 |
| `contact_damage` | 15 | HP | 접촉 피해(밀고 들어올 때) |
| `rest` | 2.2 | s | 패턴 간 휴식 |
| `par` | 120 | s | 파 시간 |

패턴 순환: `blocks5, charge, ring24, summon_kn2_ar2`

| 페이즈 | 값 |
|---|---|
| 1 | `{"hp_frac": 1.0, "speed_mult": 1.0}` |
| 2 | `{"hp_frac": 0.7, "speed_mult": 1.15}` |
| 3 | `{"hp_frac": 0.35, "speed_mult": 1.3}` |

| 패턴 | 정의 |
|---|---|
| `blocks5` | `{"type": "aoe", "telegraph": 1.2, "count": 4, "radius": 1.8, "scatter": 3.5, "damage": 20}` |
| `charge` | `{"type": "charge", "telegraph": 1.3, "dash_speed": 9.0, "damage": 20, "post_rest": 3.0, "max_distance": 12.0, "lock_frac": 0.35}` |
| `ring24` | `{"type": "ring", "telegraph": 1.0, "count": 12, "damage": 11, "proj_speed": 8.5}` |
| `summon_kn2_ar2` | `{"type": "summon", "telegraph": 1.0, "enemies": {"archer": 2}, "max_uses": 3}` |

### 컴파일러 (`compiler`)

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `chapter` | 5 |  | 등장 챕터 |
| `hp` | 3800 | HP | 체력 |
| `radius` | 2.5 | m | 반경 |
| `speed` | 0 | m/s | 속도 |
| `contact_damage` | 0 | HP | 접촉 피해(밀고 들어올 때) |
| `rest` | 1.8 | s | 패턴 간 휴식 |
| `par` | 120 | s | 파 시간 |

패턴 순환: `summon_drone4, beam, ring20, aoe3`

| 페이즈 | 값 |
|---|---|
| 1 | `{"hp_frac": 1.0, "speed_mult": 1.0}` |
| 2 | `{"hp_frac": 0.5, "speed_mult": 1.2, "add_patterns": ["summon_debugger1"]}` |

| 패턴 | 정의 |
|---|---|
| `summon_drone4` | `{"type": "summon", "telegraph": 0.8, "enemies": {"drone": 2}, "max_uses": 6}` |
| `beam` | `{"type": "beam", "telegraph": 1.1, "lock_at": 0.6, "length": 14.0, "width": 0.8, "damage": 24}` |
| `ring20` | `{"type": "ring", "telegraph": 1.0, "count": 16, "damage": 12, "proj_speed": 9.0}` |
| `aoe3` | `{"type": "aoe", "telegraph": 1.2, "count": 3, "radius": 2.0, "scatter": 2.5, "damage": 22}` |
| `summon_debugger1` | `{"type": "summon", "telegraph": 1.0, "enemies": {"debugger": 1}, "max_uses": 1}` |

### 감시자 오버시어 (`overseer`)

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `chapter` | 6 |  | 등장 챕터 |
| `hp` | 4400 | HP | 체력 |
| `radius` | 2.5 | m | 반경 |
| `speed` | 2 | m/s | 속도 |
| `contact_damage` | 15 | HP | 접촉 피해(밀고 들어올 때) |
| `rest` | 1.8 | s | 패턴 간 휴식 |
| `par` | 150 | s | 파 시간 |

패턴 순환: `fan9, ring20, aoe4, charge, beam, summon_drone2`

| 페이즈 | 값 |
|---|---|
| 1 | `{"hp_frac": 1.0, "speed_mult": 1.0, "rest": 2.0}` |
| 2 | `{"hp_frac": 0.66, "speed_mult": 1.15, "rest": 1.8}` |
| 3 | `{"hp_frac": 0.33, "speed_mult": 1.3, "rest": 1.6, "add_patterns": ["summon_mix"]}` |

| 패턴 | 정의 |
|---|---|
| `fan9` | `{"type": "fan", "telegraph": 0.8, "count": 7, "spread_deg": 50.0, "damage": 10, "proj_speed": 12.0}` |
| `ring20` | `{"type": "ring", "telegraph": 1.0, "count": 16, "damage": 10, "proj_speed": 9.0}` |
| `aoe4` | `{"type": "aoe", "telegraph": 1.2, "count": 4, "radius": 2.0, "scatter": 3.0, "damage": 20}` |
| `charge` | `{"type": "charge", "telegraph": 1.3, "dash_speed": 12.0, "damage": 26, "post_rest": 2.5, "max_distance": 14.0, "lock_frac": 0.4}` |
| `beam` | `{"type": "beam", "telegraph": 1.1, "lock_at": 0.6, "length": 14.0, "width": 0.8, "damage": 22}` |
| `summon_drone2` | `{"type": "summon", "telegraph": 1.0, "enemies": {"drone": 2}, "max_uses": 4}` |
| `summon_mix` | `{"type": "summon", "telegraph": 1.0, "enemies": {"debugger": 1, "drone": 2}, "max_uses": 1}` |

## 6. 성장 (`progression`)

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `memory_per_room.combat` | 30 |  | 방 타입별 메모리 조각 |
| `memory_per_room.rescue` | 45 |  | 방 타입별 메모리 조각 |
| `memory_per_room.defend` | 40 |  | 방 타입별 메모리 조각 |
| `memory_per_room.rush` | 35 |  | 방 타입별 메모리 조각 |
| `memory_per_room.bug` | 40 |  | 방 타입별 메모리 조각 |
| `memory_per_room.midboss` | 80 |  | 방 타입별 메모리 조각 |
| `memory_per_room.boss` | 150 |  | 방 타입별 메모리 조각 |
| `grade_bonus_mult.S` | 2 |  | 등급 보너스 배율 |
| `grade_bonus_mult.A` | 1.5 |  | 등급 보너스 배율 |
| `grade_bonus_mult.B` | 1.2 |  | 등급 보너스 배율 |
| `grade_bonus_mult.C` | 1 |  | 등급 보너스 배율 |
| `rescue_memory` | 25 |  | 구출 메모리 |
| `modules.mobility.levels` | 10 |  | 최대 레벨 |
| `modules.mobility.dash_cooldown_mult_per_level` | -0.03 |  | 레벨당 대시 재사용 배율 |
| `modules.mobility.dash_distance_per_level` | 0.1 |  | 레벨당 대시 거리 |
| `modules.mobility.move_speed_per_level` | 0.05 |  | 레벨당 이동 속도 |
| `modules.mobility.cost_base` | 100 |  | 1레벨 비용 |
| `modules.mobility.cost_growth` | 1.35 |  | 레벨당 비용 증가율 |
| `modules.firepower.levels` | 10 |  | 최대 레벨 |
| `modules.firepower.chip_ammo_mult_per_level` | 0.04 |  | 레벨당 칩 탄약 배율 |
| `modules.firepower.charges_max_per_level` | 0.3 |  | 레벨당 차지 최대 |
| `modules.firepower.basic_damage_mult_per_level` | 0.025 |  | 레벨당 기본 피해 배율 |
| `modules.firepower.cost_base` | 100 |  | 1레벨 비용 |
| `modules.firepower.cost_growth` | 1.35 |  | 레벨당 비용 증가율 |
| `modules.survival.levels` | 10 |  | 최대 레벨 |
| `modules.survival.hp_per_level` | 6 |  | 레벨당 HP |
| `modules.survival.instances_at_levels` | `[5, 10]` |  | 인스턴스 +1 레벨 |
| `modules.survival.hit_iframes_per_level` | 0.02 |  | 레벨당 피격 무적 |
| `modules.survival.cost_base` | 100 |  | 1레벨 비용 |
| `modules.survival.cost_growth` | 1.35 |  | 레벨당 비용 증가율 |
| `mastery.trigger.levels` | 5 |  | 최대 레벨 |
| `mastery.trigger.pistol_interval_mult_per_level` | -0.04 |  | 레벨당 권총 간격 배율 |
| `mastery.trigger.grenade_radius_per_level` | 0.15 |  | 레벨당 수류탄 반경 |
| `mastery.trigger.knife_damage_per_level` | 5 |  | 레벨당 나이프 피해 |
| `mastery.knuckle.levels` | 5 |  | 최대 레벨 |
| `mastery.knuckle.throw_range_per_level` | 1 |  | 레벨당 투척 거리 |
| `mastery.knuckle.combo3_damage_per_level` | 4 |  | 레벨당 3타 피해 |
| `mastery.knuckle.heal_per_level` | 1 |  | 레벨당 회복 |
| `mastery.edge.levels` | 5 |  | 최대 레벨 |
| `mastery.edge.reflect_mult_per_level` | 0.15 |  | 레벨당 반사 배율 |
| `mastery.edge.counter_window_per_level` | 0.02 |  | 레벨당 카운터 판정 |
| `mastery.edge.wave_range_per_level` | 1 |  | 레벨당 참격파 사거리 |

## 7. 시뮬레이션 전용 가정

게임 데이터가 아니다. 봇과 챕터 진입 시점의 성장 가정을 정의한다.

| 키 | 값 | 단위 | 설명 |
|---|---|---|---|
| `sim_dt` | 0.05 |  | 시뮬레이션 틱 간격 (시뮬 전용) |
| `max_room_time` | 240 | s | 방 최대 시간(초과 시 실패 처리) |
| `bot_skill.novice.reaction` | 0.45 | s | 반응 시간 |
| `bot_skill.novice.dodge_prob` | 0.35 |  | 탄 회피 성공 확률 |
| `bot_skill.novice.aim_error_deg` | 8 | ° | 조준 오차(표준편차) |
| `bot_skill.novice.decision_period` | 0.3 | s | 판단 주기 |
| `bot_skill.novice.tactic_prob` | 0.5 |  | 전술 행동 선택 확률 |
| `bot_skill.novice.telegraph_dodge_prob` | 0.5 |  | 텔레그래프 공격 회피 확률 |
| `bot_skill.average.reaction` | 0.3 | s | 반응 시간 |
| `bot_skill.average.dodge_prob` | 0.6 |  | 탄 회피 성공 확률 |
| `bot_skill.average.aim_error_deg` | 4 | ° | 조준 오차(표준편차) |
| `bot_skill.average.decision_period` | 0.2 | s | 판단 주기 |
| `bot_skill.average.tactic_prob` | 0.75 |  | 전술 행동 선택 확률 |
| `bot_skill.average.telegraph_dodge_prob` | 0.75 |  | 텔레그래프 공격 회피 확률 |
| `bot_skill.expert.reaction` | 0.18 | s | 반응 시간 |
| `bot_skill.expert.dodge_prob` | 0.85 |  | 탄 회피 성공 확률 |
| `bot_skill.expert.aim_error_deg` | 1.5 | ° | 조준 오차(표준편차) |
| `bot_skill.expert.decision_period` | 0.1 | s | 판단 주기 |
| `bot_skill.expert.tactic_prob` | 0.95 |  | 전술 행동 선택 확률 |
| `bot_skill.expert.telegraph_dodge_prob` | 0.95 |  | 텔레그래프 공격 회피 확률 |
| `progression_assumption.description` | 평균 플레이어가 각 챕터 진입 시 보유한 공용 모듈 레벨(트리당). 시뮬레이션에만 쓰는 가정값. |  | 설명 |
| `progression_assumption.levels_by_chapter` | `[0, 1, 2, 3, 4, 5]` |  | 챕터 진입 시 트리당 레벨 |
| `progression_assumption.hp_per_level` | 6 |  | 레벨당 HP |
| `progression_assumption.dmg_mult_per_level` | 0.025 |  | 레벨당 피해 배율 |
| `progression_assumption.dash_cd_mult_per_level` | -0.03 |  | 레벨당 대시 재사용 배율 |
| `progression_assumption.ammo_mult_per_level` | 0.04 |  | 레벨당 탄약 배율 |
| `progression_assumption.charges_per_level` | 0.3 |  | 레벨당 차지 |
| `skill_growth_per_chapter` | 0.03 |  | 챕터당 회피 확률 성장 (시뮬 전용) |
