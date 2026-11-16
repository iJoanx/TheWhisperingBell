import unreal, collections
out = []
def dump():
    open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump337.txt", "w", encoding="utf-8").write("\n".join(out))
try:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    out.append("level: " + world.get_path_name())
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    acts = eas.get_all_level_actors()
    out.append("actors loaded: %d" % len(acts))
    cls = collections.Counter(a.get_class().get_name() for a in acts)
    out.append("classes: " + str(cls.most_common(15)))
    towers = []
    for a in acts:
        lab = a.get_actor_label()
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            sm = c.static_mesh
            nm = sm.get_name() if sm else ''
            if 'ower' in lab or 'ower' in nm:
                towers.append((a, c, sm))
    out.append("tower-like components: %d" % len(towers))
    def desc(a, c, sm):
        mats = [m.get_path_name() if m else None for m in c.get_materials()]
        try: cpd = list(c.get_editor_property('custom_primitive_data').get_editor_property('data'))
        except Exception as e: cpd = 'err ' + str(e)[:60]
        tags = [str(t) for t in a.tags] + [str(t) for t in c.component_tags]
        md = {}
        if sm:
            try: md = unreal.EditorAssetLibrary.get_metadata_tag_values(sm)
            except Exception: pass
        vc = None
        try: vc = sm.get_editor_property('lod_info') if False else None
        except Exception: pass
        return "%s | mesh %s | mats %s | cpd %s | tags %s | meta %s | class %s" % (a.get_actor_label(), sm.get_path_name() if sm else None, mats, cpd, tags, dict(list(md.items())[:8]) if md else {}, a.get_class().get_name())
    for a, c, sm in towers[:40]:
        out.append(desc(a, c, sm))
    # what do houses look like (for comparison)
    n = 0
    for a in acts:
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            sm = c.static_mesh
            if sm and 'House' in sm.get_name():
                out.append("HOUSE " + desc(a, c, sm)); n += 1
                break
        if n >= 5: break
except Exception:
    import traceback; out.append(traceback.format_exc()[-1500:])
dump(); print("ok")
