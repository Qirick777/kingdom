class_name PersonLook
extends RefCounted
## 유전자 + 나이 + 계층 + 생업 + 감정 → 외형 파라미터 (17_visual_procgen.md 2절).
## 무작위 색을 뿌리지 않는다: 얼굴과 체형은 유전자, 옷은 계층과 생업, 표정은 상태에서 나온다.

const SOCIAL := ["노예", "평민", "장인상인", "지주기사", "귀족"]
const OCCUPATIONS := {
	"노예": ["노예"],
	"평민": ["농부", "농부", "농부", "병사"],
	"장인상인": ["장인", "상인"],
	"지주기사": ["지주", "기사"],
	"귀족": ["귀족", "사제"],
}
const MOODS := ["평소", "기쁨", "화남", "슬픔", "놀람", "잠"]
const HAIR_MALE := ["짧은", "짧은", "더벅", "상투", "묶음"]
const HAIR_FEMALE := ["단발", "긴", "긴", "묶음", "땋은"]

var id := 0
var genome: Genome
var male := true
var age := 30
var social := "평민"
var occupation := "농부"
var mood := "평소"

var skin := Color.WHITE
var hair := Color.WHITE
var hair_name := ""
var eye := Color.WHITE
var height_tier := 1          ## 0 작음, 1 보통, 2 큼
var height_scale := 1.0
var build_index := 1
var build_w := 1.0
var body_scale := 1.0         ## 거구 1.12, 왜소 0.9
var trait_label := ""
var face_shape: Dictionary = {}

var hairstyle := "짧은"
var beard := "없음"
var outfit := "튜닉"
var shirt := Color.WHITE
var pants := Color.WHITE
var accent := Color(0, 0, 0, 0)
var hat := "없음"
var prop := "없음"

var base_eyes := "점 눈"
var base_mouth := "기본"
var base_overlays: Array = []
var natural_blush := false
var eyes_kind := "점 눈"
var brow := "없음"
var mouth := "기본"
var overlays: Array = []


static func make(pid: int, g: Genome, age_years: int, social_class: String, occ: String, mood_name: String, world_seed: int) -> PersonLook:
	var L := PersonLook.new()
	var rng := DetRng.make([world_seed, pid, "look"])
	var pal := DataDB.palettes()
	var fmeta := DataDB.face_meta()
	L.id = pid
	L.genome = g
	L.male = g.male
	L.age = age_years
	L.social = social_class
	L.occupation = occ
	L.mood = mood_name

	# ---- 유전자에서 오는 것
	L.skin = Color(pal["skin"][g.skin_value() - 1])
	L.skin = L.skin.lightened(rng.randf_range(-0.03, 0.03)) if rng.randf() < 0.5 else L.skin.darkened(rng.randf_range(0.0, 0.03))
	L.hair_name = Genome.HAIR[g.hair_index()]
	L.hair = Color(pal["hair"][L.hair_name])
	var shade := rng.randi_range(-2, 2) * 0.05
	L.hair = L.hair.lightened(shade) if shade > 0 else L.hair.darkened(-shade)
	if age_years >= 45:
		var gray := clampf((age_years - 45) / 30.0, 0.0, 1.0)
		L.hair = L.hair.lerp(Color(pal["hair"]["회색"]), gray * 0.85)
	L.eye = Color(pal["eye"][Genome.EYE[g.eye_index()]])
	var h := g.height_value(rng)
	L.height_tier = 0 if h <= 3 else (2 if h >= 8 else 1)
	L.height_scale = 0.9 + (h - 1) * 0.2 / 9.0
	L.build_index = g.build_index()
	L.build_w = [0.85, 1.0, 1.15][L.build_index]
	L.face_shape = fmeta["layout"]["face_shapes"][g.face_index()]
	var trait_roll := rng.randf()
	if trait_roll < 0.03:
		L.body_scale = 1.12
		L.build_w *= 1.15
		L.trait_label = "거구"
	elif trait_roll < 0.06:
		L.body_scale = 0.9
		L.trait_label = "왜소"

	# ---- 나이
	var adult := age_years >= 16
	# ---- 머리 모양, 수염
	var styles: Array = HAIR_MALE if L.male else HAIR_FEMALE
	L.hairstyle = DetRng.pick(rng, styles)
	if L.male and age_years >= 55 and rng.randf() < 0.4:
		L.hairstyle = "대머리"
	if L.male and adult:
		var bw := [0.5, 0.2, 0.2, 0.1] if age_years < 50 else [0.25, 0.2, 0.15, 0.4]
		L.beard = DetRng.pick_weighted(rng, ["없음", "짧은", "콧수염", "긴"], bw)

	# ---- 옷: 생업이 모양, 계층이 색
	var cloth: Dictionary = pal["cloth"]
	var colors: Array = cloth[social_class] if cloth.has(social_class) else cloth["평민"]
	L.shirt = Color(DetRng.pick(rng, colors))
	L.pants = L.shirt.darkened(0.45).lerp(Color("#5a4a3a"), 0.5)
	match occ:
		"농부":
			L.outfit = "튜닉"
			L.hat = "밀짚" if rng.randf() < 0.5 else "없음"
			L.prop = "낫" if adult and rng.randf() < 0.6 else "없음"
		"병사":
			L.outfit = "누비옷"
			L.shirt = Color("#d8c7a8").darkened(rng.randf_range(0.0, 0.15))
			L.prop = "창" if adult else "없음"
		"장인":
			L.outfit = "앞치마"
			L.prop = "망치" if adult else "없음"
		"상인":
			L.outfit = "조끼"
			L.accent = Color(DetRng.pick(rng, cloth["장인상인"]))
		"지주":
			L.outfit = "튜닉"
			L.accent = Color(cloth["장식"][0])
		"기사":
			L.outfit = "갑옷"
			L.accent = Color(DetRng.pick(rng, cloth["지주기사"]))
			L.prop = "칼" if adult else "없음"
		"귀족":
			L.outfit = "장식옷"
			L.accent = Color(cloth["장식"][0])
			L.hat = "장식모" if rng.randf() < 0.3 else "없음"
		"사제":
			L.outfit = "긴 옷"
			L.shirt = Color("#7a5aa8") if rng.randf() < 0.5 else Color("#fffaf0")
			L.hat = "두건"
			L.prop = "책" if adult else "없음"
		"노예":
			L.outfit = "거친 천"

	# ---- 표정: 평소 얼굴은 얼굴형 후보에서 고르고, 감정은 apply_mood가 덮어쓴다
	L.base_eyes = DetRng.pick(rng, L.face_shape["eyes"])
	if age_years < 3:
		L.base_eyes = "큰 눈"
	L.base_mouth = DetRng.pick_weighted(rng, ["기본", "미소", "무표정"], [0.5, 0.3, 0.2])
	if g.skin_value() <= 2 and rng.randf() < 0.18:
		L.base_overlays.append("주근깨")
	elif rng.randf() < 0.08 and age_years < 30:
		L.natural_blush = true
	if age_years >= 55:
		L.base_overlays.append("주름")
	L.apply_mood(mood_name)
	return L


func apply_mood(mood_name: String) -> void:
	## 감정이 눈, 눈썹, 입, 덧그림을 정한다. 유전과 나이에서 온 덧그림(주근깨, 주름)은 유지한다.
	mood = mood_name
	eyes_kind = base_eyes
	brow = "없음"
	mouth = base_mouth
	overlays = base_overlays.duplicate()
	match mood_name:
		"기쁨":
			eyes_kind = "웃는 눈"
			mouth = "활짝 웃음"
			overlays.append("볼 홍조")
		"화남":
			brow = "치켜 올라간"
			mouth = "찡그림"
		"슬픔":
			brow = "처진"
			mouth = "찡그림"
			overlays.append("눈물")
		"놀람":
			eyes_kind = "둥근 눈"
			mouth = "놀람"
		"잠":
			eyes_kind = "감은 눈"
			mouth = "없음"
		_:
			if natural_blush:
				overlays.append("볼 홍조")


func signature() -> String:
	## 멀리서 "닮아 보이는" 요소 (17_visual_procgen.md 2-5)
	return "%s|%s|%s|%s|%d|%d" % [hair_name, hairstyle, outfit, shirt.to_html(false), height_tier, build_index]


func reroll_non_genetic(rng: RandomNumberGenerator) -> void:
	## 서명이 겹칠 때: 유전이 아닌 요소(머리 모양, 옷 주색)만 다시 뽑는다.
	var styles: Array = HAIR_MALE if male else HAIR_FEMALE
	hairstyle = DetRng.pick(rng, styles)
	var pal := DataDB.palettes()
	var cloth: Dictionary = pal["cloth"]
	var colors: Array = cloth[social] if cloth.has(social) else cloth["평민"]
	if outfit != "누비옷" and outfit != "긴 옷":
		shirt = Color(DetRng.pick(rng, colors))
		pants = shirt.darkened(0.45).lerp(Color("#5a4a3a"), 0.5)


func describe() -> String:
	var a := "%d세 %s" % [age, "남" if male else "여"]
	var t := (" · " + trait_label) if trait_label != "" else ""
	return "%s · %s · %s · 피부 %d · %s 머리 · %s 눈 · %s%s" % [
		a, social, occupation, genome.skin_value(), hair_name, Genome.EYE[genome.eye_index()],
		face_shape.get("name", ""), t]
