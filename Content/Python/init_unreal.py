# Runs when the Whispering Bell editor starts: Sewer menu + live editor watchers.
import unreal

try:
    import sewer_tools
    sewer_tools.register_menu()
except Exception as e:  # never block editor start-up
    unreal.log_warning("Sewer menu not added: %s" % e)

for _module_name in ("walls_spline", "door_wrap", "agent_bridge"):
    try:
        _module = __import__(_module_name)
        _module.start()
    except Exception as e:  # one watcher failing must not block the others
        unreal.log_warning("%s watcher not started: %s" % (_module_name, e))


# --------------------------------------------------------------------------- clean exit
# The editor crashed on close inside Python: when Python shuts down it frees whatever our
# scripts still keep in module-level caches (actors, components, meshes, vectors...), but by then
# Unreal has already destroyed those objects. Before Python shuts down, drop every Unreal object
# our scripts hold, so nothing is left to free that late.
_OUR_MODULES = ("walls_", "door_wrap", "sewer_", "agent_bridge")


def _release_unreal_objects():
    import builtins
    import gc
    import sys
    for name in ("_WALLS_TICK_HANDLE", "_DOOR_WRAP_HANDLE", "_AGENT_BRIDGE_HANDLE"):
        if hasattr(builtins, name):
            setattr(builtins, name, None)          # Slate is already gone: nothing left to unregister
    for name, module in list(sys.modules.items()):
        if module is None or not name.startswith(_OUR_MODULES):
            continue
        for key, value in list(vars(module).items()):
            if key.startswith("__"):
                continue
            try:
                if isinstance(value, (dict, list, set)):
                    value.clear()
                elif isinstance(value, (unreal.Object, unreal.StructBase)):
                    setattr(module, key, None)
            except Exception:
                pass
    gc.collect()


try:
    unreal.register_python_shutdown_callback(_release_unreal_objects)
except Exception as e:
    unreal.log_warning("Clean-exit hook not registered: %s" % e)
