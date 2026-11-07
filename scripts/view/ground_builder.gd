class_name GroundBuilder
extends RefCounted
## 땅 텍스처를 0.5m 칸마다 조립한다. 칸마다 변형을 고르고, 자연 바닥은 뒤집기까지 섞어 반복 무늬를 지운다.

const NATURAL := ["풀", "흙", "흙길", "모래", "눈"]   ## 뒤집어도 티가 안 나는 바닥


static func build(world_seed: int, size_m: float, regions: Array, base := "풀", contrast := 0.55) -> MeshInstance3D:
	## regions: [[Rect2(월드 x,z), 재료 이름], ...] 뒤에 오는 것이 위에 깔린다.
	var mi := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(size_m, size_m)
	mi.mesh = pm
	var n := int(size_m * 2.0)
	var img := Image.create(n * 8, n * 8, false, Image.FORMAT_RGBA8)
	var meta := DataDB.material_meta()
	var rng := DetRng.make([world_seed, "ground"])
	var cache := {}
	for cz in n:
		for cx in n:
			var w := Vector2(-size_m / 2.0 + (cx + 0.5) * 0.5, -size_m / 2.0 + (cz + 0.5) * 0.5)
			var mname := base
			for r in regions:
				if (r[0] as Rect2).has_point(w):
					mname = r[1]
			var v := rng.randi_range(0, meta["materials"][mname].size() - 1)
			var key := "%s%d" % [mname, v]
			if not cache.has(key):
				cache[key] = soften(DataDB.material_image(mname, v), contrast)
			var cell: Image = (cache[key] as Image).duplicate()
			if NATURAL.has(mname):
				if rng.randf() < 0.5:
					cell.flip_x()
				if rng.randf() < 0.5:
					cell.flip_y()
			img.blit_rect(cell, Rect2i(0, 0, 8, 8), Vector2i(cx * 8, cz * 8))
	var gm := StandardMaterial3D.new()
	gm.albedo_texture = ImageTexture.create_from_image(img)
	gm.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
	gm.roughness = 1.0
	gm.specular_mode = BaseMaterial3D.SPECULAR_DISABLED
	mi.material_override = gm
	return mi


static func soften(img: Image, keep: float) -> Image:
	## 각 픽셀을 칸 평균색 쪽으로 당긴다. keep=1이면 원본, 0이면 단색.
	var avg := Color(0, 0, 0, 0)
	var n := img.get_width() * img.get_height()
	for y in img.get_height():
		for x in img.get_width():
			avg += img.get_pixel(x, y) / n
	for y in img.get_height():
		for x in img.get_width():
			img.set_pixel(x, y, avg.lerp(img.get_pixel(x, y), keep))
	return img


static func ring_texture(px: int, r_in: float, r_out: float, color: Color) -> ImageTexture:
	## 바닥 표시용 고리(선택, 마우스 올림, 이동 지점)
	var img := Image.create(px, px, false, Image.FORMAT_RGBA8)
	var c := (px - 1) / 2.0
	for y in px:
		for x in px:
			var d := Vector2(x - c, y - c).length()
			if d >= r_in and d <= r_out:
				img.set_pixel(x, y, color)
	return ImageTexture.create_from_image(img)
