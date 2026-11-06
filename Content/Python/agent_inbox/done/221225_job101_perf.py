import unreal, time, builtins
OUT = r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\perf101.txt"
LOG = []
def log(s):
    LOG.append(s); open(OUT, "w", encoding="utf-8").write("\n".join(LOG))
ps = unreal.get_default_object(unreal.load_class(None, '/Script/UnrealEd.LevelEditorPlaySettings'))
eps = unreal.get_default_object(unreal.load_class(None, '/Script/UnrealEd.EditorPerformanceSettings'))
saved = {}
enum_names = [n for n in dir(unreal) if 'NetMode' in n]
log("enums: %s" % enum_names)
try:
    saved['play_net_mode'] = ps.get_editor_property('play_net_mode')
    E = type(saved['play_net_mode'])
    ps.set_editor_property('play_net_mode', [v for k, v in E.__members__.items() if 'STANDALONE' in k][0])
    log("net mode %s -> standalone" % saved['play_net_mode'])
except Exception as e: log("net mode err %s" % e)
try:
    saved['play_number_of_clients'] = ps.get_editor_property('play_number_of_clients'); ps.set_editor_property('play_number_of_clients', 1)
except Exception as e: log("clients err %s" % e)
try:
    saved['throttle'] = eps.get_editor_property('throttle_cpu_when_not_foreground'); eps.set_editor_property('throttle_cpu_when_not_foreground', False)
    log("background throttle %s -> off" % saved['throttle'])
except Exception as e: log("throttle err %s" % e)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.editor_request_begin_play()
def gw(): return unreal.EditorLevelLibrary.get_game_world()
def cmd(c):
    w = gw()
    if w: unreal.SystemLibrary.execute_console_command(w, c)
def dn():
    w = gw(); a = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.load_class(None, '/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle_C')) if w else []
    return a[0] if a else None
def dn_tick(on):
    a = dn()
    if a:
        a.set_actor_tick_enabled(on)
        for c in a.get_components_by_class(unreal.ActorComponent): c.set_component_tick_enabled(on)
def hide(tag, hidden):
    w = gw()
    for a in (unreal.GameplayStatics.get_all_actors_with_tag(w, tag) if w else []): a.set_actor_hidden_in_game(hidden)

def comps():
    a = dn()
    return a.get_components_by_class(unreal.ActorComponent) if a else []
def set_day(minutes):
    a = dn()
    if not a: return
    a.set_editor_property('TotalDayTime', float(minutes))
    for c in comps():
        if isinstance(c, unreal.TimelineComponent):
            c.set_play_rate(24.0 / (minutes * 60.0)); c.play()
    log("TotalDayTime=%s; components: %s" % (minutes, [(c.get_name(), c.get_class().get_name()) for c in comps()]))
def sky_meshes(on):
    for c in comps():
        if isinstance(c, unreal.StaticMeshComponent):
            c.set_cast_shadow(on)
            try: c.set_affect_distance_field_lighting(on)
            except Exception as e: log("adfl %s" % e)
            try: c.set_editor_property('affect_dynamic_indirect_lighting', on); c.mark_render_state_dirty()
            except Exception as e: log("adil %s" % e)
def freeze_cone(on):
    a = dn()
    st["cone_freeze"] = on
def fog_scatter(on):
    for c in comps():
        if isinstance(c, unreal.DirectionalLightComponent):
            c.set_volumetric_scattering_intensity(c.get_editor_property('volumetric_scattering_intensity') if on else 0.0) if on else c.set_volumetric_scattering_intensity(0.0)

PLAN = [
    ("warmup (sets a 2-minute day)", lambda: set_day(2.0), 8.0, False),
    ("A sun moving (2-min day), sewers hidden", lambda: None, 6.0, True),
    ("B sun moving, sky meshes: no shadow / no DF / no GI", lambda: sky_meshes(False), 6.0, True),
    ("C B + sun & moon fog scattering off", lambda: fog_scatter(False), 6.0, True),
    ("D everything back, day/night paused", lambda: (sky_meshes(True), dn_tick(False)), 6.0, True),
]
st = {"i": -1, "t0": 0, "d": [], "prof": False, "start": time.time()}
def step(dt):
    try:
        if time.time() - st["start"] > 150: finish("timeout"); return
        if gw() is None:
            if st["i"] >= 0: finish("PIE ended early")
            return
        now = time.time()
        if st["i"] == -1:
            st.update(i=0, t0=now, d=[], prof=False); cmd("r.ProfileGPU.ShowUI 0"); log("PIE up %s" % gw().get_path_name()); return
        st["d"].append(dt)
        name, _, secs, prof = PLAN[st["i"]]
        if prof and not st["prof"] and now - st["t0"] > secs - 1.5:
            unreal.log_warning("PERF101 PROFILE " + name.split()[0]); cmd("ProfileGPU"); st["prof"] = True
        if now - st["t0"] >= secs:
            d = sorted(st["d"][3:]) or [0]
            avg = sum(d) / len(d)
            log("%-48s frames=%4d avg=%6.2f ms (%5.1f fps) p95=%6.2f ms" % (name, len(d), avg * 1000, 1 / avg if avg else 0, d[max(0, int(len(d) * .95) - 1)] * 1000))
            st["i"] += 1
            if st["i"] >= len(PLAN): finish("done"); return
            PLAN[st["i"]][1](); st.update(t0=time.time(), d=[], prof=False)
    except Exception as e: finish("error %s" % e)
def finish(why):
    h_ = getattr(builtins, "_PERF101", None)
    if h_ is not None: unreal.unregister_slate_post_tick_callback(h_); builtins._PERF101 = None
    try: les.editor_request_end_play()
    except Exception: pass
    for k, v in saved.items():
        try:
            if k == 'throttle': eps.set_editor_property('throttle_cpu_when_not_foreground', v)
            else: ps.set_editor_property(k, v)
        except Exception: pass
    log("finished: %s; settings restored" % why)
if getattr(builtins, "_PERF101", None) is not None: unreal.unregister_slate_post_tick_callback(builtins._PERF101)
builtins._PERF101 = unreal.register_slate_post_tick_callback(step)
print("scheduled")
