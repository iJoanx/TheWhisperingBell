import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
DN = '/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle'
G = DN + ':GetSunYear'
unreal.load_asset('/Game/NightSky/BP_DayNightCycle').modify()
# 0) fold "Make Literal Int" nodes into plain values typed on the pins they feed
for x in infos(nodes(G)):
    if x['type_id'] != 'Math|Integer|MakeLiteralInt': continue
    v = [p for p in x['input_pins'] if not 'Exec' in str(p.get('type_id'))][0].get('value')
    dsts = x['output_pins'][0].get('connected_pins') or []
    call('delete_node', {'node': {'refPath': x['node']['refPath']}})
    for d in dsts:
        for y in infos([d['node']['refPath']]):
            for p in y['input_pins']:
                if p['pin_id'] == d or (p['pin_id'].get('index_id') == d.get('index_id') and p['pin_id'].get('direction') == d.get('direction')):
                    setv(p, v)
    out.append("folded literal %s into %d pin(s)" % (v, len(dsts)))
# 1) give every getter its own copy so wires don't fan out across the graph
for x in infos(nodes(G)):
    if 'VariableGet' not in x['node']['refPath']: continue
    o = x['output_pins'][0]
    links = o.get('connected_pins') or []
    for d in links[1:]:
        n = node(G, x['type_id'], 0, 0)
        call('break_pins', {'output_pin': o['pin_id'], 'input_pin': d})
        connect(info(n)['output_pins'][0], {'pin_id': d})
        out.append("split getter %s" % x['type_id'])
X = {x['node']['refPath']: x for x in infos(nodes(G))}
obj = {r: unreal.find_object(None, r) for r in X}
for o in obj.values(): o.modify()
def size(r):
    s = obj[r].get_node_size(); w, hh = int(s.x), int(s.y)
    return (w if w > 0 else 180, hh if hh > 0 else 60)
def setpos(r, x, y): obj[r].set_node_pos(unreal.IntPoint(int(x), int(y)))
def is_exec(p): return 'Exec' in str(p.get('type_id', ''))
def children(r):
    res = []
    for p in X[r]['input_pins']:
        if is_exec(p): continue
        for c in (p.get('connected_pins') or []): res.append(c['node']['refPath'])
    return res
GAP_X, GAP_Y = 70, 30
def place_tree(r, right, top):
    """Place r with its right edge at `right`, its inputs stacked to its left. Returns the height used."""
    w, hh = size(r)
    ch = children(r)
    y = top; used = 0
    for c in ch:
        hgt = place_tree(c, right - w - GAP_X, y)
        y += hgt + GAP_Y; used += hgt + GAP_Y
    used = max(hh, used - GAP_Y if ch else hh)
    setpos(r, right - w, top + (used - hh) // 2 if ch else top)
    return used
entry = next(r for r in X if 'FunctionEntry' in r)
branch = next(r for r in X if 'IfThenElse' in r)
results = [r for r in X if 'FunctionResult' in r]
def exec_target(pin_name):
    for p in X[branch]['output_pins']:
        if p['name'] == pin_name:
            for c in (p.get('connected_pins') or []): return c['node']['refPath']
r_true, r_false = exec_target('then'), exec_target('else')
out.append("entry %s branch %s true %s false %s" % tuple(s.split('.')[-1] if s else None for s in (entry, branch, r_true, r_false)))
# condition tree: below-left of the Branch
cond_root = children(branch)
cond_h = 0
bw, bh = size(branch)
# measure condition tree width by placing it first relative to 0
BX = 0
if cond_root:
    cond_h = place_tree(cond_root[0], -GAP_X, 140)
def collect(r, acc):
    acc.add(r)
    for c in children(r): collect(c, acc)
    return acc
cond_nodes = collect(cond_root[0], set()) if cond_root else set()
min_x = min([obj[r].get_node_pos().x for r in cond_nodes] or [0])
# shift so the condition tree starts right of the entry
ew, eh = size(entry)
shift = (ew + 120) - min_x
for r in cond_nodes:
    p = obj[r].get_node_pos(); setpos(r, p.x + shift, p.y)
setpos(entry, 0, 0)
BX = shift + GAP_X
setpos(branch, BX, 0)
# results to the right; the stand-in formula tree sits between Branch and the false Return, below the exec wires
false_tree = children(r_false) if r_false else []
true_tree = children(r_true) if r_true else []
tmp_right = 0
fw = 0
if false_tree:
    # place to measure width
    place_tree(false_tree[0], 100000, 100000)
    xs2 = [obj[r].get_node_pos().x for r in X if obj[r].get_node_pos().x > 50000]
    fw = 100000 - min(xs2)
RX = BX + bw + 160 + fw + GAP_X
if r_true:
    setpos(r_true, RX, -120)
    if true_tree: place_tree(true_tree[0], RX - GAP_X, -200)
if r_false:
    setpos(r_false, RX, 220)
    if false_tree: place_tree(false_tree[0], RX - GAP_X, 220)
try: out.append("compile: %s" % str(compile_bp(DN))[:400])
except Exception as e: out.append("compile err %s" % str(e)[:400])
for r in X:
    p = obj[r].get_node_pos(); s = size(r)
    out.append("%-40s %-40s pos(%d,%d) size(%d,%d)" % (r.split('.')[-1], X[r]['type_id'], p.x, p.y, s[0], s[1]))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump179.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
