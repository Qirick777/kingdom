extends SceneTree
## GDExtension 연결 확인: godot --headless --path . --script native/gdext/smoke_test.gd
func _init() -> void:
	if not ClassDB.class_exists("KingdomSim"):
		print("KingdomSim 없음: bin/에 라이브러리와 kingdom.gdextension이 있는지 확인")
		quit(1)
		return
	var sim = ClassDB.instantiate("KingdomSim")
	sim.setup(1, 20000, 100)
	var s: Dictionary = sim.run_years(100)
	print("100년 뒤 산 사람 ", s["alive"], ", 누적 ", sim.person_count(), ", 검사합 ", sim.checksum())
	quit()
