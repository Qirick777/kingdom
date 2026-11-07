class_name Portrait
extends TextureRect
## 인물 초상화: 별도 3D 세계에 같은 외형 모델을 세우고 머리를 찍는다.
## 얼굴 텍스처를 지역 맵 모델과 공유하므로 표정이 바뀌면 초상화도 같이 바뀐다.
## px는 내부 픽셀 크기(텍셀 1개 = 2px). 화면에는 3배로 나온다.

var _vp: SubViewport


static func make(c: Citizen, px: int) -> Portrait:
	var p := Portrait.new()
	p._vp = SubViewport.new()
	p._vp.size = Vector2i(px, px)
	p._vp.own_world_3d = true
	p._vp.transparent_bg = true
	p._vp.msaa_3d = Viewport.MSAA_DISABLED
	p._vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	p.add_child(p._vp)
	var w := Node3D.new()
	p._vp.add_child(w)
	var env := Environment.new()
	env.background_mode = Environment.BG_CLEAR_COLOR
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(1, 1, 1)
	env.ambient_light_energy = 0.7
	var we := WorldEnvironment.new()
	we.environment = env
	w.add_child(we)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-35, 25, 0)
	sun.light_energy = 0.55
	w.add_child(sun)
	var m := PersonBuilder.build(c.look, c.face_tex)
	m.rotation_degrees.y = -28.0
	w.add_child(m)
	var s: float = PersonBuilder.TEXEL * c.look.body_scale
	var head_s := 0.85 if c.look.age < 3 else 1.0
	var head_y: float = (float(m.get_meta("leg_h")) + float(m.get_meta("torso_h")) + 4.5 * head_s) * s
	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = px / 32.0
	var eye := Vector3(0, head_y + 0.35, 3.0)
	cam.transform = Transform3D(Basis.looking_at(Vector3(0, head_y - 0.05, 0) - eye, Vector3.UP), eye)
	w.add_child(cam)
	p.texture = p._vp.get_texture()
	p.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	p.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	p.stretch_mode = TextureRect.STRETCH_SCALE
	p.custom_minimum_size = Vector2(px, px) * PixelTheme.SCALE
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return p
