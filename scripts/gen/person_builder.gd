class_name PersonBuilder
extends RefCounted
## PersonLook → 블록 모델 Node3D. 크기는 텍셀 단위(1 = 1/16m)로 짜고 루트에서 1/16로 줄인다.
## 몸: 머리 8 + 몸통 7 + 다리 6 텍셀(성인 약 1.3m). 얼굴은 머리 정면(+z)에 8×8 텍스처 판.

const TEXEL := 1.0 / 16.0
const OUTLINE_COLOR := Color("#3b2a2a")

static var _mats := {}
static var _outline: StandardMaterial3D
static var _box_mesh: BoxMesh
static var _straw: ImageTexture


static func _outline_mat() -> StandardMaterial3D:
	if _outline == null:
		_outline = StandardMaterial3D.new()
		_outline.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		_outline.albedo_color = OUTLINE_COLOR
		_outline.cull_mode = BaseMaterial3D.CULL_FRONT
		_outline.grow = true
		_outline.grow_amount = 0.55
	return _outline


static func _mat(c: Color) -> StandardMaterial3D:
	var key := c.to_html(true)
	if _mats.has(key):
		return _mats[key]
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.roughness = 1.0
	m.specular_mode = BaseMaterial3D.SPECULAR_DISABLED
	m.next_pass = _outline_mat()
	_mats[key] = m
	return m


static func _straw_tex() -> ImageTexture:
	if _straw == null:
		_straw = ImageTexture.create_from_image(DataDB.material_image("초가", 0))
	return _straw


static func _box(parent: Node3D, size: Vector3, center: Vector3, color: Color, outline := true) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	var m := _mat(color)
	if not outline:
		m = m.duplicate()
		m.next_pass = null
	mi.material_override = m
	mi.position = center
	parent.add_child(mi)
	return mi


static func _proportions(age: int) -> Array:
	## [몸통 높이, 다리 높이, 머리 배율]
	if age < 3:
		return [4.0, 2.0, 0.85]
	if age < 13:
		return [5.0, 3.0, 1.0]
	if age < 16:
		return [6.0, 5.0, 1.0]
	return [7.0, 6.0, 1.0]


static func build(look: PersonLook, face_tex: ImageTexture = null) -> Node3D:
	## 관절: Body(축소) → Pelvis(골반, 다리 위) → HipN/HipP(다리), Upper(몸통) → ArmN/ArmP(팔), Head.
	## N은 -x쪽, P는 +x쪽. 도구는 ArmP 손에 든다. PersonRig가 이 관절들을 움직인다.
	## face_tex를 넘기면 그 텍스처를 얼굴에 쓴다(표정이 바뀌면 같은 텍스처를 고쳐 그려 여러 모델에 한꺼번에 반영).
	var root := Node3D.new()
	root.name = "Person%d" % look.id
	var body := Node3D.new()
	body.name = "Body"
	body.scale = Vector3.ONE * TEXEL * look.body_scale
	root.add_child(body)

	var pr := _proportions(look.age)
	var torso_h: float = pr[0] * look.height_scale
	var leg_h: float = pr[1] * look.height_scale
	var head_s: float = pr[2]
	var bw: float = look.build_w
	var tw := 6.0 * bw
	root.set_meta("leg_h", leg_h)
	root.set_meta("torso_h", torso_h)
	root.set_meta("height_m", (leg_h + torso_h + 8.0 * head_s) * TEXEL * look.body_scale)
	root.set_meta("lean", 7.0 if look.age >= 60 else 0.0)

	# 그림자 (반투명 원판). 골반이 위아래로 움직여도 그림자는 땅에 남는다
	var sh := MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = 5.0
	cyl.bottom_radius = 5.0
	cyl.height = 0.05
	cyl.radial_segments = 12
	sh.mesh = cyl
	var shm := StandardMaterial3D.new()
	shm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	shm.albedo_color = Color(0, 0, 0, 0.22)
	shm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	sh.material_override = shm
	sh.position = Vector3(0, 0.03, 0)
	body.add_child(sh)

	var pelvis := Node3D.new()
	pelvis.name = "Pelvis"
	pelvis.position = Vector3(0, leg_h, 0)
	body.add_child(pelvis)

	# 다리, 신발 (엉덩이 관절에 매단다)
	var robe := look.outfit == "긴 옷"
	if not robe:
		for side in [-1, 1]:
			var hip := Node3D.new()
			hip.name = "HipN" if side < 0 else "HipP"
			hip.position = Vector3(side * 1.5 * bw, 0, 0)
			pelvis.add_child(hip)
			_box(hip, Vector3(2, leg_h, 2), Vector3(0, -leg_h / 2.0, 0), look.pants)
			_box(hip, Vector3(2.2, 1, 2.6), Vector3(0, -leg_h + 0.5, 0.2), Color("#5a4040"), false)

	var upper := Node3D.new()
	upper.name = "Upper"
	upper.rotation_degrees.x = root.get_meta("lean")   # 노인은 앞으로 굽는다. PersonRig도 이 값을 기본으로 쓴다
	pelvis.add_child(upper)

	var shirt := look.shirt
	if look.outfit == "갑옷":
		shirt = Color("#cfd8e0")
	if robe:
		_box(pelvis, Vector3(tw + 0.6, leg_h + torso_h, 4.6), Vector3(0, (torso_h - leg_h) / 2.0, 0), shirt)
	else:
		_box(upper, Vector3(tw, torso_h, 4), Vector3(0, torso_h / 2.0, 0), shirt)
	# 허리띠
	var belt := look.accent if look.accent.a > 0.0 else shirt.darkened(0.35)
	_box(upper, Vector3(tw + 0.2, 1, 4.2), Vector3(0, 1.5, 0), belt, false)
	match look.outfit:
		"앞치마":
			_box(upper, Vector3(tw - 1.0, torso_h + 2.0, 0.6), Vector3(0, torso_h / 2.0 - 1.0, 2.2), Color("#a26a3a"), false)
		"조끼":
			_box(upper, Vector3(1.6, torso_h - 0.5, 0.5), Vector3(-tw / 2.0 + 0.8, torso_h / 2.0, 2.1), look.accent, false)
			_box(upper, Vector3(1.6, torso_h - 0.5, 0.5), Vector3(tw / 2.0 - 0.8, torso_h / 2.0, 2.1), look.accent, false)
		"갑옷":
			for sx in [-1, 1]:
				_box(upper, Vector3(2.6, 1.6, 4.4), Vector3(sx * (tw / 2.0 + 0.6), torso_h - 0.6, 0), Color("#b3bcc6"))
			_box(upper, Vector3(tw * 0.5, torso_h * 0.5, 0.4), Vector3(0, torso_h * 0.55, 2.1), look.accent, false)
		"장식옷":
			_box(upper, Vector3(tw + 0.2, 0.8, 4.2), Vector3(0, torso_h - 0.4, 0), look.accent, false)
		"거친 천":
			_box(upper, Vector3(2, 2, 0.4), Vector3(-1.2, torso_h * 0.6, 2.05), shirt.darkened(0.2), false)

	# 팔, 손 (어깨 관절에 매단다)
	var arm_h := torso_h - 1.0
	var arms := {}
	for side in [-1, 1]:
		var arm := Node3D.new()
		arm.name = "ArmN" if side < 0 else "ArmP"
		arm.position = Vector3(side * (tw / 2.0 + 1.0), torso_h - 0.5, 0)
		upper.add_child(arm)
		_box(arm, Vector3(2, arm_h, 2), Vector3(0, -arm_h / 2.0 + 0.5, 0), shirt)
		_box(arm, Vector3(2, 1, 2), Vector3(0, -arm_h, 0), look.skin, false)
		arms[side] = arm

	# 머리
	var head := Node3D.new()
	head.name = "Head"
	head.position = Vector3(0, torso_h, 0)
	head.scale = Vector3.ONE * head_s
	upper.add_child(head)
	var hw: float = 8.0 * float(look.face_shape.get("head_w", 1.0))
	var hh: float = 8.0 * float(look.face_shape.get("head_h", 1.0))
	_box(head, Vector3(hw, hh, 8), Vector3(0, hh / 2.0, 0), look.skin)
	var bald := look.hairstyle == "대머리"
	if face_tex == null:
		face_tex = ImageTexture.create_from_image(FaceTexture.compose(look, 0 if bald else 2))
	var quad := MeshInstance3D.new()
	var qm := QuadMesh.new()
	qm.size = Vector2(hw, hh)
	quad.mesh = qm
	var fm := StandardMaterial3D.new()
	fm.albedo_texture = face_tex
	fm.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
	fm.roughness = 1.0
	fm.specular_mode = BaseMaterial3D.SPECULAR_DISABLED
	quad.material_override = fm
	quad.position = Vector3(0, hh / 2.0, 4.02)
	head.add_child(quad)
	if look.hat != "두건":   # 두건이 머리를 다 덮는다. 옆머리 판과 겹쳐 깜빡이지 않게 머리카락은 그리지 않는다
		_hair(head, look, hw, hh)
	_beard(head, look, hw, hh)
	_hat(head, look, hw, hh)
	_prop(arms[1], look, arm_h)
	if look.age >= 70:
		# 지팡이: N쪽 손에서 땅까지
		var top := -arm_h + 0.5
		var bottom := -(torso_h - 0.5) - leg_h
		_box(arms[-1], Vector3(1, top - bottom, 1), Vector3(0, (top + bottom) / 2.0, 1.5), Color("#a26a3a"))
	return root


static func face_image(look: PersonLook) -> Image:
	return FaceTexture.compose(look, 0 if look.hairstyle == "대머리" else 2)


static func _hair(head: Node3D, look: PersonLook, hw: float, hh: float) -> void:
	var c := look.hair
	var top := hh
	match look.hairstyle:
		"대머리":
			_box(head, Vector3(hw + 0.4, 2, 8.4), Vector3(0, hh * 0.45, -0.6), c)  # 뒤통수 둘레만
			return
		"짧은":
			_box(head, Vector3(hw + 0.4, 2.2, 8.4), Vector3(0, top - 1.0, 0), c)
			_box(head, Vector3(hw + 0.4, 4, 1), Vector3(0, top - 2.0, -4.2), c)
		"더벅":
			_box(head, Vector3(hw + 0.4, 2.6, 8.4), Vector3(0, top - 0.8, 0), c)
			_box(head, Vector3(4, 1.5, 4), Vector3(-1, top + 1.2, -1), c)
			_box(head, Vector3(hw + 0.4, 5, 1), Vector3(0, top - 2.5, -4.2), c)
		"상투":
			_box(head, Vector3(hw + 0.4, 2.2, 8.4), Vector3(0, top - 1.0, 0), c)
			_box(head, Vector3(2.4, 3, 2.4), Vector3(0, top + 1.6, -0.5), c)
			_box(head, Vector3(hw + 0.4, 4, 1), Vector3(0, top - 2.0, -4.2), c)
		"묶음":
			_box(head, Vector3(hw + 0.4, 2.2, 8.4), Vector3(0, top - 1.0, 0), c)
			_box(head, Vector3(hw + 0.4, 6, 1), Vector3(0, top - 3.0, -4.2), c)
			_box(head, Vector3(3, 3, 3), Vector3(0, top - 3.0, -5.6), c)
		"단발":
			_box(head, Vector3(hw + 0.4, 2.2, 8.4), Vector3(0, top - 1.0, 0), c)
			for sx in [-1, 1]:
				_box(head, Vector3(1, 5, 8.4), Vector3(sx * (hw / 2.0 + 0.5), top - 2.5, 0), c)
			_box(head, Vector3(hw + 2.4, 6, 1), Vector3(0, top - 3.0, -4.2), c)
		"긴":
			_box(head, Vector3(hw + 0.4, 2.2, 8.4), Vector3(0, top - 1.0, 0), c)
			for sx in [-1, 1]:
				_box(head, Vector3(1, 9, 7.4), Vector3(sx * (hw / 2.0 + 0.5), top - 4.5, -0.5), c)
			_box(head, Vector3(hw + 2.4, 11, 1), Vector3(0, top - 5.5, -4.2), c)
		"땋은":
			_box(head, Vector3(hw + 0.4, 2.2, 8.4), Vector3(0, top - 1.0, 0), c)
			_box(head, Vector3(hw + 0.4, 5, 1), Vector3(0, top - 2.5, -4.2), c)
			_box(head, Vector3(2, 8, 2), Vector3(0, top - 7.5, -5.0), c)


static func _beard(head: Node3D, look: PersonLook, hw: float, hh: float) -> void:
	var c := look.hair.darkened(0.1)
	match look.beard:
		"짧은":
			_box(head, Vector3(hw - 1.0, 1.2, 0.6), Vector3(0, 0.6, 4.3), c, false)
		"콧수염":
			_box(head, Vector3(4, 1, 0.6), Vector3(0, 2.5, 4.3), c, false)
		"긴":
			_box(head, Vector3(hw - 1.0, 3.5, 0.8), Vector3(0, -0.4, 4.3), c)


static func _hat(head: Node3D, look: PersonLook, hw: float, hh: float) -> void:
	match look.hat:
		"밀짚":
			var brim := _box(head, Vector3(hw + 4, 1, 12), Vector3(0, hh + 0.5, 0), Color("#f5d873"))
			var crown := _box(head, Vector3(hw + 0.6, 2.5, 8.6), Vector3(0, hh + 1.8, 0), Color("#e0b94e"))
			for mi in [brim, crown]:
				var m: StandardMaterial3D = (mi.material_override as StandardMaterial3D).duplicate()
				m.albedo_color = Color.WHITE
				m.albedo_texture = _straw_tex()
				m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
				m.uv1_scale = Vector3(2, 2, 2)
				mi.material_override = m
		"두건":
			var c := look.shirt.darkened(0.12)   # 옷과 같은 색이면 한 덩어리로 뭉개진다
			_box(head, Vector3(hw + 1.0, 3, 9), Vector3(0, hh - 0.5, -0.2), c)
			for sx in [-1, 1]:
				_box(head, Vector3(1, hh, 9), Vector3(sx * (hw / 2.0 + 0.5), hh / 2.0 - 0.5, -0.2), c)
			_box(head, Vector3(hw + 2, hh + 1, 1), Vector3(0, hh / 2.0, -4.5), c)
		"장식모":
			_box(head, Vector3(6, 2, 6), Vector3(0, hh + 1, 0), look.accent if look.accent.a > 0.0 else Color("#b8323f"))
			_box(head, Vector3(1.2, 1.2, 1.2), Vector3(0, hh + 2.2, 2.6), Color("#5f9ad6"), false)


static func _prop(arm: Node3D, look: PersonLook, arm_h: float) -> void:
	## 손 위치(어깨 기준 y = -arm_h)를 기준으로 도구를 붙인다.
	var y := -arm_h
	match look.prop:
		"낫":
			_box(arm, Vector3(1, 7, 1), Vector3(0, y + 2.5, 1.5), Color("#a26a3a"))
			_box(arm, Vector3(1, 1, 4), Vector3(0, y + 6, 3), Color("#cfd8e0"))
		"망치":
			_box(arm, Vector3(1, 5, 1), Vector3(0, y + 1.5, 1.5), Color("#a26a3a"))
			_box(arm, Vector3(2, 2, 3), Vector3(0, y + 4, 1.5), Color("#8d8780"))
		"창":
			_box(arm, Vector3(1, 22, 1), Vector3(0, y + 6, 1.5), Color("#a26a3a"))
			_box(arm, Vector3(1.2, 3, 1.2), Vector3(0, y + 18.5, 1.5), Color("#cfd8e0"))
		"칼":
			_box(arm, Vector3(1, 9, 1), Vector3(0, y + 3.5, 2.0), Color("#dfe7ee"))
			_box(arm, Vector3(3, 1, 1), Vector3(0, y - 0.5, 2.0), Color("#ffd34d"), false)
		"책":
			_box(arm, Vector3(1.5, 4, 3), Vector3(0, y + 1, 1.5), Color("#7a3fb3"))
