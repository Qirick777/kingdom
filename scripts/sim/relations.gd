class_name Relations
extends RefCounted
## 03_interaction.md 1절의 관계 수치. 방향이 있다(A→B와 B→A는 다르다).

const RANGES := {"호감": [-100, 100], "신뢰": [0, 100], "두려움": [0, 100], "원한": [0, 100], "빚": [0, 999]}

var _r := {}        ## Vector2i(a, b) → Dictionary
var _links := {}    ## Vector2i(min, max) → Array[String] ("연인", "배우자")


func of(a: int, b: int) -> Dictionary:
	## a가 b에게 가진 수치. 처음 만나면 0에서 시작한다(첫인상 공식은 매력이 아직 없어 생략).
	var k := Vector2i(a, b)
	if not _r.has(k):
		_r[k] = {"호감": 0, "신뢰": 0, "두려움": 0, "원한": 0, "빚": 0}
	return _r[k]


func add(a: int, b: int, key: String, delta: int) -> int:
	var d := of(a, b)
	var lim: Array = RANGES[key]
	d[key] = clampi(int(d[key]) + delta, lim[0], lim[1])
	return d[key]


func link(a: int, b: int, kind: String) -> void:
	var k := Vector2i(mini(a, b), maxi(a, b))
	if not _links.has(k):
		_links[k] = []
	if not (_links[k] as Array).has(kind):
		_links[k].append(kind)


func has_link(a: int, b: int, kind: String) -> bool:
	var k := Vector2i(mini(a, b), maxi(a, b))
	return _links.has(k) and (_links[k] as Array).has(kind)


func spouse_of(a: int) -> int:
	for k in _links.keys():
		if (_links[k] as Array).has("배우자"):
			if k.x == a:
				return k.y
			if k.y == a:
				return k.x
	return -1
