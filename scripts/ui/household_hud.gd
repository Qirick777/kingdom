class_name HouseholdHud
extends Control
## 가구 플레이 화면 UI (12번 6절).
##  왼쪽 아래: 행동 큐 5칸 → 선택한 가구원 큰 초상화와 정보 → 가구원 초상화 줄(클릭하면 선택, 카메라가 따라감)
##  오른쪽 위: 속도. 그 아래: 알림 피드. 오른쪽 아래: 조작 안내.
##  화면 위: 말풍선(3D 위치를 화면에 옮겨 3배 격자에 맞춰 그린다), 마우스를 올린 사람의 정보 상자.

signal member_clicked(c: Citizen)
signal queue_slot_clicked(i: int)
signal speed_chosen(s: float)

const SPEEDS := [0.0, 1.0, 2.0, 4.0]
const SPEED_TEXT := ["❚❚", "▶", "▶▶", "▶▶▶"]

var game: Node
var _bold: FontFile
var _queue_box: HBoxContainer
var _queue_slots: Array = []
var _main_pic: PanelContainer
var _name_label: Label
var _info_label: Label
var _thumbs: HBoxContainer
var _thumb_map := {}         ## Citizen → PanelContainer
var _feed: VBoxContainer
var _speed_btns: Array = []
var _tip: PanelContainer
var _tip_label: Label
var _bubble_tex: ImageTexture
var _shown: Citizen


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_bold = load("res://assets/fonts/NanumGothicBold.ttf")
	_bubble_tex = PixelTheme.scaled("res://assets/ui/bubble.png")
	_build_bottom_left()
	_build_top_right()
	_build_help()
	_tip = PanelContainer.new()
	_tip.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_tip_label = Label.new()
	_tip.add_child(_tip_label)
	_tip.visible = false
	add_child(_tip)


# ---------------------------------------------------------------- 왼쪽 아래

func _build_bottom_left() -> void:
	var panel := PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	panel.grow_vertical = Control.GROW_DIRECTION_BEGIN
	panel.offset_left = 12
	panel.offset_bottom = -12
	panel.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(panel)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 10)
	panel.add_child(col)

	_queue_box = HBoxContainer.new()
	_queue_box.add_theme_constant_override("separation", 6)
	col.add_child(_queue_box)
	for i in Citizen.QUEUE_MAX:
		var slot := PanelContainer.new()
		slot.add_theme_stylebox_override("panel", PixelTheme.box("res://assets/ui/panel_dark.png", 4, 6))
		slot.custom_minimum_size = Vector2(72, 72)
		slot.mouse_filter = Control.MOUSE_FILTER_STOP
		var inner := VBoxContainer.new()
		inner.alignment = BoxContainer.ALIGNMENT_CENTER
		inner.mouse_filter = Control.MOUSE_FILTER_IGNORE
		slot.add_child(inner)
		var ic := TextureRect.new()
		ic.stretch_mode = TextureRect.STRETCH_KEEP_CENTERED
		ic.custom_minimum_size = Vector2(36, 36)
		ic.mouse_filter = Control.MOUSE_FILTER_IGNORE
		inner.add_child(ic)
		var bar := ProgressBar.new()
		bar.custom_minimum_size = Vector2(54, 9)
		bar.show_percentage = false
		bar.max_value = 1.0
		bar.add_theme_stylebox_override("background", PixelTheme.box("res://assets/ui/bar_bg.png", 1, 0))
		bar.add_theme_stylebox_override("fill", PixelTheme.box("res://assets/ui/bar_fill.png", 1, 0))
		bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
		inner.add_child(bar)
		var idx := i
		slot.gui_input.connect(func(e): if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT: queue_slot_clicked.emit(idx))
		_queue_box.add_child(slot)
		_queue_slots.append([slot, ic, bar])

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 14)
	col.add_child(row)
	_main_pic = PanelContainer.new()
	row.add_child(_main_pic)
	var info := VBoxContainer.new()
	info.custom_minimum_size = Vector2(300, 0)
	info.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_child(info)
	_name_label = Label.new()
	_name_label.add_theme_font_override("font", _bold)
	_name_label.add_theme_font_size_override("font_size", 26)
	info.add_child(_name_label)
	_info_label = Label.new()
	info.add_child(_info_label)

	_thumbs = HBoxContainer.new()
	_thumbs.add_theme_constant_override("separation", 6)
	col.add_child(_thumbs)


func set_household(members: Array) -> void:
	for c in _thumbs.get_children():
		c.queue_free()
	_thumb_map.clear()
	for m in members:
		var cz: Citizen = m
		var box := PanelContainer.new()
		box.mouse_filter = Control.MOUSE_FILTER_STOP
		box.tooltip_text = "%s (%d세)" % [cz.display_name, cz.look.age]
		box.add_child(Portrait.make(cz, 18))
		box.gui_input.connect(func(e): if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT: member_clicked.emit(cz))
		_thumbs.add_child(box)
		_thumb_map[cz] = box


func show_active(c: Citizen) -> void:
	_shown = c
	for k in _thumb_map.keys():
		var cz: Citizen = k
		(_thumb_map[k] as PanelContainer).add_theme_stylebox_override("panel", PixelTheme.frame_box(cz.look.social, Color("#fff4dc") if cz != c else Color("#ffe98a"), cz == c))
	for ch in _main_pic.get_children():
		ch.queue_free()
	_main_pic.add_theme_stylebox_override("panel", PixelTheme.frame_box(c.look.social, Color("#fff4dc")))
	_main_pic.add_child(Portrait.make(c, 34))
	refresh_active()
	refresh_queue(c)


func refresh_active() -> void:
	var c := _shown
	if c == null:
		return
	_name_label.text = c.display_name
	var sp: int = game.rel.spouse_of(c.pid)
	var spouse_txt := ""
	if sp >= 0:
		spouse_txt = "\n배우자 " + game.by_pid(sp).display_name
	_info_label.text = "%d세 %s · %s · %s\n표정 %s%s" % [c.look.age, "남" if c.look.male else "여", c.look.social, c.look.occupation, c.look.mood, spouse_txt]


func refresh_queue(c: Citizen) -> void:
	if c != _shown:
		return
	for i in _queue_slots.size():
		var s: Array = _queue_slots[i]
		var ic: TextureRect = s[1]
		var bar: ProgressBar = s[2]
		if i < c.queue.size():
			var it: Dictionary = c.queue[i]
			var a: Dictionary = it["action"]
			ic.texture = PixelTheme.icon("icons_action", a["icon"])
			(s[0] as Control).tooltip_text = "%s → %s (클릭하면 취소)" % [a["name"], (it["target"] as Citizen).display_name]
			bar.visible = i == 0
			bar.value = it["progress"]
		else:
			ic.texture = null
			(s[0] as Control).tooltip_text = ""
			bar.visible = false


# ---------------------------------------------------------------- 오른쪽

func _build_top_right() -> void:
	var col := VBoxContainer.new()
	col.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	col.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	col.offset_right = -12
	col.offset_top = 12
	col.add_theme_constant_override("separation", 8)
	col.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(col)
	var sp := PanelContainer.new()
	sp.size_flags_horizontal = Control.SIZE_SHRINK_END
	col.add_child(sp)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	sp.add_child(row)
	var lbl := Label.new()
	lbl.text = "속도"
	row.add_child(lbl)
	for i in SPEEDS.size():
		var b := Button.new()
		b.text = SPEED_TEXT[i]
		b.toggle_mode = true
		var v: float = SPEEDS[i]
		b.pressed.connect(func(): speed_chosen.emit(v))
		row.add_child(b)
		_speed_btns.append(b)
	_feed = VBoxContainer.new()
	_feed.custom_minimum_size = Vector2(560, 0)
	_feed.add_theme_constant_override("separation", 6)
	_feed.mouse_filter = Control.MOUSE_FILTER_IGNORE
	col.add_child(_feed)


func show_speed(s: float) -> void:
	for i in _speed_btns.size():
		(_speed_btns[i] as Button).button_pressed = is_equal_approx(SPEEDS[i], s)


func notify(text: String, sub := "", seconds := 14.0) -> void:
	## 알림 피드(12번 6절). 최근 6개만 남긴다.
	var p := PanelContainer.new()
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var v := VBoxContainer.new()
	p.add_child(v)
	var l := Label.new()
	l.text = text
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size = Vector2(530, 0)
	v.add_child(l)
	if sub != "":
		var s := Label.new()
		s.text = sub
		s.add_theme_font_size_override("font_size", 16)
		s.add_theme_color_override("font_color", Color("#7a6a5a"))
		v.add_child(s)
	_feed.add_child(p)
	while _feed.get_child_count() > 6:
		var old := _feed.get_child(0)
		_feed.remove_child(old)
		old.queue_free()
	var tw := create_tween()
	tw.tween_interval(seconds)
	tw.tween_property(p, "modulate:a", 0.0, 1.0)
	tw.tween_callback(p.queue_free)


func _build_help() -> void:
	var p := PanelContainer.new()
	p.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	p.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	p.grow_vertical = Control.GROW_DIRECTION_BEGIN
	p.offset_right = -12
	p.offset_bottom = -12
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var l := Label.new()
	l.text = "우클릭 땅: 이동 · 우클릭 사람: 그 사람 앞으로\n좌클릭 사람: 상호작용 메뉴 · 큐 칸 클릭: 취소\nSpace: 카메라 따라가기 · 가운데 끌기, 화면 가장자리: 카메라 이동\nQ/E 회전 · 휠 확대 · P 일시정지 · 1/2/3 속도"
	l.add_theme_font_size_override("font_size", 17)
	p.add_child(l)
	add_child(p)


# ---------------------------------------------------------------- 정보 상자, 말풍선

func show_tip(c: Citizen, at: Vector2, active: Citizen) -> void:
	if c == null:
		_tip.visible = false
		return
	var t := "%s\n%d세 %s · %s · %s" % [c.display_name, c.look.age, "남" if c.look.male else "여", c.look.social, c.look.occupation]
	if active != null and c != active:
		var them: Dictionary = game.rel.of(c.pid, active.pid)
		var me: Dictionary = game.rel.of(active.pid, c.pid)
		t += "\n%s에게: 호감 %d · 신뢰 %d · 원한 %d" % [active.display_name, them["호감"], them["신뢰"], them["원한"]]
		t += "\n%s의 호감 %d" % [active.display_name, me["호감"]]
		if game.rel.has_link(c.pid, active.pid, "연인"):
			t += " · 연인"
	_tip_label.text = t
	_tip.visible = true
	_tip.reset_size()
	var vs := get_viewport_rect().size
	_tip.position = Vector2(minf(at.x + 24, vs.x - _tip.size.x - 8), minf(at.y + 24, vs.y - _tip.size.y - 8))


func _process(_dt: float) -> void:
	queue_redraw()


func _draw() -> void:
	if game == null:
		return
	var s := PixelTheme.SCALE
	for c in game.citizens:
		var cz: Citizen = c
		if cz.bubble_icon == "":
			continue
		var head := cz.global_position + Vector3(0, cz.height_m + 0.12, 0)
		var p: Vector2 = game.iso.to_screen(head)
		var bpos := Vector2(round((p.x - 4 * s) / s) * s, round((p.y - 18 * s) / s) * s)
		draw_texture(_bubble_tex, bpos)
		draw_texture(PixelTheme.icon("icons_action", cz.bubble_icon), bpos + Vector2(3, 2) * s)
