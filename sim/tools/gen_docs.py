#!/usr/bin/env python3
"""Generate docs/StageDesign.md, docs/Parameters.md and docs/Balance.md from sim/params.json, sim/stages.json
and the final result files in sim/results/. Hand-written prose lives in this script's TEXT dicts; numbers come from data."""
import json
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'sim'))
from roomsim.params import load_params  # noqa: E402

DATE = '2026-11-05'
CHARS = ['trigger', 'knuckle', 'edge']
CHAR_KO = {'trigger': '트리거', 'knuckle': '너클', 'edge': '엣지'}
SKILL_KO = {'novice': '입문', 'average': '평균', 'expert': '숙련'}
TYPE_KO = {'combat': '전투', 'rescue': '구출', 'rush': '돌파', 'defend': '수비', 'bug': '오류 방', 'boss': '보스', 'service': '정비'}
SIZE_KO = {'standard': '기본 20×11', 'large': '대형 30×16', 'corridor': '통로 44×9'}
MOD_KO = {'tpose': 'T포즈(접근 시 각성)', 'mixed': '혼합 데이터셋', 'deletion_wall': '삭제 벽'}
PATTERN_KO = {'charge': '돌진', 'fan': '부채꼴 탄막', 'ring': '원형 탄막', 'aoe': '지점 장판', 'aoe_self': '자기 중심 장판',
              'beam': '빔', 'sweep': '스윕(가로 띠)', 'summon': '소환', 'land': '착지(근접 창)'}


def load_json(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def agg_of(path):
    if not os.path.exists(path):
        return {}
    raw = load_json(path)['aggregate']
    out = {}
    for k, v in raw.items():
        ch, room, char, skill = k.split('|')
        out[(int(ch), room, char, skill)] = v
    return out


def wave_str(w):
    return ' + '.join('%s×%d' % (ENEMY_KO.get(k, k), v) for k, v in w.items())


# ---------------------------------------------------------------- texts
CHAPTER_TEXT = {
    1: "훈련장의 첫 코스. 연구진은 친절하고 방은 깨끗하다. 사격·대시·칩 픽업·구출·오버라이드·보스까지 게임의 모든 동사를 7개 방 안에서 한 번씩 가르친다. 적은 더미 보병 4종뿐이며 숫자로만 압박한다.",
    2: "군사 기지. 거리를 벌리는 적(슈터·폭탄병)이 처음 등장해 '움직이며 싸우기'를 강제한다. 첫 수비 방, 첫 중간보스(헬기), 첫 전차가 있다. 메탈슬러그 오마주인 장갑 열차가 챕터를 닫는다.",
    3: "오염된 데이터셋. 밤, 떼, 광역의 가치. 변이체(브루트)와 좀비 떼가 근접 압박을 만들고, 플레임·레이저 칩이 처음 등장한다. 오류 방(T포즈)이 처음 나와 '시뮬레이터가 이상하다'는 신호를 준다.",
    4: "레거시 빌드. 구버전 시뮬레이션의 중세 데이터. 궁수의 느린 화살은 엣지의 반사 연습이고, 기사의 방패는 트리거에게 '정면으로는 안 뚫린다'를 가르친다. 디버거가 처음 등장해 2막의 긴장을 연다.",
    5: "격리 구역. 연구진이 삭제 절차를 시작한 뒤의 코스. 드론·레이저 센트리·디버거가 상시 등장하고 삭제 벽이 뒤에서 밀려온다. 혼합 방에서 모든 데이터셋이 뒤섞이며, 소환형 보스 컴파일러가 막는다.",
    6: "룸 제로. 시뮬레이션 안에 재현된 연구소. 1챕터의 재현으로 시작해 모든 챕터의 적이 섞여 돌아온다. 유닛 06을 구출하고, 디버거 전초를 뚫고, 감시자를 쓰러뜨리면 마지막 문이 열린다. 문 밖은 더 큰 사각형이다.",
}
BOSS_TEXT = {
    'bulldozer': "첫 보스. 돌진 뒤 3초 경직이 접근 창이다. 부채꼴·원형 탄막은 보스 표면 1.5 m 안에서는 무장되지 않으므로(포탑 사각) 근접 캐릭터는 밀착이 정답이고, 돌진만 옆으로 피하면 된다.",
    'heli': "중간보스. 공중에 떠서 근접 공격이 닿지 않는다. 착지 패턴(3.5초)이 순환에 두 번 들어 있어 근접 창이 주기적으로 온다. 너클은 적을 던져 공중의 헬기를 맞힐 수 있다.",
    'armored_train': "레일 위의 고정 보스. 스윕(가로 띠)은 잠금 시점의 플레이어 y 주변을 치므로 세로로 빠져야 한다. 스윕 뒤 3초 정지가 접근 창. 소환된 라이플이 근접 캐릭터를 노리므로 체력이 낮으면 소환물을 먼저 정리한다.",
    'cluster': "근접형 보스. 돌진과 자기 중심 슬램이 주 피해원이고, 침 뱉기는 반사 가능하다. 좀비 소환은 4회로 제한. 2페이즈(50%)부터 1.3배 빨라진다.",
    'block_golem': "장판형 보스. 떨어지는 블록(지점 장판 4개)은 '빈 곳을 찾아 빠지는' 회피가 필요하다. 돌진은 느리지만 몸집이 커서 옆으로 멀리 피해야 한다. 궁수 소환 3회. 3페이즈로 갈수록 빨라진다.",
    'compiler': "소환형 고정 보스. 드론 2기씩 최대 6회, 2페이즈에 디버거 1기. 빔은 반사 불가. 소환물을 먼저 처리할지 코어를 칠지가 선택이며, 시뮬레이션에서는 트리거가 소환물에 시간을 쓰는 편이 안전했다.",
    'overseer': "최종 보스. 앞선 보스의 패턴을 모두 쓴다. 3페이즈(66%·33%)마다 속도가 오르고 휴식이 짧아진다. 3페이즈에서 디버거 1기 + 드론 2기를 한 번 소환. 돌진 피해가 가장 큰 단일 위협이다.",
}
ENEMY_KO = {}


def intro_matrix(S, P):
    first = {}
    for c in S['chapters']:
        for r in c['rooms']:
            if r['type'] == 'service':
                continue
            names = set()
            for w in r.get('waves', []):
                names |= set(w)
            if 'spawn_wave' in r:
                names |= set(r['spawn_wave'])
            if 'late_add' in r:
                names |= set(r['late_add']['wave'])
            if 'adds' in r:
                names |= set(r['adds'])
            for n in names:
                first.setdefault(n, r['id'])
    return first


# ---------------------------------------------------------------- StageDesign
def gen_stage_design(S, P, agg):
    L = []
    L.append('# ROOM ZERO — 전체 챕터·스테이지 설계')
    L.append('')
    L.append('> 작성일: %s · 데이터 버전: stages.json %s / params.json %s' % (DATE, S['meta']['version'], P['meta']['version']))
    L.append('> 이 문서는 `sim/tools/gen_docs.py`가 `sim/stages.json`과 `sim/params.json`에서 생성한다. 숫자를 고치려면 JSON을 고치고 다시 생성한다.')
    L.append('> 플레이 시간과 사망률은 `sim/results/final_normal.json`(평균 숙련, 보통 난이도)의 시뮬레이션 값이다.')
    L.append('')
    L.append('## 0. 설계 문법')
    L.append('')
    g = P['global']
    sp = g['spawn']
    L.append('- **방 크기**: 기본 %g×%g m(한 화면, 카메라 고정) · 대형 %g×%g m(보스·혼합 방, 카메라 팔로우) · 통로 %g×%g m(돌파 방, 카메라 팔로우).' % tuple(g['room_sizes']['standard'] + g['room_sizes']['large'] + g['room_sizes']['corridor']))
    L.append('- **진행 방향**: 입구 왼쪽 벽, 출구 오른쪽 벽. 플레이어는 (2, H/2)에서 시작한다.')
    L.append('- **웨이브 규칙**: 한 웨이브의 적은 첫 1기 즉시, 나머지는 %g초 간격으로 벽에서 컴파일된다(스폰 텔레그래프 %g초, 플레이어로부터 최소 %g m). 생존 적이 %d 이하가 되면 %g초 뒤 다음 웨이브. 화면 내 동시 적 최대 %d.' % (sp['stagger'], sp['telegraph_time'], sp['min_distance_from_player'], sp['next_wave_when_alive_leq'], sp['wave_gap'], sp['max_concurrent']))
    L.append('- **상자와 차지**: 방마다 칩 상자 0~2개, 차지 픽업 0~3개. 상자 칩은 세 교리가 모두 쓸 수 있는 공용 엔티티이고, 그 방에서 가장 약한 교리를 돕는 칩을 고른다(예: 떼 방에는 S).')
    L.append('- **칩 등장 일정**: 1~2챕터 H·S·R, 3챕터부터 F·L, 5챕터부터 C. 드롭 풀도 같은 일정을 따른다.')
    L.append('- **파(par)**: 숙련 봇 클리어 시간 중앙값(세 교리 중앙값)의 1.15배를 5초 단위로 올림. 수비 방은 방어 시간, 돌파 방은 1.2배. S등급은 파 이내 + 순 체력 손실 15% 이하.')
    L.append('- **세 교리 검증**: 모든 방은 세 캐릭터로 각각 시뮬레이션한다. 거리 벌리기 적(슈터·폭탄병·궁수·마법사)은 웨이브 총원의 1/3 이하, 너클이 던질 수 있는 적이 방마다 있어야 하며, 반사 불가 투사체(빔)는 보라색으로 구분한다.')
    L.append('- **보스 공통 규칙**: 부채꼴·원형 탄막은 보스 표면 1.5 m 안에서 무장되지 않는다(포탑 사각). 돌진은 텔레그래프 1.3초, 방향 잠금은 텔레그래프의 35~50% 시점. 모든 보스에 근접 접근 창(돌진 후 경직, 착지, 스윕 후 정지)이 있다.')
    L.append('')
    # overview
    L.append('## 1. 전체 구조')
    L.append('')
    L.append('| 챕터 | 코드 | 이름 | 테마(에셋) | 막 | 방 수 | 시뮬 전투 시간(평균 숙련) | 예상 플레이 시간 |')
    L.append('|---|---|---|---|---|---|---|---|')
    total_rooms = 0
    total_time = 0.0
    for c in S['chapters']:
        rooms = c['rooms']
        sim_rooms = [r for r in rooms if r['type'] != 'service']
        t = 0.0
        for r in sim_rooms:
            ts = [agg[(c['chapter'], r['id'], ch, 'average')]['time_mean'] for ch in CHARS if (c['chapter'], r['id'], ch, 'average') in agg]
            t += statistics.fmean(ts) if ts else r.get('par', 40)
        play = t + len(rooms) * P['global']['door_transition_time'] + 45.0  # service room + rescue/UI
        total_rooms += len(rooms)
        total_time += play
        L.append('| %d | %s | %s | %s | %d막 | %d | %d초 | 약 %.1f분 |' % (c['chapter'], c['code'], c['name'], c['theme'], c['act'], len(rooms), round(t), play / 60.0))
    L.append('')
    L.append('합계: %d개 방, 초회 클리어 약 %.0f분(사망·재시도 제외). 세 교리로 각각 클리어하면 약 %.0f분.' % (total_rooms, total_time / 60.0, 3 * total_time / 60.0))
    L.append('')
    # per chapter
    L.append('## 2. 챕터별 상세')
    L.append('')
    for c in S['chapters']:
        L.append('### 챕터 %d · 코스 %s 「%s」' % (c['chapter'], c['code'], c['name']))
        L.append('')
        L.append(CHAPTER_TEXT[c['chapter']])
        L.append('')
        L.append('| 방 | 타입 | 크기 | 파 | 웨이브 구성 | 상자 / 차지 | 특수 | 의도 | 시뮬 시간 · 사망률 (트/너/엣) |')
        L.append('|---|---|---|---|---|---|---|---|---|')
        for r in c['rooms']:
            if r['type'] == 'service':
                L.append('| %s | 정비 | - | - | - | - | 모듈 1택 · HP 회복 · 캐릭터 교체 · 체크포인트 | %s | - |' % (r['id'], r['intent']))
                continue
            if r['type'] == 'boss':
                b = P['bosses'][r['boss']]
                waves = '보스 %s (HP %d)' % (b['display'], b['hp']) + ((' + 초기 ' + wave_str(r['adds'])) if r.get('adds') else '')
            elif r['type'] in ('defend',):
                waves = '%g초마다 %s' % (r['spawn_every'], wave_str(r['spawn_wave']))
                la = r.get('late_add')
                if la:
                    waves += ' · %g초 후 %s (스폰 %d회마다, 최대 %d회)' % (la['after'], wave_str(la['wave']), la.get('every', 2), la.get('max', 3))
                waves += ' · 노드 HP %d · %g초 방어' % (r['node_hp'], r['duration'])
            elif r['type'] == 'rush':
                waves = '%g초마다 전방에 %s · 제한 %g초' % (r['spawn_every'], wave_str(r['spawn_wave']), r['time_limit'])
            else:
                waves = ' → '.join('[%s]' % wave_str(w) for w in r['waves'])
            crates = ', '.join(r.get('crates', [])) or '-'
            if r.get('charges'):
                crates += ' / 차지 %d' % r['charges']
            special = []
            if r.get('rescue'):
                special.append('구출')
            if r.get('modifier'):
                special.append(MOD_KO.get(r['modifier'], r['modifier']))
            if r.get('midboss'):
                special.append('중간보스')
            if r.get('elite'):
                special.append('정예')
            if r.get('mixed'):
                special.append('혼합')
            stats = []
            for ch in CHARS:
                a = agg.get((c['chapter'], r['id'], ch, 'average'))
                stats.append('%ds·%d%%' % (round(a['time_mean']), round(a['death'] * 100)) if a else '-')
            L.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
                r['id'], TYPE_KO[r['type']], SIZE_KO.get(r.get('size', 'standard'), r.get('size')), r.get('par', '-'), waves, crates,
                ' · '.join(special) or '-', r['intent'], ' / '.join(stats)))
        L.append('')
        # boss detail
        for r in c['rooms']:
            if r['type'] != 'boss':
                continue
            b = P['bosses'][r['boss']]
            L.append('**보스 「%s」 (%s)** — HP %d · 반경 %g m · 이동 %g m/s · 접촉 피해 %d · 휴식 %g초 · 파 %d초' % (
                b['display'], r['id'], b['hp'], b['radius'], b.get('speed', 0), b.get('contact_damage', 0), b['rest'], r['par']))
            L.append('')
            L.append(BOSS_TEXT.get(r['boss'], ''))
            L.append('')
            L.append('| 페이즈 | 진입 HP | 속도 배율 | 휴식 | 추가 패턴 |')
            L.append('|---|---|---|---|---|')
            for i, ph in enumerate(b['phases']):
                L.append('| %d | %d%% | ×%g | %s | %s |' % (i + 1, round(ph['hp_frac'] * 100), ph.get('speed_mult', 1.0), ph.get('rest', b['rest']), ', '.join(ph.get('add_patterns', [])) or '-'))
            L.append('')
            L.append('| 패턴 | 종류 | 수치 |')
            L.append('|---|---|---|')
            for pn, pd in b['pattern_defs'].items():
                t = pd['type']
                if t == 'charge':
                    desc = '텔레그래프 %g초, 잠금 %d%% 시점, 속도 %g m/s, 피해 %d, 최대 %g m, 후 경직 %g초' % (pd['telegraph'], round(pd.get('lock_frac', 0.5) * 100), pd['dash_speed'], pd['damage'], pd.get('max_distance', 12), pd.get('post_rest', b['rest']))
                elif t in ('fan', 'ring'):
                    desc = '텔레그래프 %g초, 탄 %d개%s, 피해 %d, 탄속 %g m/s, 무장 거리 %g m, 반사 %s' % (pd['telegraph'], pd['count'], (' / %g°' % pd['spread_deg']) if t == 'fan' else '', pd['damage'], pd['proj_speed'], pd.get('arm', 1.5), '가능' if pd.get('reflectable', True) else '불가')
                elif t == 'aoe':
                    desc = '텔레그래프 %g초, 장판 %d개(반경 %g m, 산포 ±%g m), 피해 %d' % (pd['telegraph'], pd['count'], pd['radius'], pd['scatter'], pd['damage'])
                elif t == 'aoe_self':
                    desc = '텔레그래프 %g초, 반경 %g m + 보스 반경, 피해 %d' % (pd['telegraph'], pd['radius'], pd['damage'])
                elif t == 'beam':
                    desc = '텔레그래프 %g초, 잠금 %g초, 길이 %g m, 폭 %g m, 피해 %d, 반사 불가' % (pd['telegraph'], pd['lock_at'], pd['length'], pd['width'], pd['damage'])
                elif t == 'sweep':
                    desc = '텔레그래프 %g초(40%% 시점 y 잠금), 반폭 %g m, 피해 %d, 후 정지 %g초' % (pd['telegraph'], pd['half_width'], pd['damage'], pd.get('post_rest', b['rest']))
                elif t == 'summon':
                    desc = '텔레그래프 %g초, %s, 최대 %s회' % (pd['telegraph'], wave_str(pd['enemies']), pd.get('max_uses', '제한 없음'))
                elif t == 'land':
                    desc = '텔레그래프 %g초, %g초 착지(근접 가능)' % (pd['telegraph'], pd['duration'])
                else:
                    desc = json.dumps(pd, ensure_ascii=False)
                L.append('| %s | %s | %s |' % (pn, PATTERN_KO.get(t, t), desc))
            L.append('')
    # enemy intro schedule
    L.append('## 3. 적 등장 일정')
    L.append('')
    first = intro_matrix(S, P)
    L.append('| 적 | 첫 등장 방 | 역할 | 세 교리 대응 |')
    L.append('|---|---|---|---|')
    ROLE = {
        'rifle': ('기본 보병, 8 m에서 멈춰 3점사', '트리거 기준 적. 너클은 던지기 재료, 엣지는 반사 연습'),
        'rusher': ('근접 돌진', '트리거는 자동 나이프, 근접 교리에겐 먹이'),
        'shielder': ('전면 방패(내구 60, 깨지면 3초 개방)', '트리거는 방패를 깨거나 측면, 너클은 잡아 던짐, 엣지는 섬광 베기로 통과'),
        'sentry': ('고정 터렛, 1.5초 스트림', '트리거는 우선 제거, 너클은 체력 50% 이하일 때 뜯어 휴대'),
        'shooter': ('9~14 m 저격, 조준선 1.2초', '엣지는 반사로 역살, 너클은 차지 대시 접근'),
        'bomber': ('장판 투척', '텔레그래프 회피. 너클 슬램이 투사체 삭제'),
        'zombie': ('느리고 많은 러셔', '광역 칩과 던지기의 가치'),
        'brute': ('정예 근접, 넉백 저항', '던질 수 없음. 윈드업 0.8초를 읽고 빠진다'),
        'knight': ('방패 보병(내구 90)', '쉴더와 같되 단단함'),
        'archer': ('느린 화살 단발', '엣지 반사 최적. 트리거는 거리 유지'),
        'mage': ('느린 광역 구체', '장판 회피'),
        'drone': ('비행 러셔, 던질 수 없음', '트리거 자동 나이프, 엣지 섬광 베기'),
        'laser_sentry': ('빔 터렛, 반사 불가', '잠금 0.5초 뒤 옆으로'),
        'debugger': ('순간이동 + 빔(반사 불가)', '순간이동 직후 0.6초 무방비 창에 근접 교리가 달려든다'),
        'apc': ('장갑차, 25% 이하 기절 6초', '오버라이드 대상'),
        'tank': ('전차, 포격 장판 + 기관총', '오버라이드 대상. 포격은 텔레그래프 1초'),
    }
    for name, spec in P['enemies'].items():
        role = ROLE.get(name, ('', ''))
        L.append('| %s (%s) | %s | %s | %s |' % (spec.get('display', name), name, first.get(name, '-'), role[0], role[1]))
    L.append('')
    L.append('## 4. 특수 방 규칙')
    L.append('')
    rr = P['global']['room_rules']
    L.append('- **수비**: 노드는 방 중앙, 반경 %g m. 근접 적은 노드와 플레이어 중 가까운 쪽을 노리고, 원거리 적은 플레이어를 쏜다. 노드 HP가 절반 이상이면 플레이어는 노드에서 6 m까지 벗어나도 되고, 절반 아래면 2.5 m 안에 붙어야 한다. 노드 파괴는 방 재시작이며 인스턴스를 잃지 않는다.' % rr['defend_node_radius'])
    L.append('- **돌파**: 통로 44×9 m. 적은 플레이어 앞 6~14 m 지점의 벽에서 스폰된다. 제한 시간 초과는 방 재시작. 삭제 벽이 있는 방에서는 벽이 %g m/s로 따라오며 벽 안에 있으면 초당 %g 피해.' % (rr['deletion_wall']['speed'], rr['deletion_wall']['dps']))
    L.append('- **오류 방(T포즈)**: 모든 웨이브가 처음부터 방 안에 서 있다. %g m 안으로 접근하거나 피격되면 깨어나고, 깨어난 적 주변 %g m의 적도 함께 깬다. 멀리서 쏘면 한 기씩 깨울 수 있다.' % (rr['tpose_wake_range'], rr['tpose_chain_range']))
    L.append('- **오류 방(혼합)**: 시뮬레이터 고장 연출. 다른 챕터의 적 데이터셋이 섞여 나온다. 규칙 변화는 없고 조합만 바뀐다.')
    L.append('- **구출**: 구출 대상 해제에 %g초. 보상은 칩 %d%% / 차지 %d%% / 메모리 %d%%.' % (rr['rescue_interaction_time'], P['global']['pickups']['rescue_reward']['chip'] * 100, P['global']['pickups']['rescue_reward']['charges'] * 100, P['global']['pickups']['rescue_reward']['memory'] * 100))
    L.append('')
    return '\n'.join(L)


# ---------------------------------------------------------------- Parameters
DESC = {
    'sim_dt': '시뮬레이션 틱 간격 (시뮬 전용)', 'max_room_time': '방 최대 시간(초과 시 실패 처리)', 'room_sizes': '방 크기 [가로, 세로]', 'door_transition_time': '문 전환(컴파일 연출) 시간',
    'telegraph_time': '스폰 텔레그래프(조립 연출) 시간. 이 동안 무적·비활성', 'min_distance_from_player': '스폰 지점의 플레이어 최소 거리', 'next_wave_when_alive_leq': '다음 웨이브 조건: 생존 적 수 이하',
    'wave_gap': '웨이브 조건 충족 후 다음 웨이브까지 지연', 'max_concurrent': '동시 존재 적 최대(초과분은 대기열)', 'stagger': '웨이브 내 적 간 스폰 간격',
    'hitbox_radius': '플레이어 피격 반경', 'pickup_radius': '픽업 획득 반경', 'hit_iframes': '피격 후 무적(글리치) 시간', 'charges_max': '차지 최대 보유', 'charges_start': '스테이지 시작 차지',
    'instances_per_stage': '스테이지당 인스턴스(목숨)', 'override_min_enemy_distance': '오버라이드 시도 시 주변 적 허용 거리(봇 판단)',
    'chip_drop_chance': '처치 시 칩 드롭 확률(티어별)', 'charge_drop_chance': '처치 시 차지 드롭 확률(티어별)', 'rescue_reward': '구출 보상 확률 분포', 'rescue_charges': '구출 보상이 차지일 때 개수',
    'grades': '등급 기준: 파 배율 이내 + 순 체력 손실 비율 이하', 'time_mult': '파 배율', 'damage_frac': '허용 순 체력 손실 비율',
    'enemy_hp_mult': '챕터별 적 HP 배율', 'enemy_dmg_mult': '챕터별 적 피해 배율', 'enemy_speed_mult': '챕터별 적 속도 배율',
    'assist': '어시스트 난이도', 'normal': '보통', 'hard': '하드', 'arcade': '아케이드(인스턴스 1, 모듈 비활성)', 'instances': '인스턴스 수', 'auto_target': '자동 타겟 기본값', 'modules_disabled': '모듈 비활성',
    'tpose_wake_range': 'T포즈 적 각성 거리', 'tpose_chain_range': '각성 연쇄 거리', 'deletion_wall': '삭제 벽 속도·초당 피해', 'speed': '속도', 'dps': '초당 피해', 'defend_node_radius': '수비 노드 반경', 'rescue_interaction_time': '구출 상호작용 시간',
    'display': '표시 이름', 'hp': '체력', 'move_speed': '이동 속도', 'attack_move_mult': '공격 중 이동 속도 배율', 'basic': '기본 공격', 'kind': '종류', 'damage': '피해', 'damages': '콤보 타별 피해', 'interval': '공격 간격',
    'proj_speed': '투사체 속도', 'range': '사거리', 'spread_deg': '탄 퍼짐(각도)', 'pellets': '발당 탄 수', 'melee_auto': '밀착 시 자동 근접', 'dash': '대시', 'distance': '거리', 'duration': '지속 시간', 'iframes': '무적 시간', 'cooldown': '재사용 대기',
    'super_armor': '슈퍼아머(경직 없음)', 'pass_through': '적 통과', 'skill': '스킬(차지 소비)', 'radius': '반경', 'flight': '비행(도달) 시간', 'cast': '시전 시간', 'passive': '패시브', 'chip_ammo_mult': '칩 탄약 배율', 'last_mag_frac': '마지막 탄창 비율',
    'last_mag_dmg_mult': '마지막 탄창 피해 배율', 'override': '오버라이드', 'time': '홀드 시간', 'arc_deg': '공격 각도', 'knockback_last': '마지막 타 넉백 거리', 'dmg_reduction': '피해 감소율', 'combo_reset': '콤보 유지 시간', 'hold': '홀드 공격',
    'grab_time': '잡기 시간', 'throw_speed': '투척 속도', 'throw_damage': '투척체 피해', 'wall_kill': '벽 충돌 시 일반 적 즉사', 'wall_damage': '벽 충돌 피해(정예)', 'throw_range': '투척 거리', 'land_knockdown': '착지 다운 시간', 'knockdown': '다운 시간',
    'wall_slam_bonus': '벽 밀어붙이기 추가 피해', 'wall_slam_range': '벽 판정 거리', 'clears_projectiles': '적 투사체 삭제', 'heal_on_melee_kill': '근접 처치 시 회복', 'carry_sentry': '센트리 휴대 가능', 'carry_shots': '휴대 센트리 탄 수', 'carry_speed_mult': '휴대 중 이동 배율',
    'carry_hp_frac': '휴대 가능 센트리 HP 비율', 'carry_dmg_mult': '휴대 센트리 피해 배율', 'carry_interval': '휴대 센트리 발사 간격', 'carry_time': '센트리 탈취 홀드 시간', 'step': '타격 시 전진 거리', 'reflect': '반사 가능', 'reflect_dmg_mult': '반사탄 피해 배율',
    'active_frames': '반사 판정 유효 시간(타당)', 'lunge_if_farther_than': '전진 스텝 조건(사거리 비율)', 'charge': '차지 시간', 'length': '길이', 'width': '폭', 'pierce': '관통', 'counter_window': '카운터 판정 시간(대시 직후)', 'counter_damage': '카운터 피해', 'counter_range': '카운터 반격 거리',
    'ammo': '탄약', 'hits': '타격 횟수(근접 교리 칩)', 'knockback': '넉백 거리', 'homing': '유도', 'aoe_radius': '폭발 반경', 'burn_dps': '화상 초당 피해', 'burn_time': '화상 시간', 'extra_ranged': '타격마다 추가 투사체', 'attack_speed_mult': '공격 속도 배율',
    'per_hit_wave': '타격마다 검기', 'hit_aoe': '타격 시 광역', 'range_mult': '사거리 배율', 'hold_replace': '홀드 공격 대체', 'dash_explosion': '대시 종료 폭발', 'dash_cooldown_mult': '대시 재사용 배율', 'ground_fire': '타격 지점 화염', 'fire_trail': '베기 궤적 화염', 'orbitals': '떠다니는 보조 무기',
    'count': '개수', 'tier': '티어(드롭·투척 규칙)', 'behavior': '행동 유형', 'stop_range': '접근 정지 거리', 'fire_range': '사격 거리', 'retreat_range': '후퇴 거리', 'attack': '공격', 'telegraph': '텔레그래프(예고) 시간', 'burst': '점사 탄 수', 'burst_gap': '점사 간격',
    'throwable': '너클 투척 가능', 'reflectable': '엣지 반사 가능', 'score': '점수', 'spawn_cost': '스폰 예산 비용', 'windup': '근접 윈드업', 'hit_range': '근접 판정 거리', 'shield_arc_deg': '방패 보호 각도', 'shield_hp': '방패 내구', 'shield_down_time': '방패 파괴 후 개방 시간',
    'turn_rate_deg': '회전 속도(도/초)', 'aim_tolerance_deg': '사격 허용 각도', 'stream_time': '스트림 지속', 'shot_gap': '스트림 발사 간격', 'overridable': '오버라이드 가능', 'min_range': '유지 최소 거리', 'max_range': '유지 최대 거리', 'lock_at': '조준 잠금 시점', 'reposition': '사격 후 재배치 거리',
    'knockback_resist': '넉백·다운 저항', 'flying': '비행(지상 근접 불가)', 'beam_length': '빔 길이', 'beam_width': '빔 폭', 'teleport_every': '순간이동 주기', 'teleport_range': '순간이동 거리 범위', 'materialize': '순간이동 후 무방비 시간', 'stun_hp_frac': '기절 진입 HP 비율', 'stun_time': '기절 시간',
    'pilot': '탑승 시 성능', 'gun': '주포', 'sub': '부무장', 'cannon': '포격', 'base': '상속 원본', 'chapter': '등장 챕터', 'contact_damage': '접촉 피해(밀고 들어올 때)', 'rest': '패턴 간 휴식', 'par': '파 시간', 'phases': '페이즈', 'hp_frac': '진입 HP 비율', 'speed_mult': '속도 배율', 'add_patterns': '추가 패턴',
    'patterns': '패턴 순환 목록', 'pattern_defs': '패턴 정의', 'keep_range': '유지 거리(비행 보스)', 'type': '패턴 종류', 'dash_speed': '돌진 속도', 'post_rest': '패턴 후 경직', 'max_distance': '돌진 최대 거리', 'lock_frac': '방향 잠금 시점(텔레그래프 비율)', 'scatter': '장판 산포', 'half_width': '스윕 반폭', 'enemies': '소환 구성', 'max_uses': '최대 사용 횟수', 'arm': '무장 거리',
    'memory_per_room': '방 타입별 메모리 조각', 'grade_bonus_mult': '등급 보너스 배율', 'rescue_memory': '구출 메모리', 'modules': '공용 모듈 트리', 'mastery': '교리 숙련', 'levels': '최대 레벨', 'cost_base': '1레벨 비용', 'cost_growth': '레벨당 비용 증가율',
    'dash_cooldown_mult_per_level': '레벨당 대시 재사용 배율', 'dash_distance_per_level': '레벨당 대시 거리', 'move_speed_per_level': '레벨당 이동 속도', 'chip_ammo_mult_per_level': '레벨당 칩 탄약 배율', 'charges_max_per_level': '레벨당 차지 최대', 'basic_damage_mult_per_level': '레벨당 기본 피해 배율',
    'hp_per_level': '레벨당 HP', 'instances_at_levels': '인스턴스 +1 레벨', 'hit_iframes_per_level': '레벨당 피격 무적', 'pistol_interval_mult_per_level': '레벨당 권총 간격 배율', 'grenade_radius_per_level': '레벨당 수류탄 반경', 'knife_damage_per_level': '레벨당 나이프 피해',
    'throw_range_per_level': '레벨당 투척 거리', 'combo3_damage_per_level': '레벨당 3타 피해', 'heal_per_level': '레벨당 회복', 'reflect_mult_per_level': '레벨당 반사 배율', 'counter_window_per_level': '레벨당 카운터 판정', 'wave_range_per_level': '레벨당 참격파 사거리',
    'bot_skill': '봇 숙련도 프로필 (시뮬 전용)', 'reaction': '반응 시간', 'dodge_prob': '탄 회피 성공 확률', 'telegraph_dodge_prob': '텔레그래프 공격 회피 확률', 'aim_error_deg': '조준 오차(표준편차)', 'decision_period': '판단 주기', 'tactic_prob': '전술 행동 선택 확률',
    'progression_assumption': '챕터별 보유 모듈 가정 (시뮬 전용)', 'levels_by_chapter': '챕터 진입 시 트리당 레벨', 'dmg_mult_per_level': '레벨당 피해 배율', 'dash_cd_mult_per_level': '레벨당 대시 재사용 배율', 'ammo_mult_per_level': '레벨당 탄약 배율', 'charges_per_level': '레벨당 차지', 'skill_growth_per_chapter': '챕터당 회피 확률 성장 (시뮬 전용)',
    'description': '설명', 'version': '버전', 'units': '단위',
}
UNIT = {'speed': 'm/s', 'move_speed': 'm/s', 'proj_speed': 'm/s', 'dash_speed': 'm/s', 'throw_speed': 'm/s', 'range': 'm', 'distance': 'm', 'radius': 'm', 'hitbox_radius': 'm', 'pickup_radius': 'm', 'stop_range': 'm', 'fire_range': 'm',
        'retreat_range': 'm', 'hit_range': 'm', 'min_range': 'm', 'max_range': 'm', 'throw_range': 'm', 'length': 'm', 'width': 'm', 'beam_length': 'm', 'beam_width': 'm', 'aoe_radius': 'm', 'step': 'm', 'knockback': 'm', 'knockback_last': 'm',
        'interval': 's', 'cooldown': 's', 'duration': 's', 'iframes': 's', 'telegraph': 's', 'windup': 's', 'cast': 's', 'flight': 's', 'grab_time': 's', 'charge': 's', 'rest': 's', 'post_rest': 's', 'lock_at': 's', 'stream_time': 's', 'shot_gap': 's',
        'burst_gap': 's', 'teleport_every': 's', 'materialize': 's', 'stun_time': 's', 'combo_reset': 's', 'active_frames': 's', 'counter_window': 's', 'hit_iframes': 's', 'telegraph_time': 's', 'wave_gap': 's', 'stagger': 's', 'time': 's', 'par': 's',
        'knockdown': 's', 'land_knockdown': 's', 'burn_time': 's', 'shield_down_time': 's', 'reaction': 's', 'decision_period': 's', 'door_transition_time': 's', 'max_room_time': 's', 'carry_time': 's', 'carry_interval': 's',
        'arc_deg': '°', 'spread_deg': '°', 'shield_arc_deg': '°', 'turn_rate_deg': '°/s', 'aim_tolerance_deg': '°', 'aim_error_deg': '°', 'hp': 'HP', 'damage': 'HP', 'damages': 'HP', 'shield_hp': 'HP', 'counter_damage': 'HP', 'throw_damage': 'HP', 'wall_damage': 'HP',
        'burn_dps': 'HP/s', 'dps': 'HP/s', 'heal_on_melee_kill': 'HP', 'contact_damage': 'HP', 'ammo': '발', 'hits': '타', 'carry_shots': '발'}


def fmt(v):
    if isinstance(v, bool):
        return 'O' if v else 'X'
    if isinstance(v, float):
        return ('%g' % v)
    if isinstance(v, (list, dict)):
        return '`' + json.dumps(v, ensure_ascii=False) + '`'
    return str(v)


def rows(obj, prefix=''):
    out = []
    for k, v in obj.items():
        if isinstance(v, dict) and k not in ('room_sizes', 'chip_drop_chance', 'charge_drop_chance', 'rescue_reward', 'teleport_range', 'enemies'):
            out += rows(v, prefix + k + '.')
        else:
            out.append((prefix + k, v))
    return out


def table(obj, prefix=''):
    L = ['| 키 | 값 | 단위 | 설명 |', '|---|---|---|---|']
    for k, v in rows(obj, prefix):
        leaf = k.split('.')[-1]
        L.append('| `%s` | %s | %s | %s |' % (k, fmt(v), UNIT.get(leaf, ''), DESC.get(leaf, DESC.get(k.split('.')[-2] if '.' in k else '', '-'))))
    return '\n'.join(L)


def gen_parameters(P_raw, P):
    L = ['# ROOM ZERO — 밸런스 파라미터 목록', '',
         '> 작성일: %s · params.json %s' % (DATE, P['meta']['version']),
         '> 단일 소스는 `sim/params.json`이다. 이 문서는 `sim/tools/gen_docs.py`가 거기서 생성한다. 값은 시뮬레이션으로 조정한 현재 값이며, 실제 빌드에서 플레이테스트로 다시 검증해야 한다.',
         '> 단위: 길이 m, 시간 s, 각도 °, 피해 HP. 적 수치는 1챕터 기준이며 `chapter_scaling`과 난이도 배율이 곱해진다.', '',
         '## 0. 구조와 Unity 매핑 제안', '',
         '| 섹션 | 내용 | Unity 제안 |', '|---|---|---|',
         '| `global` | 방·스폰·픽업·등급·챕터 배율·난이도·특수 방 규칙 | `GlobalBalanceConfig` ScriptableObject 1개 |',
         '| `characters` | 세 교리의 기본 공격·홀드·대시·스킬·패시브·오버라이드 | `DoctrineData` ScriptableObject ×3. 플레이어 컨트롤러는 하나 |',
         '| `chips` | 칩 6종 × 교리 3종 변환표 | `ChipData` ×6, 교리별 서브 블록 |',
         '| `enemies` | 적 16종(상속 포함) | `EnemyData` ×16. `base`는 프리팹 베리언트로 |',
         '| `bosses` | 보스 7기, 페이즈·패턴 | `BossData` + `BossPatternData` |',
         '| `progression` | 메모리·모듈·숙련 | `ProgressionData` |',
         '| 시뮬 전용 | `bot_skill`, `progression_assumption`, `skill_growth_per_chapter`, `sim_dt`, `max_room_time` | 게임에 넣지 않는다 |', '']
    g = P_raw['global']
    L += ['## 1. 전역 (`global`)', '']
    sim_only = {'sim_dt', 'max_room_time', 'bot_skill', 'progression_assumption', 'skill_growth_per_chapter'}
    L.append(table({k: v for k, v in g.items() if k not in sim_only}))
    L.append('')
    L += ['## 2. 캐릭터 (`characters`)', '']
    for cid, c in P_raw['characters'].items():
        L.append('### %s (`%s`)' % (c['display'], cid))
        L.append('')
        L.append(table({k: v for k, v in c.items() if k != 'display'}))
        L.append('')
    L += ['## 3. 칩 변환표 (`chips`)', '',
          '같은 칩 픽업을 교리별로 다르게 해석한다. 트리거는 무기 교체, 너클·엣지는 기본 공격 변형이며 소모 단위는 각각 탄약/타격 횟수다.', '']
    for cid, c in P_raw['chips'].items():
        L.append('### %s 「%s」' % (cid, c['display']))
        L.append('')
        for ch in CHARS:
            L.append('**%s**: %s' % (CHAR_KO[ch], ', '.join('%s=%s' % (k, fmt(v)) for k, v in c[ch].items())))
            L.append('')
    L += ['## 4. 적 (`enemies`)', '', '상속(`base`)을 풀어 쓴 값이다. 1챕터 기준.', '']
    for eid, e in P['enemies'].items():
        base = P_raw['enemies'][eid].get('base')
        L.append('### %s (`%s`)%s' % (e.get('display', eid), eid, (' — `%s` 상속' % base) if base else ''))
        L.append('')
        L.append(table({k: v for k, v in e.items() if k not in ('display', 'id')}))
        L.append('')
    L += ['## 5. 보스 (`bosses`)', '', '보스 피해는 챕터 배율을 곱하지 않고 난이도 배율만 곱한다(챕터별로 직접 튠).', '']
    for bid, b in P_raw['bosses'].items():
        L.append('### %s (`%s`)' % (b['display'], bid))
        L.append('')
        L.append(table({k: v for k, v in b.items() if k not in ('display', 'pattern_defs', 'phases', 'patterns')}))
        L.append('')
        L.append('패턴 순환: `%s`' % ', '.join(b['patterns']))
        L.append('')
        L.append('| 페이즈 | 값 |')
        L.append('|---|---|')
        for i, ph in enumerate(b['phases']):
            L.append('| %d | %s |' % (i + 1, fmt(ph)))
        L.append('')
        L.append('| 패턴 | 정의 |')
        L.append('|---|---|')
        for pn, pd in b['pattern_defs'].items():
            L.append('| `%s` | %s |' % (pn, fmt(pd)))
        L.append('')
    L += ['## 6. 성장 (`progression`)', '', table(P_raw['progression']), '']
    L += ['## 7. 시뮬레이션 전용 가정', '', '게임 데이터가 아니다. 봇과 챕터 진입 시점의 성장 가정을 정의한다.', '',
          table({k: g[k] for k in ('sim_dt', 'max_room_time', 'bot_skill', 'progression_assumption', 'skill_growth_per_chapter') if k in g}), '']
    return '\n'.join(L)


# ---------------------------------------------------------------- Balance
TARGETS = [
    ('기본 방 클리어 시간 (평균 숙련)', '초반 20~40초, 후반 30~60초', '방 단위로 보면 대체로 충족. 돌파 방은 8~10초로 짧은 "숨 돌리기"로 둔다'),
    ('보스 전투 시간', '45~90초', '충족 (41~90초)'),
    ('방당 사망률 (평균 숙련, 보통)', '일반 방 ≤15%, 보스 1챕터 ≤10% → 6챕터 ≤35%', '대부분 충족. 예외는 7절'),
    ('스테이지당 기대 인스턴스 손실 (평균 숙련, 보통)', '1챕터 ≤0.4 → 6챕터 ≤2.0 (보유 3)', '충족. 후반이 목표보다 쉬운 편 → 하드가 "의도한 메탈슬러그 난이도"'),
    ('숙련도 표현력', '숙련 사망률 ≤ 평균의 1/2, 입문 ≥ 평균의 2배', '트리거·엣지 충족. 너클은 숙련도에 둔감(탱커 설계)'),
    ('교리 간 균형', '방별 클리어 시간 ±25%, 챕터 사망률 차이 ≤10%p', '시간은 대체로 충족(엣지가 가장 빠름). 사망률은 너클이 가장 안전, 엣지가 빔 방에서 취약'),
    ('칩 가동률', '30~60%', '초반 방은 상자 때문에 80~95%로 높음. 상자 배치를 방 중반으로 옮기는 과제'),
    ('적 아키타입 기여', '등장 방에서 피해 기여 ≥8%', '대체로 충족. 러셔는 트리거 상대로 기여가 낮음(자동 나이프)'),
]
DECISIONS = [
    ('v0.1→0.2', '던져진 적이 리스트에서 빠져 방이 안 끝나던 버그 수정. 보스 접촉 피해를 "밀고 들어올 때만"으로 제한. 웨이브 내 0.4초 간격 스폰 도입. 일반 적 HP 1.5배, 보스 HP 2배. 돌파 방을 44 m 통로로.', '방이 8~12초에 끝나고 보스가 18초에 죽는 문제'),
    ('v0.3', '너클 돌진 대시 피해 감소 50%, 오버라이드 홀드 슈퍼아머. 엣지 전진 스텝을 "멀 때만", 3타 넉백. 불도저 휴식 2.5초, 탄 수 감소. 1챕터 웨이브 1.5배.', '근접 교리의 보스 사망률 90%+'),
    ('v0.4', '텔레그래프 공격 전용 회피 확률(평균 0.75) 분리. 등급을 "순 체력 손실"로. 돌파 방 스폰을 플레이어 전방으로. 휴대 센트리 강화.', '예고된 공격은 탄보다 피하기 쉬워야 함. 너클의 흡수가 등급에 반영되지 않던 문제'),
    ('v0.5', '챕터 배율 완화(피해 1.0→1.25), 챕터별 모듈 보유 가정과 회피 성장(+0.03/챕터) 도입. 보스 피해에 챕터 배율 미적용. 디버거·레이저 텔레그래프 1.0초/잠금 0.5초, 순간이동 후 0.6초 무방비. 드론·궁수·브루트·폭탄병 약화. 수비 노드 HP 2배.', '5~6챕터 전원 100% 사망'),
    ('v0.6', '보스 탄막 무장 거리 1.5 m(포탑 사각). 방패 내구(60/90)와 회전 속도 150°/s. 소환 횟수 상한. 골렘 소환을 궁수로, 오버시어·컴파일러·클러스터 HP 하향.', '트리거가 기사를 못 뚫음. 근접 캐릭터가 보스 밀착 시 탄막에 즉사'),
    ('v0.7→0.8', '회피 중 공격 취소를 전면 도입했다가(모든 캐릭터 악화) 장판·빔·보스 돌진·스윕에만 적용하도록 축소. 트리거 권총 14, HP 105. 엣지 콤보 15/15/22, 반사 1.5배.', '너클의 슈퍼아머·흡수, 엣지의 공격 중 반사가 회피 취소로 무력화됨'),
    ('v0.9', '근접 봇이 사거리 안에서 밀고 들어가지 않도록(접촉 피해 원인). 탄막 텔레그래프 때 근접은 보스를 끌어안도록. 돌진 텔레그래프 1.3초.', '보스전 근접 사망의 절반이 접촉 피해'),
    ('v0.10', '공격 중 이동 감속이 콤보 유지 시간(0.8초) 내내 걸리던 것을 스윙 중(0.3초)으로. 여러 장판이 겹칠 때 8방향 중 빈 곳으로 탈출. 돌진 잠금 50%→40%, 돌진 피해 15% 하향.', '보스 패턴별 피해 집계 결과 돌진이 근접 사망의 47~78%'),
    ('v0.11~0.13', '센트리 휴대는 스트림 중이 아니고 주변 8 m에 적이 없을 때만, 홀드 1.0초. Z-09·E-02·Z-07 구성 축소. 오버시어 혼합 소환 1회. 골렘 돌진 피해 20, 잠금 35%.', '잔여 핫스팟 정리'),
]
OPEN_ITEMS = [
    '하드 난이도에서 근접 교리의 보스 사망률이 급등한다(3·4챕터 보스 사망률 90%+). 하드는 보스 피해 배율을 1.4가 아니라 1.2로 따로 두거나, 하드 전용으로 돌진 잠금을 더 당기는 것을 검토.',
    '너클이 5~6챕터에서 가장 안전하다(사망 0~1%). 흡수 회복(6)을 5로 줄이거나 후반 적의 넉백 저항을 늘려 던지기 효율을 낮추는 방향을 검토. 단 너클의 "피해를 많이 받고 버틴다"는 정체성은 유지.',
    '엣지는 빔(디버거·레이저 센트리) 방에서 가장 취약하다. 설계 의도(반사 불가)이지만 Z-09·E-02 수준은 재검토. 엣지 카운터 창(0.2초)이 빔에도 적용되는지 실제 구현에서 확인.',
    '칩 상자가 방 시작 위치 근처에 있어 가동률이 90%대다. 상자를 방 중반·구석으로 옮기고 다시 측정.',
    '돌파 방이 8~10초로 짧고 위협이 낮다. 숨 돌리기로 두되, 후반 돌파 방에 쉴더를 길막 요소로 넣는 실험.',
    '봇은 사람보다 "조준이 정확하고 읽기가 느리다". 실제 플레이테스트에서 입문자의 텔레그래프 회피율(0.5)과 반응 시간(0.45초)을 측정해 봇 프로필을 교정.',
    '시뮬레이션에 없는 것: 엄폐물, 히트스톱, 카메라 가독성, 패드 조준 지연, 사운드 큐. 엄폐물은 트리거에게 유리하고 너클에게 던질 물건이므로 실제 수치는 달라진다.',
]


def roll(agg):
    out = {}
    for (ch, room, char, skill), a in agg.items():
        r = out.setdefault((ch, char, skill), {'n': 0, 'death': 0.0, 'exp': 0.0, 'dmg': 0.0, 'time': 0.0, 'fail': 0.0})
        r['n'] += 1
        r['death'] += a['death']
        p = min(a['death'], 0.95)
        r['exp'] += p / (1 - p)
        r['dmg'] += a['dmg_frac_mean']
        r['time'] += a['time_mean']
        r['fail'] += a['fail']
    return out


def rollup_table(agg, skills, title):
    r = roll(agg)
    L = ['**%s**' % title, '', '| 챕터 | 교리 | ' + ' | '.join('%s: 사망률 / 기대 손실' % SKILL_KO[s] for s in skills) + ' |', '|---|---|' + '---|' * len(skills)]
    for ch in range(1, 7):
        for c in CHARS:
            cells = []
            for s in skills:
                x = r.get((ch, c, s))
                cells.append('%d%% / %.2f' % (round(x['death'] / x['n'] * 100), x['exp']) if x else '-')
            L.append('| %d | %s | %s |' % (ch, CHAR_KO[c], ' | '.join(cells)))
    L.append('')
    return '\n'.join(L)


def gen_balance(S, P, A_normal, A_hard, A_arcade, A_assist):
    L = ['# ROOM ZERO — 밸런스 설계와 시뮬레이션 결과', '',
         '> 작성일: %s · params.json %s · stages.json %s' % (DATE, P['meta']['version'], S['meta']['version']),
         '> 이 문서의 표는 `sim/tools/gen_docs.py`가 `sim/results/final_*.json`에서 생성한다. 재현: `python3 sim/run_balance.py --chapters 1,2,3,4,5,6 --skills novice,average,expert --trials 24 --out sim/results/final_normal` 등.', '']
    # 0 summary
    rn = roll(A_normal)
    L += ['## 0. 요약', '',
          '- 46개 전투 방 × 3교리 × 3숙련도 × 24회(보통 난이도) + 하드·아케이드·어시스트를 2D 단순화 시뮬레이터로 측정했다. 한 세트 약 10,000회 실행에 1분이 걸린다.',
          '- 13번의 조정으로 1챕터 사망률 0~1%, 6챕터 평균 사망률 1~7%(교리별), 스테이지당 기대 인스턴스 손실 0.1~0.8(보유 3)에 수렴했다. 숙련 봇은 전 챕터에서 0.5 이하, 입문 봇은 6챕터에서 2~6이다.',
          '- 가장 많이 바뀐 설계는 보스였다. 근접 교리가 살아남으려면 "탄막 포탑 사각(1.5 m)", "돌진 잠금 시점(35~50%)", "밀고 들어오지 않는 보스"가 필요했고, 이 셋은 실제 보스 설계 규칙으로 승격했다.',
          '- 남은 과제는 하드 난이도의 근접 보스전, 후반 너클의 과잉 안전, 엣지의 빔 취약, 칩 상자 위치다(7절).', '']
    # 1 model
    L += ['## 1. 시뮬레이션 모형', '',
          '2D 평면(탑다운)에서 방 하나를 0.05초 단위로 돌린다. 코드는 `sim/roomsim/`, 실행은 `sim/run_balance.py`.', '',
          '**모델링한 것**', '',
          '- 방: 사각 경계, 크기 3종, 벽 스폰(돌파 방은 전방 스폰), 웨이브·스태거·동시 상한, 상자·차지·드롭, 수비 노드, 돌파 출구·삭제 벽, T포즈 각성.',
          '- 플레이어: 세 교리의 기본 공격·홀드·대시·스킬·패시브·오버라이드·탑승, 칩 변환 6×3, 피격 무적, 콤보, 반사(엣지), 던지기(너클), 휴대 센트리.',
          '- 적 16종: 근접/사격/저격/투척/터렛/빔 터렛/순간이동/차량 행동, 방패 내구와 회전, 넉백·다운·기절, 화상.',
          '- 보스 7기: 페이즈, 패턴 순환(돌진·부채꼴·원형·지점 장판·자기 장판·빔·스윕·소환·착지), 무장 거리, 접촉, 비행.',
          '- 봇: 교리별 휴리스틱 정책 + 숙련도 프로필(반응 시간, 탄 회피 확률, 텔레그래프 회피 확률, 조준 오차, 판단 주기, 전술 확률). 챕터가 오를수록 회피 확률이 +0.03씩 자란다(같은 사람이 숙달된다는 가정).',
          '- 성장: 챕터 진입 시 트리당 모듈 레벨 [0,1,2,3,4,5]를 가정해 HP·피해·대시·탄약·차지에 반영. 아케이드는 0.', '',
          '**모델링하지 않은 것**', '',
          '- 엄폐물·지형, 히트스톱·경직 연출, 카메라와 가독성, 패드/마우스 조준 지연, 사운드 큐, 플레이어의 학습 곡선(챕터 성장 가정으로만 근사), 정비 방의 모듈 선택.', '',
          '**봇 숙련도 프로필**', '',
          '| 프로필 | 반응 시간 | 탄 회피 | 텔레그래프 회피 | 조준 오차 | 판단 주기 | 전술 확률 |', '|---|---|---|---|---|---|---|']
    for k, v in P['global']['bot_skill'].items():
        L.append('| %s | %gs | %d%% | %d%% | %g° | %gs | %d%% |' % (SKILL_KO[k], v['reaction'], v['dodge_prob'] * 100, v['telegraph_dodge_prob'] * 100, v['aim_error_deg'], v['decision_period'], v['tactic_prob'] * 100))
    L.append('')
    L += ['**측정 지표**: 성공/사망/실패(노드 파괴·시간 초과), 클리어 시간(평균·p50·p90), 받은 피해(최대 HP 대비), 종료 HP, 칩 가동률, 스킬·대시·던지기·반사·오버라이드 횟수, 등급 분포, 피해원별 기여(보스는 패턴별).', '',
          '**스테이지 지표**: 기대 인스턴스 손실 = Σ 방별 p/(1−p). 사망 시 그 방을 처음부터 다시 하므로 기하급수 근사.', '']
    # 2 targets
    L += ['## 2. 밸런스 목표와 달성 여부', '', '| 지표 | 목표 | 결과 |', '|---|---|---|']
    for t in TARGETS:
        L.append('| %s | %s | %s |' % t)
    L.append('')
    # 3 results
    L += ['## 3. 결과', '', '### 3.1 보통 난이도 · 챕터 롤업', '']
    L.append(rollup_table(A_normal, ['expert', 'average', 'novice'], '사망률 = 챕터 내 방 평균 사망률, 기대 손실 = 스테이지당 기대 인스턴스 손실 (보유 3)'))
    L += ['### 3.2 난이도별 (평균 숙련; 어시스트는 입문)', '']
    merged = {}
    for name, A, sk in (('normal', A_normal, 'average'), ('hard', A_hard, 'average'), ('arcade', A_arcade, 'average'), ('assist', A_assist, 'novice')):
        for (ch, room, char, skill), a in A.items():
            if skill == sk:
                merged[(ch, room, char, name)] = a
    r = roll(merged)
    L += ['| 챕터 | 교리 | 보통 | 하드(인스턴스 2) | 아케이드(인스턴스 1, 모듈 없음) | 어시스트(입문 봇, 인스턴스 5) |', '|---|---|---|---|---|---|']
    for ch in range(1, 7):
        for c in CHARS:
            cells = []
            for name in ('normal', 'hard', 'arcade', 'assist'):
                x = r.get((ch, c, name))
                cells.append('%d%% / %.2f' % (round(x['death'] / x['n'] * 100), x['exp']) if x else '-')
            L.append('| %d | %s | %s |' % (ch, CHAR_KO[c], ' | '.join(cells)))
    L.append('')
    L += ['### 3.3 방별 결과 (보통 난이도, 평균 숙련)', '', '셀 = 평균 클리어 시간 · 사망률 · 받은 피해(최대 HP 대비) · S등급 비율. 사망률 15% 이상은 굵게.', '']
    for c in S['chapters']:
        L.append('**챕터 %d · %s**' % (c['chapter'], c['name']))
        L.append('')
        L.append('| 방 | 타입 | 파 | 트리거 | 너클 | 엣지 | 주 피해원(트리거) |')
        L.append('|---|---|---|---|---|---|---|')
        for rm in c['rooms']:
            if rm['type'] == 'service':
                continue
            cells = []
            for ch in CHARS:
                a = A_normal.get((c['chapter'], rm['id'], ch, 'average'))
                if not a:
                    cells.append('-')
                    continue
                n = a['n']
                s_pct = round(a['grades']['S'] / n * 100)
                cell = '%ds · %d%% · %d%% · S%d%%' % (round(a['time_mean']), round(a['death'] * 100), round(a['dmg_frac_mean'] * 100), s_pct)
                if a['death'] >= 0.15:
                    cell = '**%s**' % cell
                cells.append(cell)
            a = A_normal.get((c['chapter'], rm['id'], 'trigger', 'average'))
            src = ', '.join('%s %d%%' % (k, round(v * 100)) for k, v in list(a['dmg_src_share'].items())[:3]) if a else ''
            L.append('| %s | %s | %s | %s | %s |' % (rm['id'], TYPE_KO[rm['type']], rm.get('par', '-'), ' | '.join(cells), src))
        L.append('')
    # 4 doctrine balance
    L += ['## 4. 교리 간 균형', '', '| 챕터 | 평균 클리어 시간 트/너/엣 (초) | 너클/트리거 | 엣지/트리거 | 받은 피해 트/너/엣 | 던지기(너) · 반사(엣) · 오버라이드(트/너/엣) 방당 |', '|---|---|---|---|---|---|']
    for ch in range(1, 7):
        t = {c: [] for c in CHARS}
        d = {c: [] for c in CHARS}
        u = {'throws': [], 'reflects': [], 'ov': {c: [] for c in CHARS}}
        for (cc, room, char, skill), a in A_normal.items():
            if cc != ch or skill != 'average':
                continue
            t[char].append(a['time_mean'])
            d[char].append(a['dmg_frac_mean'])
            if char == 'knuckle':
                u['throws'].append(a['throws'])
            if char == 'edge':
                u['reflects'].append(a['reflects'])
            u['ov'][char].append(a['overrides'])
        tm = {c: statistics.fmean(t[c]) for c in CHARS}
        dm = {c: statistics.fmean(d[c]) for c in CHARS}
        L.append('| %d | %d / %d / %d | %.2f | %.2f | %d%% / %d%% / %d%% | %.1f · %.1f · %.2f/%.2f/%.2f |' % (
            ch, tm['trigger'], tm['knuckle'], tm['edge'], tm['knuckle'] / tm['trigger'], tm['edge'] / tm['trigger'],
            dm['trigger'] * 100, dm['knuckle'] * 100, dm['edge'] * 100, statistics.fmean(u['throws']), statistics.fmean(u['reflects']),
            statistics.fmean(u['ov']['trigger']), statistics.fmean(u['ov']['knuckle']), statistics.fmean(u['ov']['edge'])))
    L += ['',
          '- **트리거**는 기준점이다. 클리어가 가장 느린 편인데, 거리를 유지하느라 이동 시간이 길고 방패 적에 시간을 쓰기 때문이다. 후반 드론·디버거·레이저 방에서 사망률이 가장 높다.',
          '- **너클**은 받는 피해가 가장 크지만 흡수(근접 처치 회복 6)로 상쇄해 사망률이 가장 낮다. 숙련도에 둔감하다. 보스 돌진이 유일한 큰 위협.',
          '- **엣지**는 클리어가 가장 빠르고 탄 방에서 가장 안전하다. 반사 불가 빔(디버거·레이저)이 약점이며 그 방에서 사망률이 튄다. 이 비대칭은 의도한 것이지만 폭은 좁혀야 한다.', '']
    # 5 decisions
    L += ['## 5. 조정 이력', '', '| 버전 | 변경 | 계기 |', '|---|---|---|']
    for v, what, why in DECISIONS:
        L.append('| %s | %s | %s |' % (v, what, why))
    L.append('')
    # 6 hot spots computed
    L += ['## 6. 남은 핫스팟 (보통 난이도, 평균 숙련, 사망률 15% 이상)', '', '| 방 | 교리 | 사망률 | 시간 | 주 피해원 |', '|---|---|---|---|---|']
    hot = sorted([(k, a) for k, a in A_normal.items() if k[3] == 'average' and a['death'] >= 0.15], key=lambda ka: -ka[1]['death'])
    for (ch, room, char, skill), a in hot:
        L.append('| %s | %s | %d%% | %ds | %s |' % (room, CHAR_KO[char], round(a['death'] * 100), round(a['time_mean']), ', '.join('%s %d%%' % (k, round(v * 100)) for k, v in list(a['dmg_src_share'].items())[:3])))
    L.append('')
    L.append('이 방들은 3인스턴스 안에서 "한 번쯤 죽는 방"으로 두어도 되지만, 플레이테스트에서 좌절 지점이 되면 위 피해원부터 손댄다.')
    L.append('')
    L += ['## 7. 과제와 다음 단계', '']
    for it in OPEN_ITEMS:
        L.append('- ' + it)
    L += ['', '## 8. 실제 빌드로 옮길 때', '',
          '- `params.json`의 값을 ScriptableObject로 옮기되 키 이름을 유지한다. 그래야 플레이테스트 결과를 시뮬레이터에 되돌려 넣어 다시 돌릴 수 있다.',
          '- 첫 플레이테스트에서 측정할 것: (1) 입문자의 텔레그래프 회피율과 반응 시간, (2) 트리거의 실제 명중률, (3) 방당 클리어 시간이 시뮬 값의 ±30% 안인지. 셋 중 하나라도 벗어나면 봇 프로필을 교정하고 전체를 다시 돌린다.',
          '- 보스 규칙 셋(포탑 사각, 돌진 잠금 시점, 밀지 않는 보스)은 시뮬레이션 산물이 아니라 설계 규칙으로 문서화했다. 실제 구현에서 생략하면 근접 교리가 다시 죽는다.',
          '- 챕터 성장 가정([0,1,2,3,4,5] 레벨)은 평균 플레이어가 각 챕터에서 번 메모리로 살 수 있는 양과 맞춰야 한다. `progression.modules.cost_base`와 `memory_per_room`으로 검산한다.', '']
    return '\n'.join(L)


def main():
    P_raw = load_json(os.path.join(ROOT, 'sim', 'params.json'))
    P = load_params(os.path.join(ROOT, 'sim', 'params.json'))
    S = load_json(os.path.join(ROOT, 'sim', 'stages.json'))
    for eid, e in P['enemies'].items():
        ENEMY_KO[eid] = e.get('display', eid)
    res = os.path.join(ROOT, 'sim', 'results')
    A_normal = agg_of(os.path.join(res, 'final_normal.json'))
    A_hard = agg_of(os.path.join(res, 'final_hard.json'))
    A_arcade = agg_of(os.path.join(res, 'final_arcade.json'))
    A_assist = agg_of(os.path.join(res, 'final_assist.json'))
    docs = os.path.join(ROOT, 'docs')
    with open(os.path.join(docs, 'StageDesign.md'), 'w', encoding='utf-8') as f:
        f.write(gen_stage_design(S, P, A_normal))
    with open(os.path.join(docs, 'Parameters.md'), 'w', encoding='utf-8') as f:
        f.write(gen_parameters(P_raw, P))
    with open(os.path.join(docs, 'Balance.md'), 'w', encoding='utf-8') as f:
        f.write(gen_balance(S, P, A_normal, A_hard, A_arcade, A_assist))
    print('generated docs/StageDesign.md, docs/Parameters.md, docs/Balance.md')


if __name__ == '__main__':
    main()
