import os, re
root = r"C:\Program Files\Epic Games\UE_5.8\Engine\Source\Runtime\Engine"
hits = 0
for dp, dn, fn in os.walk(root):
    for f in fn:
        if not f.endswith((".h",".cpp")): continue
        p = os.path.join(dp, f)
        if "DataLayer" not in p and "WorldPartition" not in p: continue
        try: lines = open(p, encoding="utf-8", errors="ignore").read().splitlines()
        except Exception: continue
        for i, l in enumerate(lines):
            if re.search(r"ClientOnly", l):
                print(p.replace(root, ""), i+1, l.strip()[:200]); hits += 1
                if hits > 120: raise SystemExit
print("hits", hits)
