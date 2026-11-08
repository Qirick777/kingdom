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

윈도우용 DLL(`bin/libkingdom.windows.template_debug.x86_64.dll`, `..._release...`)은 저장소에 들어 있다. 윈도우에서는 빌드 없이 프로젝트를 열면 된다. C++ 코드를 고치면 아래처럼 다시 빌드한다.

godot-cpp는 하위 모듈(native/godot-cpp, 4.4.1-stable)이다. 새로 받은 저장소에서는 `git submodule update --init`을 먼저 한다. scons가 필요하다(`pip install scons`).

- 리눅스에서 윈도우 DLL 교차 빌드(이 저장소의 DLL은 이렇게 만들었다): `apt-get install g++-mingw-w64-x86-64-posix` 뒤 `cd native/gdext && scons platform=windows use_mingw=yes target=template_debug -j4`(release도 같은 방식). DLL은 윈도우 시스템 DLL(KERNEL32, msvcrt)만 쓴다.
- 윈도우에서 직접 빌드: Visual Studio C++ 도구와 Python, scons를 설치한 뒤 `cd native\gdext` → `scons platform=windows target=template_debug`. Godot 편집기가 열려 있으면 DLL이 잠기므로 닫고 빌드한다.

리눅스:

```
cd native/gdext && scons platform=linux target=template_debug -j4
godot --headless --path . --script native/gdext/smoke_test.gd
```

`bin/kingdom.gdextension`이 플랫폼별 라이브러리를 고른다.

## 측정 (2026-11, 4코어 컨테이너, 단일 스레드)

| 항목 | 값 |
|---|---|
| 대 맵: 시작 30만 명, 마을 1,600, 300년 | 15.3초. 1년 평균 51ms, 가장 느린 해 68ms |
| 32x에서 1년(126초) 대비 | 0.04% |
| 300년 뒤 누적 인물 | 357만 명, 인물 배열 161MB(1명 47.5바이트) |
| 인구 | 35.5만 명 근처에서 안정. 평균 나이 25.8세, 출생률 연 3.1%, 사망률 연 3.1%, 식량 충족률 0.92 |
| 결정성 | 같은 시드 두 번 실행 검사합 일치, 다른 시드는 다름 |
| 시조 1명 혈통 150년 생존(소 맵, 시드 12개) | 10/12 |
| Godot 연결(smoke_test.gd, 2만 명 100년) | 리눅스 Godot + .so, 윈도우 Godot(Wine) + .dll 둘 다 검사합 64553e67f5e50b8c. 단독 벤치마크와 같다 |
