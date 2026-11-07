extends Control
## 가구 조작 시험장 (12번 1~3절, 6절).
## 내 가구원 중 한 명을 골라 직접 움직인다(초상화 클릭). 가구 밖 사람은 상호작용으로만 움직인다.
##  우클릭 땅: 그 지점으로 곧장 걸어간다(큐를 비운다).
##  우클릭 사람: 그 사람이 보는 쪽 정면으로 간다.
##  좌클릭 사람: 파이 메뉴 → 행동을 큐(최대 5칸)에 넣는다. 수행할 때 대상이 나를 향해 돌아서고, 나는 그 정면으로 가서 마주 본다.
##
## 명령줄(-- 뒤): --seed=N --demo --pose=경로.csv --shots=폴더 --screenshot=경로.png

const GROUND_M := 64.0
const VILLAGERS := 16
const EDGE_PX := 6.0
const EDGE_SPEED := 260.0     ## 가장자리 스크롤, 내부 픽셀/초

var world_seed := 1
var iso: IsoView
var rel := Relations.new()
var citizens: Array = []
var household: Array = []
var active: Citizen
var sim_speed := 1.0
var follow := true
var hud: HouseholdHud
var pie: PieMenu
var _judge_rng: RandomNumberGenerator
var _sel_ring: MeshInstance3D
var _hover_ring: MeshInstance3D
var _marker: MeshInstance3D
var _marker_t := 0.0
var _hover: Citizen
var _drag := false
var _pid_map := {}
var _cursor_hand := false

# 시연과 캡처
var _demo := false
var _pose_path := ""
var _pose_lines: PackedStringArray = []
var _shots_dir := ""
var _screenshot := ""
var _t := 0.0
var _frames := 0
var _demo_state := {}


func _ready() -> void:
	_parse_args()
	theme = PixelTheme.make()
	iso = IsoView.create(self)
	_judge_rng = DetRng.make([world_seed, "judge"])
	var lot := Rect2(-5, -4, 10, 8)
	iso.world.add_child(GroundBuilder.build(world_seed, GROUND_M, [
		[Rect2(-1, 4, 2, 40), "흙길"], [Rect2(5, -1, 40, 2), "흙길"], [lot, "흙"]]))
	_sel_ring = _ring_mesh(GroundBuilder.ring_texture(16, 5.0, 7.5, Color(1.0, 0.83, 0.3, 0.95)), 1.0)
	_hover_ring = _ring_mesh(GroundBuilder.ring_texture(16, 5.5, 7.5, Color(1, 1, 1, 0.8)), 1.0)
	_marker = _ring_mesh(GroundBuilder.ring_texture(16, 5.0, 7.5, Color("#8fd16a")), 0.9)
	_marker.visible = false
	_spawn()
	hud = HouseholdHud.new()
	hud.game = self
	add_child(hud)
	hud.set_household(household)
	hud.member_clicked.connect(func(c): select(c))
	hud.queue_slot_clicked.connect(func(i): if active != null: active.cancel(i))
	hud.speed_chosen.connect(set_speed)
	pie = PieMenu.new()
	add_child(pie)
	pie.chosen.connect(_on_pie)
	for c in citizens:
		(c as Citizen).queue_changed.connect(func(cz): hud.refresh_queue(cz))
	select(household[0])
	set_speed(1.0)
	hud.notify("%s 가구를 맡았다. 아래 초상화를 눌러 가구원을 고른다." % household[0].display_name.substr(0, 1))
	iso.focus = active.position
	iso.apply()


func _parse_args() -> void:
	for a in OS.get_cmdline_user_args():
		var kv: PackedStringArray = a.trim_prefix("--").split("=", true, 1)
		match kv[0]:
			"seed":
				world_seed = int(kv[1])
			"demo":
				_demo = true
			"pose":
				_pose_path = kv[1]
			"shots":
				_shots_dir = kv[1]
			"screenshot":
				_screenshot = kv[1]


# ---------------------------------------------------------------- 인물 만들기

func _name(rng: RandomNumberGenerator, male: bool, surname: String) -> String:
	var n: Dictionary = DataDB.json("res://data/names.json")
	var a: Array = n["male_first"] if male else n["female_first"]
	var b: Array = n["male_second"] if male else n["female_second"]
	return surname + DetRng.pick(rng, a) + DetRng.pick(rng, b)


func _add(look: PersonLook, name_text: String, hh: bool, pos: Vector3) -> Citizen:
	var c := Citizen.new()
	iso.world.add_child(c)
	c.setup(look.id, look, name_text, hh, self)
	c.position = pos
	c.home = pos
	c.heading = DetRng.make([look.id, "facing"]).randf() * TAU
	c.rotation.y = c.heading
	citizens.append(c)
	_pid_map[c.pid] = c
	return c


func _spawn() -> void:
	var r := DetRng.make([world_seed, "household"])
	var names: Dictionary = DataDB.json("res://data/names.json")
	var fam: String = DetRng.pick(r, names["surnames"])
	var gpa := Genome.random(r, 2)
	gpa.male = true
	var gma := Genome.random(r, 2)
	gma.male = false
	var father := Genome.child(gpa, gma, r)
	father.male = true
	var mother := Genome.random(r, 3)
	mother.male = false
	var kids: Array = []
	for male in [true, false, true]:
		var g := Genome.child(father, mother, r)
		g.male = male
		kids.append(g)
	# 가구주, 배우자, 자녀 셋, 가구주의 어머니(12번 1절 기본 구성)
	var rows := [
		[father, 42, fam, Vector3(0.0, 0, 0.8)],
		[mother, 38, DetRng.pick(r, names["surnames"]), Vector3(1.2, 0, 0.2)],
		[kids[0], 16, fam, Vector3(-1.4, 0, -0.6)],
		[kids[1], 13, fam, Vector3(-0.2, 0, -1.6)],
		[kids[2], 6, fam, Vector3(1.6, 0, -1.4)],
		[gma, 66, DetRng.pick(r, names["surnames"]), Vector3(-2.2, 0, 1.2)],
	]
	for i in rows.size():
		var row: Array = rows[i]
		var g: Genome = row[0]
		var age: int = row[1]
		var look := PersonLook.make(100 + i, g, age, "평민", "농부", "평소", world_seed)
		var c := _add(look, _name(r, g.male, row[2]), true, row[3])
		c.wander_radius = 3.5
		c.home = Vector3.ZERO
		household.append(c)
	rel.link(household[0].pid, household[1].pid, "배우자")
	# 마을 사람
	for k in VILLAGERS:
		var vr := DetRng.make([world_seed, k, "villager"])
		var g := Genome.random(vr, vr.randi_range(2, 4))
		var social: String = DetRng.pick_weighted(vr, PersonLook.SOCIAL, [0.1, 0.5, 0.15, 0.15, 0.1])
		var occ: String = DetRng.pick(vr, PersonLook.OCCUPATIONS[social])
		var age := vr.randi_range(8, 70)
		var look := PersonLook.make(1000 + k, g, age, social, occ, "평소", world_seed)
		var ang := vr.randf() * TAU
		var rad := vr.randf_range(6.5, 16.0)
		var c := _add(look, _name(vr, g.male, DetRng.pick(vr, names["surnames"])), false, Vector3(cos(ang) * rad, 0, sin(ang) * rad))
		c.wander_radius = 5.0


func by_pid(p: int) -> Citizen:
	return _pid_map.get(p)


func _ring_mesh(tex: ImageTexture, size: float) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(size, size)
	mi.mesh = pm
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.albedo_texture = tex
	m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
	mi.material_override = m
	mi.position.y = 0.012
	iso.world.add_child(mi)
	return mi


# ---------------------------------------------------------------- 게임 규칙 연결

func select(c: Citizen) -> void:
	## 가구원만 고를 수 있다(12번 1절). 고른 사람은 자율 행동을 멈추고 지시를 기다린다.
	if not c.household:
		return
	if active != null:
		active.autonomy = true
	active = c
	c.autonomy = false
	if c.state == Citizen.State.IDLE and c._strolling:
		c.has_dest = false
	hud.show_active(c)
	follow = true


func set_speed(s: float) -> void:
	sim_speed = s
	hud.show_speed(s)


func separation(c: Citizen) -> Vector3:
	## 걷는 사람이 가까운 사람을 옆으로 비켜 가게 하는 힘
	var push := Vector3.ZERO
	for o in citizens:
		if o == c:
			continue
		var d: Vector3 = c.position - (o as Citizen).position
		d.y = 0
		var l := d.length()
		if l < Citizen.PERSONAL and l > 0.001:
			push += d / l * (1.0 - l / Citizen.PERSONAL)
	return push


func resolve(actor: Citizen, target: Citizen, a: Dictionary) -> Dictionary:
	var res := InteractionRules.resolve(actor, target, a, rel, _judge_rng)
	var show: Dictionary = res["show"]
	if show.has("target"):
		target.set_mood(show["target"], 6.0)
	if show.has("actor"):
		actor.set_mood(show["actor"], 6.0)
	if res["ok"]:
		target.show_bubble(a["icon"], 1.6)
	else:
		actor.show_bubble("실패", 1.6)
	hud.notify(res["text"], res["calc"])
	hud.refresh_active()
	return res


func _on_pie(kind: String, payload: Variant, target: Citizen) -> void:
	if kind == "control":
		select(target)
		return
	if active == null:
		return
	if not active.enqueue(payload, target):
		hud.notify("행동 큐가 가득 찼다(최대 %d칸)." % Citizen.QUEUE_MAX)


func open_pie(target: Citizen, at: Vector2) -> void:
	var cats := InteractionRules.by_category(active, target) if target != active else {}
	var extra: Array = []
	if target.household and target != active:
		extra.append("조종하기")
	pie.open(at, target, cats, extra)


# ---------------------------------------------------------------- 입력

func pick(screen_pos: Vector2) -> Citizen:
	## 화면 좌표 → 가장 앞에 있는 사람. 사람을 세로 원기둥으로 보고 광선과 만나는지 본다.
	var r := iso.ray(screen_pos)
	var o: Vector3 = r[0]
	var d: Vector3 = r[1]
	var best: Citizen = null
	var best_t := INF
	for c in citizens:
		var cz: Citizen = c
		var rad := 0.3 * cz.look.body_scale
		var h := cz.height_m + 0.1
		var ox := o.x - cz.position.x
		var oz := o.z - cz.position.z
		var a := d.x * d.x + d.z * d.z
		var b := 2.0 * (ox * d.x + oz * d.z)
		var cc := ox * ox + oz * oz - rad * rad
		var disc := b * b - 4.0 * a * cc
		if disc < 0.0 or a < 1e-8:
			continue
		var sq := sqrt(disc)
		for t in [(-b - sq) / (2.0 * a), (-b + sq) / (2.0 * a)]:
			var y: float = o.y + d.y * t - cz.position.y
			if y >= 0.0 and y <= h and t < best_t:
				best_t = t
				best = cz
				break
		# 윗면(정수리)
		if absf(d.y) > 1e-5:
			var tt := (cz.position.y + h - o.y) / d.y
			var px := o.x + d.x * tt - cz.position.x
			var pz := o.z + d.z * tt - cz.position.z
			if px * px + pz * pz <= rad * rad and tt < best_t:
				best_t = tt
				best = cz
	return best


func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventMouseButton:
		if e.button_index == MOUSE_BUTTON_MIDDLE:
			_drag = e.pressed
			if e.pressed:
				follow = false
			return
		if not e.pressed:
			return
		match e.button_index:
			MOUSE_BUTTON_WHEEL_UP:
				iso.zoom = mini(3, iso.zoom + 1)
				iso.apply()
			MOUSE_BUTTON_WHEEL_DOWN:
				iso.zoom = maxi(1, iso.zoom - 1)
				iso.apply()
			MOUSE_BUTTON_LEFT:
				var c := pick(e.position)
				if c != null:
					open_pie(c, e.position)
			MOUSE_BUTTON_RIGHT:
				_right_click(e.position)
	elif e is InputEventMouseMotion:
		if _drag:
			iso.pan_screen(-e.relative / IsoView.SHRINK)
	elif e is InputEventKey and e.pressed and not e.echo:
		match e.keycode:
			KEY_Q:
				iso.yaw -= 90.0
				iso.apply()
			KEY_E:
				iso.yaw += 90.0
				iso.apply()
			KEY_SPACE:
				follow = true
			KEY_P:
				set_speed(0.0 if sim_speed > 0.0 else 1.0)
			KEY_1:
				set_speed(1.0)
			KEY_2:
				set_speed(2.0)
			KEY_3:
				set_speed(4.0)


func _right_click(at: Vector2) -> void:
	if active == null:
		return
	var c := pick(at)
	if c != null and c != active:
		active.command_front_of(c)
		_flash_marker(active.dest)
		return
	var g: Variant = iso.ground_point(at)
	if g == null:
		return
	var p: Vector3 = g
	var lim := GROUND_M / 2.0 - 1.0
	p = Vector3(clampf(p.x, -lim, lim), 0, clampf(p.z, -lim, lim))
	active.command_move(p)
	_flash_marker(p)


func _flash_marker(p: Vector3) -> void:
	_marker.position = Vector3(p.x, 0.014, p.z)
	_marker_t = 0.45
	_marker.visible = true


# ---------------------------------------------------------------- 매 프레임

func _process(dt: float) -> void:
	_t += dt
	_frames += 1
	if _demo:
		_demo_step()
	var sdt := dt * sim_speed
	if sdt > 0.0:
		for c in citizens:
			(c as Citizen).tick(sdt)
	if _pose_path != "" and active != null:
		_record_pose()

	# 카메라: 고른 사람을 따라간다. 가장자리 스크롤이나 가운데 끌기를 하면 멈추고, Space로 다시 따라간다
	var mp := get_viewport().get_mouse_position()
	var vs := get_viewport_rect().size
	var edge := Vector2.ZERO
	if not _demo and Rect2(Vector2.ZERO, vs).has_point(mp) and DisplayServer.window_is_focused():
		if mp.x < EDGE_PX:
			edge.x = -1
		elif mp.x > vs.x - EDGE_PX:
			edge.x = 1
		if mp.y < EDGE_PX:
			edge.y = -1
		elif mp.y > vs.y - EDGE_PX:
			edge.y = 1
	if edge != Vector2.ZERO:
		follow = false
		iso.pan_screen(edge * EDGE_SPEED * dt)
	elif follow and active != null:
		iso.focus = iso.focus.lerp(active.position, 1.0 - exp(-dt * 6.0))
		iso.apply()

	# 바닥 표시
	if active != null:
		_sel_ring.position = Vector3(active.position.x, 0.012, active.position.z)
	if _marker_t > 0.0:
		_marker_t -= dt
		var k := clampf(_marker_t / 0.45, 0.0, 1.0)
		_marker.scale = Vector3.ONE * (0.4 + 0.6 * k)
		(_marker.material_override as StandardMaterial3D).albedo_color.a = k
		_marker.visible = _marker_t > 0.0

	# 마우스 올림
	var h: Citizen = null
	if not pie.visible:
		h = pick(mp) if not _demo else _demo_state.get("hover")
	_hover = h
	_hover_ring.visible = h != null and h != active
	if _hover_ring.visible:
		_hover_ring.position = Vector3(h.position.x, 0.013, h.position.z)
	hud.show_tip(h, mp if not _demo else _demo_state.get("hover_at", mp), active)
	var want_hand := h != null
	if want_hand != _cursor_hand:
		_cursor_hand = want_hand
		Input.set_custom_mouse_cursor(PixelTheme.scaled("res://assets/ui/cursor_interact.png" if want_hand else "res://assets/ui/cursor_default.png"))
	if active != null:
		hud.refresh_queue(active)
	if _screenshot != "" and _frames == 8:
		_save(_screenshot)
		get_tree().quit()


# ---------------------------------------------------------------- 시연 (캡처용 각본)

func _save(path: String) -> void:
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(path)
	print("saved ", path)


func _shot(name_text: String) -> void:
	if _shots_dir != "":
		_save(_shots_dir.path_join(name_text))


func _record_pose() -> void:
	if _pose_lines.is_empty():
		_pose_lines.append("t,moving,speed,hip,pelvis_y,pelvis_yaw,pelvis_roll,torso_pitch,torso_yaw,head_yaw,head_pitch,arm,lean,arm_walk")
	var p := active.rig.pose_record()
	_pose_lines.append("%.4f,%d,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f" % [
		_t, int(active.rig.moving), active.speed, p["hip"], p["pelvis_y"], p["pelvis_yaw"], p["pelvis_roll"],
		p["torso_pitch"], p["torso_yaw"], p["head_yaw"], p["head_pitch"], p["arm"], p["lean"], p["arm_walk"]])


func _demo_step() -> void:
	## 각본: 이동 → 마을 사람 클릭(파이 메뉴) → 잡담, 칭찬을 큐에 넣기 → 다가가 마주 보고 대화 → 결과 → 다른 가구원으로 바꿔 이동
	var s := _demo_state
	var ev := func(key: String, at: float) -> bool:
		if _t >= at and not s.has(key):
			s[key] = true
			return true
		return false
	if ev.call("move", 0.5):
		var p := active.position + Vector3(3.0, 0, 3.6)
		active.command_move(p)
		_flash_marker(p)
	if ev.call("shot_move", 1.2):
		_shot("01_move.png")
	if ev.call("pie", 4.6):
		var best: Citizen = null
		for c in citizens:
			var cz: Citizen = c
			if not cz.household and (best == null or cz.position.distance_to(active.position) < best.position.distance_to(active.position)):
				best = cz
		s["target"] = best
		s["hover"] = best
		s["hover_at"] = iso.to_screen(best.position + Vector3(0, best.height_m * 0.6, 0))
		open_pie(best, s["hover_at"])
	if ev.call("shot_pie", 5.0):
		_shot("02_pie.png")
	if ev.call("cat", 5.4):
		pie._show_actions("대화")
	if ev.call("shot_cat", 5.8):
		_shot("03_pie_actions.png")
	if ev.call("choose", 6.2):
		var acts: Array = InteractionRules.by_category(active, s["target"])["대화"]
		pie.chosen.emit("action", acts[0], s["target"])
		pie.chosen.emit("action", acts[1], s["target"])
		pie.close()
		s.erase("hover")
	if ev.call("shot_queue", 6.9):
		_shot("04_approach.png")
	if not s.has("perf_at") and active.state == Citizen.State.PERFORM:
		s["perf_at"] = _t
	if s.has("perf_at") and ev.call("shot_talk", s["perf_at"] + 1.6):
		_shot("05_talk.png")
	if s.has("perf_at") and ev.call("shot_result", s["perf_at"] + 4.3):
		_shot("06_result.png")
	if not s.has("done_at") and s.has("perf_at") and active.queue.is_empty() and active.state == Citizen.State.IDLE:
		s["done_at"] = _t
	if s.has("done_at") and ev.call("switch", s["done_at"] + 1.0):
		select(household[1])
		var p2 := active.position + Vector3(-3.0, 0, 2.5)
		active.command_move(p2)
		_flash_marker(p2)
	if s.has("done_at") and ev.call("shot_switch", s["done_at"] + 2.2):
		_shot("07_switch.png")
	if s.has("done_at") and ev.call("quit", s["done_at"] + 4.5):
		if _pose_path != "":
			var f := FileAccess.open(_pose_path, FileAccess.WRITE)
			f.store_string("\n".join(_pose_lines))
			f.close()
		get_tree().quit()
