extends Control
## 주민 뷰어 (17_visual_procgen.md 7절 1단계).
## 3D 세계는 640×360 서브뷰포트에 그려 3배로 키우고(도트), UI는 원래 해상도로 그린다.
## 확인 항목: 서명 중복 규칙(2-5), 가족이 닮아 보이는지, 계층이 옷으로 구분되는지.
##
## 명령줄(-- 뒤): --mode=crowd|family --seed=N --social=섞음|노예|... --age=섞음|아이|청년|중년|노인
##               --mood=평소|기쁨|... --zoom=1|2|3 --yaw=45 --pan=x,z --hover=x,y --screenshot=경로.png
##
## 주민은 모두 월드 +z(남쪽)를 본다. 카메라가 45° 비껴 보므로 얼굴과 옆면이 함께 보인다.
## Q/E는 카메라만 돌린다(주민은 그대로).

const SHRINK := 3
const PX_PER_M := 16.0
const SOCIAL_OPTS := ["섞음", "노예", "평민", "장인상인", "지주기사", "귀족"]
const AGE_OPTS := ["섞음", "아이", "청년", "중년", "노인"]
const MODE_OPTS := ["무작위 48명", "가족 3대"]
const GROUND_M := 48.0
const GROUND_CONTRAST := 0.55  ## 바닥 무늬 대비를 원본의 55%로
const CROWD_STEP := 2.0         ## 무작위 모드 격자 간격(m). 2m면 아이소 시점에서 서로 안 겹친다

var world_seed := 1
var mode := 0
var social_opt := 0
var age_opt := 0
var mood_opt := 0
var zoom := 0                  ## 0이면 모드 기본값(무작위 1, 가족 2)

var _svc: SubViewportContainer
var _sv: SubViewport
var _world: Node3D
var _people_root: Node3D
var _pivot: Node3D
var _cam: Camera3D
var _yaw := 45.0
var _pan := Vector3.ZERO
var _drag := false
var _ground: MeshInstance3D
var _hl: MeshInstance3D
var _zoom_btn: Button
var _people: Array = []        ## [PersonLook, Vector3]
var _seed_label: Label
var _status: Label
var _info: Label
var _screenshot := ""
var _hover_at := Vector2(-1, -1)  ## 캡처 검증용: 이 화면 좌표에 마우스를 올린 것처럼 한다
var _frames := 0


func _ready() -> void:
	_parse_args()
	theme = PixelTheme.make()
	_build_world()
	_build_ui()
	_regenerate()


func _parse_args() -> void:
	for a in OS.get_cmdline_user_args():
		var kv: PackedStringArray = a.trim_prefix("--").split("=", true, 1)
		if kv.size() < 2:
			continue
		match kv[0]:
			"mode":
				mode = 1 if kv[1] == "family" else 0
			"seed":
				world_seed = int(kv[1])
			"social":
				social_opt = max(0, SOCIAL_OPTS.find(kv[1]))
			"age":
				age_opt = max(0, AGE_OPTS.find(kv[1]))
			"mood":
				mood_opt = max(0, PersonLook.MOODS.find(kv[1]))
			"zoom":
				zoom = int(kv[1])
			"yaw":
				_yaw = float(kv[1])
			"pan":
				var xz := kv[1].split(",")
				if xz.size() == 2:
					_pan = Vector3(float(xz[0]), 0, float(xz[1]))
			"screenshot":
				_screenshot = kv[1]
			"hover":
				var xy := kv[1].split(",")
				if xy.size() == 2:
					_hover_at = Vector2(float(xy[0]), float(xy[1]))


# ---------------------------------------------------------------- 3D 세계

func _build_world() -> void:
	_svc = SubViewportContainer.new()
	_svc.stretch = true
	_svc.stretch_shrink = SHRINK
	_svc.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_svc.set_anchors_preset(Control.PRESET_FULL_RECT)
	_svc.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_svc)
	_sv = SubViewport.new()
	_sv.msaa_3d = Viewport.MSAA_DISABLED
	_sv.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_NEAREST
	_svc.add_child(_sv)

	_world = Node3D.new()
	_sv.add_child(_world)

	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("#bfe6ff")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(1, 1, 1)
	env.ambient_light_energy = 0.62
	var we := WorldEnvironment.new()
	we.environment = env
	_world.add_child(we)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-62, 20, 0)
	sun.light_energy = 0.62
	_world.add_child(sun)

	_hl = MeshInstance3D.new()
	var hm := PlaneMesh.new()
	hm.size = Vector2(1.0, 1.0)
	_hl.mesh = hm
	var hmat := StandardMaterial3D.new()
	hmat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	hmat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	hmat.albedo_color = Color(1.0, 0.83, 0.3, 0.55)
	_hl.material_override = hmat
	_hl.position.y = 0.01
	_hl.visible = false
	_world.add_child(_hl)

	_people_root = Node3D.new()
	_world.add_child(_people_root)

	_pivot = Node3D.new()
	_world.add_child(_pivot)
	_cam = Camera3D.new()
	_cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	_cam.near = 0.1
	_cam.far = 400.0
	_pivot.add_child(_cam)
	_apply_camera()


func _apply_camera() -> void:
	## 직교, 아래로 30°, 수평 45°. 화면 1픽셀 = 텍셀 1개(zoom 1) 또는 2픽셀(zoom 2).
	if zoom == 0:
		zoom = 1 if mode == 0 else 2
	_pivot.position = _pan
	_pivot.rotation_degrees = Vector3(0, _yaw, 0)
	_cam.rotation_degrees = Vector3(-30, 0, 0)
	_cam.position = Vector3(0, 0, 0) + Basis.from_euler(Vector3(deg_to_rad(-30), 0, 0)) * Vector3(0, 0, 60)
	var px_per_m_cam := PX_PER_M / cos(deg_to_rad(45.0))
	_cam.size = (1080.0 / SHRINK) / (px_per_m_cam * zoom)
	if _zoom_btn != null:
		_zoom_btn.text = "확대 ×%d" % zoom


# ---------------------------------------------------------------- UI

func _build_ui() -> void:
	var top := PanelContainer.new()
	top.set_anchors_preset(Control.PRESET_TOP_WIDE)
	top.offset_left = 12
	top.offset_right = -12
	top.offset_top = 12
	add_child(top)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	top.add_child(row)
	var title := Label.new()
	title.text = "주민 뷰어"
	title.add_theme_font_override("font", load("res://assets/fonts/NanumGothicBold.ttf"))
	title.add_theme_font_size_override("font_size", 24)
	row.add_child(title)
	row.add_child(_option(MODE_OPTS, mode, func(i): mode = i; zoom = 0; _pan = Vector3.ZERO; _apply_camera(); _regenerate()))
	var prev := Button.new()
	prev.text = "◀"
	prev.pressed.connect(func(): world_seed -= 1; _regenerate())
	row.add_child(prev)
	_seed_label = Label.new()
	row.add_child(_seed_label)
	var nxt := Button.new()
	nxt.text = "▶"
	nxt.pressed.connect(func(): world_seed += 1; _regenerate())
	row.add_child(nxt)
	row.add_child(_label("계층"))
	row.add_child(_option(SOCIAL_OPTS, social_opt, func(i): social_opt = i; _regenerate()))
	row.add_child(_label("나이"))
	row.add_child(_option(AGE_OPTS, age_opt, func(i): age_opt = i; _regenerate()))
	row.add_child(_label("표정"))
	row.add_child(_option(PersonLook.MOODS, mood_opt, func(i): mood_opt = i; _regenerate()))
	_zoom_btn = Button.new()
	_zoom_btn.pressed.connect(func(): zoom = zoom % 3 + 1; _apply_camera())
	row.add_child(_zoom_btn)
	_apply_camera()

	var bottom := PanelContainer.new()
	bottom.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	bottom.offset_left = 12
	bottom.offset_right = -12
	bottom.offset_bottom = -12
	bottom.grow_vertical = Control.GROW_DIRECTION_BEGIN
	add_child(bottom)
	var col := VBoxContainer.new()
	bottom.add_child(col)
	_status = Label.new()
	col.add_child(_status)
	_info = Label.new()
	_info.text = "주민 위에 마우스를 올리면 정보가 나온다 · Q/E 카메라 회전 · 휠 확대 · WASD/우클릭 끌기 이동"
	col.add_child(_info)


func _label(t: String) -> Label:
	var l := Label.new()
	l.text = t
	return l


func _option(items: Array, selected: int, cb: Callable) -> OptionButton:
	var ob := OptionButton.new()
	for it in items:
		ob.add_item(str(it))
	ob.select(selected)
	ob.item_selected.connect(cb)
	return ob


# ---------------------------------------------------------------- 주민 생성

func _pick_social(rng: RandomNumberGenerator) -> String:
	if social_opt > 0:
		return SOCIAL_OPTS[social_opt]
	return DetRng.pick_weighted(rng, PersonLook.SOCIAL, [0.1, 0.5, 0.15, 0.15, 0.1])


func _pick_age(rng: RandomNumberGenerator) -> int:
	var opt := age_opt
	if opt == 0:
		opt = DetRng.pick_weighted(rng, [1, 2, 3, 4], [0.2, 0.45, 0.22, 0.13])
	match opt:
		1:
			return rng.randi_range(1, 14)
		2:
			return rng.randi_range(16, 34)
		3:
			return rng.randi_range(35, 54)
		_:
			return rng.randi_range(55, 78)


func _regenerate() -> void:
	for c in _people_root.get_children():
		c.queue_free()
	_people.clear()
	_hl.visible = false
	_seed_label.text = "시드 %d" % world_seed
	var mood: String = PersonLook.MOODS[mood_opt]
	if mode == 0:
		_make_crowd(mood)
	else:
		_make_family(mood)
	var lo := Vector2(INF, INF)
	var hi := Vector2(-INF, -INF)
	for item in _people:
		var p: Vector3 = item[1]
		lo = Vector2(minf(lo.x, p.x), minf(lo.y, p.z))
		hi = Vector2(maxf(hi.x, p.x), maxf(hi.y, p.z))
	_make_ground(Rect2(lo - Vector2(1.5, 1.5), hi - lo + Vector2(3, 3)))


func _make_ground(plaza: Rect2) -> void:
	## plaza(월드 x,z 사각형)는 흙길. 사각형 모서리가 마름모로 보이면 아이소 시점이 맞다.
	## 뷰어 배경이므로 대비를 줄여 사람이 먼저 보이게 한다.
	if _ground != null:
		_ground.queue_free()
	_ground = GroundBuilder.build(world_seed, GROUND_M, [[plaza, "흙길"]], "풀", GROUND_CONTRAST)
	_world.add_child(_ground)


func _place(look: PersonLook, pos: Vector3) -> void:
	var node := PersonBuilder.build(look)
	node.position = pos
	_people_root.add_child(node)
	_people.append([look, pos])


func _world_grid(row: int, col: int, cols: int, rows: int, step: float) -> Vector3:
	## 월드 x,z 정격자. 카메라가 45° 돌아 있어 화면에서는 마름모로 놓인다.
	return Vector3((col - (cols - 1) / 2.0) * step, 0, (row - (rows - 1) / 2.0) * step)


func _screen_row(row: int, col: int, cols: int, rows: int, dx: float, dz: float) -> Vector3:
	## 화면 가로줄(기본 카메라 45° 기준)에 맞춰 세운다. 가족 세대를 줄로 보이게 할 때 쓴다.
	var yaw := deg_to_rad(45.0)
	var right := Vector3(cos(yaw), 0, -sin(yaw))
	var toward := Vector3(sin(yaw), 0, cos(yaw))
	return right * (col - (cols - 1) / 2.0) * dx + toward * (row - (rows - 1) / 2.0) * dz


func _make_crowd(mood: String) -> void:
	var cols := 8
	var rows := 6
	var counts := {}
	var looks: Array = []
	var rerolled := 0
	for k in cols * rows:
		var rng := DetRng.make([world_seed, k, "crowd"])
		var g := Genome.random(rng, rng.randi_range(2, 4))
		var social := _pick_social(rng)
		var occ: String = DetRng.pick(rng, PersonLook.OCCUPATIONS[social])
		var look := PersonLook.make(k, g, _pick_age(rng), social, occ, mood, world_seed)
		# 서명 중복 규칙: 같은 서명은 최대 2명. 셋째부터 유전이 아닌 요소를 다시 뽑는다
		var tries := 0
		while counts.get(look.signature(), 0) >= 2 and tries < 12:
			look.reroll_non_genetic(DetRng.make([world_seed, k, "reroll", tries]))
			tries += 1
		if tries > 0:
			rerolled += 1
		counts[look.signature()] = counts.get(look.signature(), 0) + 1
		looks.append(look)
	var max_dup := 0
	for v in counts.values():
		max_dup = max(max_dup, v)
	for k in looks.size():
		_place(looks[k], _world_grid(k / cols, k % cols, cols, rows, CROWD_STEP))
	_status.text = "무작위 %d명 · 외형 서명 %d종 · 같은 서명 최대 %d명 · 다시 뽑은 사람 %d명" % [looks.size(), counts.size(), max_dup, rerolled]


func _make_family(mood: String) -> void:
	var rng := DetRng.make([world_seed, "family"])
	var gpa_f := Genome.random(rng, 2)
	var gma_f := Genome.random(rng, 2)
	var gpa_m := Genome.random(rng, 4)
	var gma_m := Genome.random(rng, 4)
	gpa_f.male = true
	gpa_m.male = true
	gma_f.male = false
	gma_m.male = false
	var father := Genome.child(gpa_f, gma_f, rng)
	father.male = true
	var mother := Genome.child(gpa_m, gma_m, rng)
	mother.male = false
	var kids: Array = []
	for i in 5:
		kids.append(Genome.child(father, mother, rng))
	var social := _pick_social(rng)
	var occ: String = DetRng.pick(rng, PersonLook.OCCUPATIONS[social])
	var rows := [[gpa_f, gma_f, gpa_m, gma_m], [father, mother], kids]
	var ages := [[70, 66, 64, 61], [42, 38], [16, 13, 10, 6, 2]]
	var pid := 0
	for r in rows.size():
		var n: int = rows[r].size()
		for c in n:
			var age: int = ages[r][c]
			var o := occ if age >= 16 else "농부"
			var look := PersonLook.make(1000 + pid, rows[r][c], age, social, o, mood, world_seed)
			_place(look, _screen_row(r, c, n, 3, 1.5, 2.6))
			pid += 1
	_status.text = "가족 3대 · 윗줄: 친가 조부모, 외가 조부모 · 가운데: 부모 · 아랫줄: 자녀 5명 (머리색, 눈색, 피부, 얼굴형, 키, 골격이 유전된다)"


# ---------------------------------------------------------------- 입력

func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventKey and e.pressed and not e.echo:
		if e.keycode == KEY_Q:
			_yaw -= 90.0
			_apply_camera()
		elif e.keycode == KEY_E:
			_yaw += 90.0
			_apply_camera()
	elif e is InputEventMouseButton:
		if e.button_index == MOUSE_BUTTON_RIGHT or e.button_index == MOUSE_BUTTON_MIDDLE:
			_drag = e.pressed
		elif e.pressed and e.button_index == MOUSE_BUTTON_WHEEL_UP:
			zoom = mini(3, zoom + 1)
			_apply_camera()
		elif e.pressed and e.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			zoom = maxi(1, zoom - 1)
			_apply_camera()
	elif e is InputEventMouseMotion:
		if _drag:
			_pan_screen(-e.relative / SHRINK)
		_hover(e.position)


func _pan_screen(d: Vector2) -> void:
	## 화면 픽셀(내부 해상도) 이동량 → 땅 위 이동. 화면 세로 1m는 땅 깊이 1/sin30° = 2m.
	var m_per_px := 1.0 / ((PX_PER_M / cos(deg_to_rad(45.0))) * zoom)
	var right := _pivot.global_transform.basis.x
	var fwd := -_pivot.global_transform.basis.z
	_pan += right * d.x * m_per_px - fwd * d.y * m_per_px / sin(deg_to_rad(30.0))
	_apply_camera()


func _hover(screen_pos: Vector2) -> void:
	var p := screen_pos / SHRINK
	var origin := _cam.project_ray_origin(p)
	var dir := _cam.project_ray_normal(p)
	if absf(dir.y) < 1e-4:
		return
	var t := (0.6 - origin.y) / dir.y
	var hit := origin + dir * t
	var best = null
	var best_pos := Vector3.ZERO
	var best_d := 0.6
	for item in _people:
		var d := Vector2(hit.x - item[1].x, hit.z - item[1].z).length()
		if d < best_d:
			best_d = d
			best = item[0]
			best_pos = item[1]
	_hl.visible = best != null
	if best != null:
		_hl.position = Vector3(best_pos.x, 0.01, best_pos.z)
		_info.text = (best as PersonLook).describe()


# ---------------------------------------------------------------- 캡처

func _process(dt: float) -> void:
	var k := Vector2.ZERO
	if Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT):
		k.x -= 1
	if Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT):
		k.x += 1
	if Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP):
		k.y -= 1
	if Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN):
		k.y += 1
	if k != Vector2.ZERO:
		_pan_screen(k * 160.0 * dt)
	if _screenshot == "":
		return
	_frames += 1
	if _frames == 3 and _hover_at.x >= 0.0:
		_hover(_hover_at)
	if _frames == 6:
		await RenderingServer.frame_post_draw
		var img := get_viewport().get_texture().get_image()
		img.save_png(_screenshot)
		print("saved ", _screenshot)
		get_tree().quit()
