"""12×12 상태, 계층 아이콘을 격자로 직접 찍는다. 채움만 찍고 외곽선은 자동."""
import numpy as np

from pixel import Canvas, hexc

PAL = {
    "W": "#c98c52", "L": "#e6b072", "w": "#a26a3a", "S": "#cfd8e0", "s": "#9aa6b2", "B": "#5fb0e8", "b": "#a8dcff",
    "C": "#8f86a8", "Y": "#ffd34d", "y": "#d9a73a", "P": "#ff8fa8", "R": "#e8574f", "r": "#b83c36", "G": "#8fd16a",
    "g": "#5fae4f", "H": "#ffffff", "D": "#3b2a2a", "U": "#5f9ad6",
}

STATUS = {
    "허기": ["............", "........S...", ".......S....", "......S.....", ".LLLLLLLLLL.", ".WWWWWWWWWW.",
             "..WWWWWWWW..", "..WWWWWWWW..", "...WWWWWW...", "............"],
    "추위": ["....B.....", ".B..B..B..", "..B.B.B...", "...BbB....", "BBBbbbBBB.", "...BbB....",
             "..B.B.B...", ".B..B..B..", "....B....."],
    "스트레스": ["...CCC.CC...", "..CCCCCCCC..", ".CCCCCCCCCC.", ".CCCCCCCCCC.", "..CCYCCCCC..",
                 "....YY......", "...YY.......", "....Y......."],
    "임신": ["..PP...PP...", ".PPPP.PPPP..", ".PPPPPPPPP..", ".PPPHHPPPP..", "..PPHHPPP...", "...PPPPP....",
             "....PPP.....", ".....P......"],
    "부상": ["...HHHHH....", "..HHHRHHH...", ".HHHHRHHHH..", ".HHRRRRRHH..", ".HHHHRHHHH..", "..HHHRHHH...",
             "...HHHHH...."],
    "질병": [".......GG...", "......GGGG..", "......GGGG..", "..GGG..GG...", ".GGGGG......", ".GGgGG.GG...",
             ".GGGGG.GG...", "..GGG......."],
    "거부 위험": ["...RRRRR....", "..RRRHRRR...", ".RRRRHRRRR..", ".RRRRHRRRR..", ".RRRRHRRRR..", ".RRRRRRRRR..",
                  ".RRRRHRRRR..", "..RRRRRRR...", "...RRRRR...."],
    "비밀": ["....SSS.....", "...S...S....", "...S...S....", "..YYYYYYY...", "..YYYYYYY...", "..YYYDYYY...",
             "..YYYDYYY...", "..YYYYYYY..."],
    "원한": [".....R......", "....RR......", "...RRR.R....", "..RRRRRR....", "..RRYRRRR...", ".RRRYYRRR...",
             ".RRYYYYRR...", "..RYYYYR....", "...RRRR....."],
    "호감": ["..RR...RR...", ".RHRR.RRRR..", ".RRRRRRRRR..", ".RRRRRRRRR..", "..RRRRRRR...", "...RRRRR....",
             "....RRR.....", ".....R......"],
    "충성": [".UUUUUUUU...", ".UUUUUUUU...", ".UUUUUUHU...", ".UUUUUHUU...", ".UHUUHUUU...", ".UUHHUUUU...",
             "..UUUUUU....", "...UUUU.....", "....UU......"],
    "두려움": [".....B......", ".....B......", "....BBB.....", "....BBB.....", "...BbBBB....", "...BbBBB....",
               "...BBBBB....", "....BBB....."],
    "신뢰": ["............", ".YYY........", "Y...Y.......", "Y...YYYYYYY.", "Y...Y...Y.Y.", ".YYY........"],
}

CLASSES = {
    "노예": ["............", ".SSS...SSS..", "S...SSS...S.", ".SSS...SSS.."],
    "무산": [".......RRR..", "......RRRRR.", "......RRRRR.", ".......RRR..", "......W.....", ".....W......",
             "....W.......", "...W........", "..W........."],
    "소작농": ["....SSSS....", "...SS..SS...", "..SS........", "..S.........", "..S.........", "..SS........",
               "...SSW......", ".....WW.....", "......WW...."],
    "자영농": ["..Y..Y..Y...", ".YY.YY.YY...", "..Y..Y..Y...", "...y.y.y....", "....yyy.....", "....yyy.....",
               "...y.y.y....", "..y..y..y..."],
    "지주·기사": ["....SSSS....", "...SSSSSS...", "..SSSSSSSS..", "..SSSSSSSS..", "..SDDDDDDS..", "..SSSSSSSS..",
                  "..SSSSSSSS..", "..SS....SS.."],
    "귀족": [".S...S...S..", ".SS.SSS.SS..", ".SSSSSSSSS..", ".SSSSUSSSS..", ".SSSSSSSSS.."],
    "왕족": [".Y...Y...Y..", ".YY..Y..YY..", ".YYY.Y.YYY..", ".YYYYYYYYY..", ".YRYYRYYRY..", ".YYYYYYYYY.."],
}

NO_OUTLINE = {"추위"}


def draw(name, rows, size=12):
    c = Canvas(size, size)
    h = len(rows)
    w = max(len(r) for r in rows)
    oy = (size - h) // 2
    ox = (size - w) // 2 if w < size else 0
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                c.put(ox + x, oy + y, hexc(PAL[ch]))
    if name not in NO_OUTLINE:
        c.outline()
    else:
        c.outline(hexc("#2f6f9f"))
    return c.px


# ---- 행동 아이콘 (행동 큐, 말풍선 안에 쓴다)
ACTIONS = {
    "이동": ["............", ".GGGGGG.....", ".GGGGG......", ".GGGGGG.....", ".GGG.GGG....", ".GG...GGG...",
             "......GGG...", ".......GGG..", "........GG.."],
    "잡담": ["............", "..HHHHHHHH..", ".HHHHHHHHHH.", ".HHDHHDHHDH.", ".HHHHHHHHHH.", "..HHHHHHHH..",
             "...HH.......", "..HH........"],
    "칭찬": [".....Y......", ".....Y......", "....YYY.....", "YYYYYYYYYYY.", ".YYYYYYYYY..", "..YYYYYYY...",
             "..YYYyYYY...", ".YYYy.yYYY..", ".YYy...yYY..", ".Yy.....yY.."],
    "모욕": ["...RR..RR...", "...RR..RR...", ".RRRR..RRRR.", ".RRR....RRR.", "............", ".RRR....RRR.",
             ".RRRR..RRRR.", "...RR..RR...", "...RR..RR..."],
    "위로": [".....B......", ".....B......", "....BBB.....", "....BBB.....", "...BbBBB....", "..BbBBBBB...",
             "..BbBBBBB...", "..BBBBBBB...", "...BBBBB....", "....BBB....."],
    "유혹": ["..PP...PP...", ".PHPP.PPPP..", ".PPPPPPPPP..", ".PPPPPPPPP..", "..PPPPPPP...", "...PPPPP....",
             "....PPP.....", ".....P......"],
    "기다림": ["..wwwwwww...", "...YYYYY....", "...YYYYY....", "....YYY.....", ".....Y......", "....Y.Y.....",
               "...Y...Y....", "...YYYYY....", "..wwwwwww..."],
    "실패": ["............", ".RR.....RR..", "..RR...RR...", "...RR.RR....", "....RRR.....", "...RR.RR....",
             "..RR...RR...", ".RR.....RR.."],
}

# 말풍선 18×18. 안쪽 (3,2)에 12px 아이콘을 얹는다.
BUBBLE = ["....HHHHHHHHHH....", "..HHHHHHHHHHHHHH..", ".HHHHHHHHHHHHHHHH."] + \
         [".HHHHHHHHHHHHHHHH."] * 10 + \
         ["..HHHHHHHHHHHHHH..", "....HHHHHHHHHH....", "....HHH...........", "...HH.............",
          "..H..............."]


def main():
    """행동 아이콘과 말풍선만 만든다. 기존 아틀라스(make_icons.py)는 건드리지 않는다."""
    import json
    import os
    from PIL import Image
    root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
    ui = os.path.join(root, "assets", "ui")
    cols = 8
    rows = (len(ACTIONS) + cols - 1) // cols
    a = np.zeros((rows * 12, cols * 12, 4), dtype=np.uint8)
    idx = {}
    for k, (n, grid) in enumerate(ACTIONS.items()):
        x, y = (k % cols) * 12, (k // cols) * 12
        a[y:y + 12, x:x + 12] = draw(n, grid)
        idx[n] = k
    Image.fromarray(a, "RGBA").save(os.path.join(ui, "icons_action.png"))
    Image.fromarray(draw("말풍선", BUBBLE, 18), "RGBA").save(os.path.join(ui, "bubble.png"))
    path = os.path.join(root, "data", "visual", "ui_atlas.json")
    meta = json.load(open(path, encoding="utf-8"))
    meta["icons_action"] = {"cell": 12, "columns": 8, "index": idx}
    meta["bubble"] = {"size": 18, "icon_at": [3, 2]}
    json.dump(meta, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("행동 아이콘", len(ACTIONS), "개, 말풍선 1장")


if __name__ == "__main__":
    main()
