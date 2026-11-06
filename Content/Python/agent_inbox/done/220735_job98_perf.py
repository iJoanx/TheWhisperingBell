# Self-timed PIE experiment. Runs from a Slate tick callback so the editor keeps rendering between steps.
import unreal, time, builtins, json
OUT = r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\perf98.txt"
LOG = []
def log(s):
    LOG.append(s)
    open(OUT, "w", encoding="utf-8").write("\n".join(LOG))
ps = unreal.get_default_object(unreal.load_class(None, '/Script/UnrealEd.LevelEditorPlaySettings'))
saved = {}
for p in ('play_net_mode', 'play_number_of_clients'):
    try: saved[p] = ps.get_editor_property(p)
    except Exception: pass
try:
    ps.set_editor_property('play_net_mode', getattr(unreal, 'PlayNetMode').PIE_STANDALONE)
    ps.set_editor_property('play_number_of_clients', 1)
except Exception as e: log("could not force standalone: %s" % e)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.editor_request_begin_play()
log("requested PIE (standalone, 1 player); saved play settings %s" % saved)

def gw(): return unreal.EditorLevelLibrary.get_game_world()
def cmd(c):
    w = gw()
    if w: unreal.SystemLibrary.execute_console_command(w, c)
def dn_actor():
    w = gw()
    if not w: return None
    a = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.load_class(None, '/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle_C'))
    return a[0] if a else None
def tagged(tag):
    w = gw()
    return unreal.GameplayStatics.get_all_actors_with_tag(w, tag) if w else []
def set_dn_tick(on):
    a = dn_actor()
    if not a: return
    a.set_actor_tick_enabled(on)
    for c in a.get_components_by_class(unreal.ActorComponent): c.set_component_tick_enabled(on)
def set_hidden(actors, hidden):
    for a in actors: a.set_actor_hidden_in_game(hidden)

# plan: (name, setup, seconds)
PLAN = [
    ("warmup", lambda: None, 6.0),
    ("A baseline (as you play: day/night running, sewers hidden by the entries)", lambda: None, 5.0),
    ("B day/night paused (no sun movement)", lambda: set_dn_tick(False), 5.0),
    ("C day/night running, sky actors hidden", lambda: (set_dn_tick(True), set_hidden(tagged('RDL_Sky'), True)), 5.0),
    ("D sky back, sewers VISIBLE too", lambda: (set_hidden(tagged('RDL_Sky'), False), set_hidden(tagged('RDL_Sewers'), False)), 5.0),
    ("E sewers visible, day/night paused", lambda: set_dn_tick(False), 5.0),
    ("F back to normal + GPU profile", lambda: (set_dn_tick(True), set_hidden(tagged('RDL_Sewers'), True), cmd("r.ProfileGPU.ShowUI 0"), cmd("ProfileGPU")), 3.0),
    ("G CPU stat dump", lambda: (cmd("stat dumpframe -ms=0.2")), 2.0),
]
st = {"i": -1, "t0": 0.0, "deltas": [], "started": time.time()}
def step(dt):
    try:
        if time.time() - st["started"] > 120:
            finish("timeout"); return
        if gw() is None:
            if st["i"] >= 0: finish("PIE ended early")
            return
        now = time.time()
        if st["i"] == -1:
            st["i"] = 0; st["t0"] = now; st["deltas"] = []; PLAN[0][1](); log("PIE world up: %s" % gw().get_path_name()); return
        st["deltas"].append(dt)
        name, _, secs = PLAN[st["i"]]
        if now - st["t0"] >= secs:
            d = sorted(st["deltas"][2:]) or [0]
            avg = sum(d) / len(d); p95 = d[int(len(d) * 0.95) - 1] if len(d) > 1 else d[0]
            log("%-75s frames=%4d avg=%6.2f ms (%5.1f fps) p95=%6.2f ms worst=%6.2f ms" % (name, len(d), avg * 1000, 1 / avg if avg else 0, p95 * 1000, d[-1] * 1000))
            st["i"] += 1
            if st["i"] >= len(PLAN): finish("done"); return
            PLAN[st["i"]][1](); st["t0"] = time.time(); st["deltas"] = []
    except Exception as e:
        finish("error %s" % e)
def finish(why):
    h = getattr(builtins, "_PERF98", None)
    if h is not None:
        unreal.unregister_slate_post_tick_callback(h); builtins._PERF98 = None
    try: les.editor_request_end_play()
    except Exception: pass
    for p, v in saved.items():
        try: ps.set_editor_property(p, v)
        except Exception: pass
    log("finished: %s; play settings restored" % why)
old = getattr(builtins, "_PERF98", None)
if old is not None: unreal.unregister_slate_post_tick_callback(old)
builtins._PERF98 = unreal.register_slate_post_tick_callback(step)
print("perf test scheduled")
