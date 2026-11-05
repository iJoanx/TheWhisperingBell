"""Lets Claude run editor scripts in this project without you typing them.

Every half second it looks in Content/Python/agent_inbox/ for *.py files (written there by
Claude), runs each once in the editor, moves it to agent_inbox/done/ and writes what it printed
(and any error) next to it as <name>.out.txt. Nothing else is touched.

    py agent_bridge.py            start it now (init_unreal.py starts it with the editor)
    py agent_bridge.py stop       stop it
"""
import builtins
import contextlib
import io
import os
import sys
import time
import traceback
import unreal

INBOX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_inbox")
DONE = os.path.join(INBOX, "done")
_STATE = {"last": 0.0}


def _run(path):
    name = os.path.basename(path)
    os.makedirs(DONE, exist_ok=True)
    target = os.path.join(DONE, time.strftime("%H%M%S_") + name)
    os.replace(path, target)                              # never runs twice
    buf = io.StringIO()
    t0 = time.time()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            code = compile(open(target, encoding="utf-8").read(), target, "exec")
            exec(code, {"__name__": "__agent__", "__file__": target})
            print("\n[ok in %.1f s]" % (time.time() - t0))
        except Exception:
            traceback.print_exc()
            print("\n[failed after %.1f s]" % (time.time() - t0))
    open(os.path.join(INBOX, os.path.splitext(name)[0] + ".out.txt"), "w", encoding="utf-8").write(buf.getvalue())
    unreal.log("AGENT ran %s" % name)


def _tick(dt):
    now = time.time()
    if now - _STATE["last"] < 0.5:
        return
    _STATE["last"] = now
    try:
        editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        if editor.get_game_world():
            return                                        # not while playing
        if editor.get_editor_world() is None:
            return                                        # map teardown / load transition
        if not os.path.isdir(INBOX):
            return
        for f in sorted(os.listdir(INBOX)):
            p = os.path.join(INBOX, f)
            if not f.endswith(".py") or not os.path.isfile(p):
                continue
            if now - os.path.getmtime(p) < 1.0:           # still being written
                continue
            _run(p)
            break                                         # one per tick
    except Exception as e:  # never break the editor tick
        unreal.log_warning("Agent bridge: %s" % e)


def start():
    stop()
    os.makedirs(INBOX, exist_ok=True)
    builtins._AGENT_BRIDGE_HANDLE = unreal.register_slate_post_tick_callback(_tick)
    unreal.log("Agent bridge on: %s" % INBOX)


def stop():
    h = getattr(builtins, "_AGENT_BRIDGE_HANDLE", None)
    if h is not None:
        try:
            unreal.unregister_slate_post_tick_callback(h)
        except Exception:
            pass
    builtins._AGENT_BRIDGE_HANDLE = None


if __name__ != "agent_bridge":                           # run as a script (py agent_bridge.py)
    if "stop" in sys.argv[1:]:
        stop()
    else:
        start()
