# 그림 생성 스크립트

텍스처, 얼굴 그림, 아이콘, UI 틀을 코드로 만든다. 색이나 크기를 바꾸면 다시 돌리면 된다.

```bash
cd tools/art
python3 make_materials.py   # 팔레트, 재료 텍스처 31종 × 2 → assets/textures/material_atlas.png
python3 make_faces.py       # 얼굴 그림 31개 → assets/faces/face_atlas.png
python3 make_icons.py       # 아이콘 51개, UI 틀 12장 → assets/ui/
python3 preview_faces.py ../../docs/images/art_faces.png   # 얼굴 조립 미리보기
```

필요: Python 3, Pillow, numpy.

| 스크립트 | 출력 | 배치 정보 |
|---|---|---|
| make_materials.py | assets/textures/material_atlas.png, assets/palette.png | data/visual/material_atlas.json, data/visual/palettes.json |
| make_faces.py | assets/faces/face_atlas.png | data/visual/face_atlas.json |
| make_icons.py | assets/ui/*.png | data/visual/ui_atlas.json |

화풍 규칙: 진한 갈색 외곽선(#3b2a2a), 위·왼쪽 밝게, 아래·오른쪽 어둡게, 밝은 파스텔 계열. 공통 도우미는 `pixel.py`.

얼굴 그림의 회색 약속(셰이더가 바꿈):
- #808080, #606060 → 유전자 눈색 × (회색 밝기 / 128)
- #404040 → 머리색 × 0.7 (눈썹)
