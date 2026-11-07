class_name PixelTheme
extends RefCounted
## assets/ui의 저해상도 틀을 정수배로 키워 UI 테마를 만든다. 글꼴은 나눔고딕.

const SCALE := 3


static func _scaled(path: String) -> ImageTexture:
	var img := (load(path) as Texture2D).get_image()
	img.convert(Image.FORMAT_RGBA8)
	img.resize(img.get_width() * SCALE, img.get_height() * SCALE, Image.INTERPOLATE_NEAREST)
	return ImageTexture.create_from_image(img)


static func _box(path: String, margin: int, pad: int) -> StyleBoxTexture:
	var sb := StyleBoxTexture.new()
	sb.texture = _scaled(path)
	for side in [SIDE_LEFT, SIDE_TOP, SIDE_RIGHT, SIDE_BOTTOM]:
		sb.set_texture_margin(side, margin * SCALE)
		sb.set_content_margin(side, pad)
	return sb


static var _icons := {}


static func box(path: String, margin: int, pad: int) -> StyleBoxTexture:
	return _box(path, margin, pad)


static func icon(sheet: String, name: String, scale: int = SCALE) -> ImageTexture:
	## ui_atlas.json의 아이콘 한 칸을 정수배로 키워 돌려준다.
	var key := "%s/%s/%d" % [sheet, name, scale]
	if _icons.has(key):
		return _icons[key]
	var meta: Dictionary = DataDB.json("res://data/visual/ui_atlas.json")[sheet]
	var cell := int(meta["cell"])
	var cols := int(meta["columns"])
	var k := int(meta["index"][name])
	var img := (load("res://assets/ui/%s.png" % sheet) as Texture2D).get_image()
	img.convert(Image.FORMAT_RGBA8)
	var sub := img.get_region(Rect2i((k % cols) * cell, (k / cols) * cell, cell, cell))
	sub.resize(cell * scale, cell * scale, Image.INTERPOLATE_NEAREST)
	var tex := ImageTexture.create_from_image(sub)
	_icons[key] = tex
	return tex


static func scaled(path: String, scale: int = SCALE) -> ImageTexture:
	var img := (load(path) as Texture2D).get_image()
	img.convert(Image.FORMAT_RGBA8)
	img.resize(img.get_width() * scale, img.get_height() * scale, Image.INTERPOLATE_NEAREST)
	return ImageTexture.create_from_image(img)


static func frame_box(social: String, bg: Color, selected := false) -> StyleBoxTexture:
	## 초상화 틀. 계층에 따라 나무(평민 이하), 은(지주기사), 금(귀족) 틀. 안쪽은 bg로 채운다.
	var path := "res://assets/ui/frame_commoner.png"
	if social == "지주기사":
		path = "res://assets/ui/frame_noble.png"
	elif social == "귀족":
		path = "res://assets/ui/frame_royal.png"
	var img := (load(path) as Texture2D).get_image()
	img.convert(Image.FORMAT_RGBA8)
	for y in img.get_height():
		for x in img.get_width():
			if img.get_pixel(x, y).a == 0.0:
				img.set_pixel(x, y, bg)
			elif selected and (x == 1 or y == 1 or x == img.get_width() - 2 or y == img.get_height() - 2):
				img.set_pixel(x, y, Color("#ffd34d"))
	img.resize(img.get_width() * SCALE, img.get_height() * SCALE, Image.INTERPOLATE_NEAREST)
	var sb := StyleBoxTexture.new()
	sb.texture = ImageTexture.create_from_image(img)
	for side in [SIDE_LEFT, SIDE_TOP, SIDE_RIGHT, SIDE_BOTTOM]:
		sb.set_texture_margin(side, 2 * SCALE)
		sb.set_content_margin(side, 2 * SCALE)
	return sb


static func make() -> Theme:
	var t := Theme.new()
	var font := load("res://assets/fonts/NanumGothic.ttf") as FontFile
	var bold := load("res://assets/fonts/NanumGothicBold.ttf") as FontFile
	t.default_font = font
	t.default_font_size = 20
	var ink := Color("#3b2a2a")
	t.set_stylebox("panel", "PanelContainer", _box("res://assets/ui/panel_light.png", 4, 14))
	for state in ["normal", "focus"]:
		t.set_stylebox(state, "Button", _box("res://assets/ui/button_normal.png", 3, 10))
		t.set_stylebox(state, "OptionButton", _box("res://assets/ui/button_normal.png", 3, 10))
	for state in ["hover"]:
		t.set_stylebox(state, "Button", _box("res://assets/ui/button_normal.png", 3, 10))
		t.set_stylebox(state, "OptionButton", _box("res://assets/ui/button_normal.png", 3, 10))
	t.set_stylebox("pressed", "Button", _box("res://assets/ui/button_pressed.png", 3, 10))
	t.set_stylebox("pressed", "OptionButton", _box("res://assets/ui/button_pressed.png", 3, 10))
	t.set_stylebox("disabled", "Button", _box("res://assets/ui/button_disabled.png", 3, 10))
	for cls in ["Label", "Button", "OptionButton"]:
		t.set_color("font_color", cls, ink)
	for cls in ["Button", "OptionButton"]:
		t.set_color("font_hover_color", cls, ink)
		t.set_color("font_pressed_color", cls, ink)
		t.set_color("font_focus_color", cls, ink)
	t.set_font("font", "Button", bold)
	t.set_font("font", "OptionButton", bold)
	t.set_stylebox("panel", "PopupMenu", _box("res://assets/ui/panel_light.png", 4, 8))
	t.set_color("font_color", "PopupMenu", ink)
	t.set_color("font_hover_color", "PopupMenu", Color("#774a2a"))
	return t
