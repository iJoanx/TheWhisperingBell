"""Puts back sewer nodes that went missing from the open level (e.g. SL_287_Crossing deleted by
accident), from the layout the level was made from, and repairs their passage links both ways.
Nothing else is changed. Then rebuild the crossing with: py sewer_one.py 287

    py sewer_restore.py

Layout: Content/Python/import/sewerdef_layout.json. Log: restore_out.txt."""
import os
import json
import traceback
import unreal

PY_DIR = os.path.dirname(os.path.abspath(__file__))
LAYOUT = os.path.join(PY_DIR, "import", "sewerdef_layout.json")
PREFIX = "SL_"
out = os.path.join(PY_DIR, "restore_out.txt")


def log(msg):
    open(out, "a").write(msg + "\n")
    unreal.log("RESTORE " + msg)


def run():
    open(out, "w").write("restore started\n")
    data = json.load(open(LAYOUT))
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    cls = unreal.EditorAssetLibrary.load_blueprint_class("/Game/Sewers/BP_SewerNode")
    have = {}
    for a in eas.get_all_level_actors():
        if a.get_class().get_name() == "BP_SewerNode_C":
            have[a.get_actor_label()] = a
    actors, restored = {}, set()
    for n in data["nodes"]:
        label = "%s%03d_%s" % (PREFIX, n["id"], n["type"])
        a = have.get(label)
        if a is None:
            a = eas.spawn_actor_from_class(cls, unreal.Vector(n["x"], n["y"], n.get("z", 0.0)))
            a.set_actor_label(label)
            a.set_folder_path("SewerTrial/" + n["type"])
            a.set_editor_property("NodeType", n["type"])
            restored.add(n["id"])
            log("put back %s at %.0f %.0f %.0f" % (label, n["x"], n["y"], n.get("z", 0.0)))
        actors[n["id"]] = a
    if not restored:
        log("nothing missing: every node of the layout is in the level (%d)" % len(actors))
        return
    # links live on node "a" of each edge (Passage12To / Passage20To): rewrite them on every node
    # that links to or from a restored one, exactly as in the layout
    links = {}
    for e in data["edges"]:
        prop = "Passage12To" if e["p"] == "P12" else "Passage20To"
        links.setdefault((e["a"], prop), []).append(e["b"])
    fixed = set()
    for (aid, prop), targets in links.items():
        if aid in restored or any(t in restored for t in targets):
            actors[aid].set_editor_property(prop, [actors[t] for t in targets])
            fixed.add(actors[aid].get_actor_label())
    # empty (None) entries left behind by the deletion on other nodes
    for (aid, prop), targets in links.items():
        cur = actors[aid].get_editor_property(prop)
        if cur is not None and any(x is None for x in cur):
            actors[aid].set_editor_property(prop, [actors[t] for t in targets])
            fixed.add(actors[aid].get_actor_label())
    log("links rewritten on: %s" % ", ".join(sorted(fixed)))
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log("saved. Now rebuild it: py sewer_one.py %s" % " / ".join(str(i) for i in sorted(restored)))


try:
    run()
except Exception:
    log(traceback.format_exc())
