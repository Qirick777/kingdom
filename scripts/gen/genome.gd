class_name Genome
extends RefCounted
## 외형 유전자 6개 (01_character.md 1절). 유전자마다 대립유전자 2개(부, 모 하나씩).

const HAIR := ["검정", "갈색", "금발", "적발"]    ## 앞일수록 우성
const EYE := ["갈색", "녹색", "청색"]             ## 앞일수록 우성
const BUILD := ["가냘픔", "보통", "단단함"]

var male := true
var skin := [3, 3]      ## 1~5, 표현형 = 평균
var hair := [1, 1]      ## HAIR 인덱스, 표현형 = 우성 쪽
var eye := [0, 0]       ## EYE 인덱스, 표현형 = 우성 쪽
var height := [5, 5]    ## 1~10, 표현형 = 평균 + 개인 편차
var face := [0, 0]      ## 얼굴형 0~5, 표현형 = 둘 중 하나(결정적)
var build := [1, 1]     ## 0~2, 표현형 = 평균


static func _allele(rng: RandomNumberGenerator, items: Array, weights: Array) -> int:
	return int(DetRng.pick_weighted(rng, items, weights))


static func random(rng: RandomNumberGenerator, region_skin: int = 3) -> Genome:
	## 지역 인구에서 뽑는다. region_skin은 그 지역 피부색 중심값.
	var g := Genome.new()
	g.male = rng.randf() < 0.5
	var sw := []
	for v in range(1, 6):
		sw.append(max(0.05, 1.0 - abs(v - region_skin) * 0.35))
	g.skin = [_allele(rng, [1, 2, 3, 4, 5], sw), _allele(rng, [1, 2, 3, 4, 5], sw)]
	g.hair = [_allele(rng, [0, 1, 2, 3], [0.35, 0.35, 0.18, 0.12]), _allele(rng, [0, 1, 2, 3], [0.35, 0.35, 0.18, 0.12])]
	g.eye = [_allele(rng, [0, 1, 2], [0.5, 0.2, 0.3]), _allele(rng, [0, 1, 2], [0.5, 0.2, 0.3])]
	g.height = [rng.randi_range(3, 8), rng.randi_range(3, 8)]
	g.face = [rng.randi_range(0, 5), rng.randi_range(0, 5)]
	g.build = [_allele(rng, [0, 1, 2], [0.3, 0.45, 0.25]), _allele(rng, [0, 1, 2], [0.3, 0.45, 0.25])]
	return g


static func child(father: Genome, mother: Genome, rng: RandomNumberGenerator) -> Genome:
	## 유전자마다 아버지에게서 하나, 어머니에게서 하나.
	var g := Genome.new()
	g.male = rng.randf() < 0.5
	for key in ["skin", "hair", "eye", "height", "face", "build"]:
		var f: Array = father.get(key)
		var m: Array = mother.get(key)
		g.set(key, [f[rng.randi_range(0, 1)], m[rng.randi_range(0, 1)]])
	return g


func skin_value() -> int:
	return int(floor((skin[0] + skin[1]) / 2.0 + 0.5))


func hair_index() -> int:
	return min(hair[0], hair[1])


func eye_index() -> int:
	return min(eye[0], eye[1])


func face_index() -> int:
	return face[0] if (face[0] + face[1]) % 2 == 0 else face[1]


func build_index() -> int:
	return int(floor((build[0] + build[1]) / 2.0 + 0.5))


func height_value(rng: RandomNumberGenerator) -> int:
	return clampi(int(floor((height[0] + height[1]) / 2.0 + rng.randf_range(-1.0, 1.0) + 0.5)), 1, 10)
