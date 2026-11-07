import unreal, traceback, time
out = []
try:
    world = unreal.EditorLevelLibrary.get_editor_world()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    node = next(a for a in eas.get_all_level_actors() if 'SL_303' in a.get_actor_label() and 'Crossing' in a.get_actor_label())
    c = node.get_actor_location()
    out.append("node %s at (%.0f,%.0f,%.0f) class %s" % (node.get_actor_label(), c.x, c.y, c.z, node.get_class().get_name()))
    R, S = 360.0, 4.0
    n = int(2 * R / S) + 1
    t0 = time.time()
    Z = {}
    for i in range(n):
        for j in range(n):
            x, y = c.x - R + i * S, c.y - R + j * S
            hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, c.z + 150), unreal.Vector(x, y, c.z - 250),
                                                         unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [], unreal.DrawDebugTrace.NONE, True)
            if hit is not None:
                h = hit.to_tuple()
                if h[0]:
                    Z[(i, j)] = h[4].z - c.z
    out.append("traces %d in %.1fs, hits %d" % (n * n, time.time() - t0, len(Z)))
    # small steps between neighbours on near-walkway ground (big drops = channel edges, ignore)
    steps = []
    for (i, j), z in Z.items():
        if z < -20: continue            # channel bed
        for di, dj in ((1, 0), (0, 1)):
            z2 = Z.get((i + di, j + dj))
            if z2 is None or z2 < -20: continue
            d = abs(z2 - z)
            if 0.6 < d < 15.0:
                steps.append((d, i, j, di, dj, z, z2))
    out.append("small steps (0.6-15 cm) between 4 cm neighbours: %d" % len(steps))
    steps.sort(reverse=True)
    for d, i, j, di, dj, z, z2 in steps[:25]:
        out.append("  %.1f cm at (%+.0f,%+.0f) z %.1f -> %.1f" % (d, -R + i * S, -R + j * S, z, z2))
    # coarse map: '.' walkway-level, '-' channel, '#' step cell, ' ' no hit
    stepcells = {(i, j) for _, i, j, _, _, _, _ in steps}
    for j in range(n - 1, -1, -6):
        row = ''
        for i in range(0, n, 3):
            z = Z.get((i, j))
            row += ' ' if z is None else ('#' if any((i + a, j + b) in stepcells for a in range(3) for b in range(6)) else ('-' if z < -20 else ('.' if abs(z) < 3 else ('^' if z > 0 else 'v'))))
        out.append(row)
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump224.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
