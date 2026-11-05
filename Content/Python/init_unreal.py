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
