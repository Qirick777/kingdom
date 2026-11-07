class_name FaceTexture
extends RefCounted
## 8×8 얼굴 텍스처 조립 (tools/art/face_compose.py와 같은 규칙).
## 회색 128, 96 → 눈색 × 밝기/128, 회색 64 → 머리색 × 0.7.

static var _atlas: Image
static var _meta: Dictionary


static func _load() -> void:
	if _atlas != null:
		return
	_atlas = (load("res://assets/faces/face_atlas.png") as Texture2D).get_image()
	_atlas.convert(Image.FORMAT_RGBA8)
	_meta = DataDB.face_meta()


static func _part(group: String, name: String) -> Image:
	var p: Dictionary = _meta["parts"][group][name]
	var k: int = int(p["cell"])
	var cell := _atlas.get_region(Rect2i((k % 8) * 8, (k / 8) * 8, 8, 8))
	if group == "덧그림":
		return cell
	var w: int = int(p["w"])
	var h: int = int(p["h"])
	return cell.get_region(Rect2i((8 - w) / 2, (8 - h) / 2, w, h))


static func _paste(face: Image, part: Image, x0: int, y0: int, eye: Color, hair: Color, mirror: bool) -> void:
	var w := part.get_width()
	var h := part.get_height()
	for y in h:
		for x in w:
			var c := part.get_pixel(w - 1 - x if mirror else x, y)
			if c.a <= 0.0:
				continue
			var r8 := c.r8
			if r8 == c.g8 and r8 == c.b8:
				if r8 == 128 or r8 == 96:
					c = Color(eye.r * r8 / 128.0, eye.g * r8 / 128.0, eye.b * r8 / 128.0, 1.0)
				elif r8 == 64:
					c = Color(hair.r * 0.7, hair.g * 0.7, hair.b * 0.7, 1.0)
			var fx := x0 + x
			var fy := y0 + y
			if fx < 0 or fx > 7 or fy < 0 or fy > 7:
				continue
			var base := face.get_pixel(fx, fy)
			face.set_pixel(fx, fy, base.lerp(Color(c.r, c.g, c.b, 1.0), c.a))


static func compose(look: PersonLook, hair_rows: int = 2) -> Image:
	_load()
	var f := Image.create(8, 8, false, Image.FORMAT_RGBA8)
	f.fill(look.skin)
	for y in hair_rows:
		for x in 8:
			f.set_pixel(x, y, look.hair)
	var ex: int = int(look.face_shape["eye_x"])
	var ey: int = int(look.face_shape["eye_y"])
	var eyes_pair: Array = [["짝눈 작은", "짝눈 큰"]] if look.eyes_kind == "짝눈" else [[look.eyes_kind, look.eyes_kind]]
	for side in 2:
		var img := _part("눈", eyes_pair[0][side])
		var w := img.get_width()
		var x_end: int = maxi(ex, 2) if w == 2 else ex
		var x0 := x_end - w + 1
		if side == 1:
			x0 = 7 - x_end
		_paste(f, img, x0, ey, look.eye, look.hair, side == 1)
	if look.brow != "없음":
		var b := _part("눈썹", look.brow)
		var bw := b.get_width()
		var bx_end: int = maxi(ex, 2) if bw == 2 else ex
		_paste(f, b, bx_end - bw + 1, ey - b.get_height(), look.eye, look.hair, false)
		_paste(f, b, 7 - bx_end, ey - b.get_height(), look.eye, look.hair, true)
	if look.mouth != "없음":
		var m := _part("입", look.mouth)
		var mx := int(round(float(_meta["layout"]["mouth_cx"]) - m.get_width() / 2.0 + 0.01))
		_paste(f, m, mx, int(_meta["layout"]["mouth_y"]), look.eye, look.hair, false)
	for o in look.overlays:
		_paste(f, _part("덧그림", o), 0, 0, look.eye, look.hair, false)
	return f
