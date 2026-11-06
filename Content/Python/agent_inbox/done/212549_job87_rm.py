import unreal
m = unreal.load_asset('/Game/Characters/Hope/Animations/Teleport/AM_TP_Dash')
for p in ('enable_root_motion_translation', 'enable_root_motion_rotation', 'root_motion_root_lock'):
    try: print("montage", p, m.get_editor_property(p))
    except Exception as e: print("montage", p, "?")
seqs = set()
try:
    for st in m.get_editor_property('slot_anim_tracks'):
        for seg in st.get_editor_property('anim_track').get_editor_property('anim_segments'):
            a = seg.get_editor_property('anim_reference')
            if a: seqs.add(a.get_path_name())
except Exception as e: print("slots err", e)
ar = unreal.AssetRegistryHelpers.get_asset_registry()
for s in seqs:
    a = unreal.load_object(None, s)
    print("seq", s)
    for p in ('enable_root_motion', 'root_motion_root_lock', 'force_root_lock'):
        try: print("   ", p, a.get_editor_property(p))
        except Exception: print("   ", p, "?")
    pkg = s.split('.')[0]
    print("    referencers:", [str(r) for r in ar.get_referencers(pkg, unreal.AssetRegistryDependencyOptions())])
for n in ('BP_Master_PC', 'CBP_PC_Hope', 'CBP_PC_GolKosh'):
    cdo = unreal.get_default_object(unreal.load_class(None, '/Game/ThirdPerson/Blueprints/%s.%s_C' % (n, n)))
    cmc = cdo.get_editor_property('character_movement')
    vals = {}
    for p in ('ignore_client_movement_error_checks_and_correction', 'server_accept_client_authoritative_position', 'network_smoothing_mode'):
        try: vals[p] = cmc.get_editor_property(p)
        except Exception as e: vals[p] = "?"
    print(n, cmc.get_class().get_name(), vals)
