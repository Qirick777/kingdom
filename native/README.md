# native: 시뮬레이션 핵심 (C++)

19번 문서(docs/design/19_simulation_scale.md) 8절 1단계. Godot에 기대지 않는 순수 C++ 핵심과, GDScript에서 부르는 GDExtension 포장으로 나뉜다.

| 폴더 | 내용 |
|---|---|
| core/ | `SimCore`: 인물 열 배열, 결정적 난수, 사건 예약 바퀴(출산), 요약 상세도 인구(사망, 임신, 출산, 혼인, 마을 부양 한계, 수확 변동, 유전, 혈통 r) |
| tools/ | `sim_bench`: 화면 없이 인구를 돌려 시간, 메모리, 검사합을 잰다 |
| gdext/ | `KingdomSim`(RefCounted) 포장, SConstruct, kingdom.gdextension, smoke_test.gd |

Godot은 이 폴더를 읽지 않는다(`.gdignore`).

## 핵심과 벤치마크 빌드

```
cmake -S native -B native/build -DCMAKE_BUILD_TYPE=Release
cmake --build native/build -j4
native/build/sim_bench 300000 1600 300 1     # 인구, 마을, 년, 시드
```

## GDExtension 빌드

godot-cpp 4.4.1-stable과 scons가 필요하다.

```
git submodule add https://github.com/godotengine/godot-cpp native/godot-cpp
git -C native/godot-cpp checkout godot-4.4.1-stable
pip install scons
cd native/gdext && scons platform=linux target=template_debug -j4    # windows, macos도 같은 방식
cp native/gdext/kingdom.gdextension bin/
godot --headless --path . --script native/gdext/smoke_test.gd
```

## 측정 (2026-11, 4코어 컨테이너, 단일 스레드)

| 항목 | 값 |
|---|---|
| 대 맵: 시작 30만 명, 마을 1,600, 300년 | 15.3초. 1년 평균 51ms, 가장 느린 해 68ms |
| 32x에서 1년(126초) 대비 | 0.04% |
| 300년 뒤 누적 인물 | 357만 명, 인물 배열 161MB(1명 47.5바이트) |
| 인구 | 35.5만 명 근처에서 안정. 평균 나이 25.8세, 출생률 연 3.1%, 사망률 연 3.1%, 식량 충족률 0.92 |
| 결정성 | 같은 시드 두 번 실행 검사합 일치, 다른 시드는 다름 |
| 시조 1명 혈통 150년 생존(소 맵, 시드 12개) | 10/12 |
