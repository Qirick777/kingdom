class_name PersonRig
extends RefCounted
## 블록 인물의 걸음, 멈춤, 돌기, 말하기, 숨쉬기를 절차적으로 움직인다.
## 자연스러운 움직임 수칙:
##  1) 걸음마다 골반, 몸통, 머리, 양팔이 모두 반응한다.
##  2) 무거운 부위(골반, 몸통)는 먼저 시작해 길게, 가벼운 부위(팔, 머리)는 늦게 시작해 짧게 움직인다.
##     흔들림마다 위상과 곡선 모양을 다르게 둔다(같은 순간에 정점을 찍지 않는다).
##     엉덩이 정점을 0으로 둔 정점 위상: 골반 비틀림 .07, 골반 기울기 .15, 골반 높이 .30/.80, 고개 끄덕임 .22/.72,
##     머리 돌림 .4, 팔 .57, 몸통 비틀림 .65, 몸통 기울기 .75
##  3) 멈출 때 몸통은 관성으로 앞으로 쏠렸다가 돌아오고, 부위마다 가라앉는 시간이 다르다.
## 각도는 도, 길이는 텍셀(1/16m) 단위다.

const LEG_SWING := 32.0        ## 엉덩이 앞뒤 흔들림
const ARM_SWING := 20.0        ## 어깨 앞뒤 흔들림
const PELVIS_BOB := 0.55       ## 골반 위아래(텍셀)
const PELVIS_ROLL := 2.0       ## 골반 좌우 기울기
const PELVIS_YAW := 5.0        ## 골반 비틀림
const TORSO_COUNTER := 0.6     ## 몸통이 골반 반대로 비트는 비율
const HEAD_PASS := 0.15        ## 몸 비틀림 중 머리에 전달되는 비율(나머지는 시선 유지로 상쇄)
const WALK_LEAN := 4.0         ## 걸을 때 몸통 앞기울기

## 부위별 [시작 지연 s, 켜지는 시간 s, 꺼지는 시간 s]. 무거운 부위가 먼저 시작하고 늦게 끝난다.
const ENV := {
	"pelvis": [0.00, 0.30, 0.38],
	"legs":   [0.02, 0.14, 0.16],
	"arms":   [0.08, 0.20, 0.50],
	"head":   [0.10, 0.18, 0.62],
}

var pelvis: Node3D
var upper: Node3D
var head: Node3D
var hip_n: Node3D
var hip_p: Node3D
var arm_n: Node3D
var arm_p: Node3D
var leg_h := 6.0
var lean_base := 0.0
var step_len_m := 0.4         ## 한 걸음 길이(m). 걸음 위상은 이동 거리에서 나온다(발 미끄러짐 방지)

var phase := 0.0              ## 0~1 = 두 걸음
var moving := false
var _since_change := 10.0
var env := {"pelvis": 0.0, "legs": 0.0, "arms": 0.0, "head": 0.0}
var talk := 0.0               ## 말하기 세기 0~1
var talk_target := 0.0
var _t := 0.0
var _speed_s := 0.0           ## 다듬은 속도
var _prev_speed := 0.0
## 몸통 앞기울기 스프링 (관성)
var _lean := 0.0
var _lean_v := 0.0
## 머리 앞질러 보기(돌 때 머리가 먼저 돈다)
var _look := 0.0
var _look_v := 0.0
var _seed := 0.0
var _arm_walk := 0.0           ## 검사용: 숨쉬기를 뺀 팔 흔들림


static func attach(root: Node3D, look: PersonLook) -> PersonRig:
	var r := PersonRig.new()
	r.pelvis = root.get_node("Body/Pelvis")
	r.upper = r.pelvis.get_node("Upper")
	r.head = r.upper.get_node("Head")
	r.hip_n = r.pelvis.get_node_or_null("HipN")
	r.hip_p = r.pelvis.get_node_or_null("HipP")
	r.arm_n = r.upper.get_node("ArmN")
	r.arm_p = r.upper.get_node("ArmP")
	r.leg_h = root.get_meta("leg_h")
	r.lean_base = root.get_meta("lean")
	var leg_m: float = (r.leg_h + 0.5) * PersonBuilder.TEXEL * look.body_scale
	r.step_len_m = 2.0 * leg_m * sin(deg_to_rad(LEG_SWING))
	r._seed = float(look.id % 97) * 0.173   # 사람마다 숨 위상을 다르게
	return r


func set_moving(m: bool) -> void:
	if m != moving:
		moving = m
		_since_change = 0.0


static func _smooth(x: float) -> float:
	x = clampf(x, 0.0, 1.0)
	return x * x * (3.0 - 2.0 * x)


func update(dt: float, speed_mps: float, turn_err_rad: float) -> void:
	## speed_mps: 실제 이동 속도. turn_err_rad: 가려는 방향과 지금 몸 방향의 차(머리가 먼저 돈다).
	_t += dt
	_since_change += dt
	_speed_s = lerpf(_speed_s, speed_mps, 1.0 - exp(-dt * 10.0))
	var accel := (_speed_s - _prev_speed) / maxf(dt, 1e-4)
	_prev_speed = _speed_s
	phase = fmod(phase + speed_mps * dt / (2.0 * step_len_m), 1.0)

	for k in env.keys():
		var e: Array = ENV[k]
		if moving:
			if _since_change >= e[0]:
				env[k] = minf(1.0, env[k] + dt / e[1])
		else:
			env[k] = maxf(0.0, env[k] - dt / e[2])
	talk = move_toward(talk, talk_target, dt / 0.25)

	var ep := _smooth(env["pelvis"])
	var el := _smooth(env["legs"])
	var ea := _smooth(env["arms"])
	var eh := _smooth(env["head"])
	var ph := phase

	# ---- 다리: 사인에 2배음을 조금 섞어 앞으로 뻗을 때가 더 빠르다
	var leg := LEG_SWING * el * (sin(TAU * ph) + 0.12 * sin(2.0 * TAU * ph))
	if hip_n != null:
		hip_n.rotation_degrees.x = leg
		hip_p.rotation_degrees.x = -leg

	# ---- 골반: 다리가 모일 때 높고 벌어질 때 낮다. 시작할 때 살짝 내려앉는다(예비동작)
	var bob := PELVIS_BOB * ep * cos(2.0 * TAU * (ph - 0.015))
	var dip := 0.0
	if moving and env["pelvis"] < 1.0:
		dip = -0.45 * sin(PI * env["pelvis"])
	pelvis.position.y = leg_h + bob + dip
	var p_roll := PELVIS_ROLL * ep * sin(TAU * (ph - 0.115))
	var p_yaw := PELVIS_YAW * ep * sin(TAU * (ph - 0.035))
	pelvis.rotation_degrees = Vector3(0, p_yaw, p_roll)

	# ---- 몸통: 골반 반대로 비틀고, 늦게 따라온다. 앞기울기는 스프링(관성)
	var t_yaw := -TORSO_COUNTER * PELVIS_YAW * ep * sin(TAU * (ph - 0.115))
	var t_roll := -0.5 * PELVIS_ROLL * ep * sin(TAU * (ph - 0.215))
	var lean_target := WALK_LEAN * ep + talk * 3.0
	var decel := maxf(0.0, -accel)
	var w := 9.0
	var zeta := 0.42
	_lean_v += (-(w * w) * (_lean - lean_target) - 2.0 * zeta * w * _lean_v + decel * 9.0) * dt
	_lean += _lean_v * dt
	var breath := 0.8 * sin(TAU * (_t * 0.27 + _seed))
	upper.rotation_degrees = Vector3(lean_base + _lean + breath * (1.0 - ep), t_yaw, t_roll)

	# ---- 머리: 몸 비틀림을 대부분 상쇄해 시선을 지키고(15%만 전달), 돌 때는 먼저 돈다
	var look_target := clampf(rad_to_deg(turn_err_rad) * 0.5, -35.0, 35.0)
	var wl := 20.0
	_look_v += (-(wl * wl) * (_look - look_target) - 2.0 * 0.7 * wl * _look_v) * dt
	_look += _look_v * dt
	var body_yaw := p_yaw + t_yaw
	var h_yaw := -(1.0 - HEAD_PASS) * body_yaw * eh + _look
	var nod := 1.5 * eh * cos(2.0 * TAU * (ph - 0.435))
	var talk_nod := talk * 4.0 * maxf(0.0, sin(TAU * (_t * 1.3 + _seed)))
	head.rotation_degrees = Vector3(nod + talk_nod - 0.3 * _lean, h_yaw, -0.6 * t_roll)

	# ---- 팔: 같은 쪽 다리와 반대. 늦은 위상, 다리와 다른 곡선. 말할 때는 P팔로 손짓
	var arm := ARM_SWING * ea * (sin(TAU * (ph - 0.03)) - 0.1 * sin(2.0 * TAU * (ph - 0.03)))
	_arm_walk = -arm
	var idle_arm := 1.2 * sin(TAU * (_t * 0.27 + _seed - 0.12)) * (1.0 - ea)
	var gesture := -28.0 * talk * maxf(0.0, sin(TAU * (_t * 0.7 + _seed)))
	arm_n.rotation_degrees = Vector3(-arm + idle_arm, 0, -2.0 * ea - 1.5)
	arm_p.rotation_degrees = Vector3(arm + idle_arm + gesture, 0, 2.0 * ea + 1.5)


func pose_record() -> Dictionary:
	## 수치 검사용: 부위별 각도
	return {
		"hip": hip_n.rotation_degrees.x if hip_n != null else 0.0,
		"pelvis_y": pelvis.position.y - leg_h,
		"pelvis_yaw": pelvis.rotation_degrees.y,
		"pelvis_roll": pelvis.rotation_degrees.z,
		"torso_pitch": upper.rotation_degrees.x - lean_base,
		"torso_yaw": upper.rotation_degrees.y,
		"head_yaw": head.rotation_degrees.y,
		"head_pitch": head.rotation_degrees.x,
		"arm": arm_n.rotation_degrees.x,
		"lean": _lean,
		"arm_walk": _arm_walk,
	}
