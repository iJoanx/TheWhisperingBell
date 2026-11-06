# Slide the whole sewer (nodes + network actors) sideways so SL_023_Shaft is right below BP_WB_SW14.
import unreal, json, os
PY = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
acts = eas.get_all_level_actors()
sw = [a for a in acts if a.get_actor_label() == "BP_WB_SW14"]
shaft = [a for a in acts if a.get_actor_label() == "SL_023_Shaft"]
if len(sw) != 1 or len(shaft) != 1:
    raise RuntimeError("BP_WB_SW14: %d, SL_023_Shaft: %d" % (len(sw), len(shaft)))
t, s = sw[0].get_actor_location(), shaft[0].get_actor_location()
d = unreal.Vector(t.x - s.x, t.y - s.y, 0.0)
mine = [a for a in acts if a.get_class().get_name() == "BP_SewerNode_C" or
        a.get_actor_label().startswith("SewerNetwork_GENERATED")]
print("moving %d actors by (%.1f, %.1f) cm" % (len(mine), d.x, d.y))
for a in mine:
    a.set_actor_location(a.get_actor_location() + d, False, False)
s2 = shaft[0].get_actor_location()
print("SL_023_Shaft now at (%.1f, %.1f, %.1f); BP_WB_SW14 at (%.1f, %.1f, %.1f)" % (s2.x, s2.y, s2.z, t.x, t.y, t.z))
# keep the layout file in step, for future rebuilds
lay = json.load(open(os.path.join(PY, "import", "sewersfinal_layout.json")))
for n in lay["nodes"]:
    n["x"] = round(n["x"] + d.x, 1)
    n["y"] = round(n["y"] + d.y, 1)
json.dump(lay, open(os.path.join(PY, "import", "sewersfinal_moved_layout.json"), "w"))
print("wrote import/sewersfinal_moved_layout.json")
