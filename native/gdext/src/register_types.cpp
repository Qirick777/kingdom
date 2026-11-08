#include <gdextension_interface.h>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/core/defs.hpp>
#include <godot_cpp/godot.hpp>

#include "kingdom_sim.h"

using namespace godot;

static void initialize_kingdom(ModuleInitializationLevel level) {
    if (level != MODULE_INITIALIZATION_LEVEL_SCENE) return;
    GDREGISTER_CLASS(KingdomSim);
}

static void uninitialize_kingdom(ModuleInitializationLevel) {}

extern "C" {
GDExtensionBool GDE_EXPORT kingdom_library_init(GDExtensionInterfaceGetProcAddress get_proc_address,
                                                const GDExtensionClassLibraryPtr library,
                                                GDExtensionInitialization* init) {
    godot::GDExtensionBinding::InitObject obj(get_proc_address, library, init);
    obj.register_initializer(initialize_kingdom);
    obj.register_terminator(uninitialize_kingdom);
    obj.set_minimum_library_initialization_level(MODULE_INITIALIZATION_LEVEL_SCENE);
    return obj.init();
}
}
