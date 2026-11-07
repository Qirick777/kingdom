class_name IsoView
extends RefCounted
## 아이소 3D 화면: 640×360 서브뷰포트를 3배로 키운다. 직교 카메라, 수평 yaw, 아래 30°.
## 화면 좌표 ↔ 월드 변환을 한곳에 모은다.

const SHRINK := 3
const PX_PER_M := 16.0
const PITCH := 30.0

var container: SubViewportContainer
var viewport: SubViewport
var world: Node3D
var pivot: Node3D
var camera: Camera3D
var yaw := 45.0
var zoom := 2
var focus := Vector3.ZERO


static func create(parent: Control) -> IsoView:
	var v := IsoView.new()
	v.container = SubViewportContainer.new()
	v.container.stretch = true
	v.container.stretch_shrink = SHRINK
	v.container.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	v.container.set_anchors_preset(Control.PRESET_FULL_RECT)
	v.container.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(v.container)
	v.viewport = SubViewport.new()
	v.viewport.msaa_3d = Viewport.MSAA_DISABLED
	v.viewport.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_NEAREST
	v.container.add_child(v.viewport)
	v.world = Node3D.new()
	v.viewport.add_child(v.world)

	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("#bfe6ff")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(1, 1, 1)
	env.ambient_light_energy = 0.62
	var we := WorldEnvironment.new()
	we.environment = env
	v.world.add_child(we)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-62, 20, 0)
	sun.light_energy = 0.62
	v.world.add_child(sun)

	v.pivot = Node3D.new()
	v.world.add_child(v.pivot)
	v.camera = Camera3D.new()
	v.camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	v.camera.near = 0.1
	v.camera.far = 400.0
	v.pivot.add_child(v.camera)
	v.apply()
	return v


func px_per_m() -> float:
	## 화면(내부 해상도) 1m당 픽셀. 45° 돌린 격자 1m가 가로 32px(×1)이 되도록 맞춘다.
	return PX_PER_M / cos(deg_to_rad(45.0)) * zoom


func apply() -> void:
	pivot.position = focus
	pivot.rotation_degrees = Vector3(0, yaw, 0)
	camera.rotation_degrees = Vector3(-PITCH, 0, 0)
	camera.position = Basis.from_euler(Vector3(deg_to_rad(-PITCH), 0, 0)) * Vector3(0, 0, 60)
	camera.size = (1080.0 / SHRINK) / px_per_m()


func pan_screen(d: Vector2) -> void:
	## 화면 픽셀(내부 해상도) 이동량만큼 초점을 땅 위에서 옮긴다. 화면 세로 1m = 땅 깊이 1/sin30° m.
	var m := 1.0 / px_per_m()
	var right := pivot.global_transform.basis.x
	var fwd := -pivot.global_transform.basis.z
	focus += right * d.x * m - fwd * d.y * m / sin(deg_to_rad(PITCH))
	apply()


func ray(screen_pos: Vector2) -> Array:
	## [원점, 방향]. screen_pos는 창 좌표.
	var p := screen_pos / SHRINK
	return [camera.project_ray_origin(p), camera.project_ray_normal(p)]


func ground_point(screen_pos: Vector2, y := 0.0) -> Variant:
	var r := ray(screen_pos)
	var o: Vector3 = r[0]
	var d: Vector3 = r[1]
	if absf(d.y) < 1e-5:
		return null
	return o + d * ((y - o.y) / d.y)


func to_screen(world_pos: Vector3) -> Vector2:
	## 창 좌표. UI를 3배 격자에 맞추려면 호출한 쪽에서 반올림한다.
	return camera.unproject_position(world_pos) * SHRINK
