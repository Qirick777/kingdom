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
