class_name InteractionRules
extends RefCounted
## 03_interaction.md 2절 판정 공식과 3절 행동 결과.
##   성공 점수 = 행동자 능력 + 관계 보정 + 성격 보정 + 권력차 보정 - 요구 크기 + 주사위(-20~20)
## 능력, 성격, 권력은 인물 능력치가 아직 없어 0이다. 관계 보정 = (대상이 행동자에게 가진 수치) / 4.


static func data() -> Dictionary:
	return DataDB.json("res://data/interactions.json")


static func by_category(actor: Citizen, target: Citizen) -> Dictionary:
	## 범주 → 지금 가능한 행동 목록. 조건이 맞지 않는 행동은 메뉴에 나오지 않는다(03 3절).
	var out := {}
	for a in data()["actions"]:
		if not _ok(a, actor, target):
			continue
		var cat: String = a["category"]
		if not out.has(cat):
			out[cat] = []
		out[cat].append(a)
	return out


static func _ok(a: Dictionary, actor: Citizen, target: Citizen) -> bool:
	for c in a.get("cond", []):
		match c:
			"both_adult":
				if actor.look.age < 16 or target.look.age < 16:
					return false
			"not_household":
				# 친족 혼인 규칙은 교리, 법(08번)이 정한다. 집단 특성이 아직 없어 시험장에서는 같은 가구를 뺀다.
				if actor.household and target.household:
					return false
	return true


static func resolve(actor: Citizen, target: Citizen, a: Dictionary, rel: Relations, rng: RandomNumberGenerator) -> Dictionary:
	var rel_key: String = a.get("relation", "")
	var rel_val := 0
	if rel_key != "":
		rel_val = int(rel.of(target.pid, actor.pid)[rel_key])
	var rel_bonus := int(floor(rel_val / 4.0))
	var demand := int(a.get("demand", 0))
	var dice := rng.randi_range(-20, 20)
	var score := rel_bonus - demand + dice
	var ok := score >= 0
	var parts: Array = []
	var eff: Dictionary = a["success"] if ok else a["fail"]
	if eff.has("target"):
		for k in eff["target"].keys():
			var dv := int(eff["target"][k])
			rel.add(target.pid, actor.pid, k, dv)
			parts.append("%s %s%d" % [k, "+" if dv >= 0 else "", dv])
	if eff.has("link"):
		rel.link(actor.pid, target.pid, eff["link"])
		parts.append("%s 관계" % eff["link"])
	var married := rel.spouse_of(actor.pid) >= 0 and rel.spouse_of(actor.pid) != target.pid
	for key in (["success_text", "success_text_married"] if ok else ["fail_text", "fail_text_married"]):
		if a.has(key) and (not key.ends_with("_married") or married):
			parts.append(a[key])
	var head := "%s → %s  %s %s" % [actor.display_name, target.display_name, a["name"], "성공" if ok else "실패"]
	var calc := "점수 %+d = 관계 %d/4 − 요구 %d + 주사위 %+d" % [score, rel_val, demand, dice]
	return {
		"ok": ok, "score": score,
		"text": head + ("  ·  " + ", ".join(parts) if parts.size() > 0 else ""),
		"calc": calc,
		"show": a["show_success"] if ok else a["show_fail"],
	}
