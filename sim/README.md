# ROOM ZERO 2D 밸런스 시뮬레이터

방 하나를 2D 탑다운 평면에서 0.05초 단위로 돌려 세 교리(트리거·너클·엣지)의 클리어 시간, 받은 피해, 사망률, 등급을 측정한다.
Unity 없이 Python만으로 돌아가며, 46개 전투 방 × 3교리 × 3숙련도 × 24회(약 10,000회)가 1분 안에 끝난다.

## 파일

| 경로 | 내용 |
|---|---|
| `params.json` | 모든 밸런스 수치의 단일 소스(전역·캐릭터·칩·적·보스·성장·봇 가정). `docs/Parameters.md`는 여기서 생성 |
| `stages.json` | 6챕터 52방의 정의(웨이브·상자·파·특수 규칙). `docs/StageDesign.md`는 여기서 생성 |
| `roomsim/params.py` | 로더. 적의 `base` 상속을 풀어 준다 |
| `roomsim/engine.py` | 월드, 투사체·장판·빔·픽업, 적 AI 8종 행동, 보스 패턴, 방 규칙(수비·돌파·T포즈·삭제 벽) |
| `roomsim/player.py` | 세 교리의 공격·홀드·대시·스킬·패시브·칩 변환·오버라이드·탑승 |
| `roomsim/bots.py` | 교리별 휴리스틱 봇과 숙련도 프로필(반응·회피·조준·전술) |
| `roomsim/runner.py` | 병렬 실행, 집계, 마크다운 출력 |
| `run_balance.py` | CLI |
| `tools/set_pars.py` | 숙련 봇 결과로 방별 파(par)를 계산해 `stages.json`에 기록 |
| `tools/gen_docs.py` | `docs/StageDesign.md`, `docs/Parameters.md`, `docs/Balance.md` 생성 |
| `results/final_*.{json,md}` | 최종 측정 결과(보통 3숙련도, 하드, 아케이드, 어시스트) |

## 실행

```bash
# 1챕터, 평균 숙련, 12회씩 (약 1초)
python3 sim/run_balance.py --chapters 1 --trials 12
```

```bash
# 전체 챕터, 3숙련도, 24회씩, 결과 저장
python3 sim/run_balance.py --chapters 1,2,3,4,5,6 --skills novice,average,expert --trials 24 --out sim/results/final_normal
```

```bash
# 하드 난이도, 특정 방만
python3 sim/run_balance.py --chapters 2 --rooms B-08 --difficulty hard --chars knuckle,edge --trials 48
```

```bash
# 파 재계산 → 문서 재생성
python3 sim/run_balance.py --chapters 1,2,3,4,5,6 --skills expert --trials 24 --out sim/results/expert
python3 sim/tools/set_pars.py sim/results/expert.json sim/stages.json
python3 sim/tools/gen_docs.py
```

## 출력 읽는 법

| 열 | 의미 |
|---|---|
| succ / death / fail | 성공률 / 사망률 / 비사망 실패율(노드 파괴, 시간 초과) |
| t_mean, t_p90 | 성공한 실행의 클리어 시간 평균, 90퍼센타일 |
| dmg% | 받은 피해 / 최대 HP (회복 전) |
| hp_end% | 종료 시 HP / 최대 HP |
| chip% | 칩을 들고 있던 시간 비율 |
| skill / dash / throw / refl / ovr | 방당 사용 횟수 |
| S/A/B/C | 등급 분포(순 체력 손실 기준) |
| top damage sources | 피해원 상위 3개. 보스는 패턴별(`boss/charge` 등) |
| expected instances lost | Σ p/(1−p). 스테이지당 기대 인스턴스 손실 |

## 수치를 바꾸는 법

1. `params.json` 또는 `stages.json`을 고친다. 적을 추가할 때는 `enemies`에 `behavior`(melee / ranged / sniper / lobber / turret / beam_turret / teleporter / vehicle) 중 하나를 쓰거나 `base`로 상속한다.
2. 해당 챕터만 빠르게 돌려 본다. 사망률 15% 이상인 방과 보스는 피해원 열을 본다.
3. 전체를 3숙련도로 돌려 숙련 < 평균 < 입문 순서가 유지되는지 확인한다.
4. `set_pars.py`로 파를 갱신하고 `gen_docs.py`로 문서를 다시 만든다.

## 한계

엄폐물, 히트스톱, 카메라 가독성, 조준 지연, 사운드 큐는 없다. 봇은 사람보다 조준이 정확하고 읽기가 느리다. 실제 플레이테스트에서 입문자의 텔레그래프 회피율과 반응 시간을 측정해 `bot_skill`을 교정한 뒤 다시 돌리는 것이 전제다.
