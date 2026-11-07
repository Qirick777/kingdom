class_name PieMenu
extends Control
## 대상을 클릭하면 뜨는 원형 메뉴(12번 3절). 가운데 대상 초상화와 이름, 둘레에 범주 → 행동.
## 빈 곳 클릭, 우클릭, Esc로 닫는다.

signal chosen(kind: String, payload: Variant, target: Citizen)   ## kind: "action" | "control"
signal closed

const RADIUS := 150.0

var target: Citizen
var _center := Vector2.ZERO
var _cats := {}
var _extra: Array = []
var _ring: Array = []
var _hub: Control


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	visible = false


func open(at: Vector2, t: Citizen, cats: Dictionary, extra: Array) -> void:
	target = t
	_cats = cats
	_extra = extra
	visible = true
	var vs := get_viewport_rect().size
	_center = Vector2(clampf(at.x, RADIUS + 140, vs.x - RADIUS - 140), clampf(at.y, RADIUS + 110, vs.y - RADIUS - 150))
	if _hub != null:
		_hub.queue_free()
	_hub = PanelContainer.new()
	var col := VBoxContainer.new()
	col.alignment = BoxContainer.ALIGNMENT_CENTER
	_hub.add_child(col)
	var pic := PanelContainer.new()
	pic.add_theme_stylebox_override("panel", PixelTheme.frame_box(t.look.social, Color("#fff4dc")))
	pic.add_child(Portrait.make(t, 24))
	pic.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	col.add_child(pic)
	var nm := Label.new()
	nm.text = t.display_name
	nm.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	nm.add_theme_font_override("font", load("res://assets/fonts/NanumGothicBold.ttf"))
	col.add_child(nm)
	add_child(_hub)
	_hub.reset_size()
	_hub.position = _center - _hub.size / 2.0
	_show_categories()


func close() -> void:
	visible = false
	_clear_ring()
	closed.emit()


func _clear_ring() -> void:
	for b in _ring:
		b.queue_free()
	_ring.clear()


func _show_categories() -> void:
	var entries: Array = []
	for cat in InteractionRules.data()["categories"]:
		if _cats.has(cat):
			entries.append({"text": cat, "icon": _cats[cat][0]["icon"], "cb": _show_actions.bind(cat)})
	for e in _extra:
		entries.append({"text": e, "icon": "", "cb": func(): chosen.emit("control", e, target); close()})
	if entries.is_empty():
		entries.append({"text": "지금 할 수 있는 행동이 없다", "icon": "", "cb": close})
	_lay(entries)


func _show_actions(cat: String) -> void:
	var entries: Array = []
	for a in _cats[cat]:
		var act: Dictionary = a
		entries.append({"text": act["name"], "icon": act["icon"], "cb": func(): chosen.emit("action", act, target); close()})
	entries.append({"text": "뒤로", "icon": "", "cb": _show_categories})
	_lay(entries)


func _lay(entries: Array) -> void:
	_clear_ring()
	var n := entries.size()
	for i in n:
		var e: Dictionary = entries[i]
		var b := Button.new()
		b.text = e["text"]
		if e["icon"] != "":
			b.icon = PixelTheme.icon("icons_action", e["icon"], 2)
		b.pressed.connect(e["cb"])
		add_child(b)
		b.reset_size()
		var ang := -PI / 2.0 + TAU * i / n
		var p := _center + Vector2(cos(ang), sin(ang)) * RADIUS
		b.position = (p - b.size / 2.0).round()
		_ring.append(b)


func _gui_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.pressed:
		close()
		accept_event()


func _unhandled_key_input(e: InputEvent) -> void:
	if visible and e is InputEventKey and e.pressed and e.keycode == KEY_ESCAPE:
		close()
		get_viewport().set_input_as_handled()
