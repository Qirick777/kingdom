class_name DetRng
extends RefCounted
## 결정적 난수: 같은 (시드, 대상 id, 용도)면 항상 같은 값 (17_visual_procgen.md 0절 4).


static func make(parts: Array) -> RandomNumberGenerator:
	var r := RandomNumberGenerator.new()
	var s := ""
	for p in parts:
		s += str(p) + "|"
	r.seed = s.hash()
	return r


static func pick(rng: RandomNumberGenerator, items: Array) -> Variant:
	return items[rng.randi_range(0, items.size() - 1)]


static func pick_weighted(rng: RandomNumberGenerator, items: Array, weights: Array) -> Variant:
	var total := 0.0
	for w in weights:
		total += float(w)
	var x := rng.randf() * total
	for i in items.size():
		x -= float(weights[i])
		if x <= 0.0:
			return items[i]
	return items[items.size() - 1]
