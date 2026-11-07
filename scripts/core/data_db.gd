class_name DataDB
extends RefCounted
## data/ 아래 JSON을 한 번만 읽어 둔다.

static var _cache := {}


static func json(path: String) -> Variant:
	if _cache.has(path):
		return _cache[path]
	var txt := FileAccess.get_file_as_string(path)
	var v: Variant = JSON.parse_string(txt)
	if v == null:
		push_error("JSON을 읽지 못함: " + path)
	_cache[path] = v
	return v


static func palettes() -> Dictionary:
	return json("res://data/visual/palettes.json")


static func face_meta() -> Dictionary:
	return json("res://data/visual/face_atlas.json")


static func material_meta() -> Dictionary:
	return json("res://data/visual/material_atlas.json")


static func material_image(name: String, variant: int = 0) -> Image:
	## 재료 아틀라스에서 8×8 칸 하나를 잘라 온다.
	var atlas: Image = (load("res://assets/textures/material_atlas.png") as Texture2D).get_image()
	atlas.convert(Image.FORMAT_RGBA8)
	var k: int = int(material_meta()["materials"][name][variant])
	return atlas.get_region(Rect2i((k % 8) * 8, (k / 8) * 8, 8, 8))
