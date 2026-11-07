class_name Citizen
extends Node3D
## 지역 맵의 인물 하나: 외형, 이동, 행동 큐(12번 3절, 최대 5칸), 상호작용 수행.
## 이동은 지점을 찍으면 곧장 간다(우클릭). 상호작용은 대상의 앞(대상이 나를 향해 돌아선 뒤 그 정면)으로 가서 마주 보고 한다.

signal queue_changed(c: Citizen)
signal finished(c: Citizen, result: Dictionary)

enum State { IDLE, MOVING, APPROACH, WAIT, PERFORM }

const QUEUE_MAX := 5
const ACCEL := 8.0            ## m/s². 0에서 걷는 속도까지 약 0.18초
const ARRIVE := 0.05
const PERSONAL := 0.55        ## 다른 사람과 이보다 가까우면 옆으로 비킨다
const WAIT_DIST := 1.6        ## 상대가 다른 사람과 이야기 중이면 이 거리에서 기다린다

var pid := 0
var look: PersonLook
var display_name := ""
var household := false
var autonomy := true          ## 큐가 비면 근처를 거닌다(12번 3절 자율 행동 "낮음"의 자리 표시)
var game: Node                ## 판정(resolve)과 이웃 찾기를 맡는 장면 루트

var model: Node3D
var rig: PersonRig
var face_tex: ImageTexture
var height_m := 1.3
var walk_speed := 1.4

var heading := 0.0            ## 라디안. 0 = +z를 본다
var speed := 0.0
var dest := Vector3.ZERO
var has_dest := false
var face_point: Variant = null   ## 서 있을 때 바라볼 곳
var state := State.IDLE
var queue: Array = []         ## {"action": Dictionary, "target": Citizen, "progress": float, "front": Vector3, "claimed": bool}
var engaged_by: Citizen = null
var perform_t := 0.0
var mood_t := 0.0
var bubble_icon := ""         ## 머리 위 말풍선 아이콘 이름("" = 없음). UI가 그린다
var bubble_t := 0.0
var home := Vector3.ZERO
var wander_radius := 6.0
var _wander_wait := 0.0
var _strolling := false
var _rng: RandomNumberGenerator
var _turn_err := 0.0


func setup(id: int, l: PersonLook, name_text: String, in_household: bool, root: Node) -> void:
	pid = id
	look = l
	display_name = name_text
	household = in_household
	game = root
	face_tex = ImageTexture.create_from_image(PersonBuilder.face_image(look))
	model = PersonBuilder.build(look, face_tex)
	add_child(model)
	rig = PersonRig.attach(model, look)
	height_m = model.get_meta("height_m")
	if look.age < 3:
		walk_speed = 0.7
	elif look.age < 13:
		walk_speed = 1.15
	elif look.age >= 70:
		walk_speed = 0.95
	_rng = DetRng.make([pid, "citizen"])
	_wander_wait = _rng.randf_range(0.5, 4.0)


# ---------------------------------------------------------------- 명령

func command_move(p: Vector3) -> void:
	## 우클릭 이동: 큐를 비우고 곧장 간다.
	clear_queue()
	_go(p)
	face_point = null
	state = State.MOVING
	_strolling = false


func command_front_of(t: Citizen) -> void:
	## 사람을 우클릭: 그 사람이 지금 보는 쪽의 정면으로 간다(말은 걸지 않는다).
	clear_queue()
	var fwd := Vector3(sin(t.heading), 0, cos(t.heading))
	_go(t.position + fwd * front_distance())
	face_point = t
	state = State.MOVING
	_strolling = false


func enqueue(action: Dictionary, target: Citizen) -> bool:
	if queue.size() >= QUEUE_MAX:
		return false
	queue.append({"action": action, "target": target, "progress": 0.0, "front": Vector3.ZERO, "claimed": false})
	queue_changed.emit(self)
	return true


func cancel(i: int) -> void:
	if i < 0 or i >= queue.size():
		return
	var it: Dictionary = queue[i]
	if i == 0:
		_release(it)
		state = State.IDLE
		has_dest = false
	queue.remove_at(i)
	queue_changed.emit(self)


func clear_queue() -> void:
	if queue.size() > 0:
		_release(queue[0])
	queue.clear()
	queue_changed.emit(self)


func set_mood(m: String, seconds: float) -> void:
	look.apply_mood(m)
	face_tex.update(PersonBuilder.face_image(look))
	mood_t = seconds


func show_bubble(icon: String, seconds: float) -> void:
	bubble_icon = icon
	bubble_t = seconds


func is_busy() -> bool:
	return engaged_by != null or queue.size() > 0


static func front_distance() -> float:
	return float(DataDB.json("res://data/interactions.json")["front_distance_m"])


# ---------------------------------------------------------------- 상대 쪽

func engage(by: Citizen) -> void:
	## 누가 말을 걸러 온다: 하던 걸음을 멈추고 그 사람을 향해 돈다.
	engaged_by = by
	has_dest = false
	_strolling = false
	face_point = by


func release(by: Citizen) -> void:
	if engaged_by == by:
		engaged_by = null
		face_point = null
		rig.talk_target = 0.0
		_wander_wait = _rng.randf_range(1.0, 3.0)


func _release(it: Dictionary) -> void:
	var t: Citizen = it["target"]
	if it["claimed"] and is_instance_valid(t):
		t.release(self)
	it["claimed"] = false
	rig.talk_target = 0.0


# ---------------------------------------------------------------- 매 틱

func tick(dt: float) -> void:
	_think(dt)
	_move(dt)
	rig.update(dt, speed, _turn_err)
	if mood_t > 0.0:
		mood_t -= dt
		if mood_t <= 0.0:
			set_mood("평소", 0.0)
	if bubble_t > 0.0:
		bubble_t -= dt
		if bubble_t <= 0.0:
			bubble_icon = ""


func _go(p: Vector3) -> void:
	dest = Vector3(p.x, 0, p.z)
	has_dest = true


func _think(dt: float) -> void:
	if engaged_by != null:
		return
	if queue.size() > 0:
		_run_item(dt, queue[0])
		return
	if state == State.MOVING and not has_dest:
		state = State.IDLE
	if state != State.IDLE or not autonomy:
		return
	# 자율: 집 근처를 천천히 거닌다
	if not has_dest:
		_wander_wait -= dt
		if _wander_wait <= 0.0:
			var a := _rng.randf() * TAU
			var r := sqrt(_rng.randf()) * wander_radius
			_go(home + Vector3(cos(a) * r, 0, sin(a) * r))
			_strolling = true
			_wander_wait = _rng.randf_range(2.0, 7.0)


func _run_item(dt: float, it: Dictionary) -> void:
	var t: Citizen = it["target"]
	if not is_instance_valid(t):
		cancel(0)
		return
	var a: Dictionary = it["action"]
	_strolling = false
	if not it["claimed"]:
		if t.engaged_by != null and t.engaged_by != self:
			# 상대가 다른 사람과 이야기 중: 조금 떨어져 기다린다
			state = State.WAIT
			var away := position - t.position
			away.y = 0
			if away.length() > WAIT_DIST + 0.2:
				_go(t.position + away.normalized() * WAIT_DIST)
			face_point = t
			show_bubble("기다림", 0.3)
			return
		# 상대를 붙잡는다: 상대가 나를 향해 돌아서고, 나는 그 정면으로 간다
		t.engage(self)
		it["claimed"] = true
		var dir := position - t.position
		dir.y = 0
		if dir.length() < 0.01:
			dir = Vector3(0, 0, 1)
		it["front"] = t.position + dir.normalized() * front_distance()
		_go(it["front"])
		face_point = null
		state = State.APPROACH
	if state == State.APPROACH or state == State.WAIT:
		if has_dest:
			return
		# 도착: 마주 보고 시작
		state = State.PERFORM
		perform_t = 0.0
		face_point = t
		rig.talk_target = 1.0
		t.rig.talk_target = 1.0
	if state == State.PERFORM:
		var dur: float = float(a["slots"]) * float(InteractionRules.data()["seconds_per_slot"])
		perform_t += dt
		it["progress"] = clampf(perform_t / dur, 0.0, 1.0)
		# 말풍선을 번갈아 띄운다(1.2초마다)
		var turn := int(perform_t / 1.2) % 2
		if turn == 0:
			show_bubble(a["icon"], 0.15)
		else:
			t.show_bubble("잡담", 0.15)
		if perform_t >= dur:
			var res: Dictionary = game.resolve(self, t, a)
			_release(it)
			queue.pop_front()
			state = State.IDLE
			face_point = null
			queue_changed.emit(self)
			finished.emit(self, res)


func _move(dt: float) -> void:
	var desired := Vector3.ZERO
	var target_speed := 0.0
	if has_dest:
		var to := dest - position
		to.y = 0
		var d := to.length()
		if d < ARRIVE:
			has_dest = false
		else:
			desired = to / d
			var top := walk_speed * (0.7 if _strolling else 1.0)
			target_speed = minf(top, d * 3.0 + 0.15)   # 도착 직전 감속
	if desired != Vector3.ZERO:
		desired = (desired + game.separation(self) * 0.9).normalized()
	speed = move_toward(speed, target_speed, ACCEL * dt)
	if speed > 0.0 and desired != Vector3.ZERO:
		position += desired * speed * dt
	elif target_speed == 0.0:
		speed = 0.0
	rig.set_moving(has_dest)

	# 방향: 움직이면 진행 방향, 서 있으면 바라볼 곳
	var want := heading
	if desired != Vector3.ZERO and speed > 0.05:
		want = atan2(desired.x, desired.z)
	elif face_point != null:
		var fp: Vector3 = face_point.position if face_point is Citizen else face_point
		var v := fp - position
		if Vector2(v.x, v.z).length() > 0.05:
			want = atan2(v.x, v.z)
	_turn_err = angle_difference(heading, want)
	heading = lerp_angle(heading, want, 1.0 - exp(-dt * 12.0))
	rotation.y = heading
