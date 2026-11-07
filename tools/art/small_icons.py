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
