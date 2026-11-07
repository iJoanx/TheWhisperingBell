import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
GAP_X, GAP_Y = 70, 30
ar = unreal.AssetRegistryHelpers.get_asset_registry()
_assets = None
def find_bp(name):
    global _assets
    if _assets is None: _assets = ar.get_assets(unreal.ARFilter(package_paths=['/Game'], recursive_paths=True))
    for a in _assets:
        if str(a.asset_name) == name: return str(a.package_name) + '.' + name
def is_exec(p): return 'Exec' in str(p.get('type_id', ''))
LITS = ('Math|Integer|MakeLiteralInt', 'Math|Float|MakeLiteralFloat', 'Math|Float|MakeLiteralDouble', 'Utilities|MakeLiteralBool', 'Math|Boolean|MakeLiteralBool')

class Graph:
    def __init__(self, G, only=None):
        self.G = G
        self.X = {x['node']['refPath']: x for x in infos(nodes(G))}
        self.only = only
        self.obj = {r: unreal.find_object(None, r) for r in self.X}
        for o in self.obj.values():
            if o: o.modify()
    def size(self, r):
        s = self.obj[r].get_node_size(); w, hh = int(s.x), int(s.y)
        return (w if w > 0 else 200, hh if hh > 0 else 60)
    def pos(self, r): p = self.obj[r].get_node_pos(); return p.x, p.y
    def setpos(self, r, x, y): self.obj[r].set_node_pos(unreal.IntPoint(int(x), int(y)))
    def has_exec(self, r): return any(is_exec(p) for p in self.X[r]['input_pins'] + self.X[r]['output_pins'])
    def data_children(self, r):
        res = []
        for p in self.X[r]['input_pins']:
            if is_exec(p): continue
            for c in (p.get('connected_pins') or []):
                cr = c['node']['refPath']
                if cr in self.X and not self.has_exec(cr): res.append(cr)
        return res
    def exec_children(self, r):
        res = []
        for p in self.X[r]['output_pins']:
            if not is_exec(p): continue
            for c in (p.get('connected_pins') or []):
                if c['node']['refPath'] in self.X: res.append(c['node']['refPath'])
        return res

def split_getters(G):
    n_ = 0
    for x in infos(nodes(G)):
        if 'VariableGet' not in x['node']['refPath'] or not x['output_pins']: continue
        o = x['output_pins'][0]
        links = (o.get('connected_pins') or [])[1:]
        if not links: continue
        t = x['type_id']
        if t.startswith('|'):
            nm = t[1:]
            try: cands = [c.get('type_id') if isinstance(c, dict) else c for c in types(G, nm)]
            except Exception: cands = []
            t = next((c for c in cands if c.startswith('Variables|') and c.endswith('|' + nm)), None)
            if not t: out.append("  (kept shared getter %s)" % nm); continue
        for d in links:
            n = node(G, t, 0, 0)
            call('break_pins', {'output_pin': o['pin_id'], 'input_pin': d})
            connect(info(n)['output_pins'][0], {'pin_id': d}); n_ += 1
    return n_
def fold_literals(G):
    n_ = 0
    for x in infos(nodes(G)):
        if x['type_id'] not in LITS: continue
        ins = [p for p in x['input_pins'] if not is_exec(p)]
        if not ins: continue
        v = ins[0].get('value')
        dsts = x['output_pins'][0].get('connected_pins') or []
        call('delete_node', {'node': {'refPath': x['node']['refPath']}})
        for d in dsts:
            for y in infos([d['node']['refPath']]):
                for p in y['input_pins']:
                    if p['pin_id'] == d: setv(p, v)
        n_ += 1
    return n_

def layout(g, roots):
    placed = set()
    def place_tree(r, right, top):
        if r in placed: return 0
        placed.add(r)
        w, hh = g.size(r)
        ch = [c for c in g.data_children(r) if c not in placed]
        y = top; used = 0
        for c in ch:
            hgt = place_tree(c, right - w - GAP_X, y)
            if hgt: y += hgt + GAP_Y; used += hgt + GAP_Y
        used = max(hh, used - GAP_Y) if used else hh
        g.setpos(r, right - w, top + (used - hh) // 2 if used > hh else top)
        return used
    def tree_width(r, seen):
        if r in seen or r in placed: return 0
        seen.add(r)
        w, _ = g.size(r)
        return w + max([tree_width(c, seen) + GAP_X for c in g.data_children(r)] or [0])
    def place_exec(r, x, y):
        """Places exec node r at lane y, left edge at least x. Returns (right edge, bottom)."""
        if r in placed: return x, y
        kids = [c for c in g.data_children(r) if c not in placed]
        tw = max([tree_width(c, set()) for c in kids] or [0])
        nx = x + (tw + GAP_X if tw else 0)
        placed.add(r)
        w, hh = g.size(r)
        g.setpos(r, nx, y)
        bottom = y + hh
        ty = y + hh + 40
        for c in kids:
            hgt = place_tree(c, nx - GAP_X, ty)
            if hgt: ty += hgt + GAP_Y
        bottom = max(bottom, ty)
        right = nx + w
        lane_y = y
        first = True
        for c in g.exec_children(r):
            if c in placed: continue
            if first:
                rr, bb = place_exec(c, right + GAP_X + 40, y); first = False
            else:
                rr, bb = place_exec(c, right + GAP_X + 40, bottom + 60)
            bottom = max(bottom, bb)
        return right, bottom
    y = 0
    for r in roots:
        _, b = place_exec(r, 0, y)
        y = b + 150
    # anything not reached (pure-only graph etc.)
    return len(placed)

def tidy_whole(bpname, graphname=None, root_filter=None):
    bp = find_bp(bpname)
    if not bp: out.append("no asset %s" % bpname); return
    graphs = {gg['refPath'].split(':')[-1]: gg['refPath'] for gg in call('list_graphs', {'blueprint': {'refPath': bp}})}
    if graphname not in graphs: out.append("%s: no graph %s" % (bpname, graphname)); return
    G = graphs[graphname]
    unreal.load_asset(bp.split('.')[0]).modify()
    if root_filter is None:
        s = split_getters(G); f = fold_literals(G)
        g = Graph(G)
        roots = [r for r in g.X if 'FunctionEntry' in r]
    else:
        g0 = Graph(G)
        root = [r for r in g0.X if root_filter in g0.X[r]['type_id']][0]
        # collect the component of this event so the rest of the graph is untouched
        comp, stack = set(), [root]
        while stack:
            r = stack.pop()
            if r in comp or r not in g0.X: continue
            comp.add(r)
            for p in g0.X[r]['input_pins'] + g0.X[r]['output_pins']:
                for c in (p.get('connected_pins') or []): stack.append(c['node']['refPath'])
        s = f = 0
        g = g0
        # keep the event where it was: offset after layout
        ox, oy = g.pos(root)
        roots = [root]
    n = layout(g, roots)
    if root_filter is not None:
        nx, ny = g.pos(roots[0])
        for r in comp:
            x, y = g.pos(r); g.setpos(r, x - nx + ox, y - ny + oy)
    out.append("tidied %s:%s (%d nodes laid out, %d getters split, %d literals folded)" % (bpname, graphname, n, s, f))

for bpn, gn in (('BP_DayNightCycle', 'OnRep_NetTime'), ('ABP_Unarmed3', 'CalcFlySpeed')):
    try: tidy_whole(bpn, gn)
    except Exception as e: out.append("ERR %s:%s %s" % (bpn, gn, str(e)[:500]))
for bpn in ('BP_DayNightCycle', 'ABP_Unarmed3'):
    try: r = compile_bp(find_bp(bpn)); out.append("compile %s: %s" % (bpn, str(r)[:200]))
    except Exception as e: out.append("compile err %s %s" % (bpn, str(e)[:300]))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump181.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
