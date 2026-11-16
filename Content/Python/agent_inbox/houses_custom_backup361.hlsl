
float2 dx = ddx(UV0);
float2 dy = ddy(UV0);
// UE flips v when it imports an FBX (v_ue = 1 - v_blender). Undo that for the logic; textures are sampled
// with the UE value (vUE) because it already matches UE's image orientation.
float u = UV0.x;
float vUE = UV0.y;
float v = 1.0 - vUE;                                // Blender's v: floor(v) = floor row, etc.
float special = UV1.x;
float cls = 1.0 - UV1.y;                            // face class (stored in Blender as UV1.v)
float rows = UV2.x;
float pk = 1.0 - UV2.y;
float oneTile = floor((pk + 0.5) / 100000.0);       // 1 = the wall is only ONE tile wide

float isWall  = abs(cls - 1.0) < 0.5 ? 1.0 : 0.0;
float isFound = abs(cls - 2.0) < 0.5 ? 1.0 : 0.0;
float isAlt   = abs(cls - 3.0) < 0.5 ? 1.0 : 0.0;
float isCTop  = abs(cls - 4.0) < 0.5 ? 1.0 : 0.0;
float isChim  = abs(cls - 5.0) < 0.5 ? 1.0 : 0.0;
float isCler  = abs(cls - 6.0) < 0.5 ? 1.0 : 0.0;
float isMans  = abs(cls - 7.0) < 0.5 ? 1.0 : 0.0;
float isGFlat = abs(cls - 8.0) < 0.5 ? 1.0 : 0.0;
float isCGab  = abs(cls - 9.0) < 0.5 ? 1.0 : 0.0;
float wallish = max(isWall, isAlt);

float fl = floor(u);
float fr = frac(u);
float parity = fmod(fl, 2.0);                       // 1 = column 2 (mirrored)

// which ward / set / random this house has (UV channel 5: u = (ward + 1) + 16 * set, v = random; v comes in flipped)
float hCode = floor(UV5.x + 0.5);
float setRaw = floor(hCode / 16.0);
float wardPlus = hCode - setRaw * 16.0;             // ward index + 1 (0 = no ward)
float hasWard = wardPlus > 0.5 ? 1.0 : 0.0;
float wi = max(wardPlus - 1.0, 0.0);
float setI = clamp(setRaw, 0.0, SetsPerWard - 1.0);
float Rand = 1.0 - UV5.y;
float blk = wi * SetsPerWard + setI;
float cb = blk * ColourStride;                      // first colour slice of this set
float mb = blk * MaskStride;                        // first mask slice of this set

// wall images: mirrored in column 2 (also on the alternating gable ends).
// A single tile (0..1) is pulled half a texel inwards (64x64 slices) so the wrap sampler never blends in
// the opposite edge: (x * 63 + 0.5) / 64
float parW = parity * wallish;
float2 uvm = float2(lerp(fr, 1.0 - fr, parW), 1.0 - frac(v));
float2 qm = saturate(uvm) * 0.9999;
    qm.x = lerp(qm.x, (saturate(uvm).x * 63.0 + 0.5) / 64.0, EdgeInset);   // horizontal only
float2 dxm = float2(dx.x * lerp(1.0, -1.0, parW), dx.y);
float2 dym = float2(dy.x * lerp(1.0, -1.0, parW), dy.y);

float ground = (isWall > 0.5 && floor(v) < 0.5) ? 1.0 : 0.0;        // first floor of a wall

// pick the slot and the sampling uv of this part (default = ordinary roof: Tiles)
float slotI = 13.0;
float2 qS = UV0;
float2 dxS = dx;
float2 dyS = dy;
if (isCler > 0.5)                                                   // clerestory flat parts: TopFloor, plain uv
    slotI = 2.0;
else if (isMans > 0.5)                                              // mansard flat top: Tiles
    slotI = 13.0;
else if (isChim > 0.5 || isCTop > 0.5)                              // chimney: slot 14, ONE image in four quadrants
{
    // top-left quadrant = chimney top, bottom-left = chimney sides (v repeats up the side); the right half is free.
    // Each quadrant is pulled 2 % inwards so the neighbouring quadrant never bleeds in.
    float qe = 0.02;
    float tx = saturate(u) * (1.0 - 2.0 * qe) + qe;
    float ty = (isCTop > 0.5) ? saturate(v) : frac(v);              // v = Blender's v (up)
    ty = saturate(ty) * (1.0 - 2.0 * qe) + qe;
    qS = float2(0.5 * tx, (isCTop > 0.5) ? 0.5 * (1.0 - ty) : 1.0 - 0.5 * ty);
    dxS = dx * 0.5;
    dyS = dy * 0.5;
    slotI = 14.0;                                                   // Chimney
}
else if (isFound > 0.5)
    slotI = 11.0;                                                   // Foundation
else if (isGFlat > 0.5)
{
    // the gable triangle spans u 0..2, apex on u = 1: left half = the image, right half = its mirror
    float ug = u - 2.0 * floor(u * 0.5);
    float gx = 1.0 - abs(1.0 - ug);
    qS = saturate(float2(gx, vUE)) * 0.9999;
    qS.x = lerp(qS.x, (saturate(float2(gx, vUE)).x * 63.0 + 0.5) / 64.0, EdgeInset);   // horizontal only
    dxS = float2(dx.x * (ug > 1.0 ? -1.0 : 1.0), dx.y);
    dyS = float2(dy.x * (ug > 1.0 ? -1.0 : 1.0), dy.y);
    slotI = 10.0;                                                   // GableFlat
}
else if (isCGab > 0.5)
{
    qS = saturate(UV0) * 0.9999;
    qS.x = lerp(qS.x, (saturate(UV0).x * 63.0 + 0.5) / 64.0, EdgeInset);   // horizontal only
    slotI = 9.0;                                                    // BarnRoof
}
else if (wallish > 0.5)
{
    qS = qm; dxS = dxm; dyS = dym;
    if (ground > 0.5)
        slotI = 0.0;                                                // BottomFloor
    else if (oneTile > 0.5 && isWall > 0.5)
        slotI = 3.0;                                                // TopFloorNarrow
    else
        slotI = 2.0;                                                // TopFloor
}

// ---- windows hidden behind a neighbouring house (walls only) ----
// The wall has 18 slots along its length, 3 bits each = how many floors from the ground the neighbour in front of
// that slot covers (0..7). Three 18-bit chunks (6 slots each): UV3.x = c0, UV3.y = c1, UV4.x = c2,
// UV4.y = tiles on the wall (UV y comes in flipped)
float c0 = floor(UV3.x + 0.5);
float c1 = floor((1.0 - UV3.y) + 0.5);
float c2 = floor(UV4.x + 0.5);
float wn = max(floor((1.0 - UV4.y) + 0.5), 1.0);
float hid = 0.0;
if (HideWindows > 0.5 && isWall > 0.5)               // the decode below only runs on wall tiles (roofs, foundations, chimneys skip it)
{
    float cen = (fl + 0.5) / wn;                     // middle of this tile along the wall, 0..1
    float slot = clamp(floor(cen * 18.0 - 0.02), 0.0, 17.0);   // the -0.02 keeps a slot edge from flipping
    float chunk = floor(slot / 6.0);
    float sl6 = slot - chunk * 6.0;
    float cv = chunk < 0.5 ? c0 : (chunk < 1.5 ? c1 : c2);
    float cov = fmod(floor((cv + 0.5) / exp2(3.0 * sl6)), 8.0);      // floors the neighbour covers (0..7)
    hid = (floor(v) < cov - 0.5) ? 1.0 : 0.0;
}
// ---- half windows next to a hidden tile ----
// The green window is split across the seam of a tile pair (columns 0|1, 2|3, ...); in image space its half always sits
// at the tile's x = 1 edge (column 2 of a pair is mirrored). If the partner tile is hidden, this tile would keep half a
// window: draw the empty image over a strip of GreenStripWidth (0..1 of a tile) along that edge.
float hidP = 0.0;
if (HideWindows > 0.5 && isWall > 0.5 && GreenStripWidth > 0.0 && hid < 0.5)
{
    float pcol = fl + ((parity < 0.5) ? 1.0 : -1.0);              // the partner column
    if (pcol > -0.5 && pcol < wn - 0.5)
    {
        float cenP = (pcol + 0.5) / wn;
        float slotP = clamp(floor(cenP * 18.0 - 0.02), 0.0, 17.0);
        float chP = floor(slotP / 6.0);
        float s6P = slotP - chP * 6.0;
        float cvP = chP < 0.5 ? c0 : (chP < 1.5 ? c1 : c2);
        float covP = fmod(floor((cvP + 0.5) / exp2(3.0 * s6P)), 8.0);
        hidP = (floor(v) < covP - 0.5) ? 1.0 : 0.0;
    }
}
if (hidP > 0.5 && (slotI < 0.5 || (slotI > 1.5 && slotI < 3.5)) && floor(saturate(qm.x) * 64.0) >= 64.0 - floor(GreenStripWidth * 64.0 + 0.5))   // whole texels of the 64 px image
{
    qS = qm; dxS = dxm; dyS = dym;
    slotI = (ground > 0.5) ? 1.0 : ((oneTile > 0.5) ? 5.0 : 4.0);   // the empty version of this tile, only in the strip
}
if (hid > 0.5)
{
    qS = qm; dxS = dxm; dyS = dym;
    slotI = (ground > 0.5) ? 1.0 : ((oneTile > 0.5) ? 5.0 : 4.0);    // BottomFloorEmpty / TopFloorNarrowEmpty / TopFloorEmpty
}

// door tile: column index + 1 == UVSpecial.u; on walls it is the first floor, on the foundation the
// tile row next to the ground (the top row: floor(v) + 1 == rows)
float isSpec = (special > 0.5 && abs(fl + 1.0 - special) < 0.01) ? 1.0 : 0.0;
float foundTop = (isFound > 0.5 && abs(floor(v) + 1.0 - rows) < 0.01) ? 1.0 : 0.0;
float sGround = max(ground, foundTop);
if (isSpec * sGround > 0.5 && hid < 0.5)       // an empty (hidden-window) tile always wins over the door
{
    float parS = parity * max(isWall, isFound);
    float2 uvs = float2(lerp(fr, 1.0 - fr, parS), 1.0 - frac(v));
    qS = saturate(uvs) * 0.9999;
    qS.x = lerp(qS.x, (saturate(uvs).x * 63.0 + 0.5) / 64.0, EdgeInset);   // horizontal only
    dxS = float2(dx.x * lerp(1.0, -1.0, parS), dx.y);
    dyS = float2(dy.x * lerp(1.0, -1.0, parS), dy.y);
    slotI = (isFound > 0.5) ? 12.0 : 6.0;                           // FoundationStairs / Door
}

// Special1 / Special2: first floor of a wall only (the foundation is never changed). UVRows.y packs
// tile index + 1 + 1000 * variant (variant 0..1); 0 = none. Not where the window is hidden.
float p2 = floor(pk + 0.5) - oneTile * 100000.0;          // rounded: at ~100000 a float only resolves ~0.008
float var2 = floor((p2 + 0.5) / 1000.0);
float t2 = p2 - var2 * 1000.0;
if (p2 > 0.5 && ground > 0.5 && hid < 0.5 && abs(fl + 1.0 - t2) < 0.01)
{
    float2 uv2 = float2(lerp(fr, 1.0 - fr, parity), 1.0 - frac(v));
    qS = saturate(uv2) * 0.9999;
    qS.x = lerp(qS.x, (saturate(uv2).x * 63.0 + 0.5) / 64.0, EdgeInset);   // horizontal only
    dxS = float2(dx.x * lerp(1.0, -1.0, parity), dx.y);
    dyS = float2(dy.x * lerp(1.0, -1.0, parity), dy.y);
    slotI = 7.0 + min(var2, 1.0);                                   // Special1 / Special2
}

// roof undersides (eaves): one flat colour, the centre of the Tiles image's bottom-left texel, so no texel edge runs through them
if (abs(slotI - 13.0) < 0.5 && Nrm.z < -0.5)
    qS = float2(0.5 / 64.0, 63.5 / 64.0);

// the colour image, then the tint: masked slots (0..10) where the mask's blue is on, Tiles (13) as a whole
float3 col = Arr.SampleLevel(ArrSampler, float3(qS, cb + slotI), 0).rgb;     // level 0: the arrays have no mips (pixel art). A plain Sample() is not allowed in the ray tracing hit shaders
float amt = 0.0;
float roofRow = 0.0;
float3 amtRaw = float3(0.0, 0.0, 0.0);
if (slotI < 10.5)
{
    amtRaw = MaskArr.SampleLevel(MaskArrSampler, float3(qS, mb + slotI), 0).rgb;     // the ONE mask read: blue = tint, red / green = the two windows
    amt = amtRaw.b;
}
else if (abs(slotI - 13.0) < 0.5)
{
    amt = 1.0;
    roofRow = 1.0;
}
float pv = (wi * 2.0 + roofRow + 0.5) / (NumWards * 2.0);
float3 tint = Pal.SampleLevel(PalSampler, float2(saturate(Rand), pv), 0).rgb;
// OVERLAY blend of the tint over the painted colour (not multiply): dark parts get darker, light parts lighter, so the
// painted detail survives; neutral grey (0.5) leaves the colour as it is
float3 ovl = lerp(2.0 * col * tint, 1.0 - 2.0 * (1.0 - col) * (1.0 - tint), step(0.5, col));
col = lerp(col, ovl, saturate(amt * TintStrength * hasWard));
// ---- lit windows: the mask's RED window and its GREEN window are each lit or dark, at random ----
// A window is made of TWO tile halves: column 2 of every pair is mirrored, so the tiles meet green-to-green (columns 0|1, 2|3, ...)
// and red-to-red (columns 1|2, 3|4, ...). Both halves of one window share one random decision (keyG / keyR below), so a window is
// never half lit. The hash only uses whole numbers (rounded first), so every pixel of a window gets exactly the same answer:
// no flicker from tiny interpolation differences in the house's random number.
float winTile = (isWall > 0.5 && hid < 0.5 && (slotI < 0.5 || (slotI > 1.5 && slotI < 3.5))) ? 1.0 : 0.0;   // BottomFloor / TopFloor / TopFloorNarrow
float glow = 0.0;
float litR = 0.0;
float litG = 0.0;
float dbgCol = 0.0;
float dbgRow = 0.0;
if ((Night > 0.001 || DebugView > 0.5) && winTile > 0.5)       // by day (Night = 0) the whole block is skipped
{
    float Rq   = floor(Rand * 1024.0 + 0.5);                        // the house's random number as a whole number 0..1024
    float rowK = floor(v + 0.001);                                  // floor (row) of the tile
    float colK = floor(fl + 0.5);                                   // column of the tile
    float wallK = fmod(c0 + 17.0 * c2 + 101.0 * wn, 997.0);         // identifies the wall
    float keyG = floor(colK * 0.5);                                 // greens meet in the pairs 0|1, 2|3, ...
    float keyR = floor((colK + 1.0) * 0.5);                         // reds meet in the pairs 1|2, 3|4, ...
    // GREEN and RED are decided independently (own hash each). A window is made of two tile halves, so both halves share one key:
    //   green: its window sits on the seam inside a tile pair (columns 2k | 2k+1)               -> key = floor(col / 2)
    //   red:   each red window lies inside ONE tile, so it is decided by that tile alone            -> key = col
    //          (RedAcrossSeam = 1 would pair red windows across the seam between the pairs, key = floor((col + 1) / 2))
    // WindowPairing = 0: every tile decides by itself for both colours.
    if (WindowPairing > 0.5)
    {
        keyG = floor(colK * 0.5);
        keyR = (RedAcrossSeam > 0.5) ? floor((colK + 1.0) * 0.5) : colK;
    }
    else
    {
        keyG = colK;
        keyR = colK;
    }
    float3 pR = frac(float3(Rq + 0.0, keyR + 3.0 * rowK, wallK) * float3(0.1031, 0.1030, 0.0973));
    pR += dot(pR, pR.yxz + 33.33);
    float hR = frac((pR.x + pR.y) * pR.z);
    float3 pG = frac(float3(Rq + 517.0, keyG + 3.0 * rowK + 211.0, wallK + 89.0) * float3(0.1031, 0.1030, 0.0973));
    pG += dot(pG, pG.yxz + 33.33);
    float hG = frac((pG.x + pG.y) * pG.z);
    // red / green come from the same mask read as the tint (amtRaw); thresholded so a soft edge still gives a clean window
    // red and green are separate lit/dark decisions (own hash); see the keys above for how the tile halves of one window agree.
    litR = smoothstep(0.3, 0.7, amtRaw.r) * step(hR, RedChance);
    litG = smoothstep(0.3, 0.7, amtRaw.g) * step(hG, GreenChance);
    dbgCol = colK;
    dbgRow = rowK;
    glow = saturate(max(litR, litG));
}
// DebugView (a material instance parameter, 0 = off): paints the base colour so the logic can be SEEN (set Night to 0 or 1, either works)
//   1 = the mask as it is read: red = the red window, green = the green window, blue = the tint region
//   2 = which windows are lit: red = red window lit, green = green window lit (yellow = both), dark = dark; outside windows = grey
//   3 = tile layout: red = odd columns, green = odd floors, blue = position across the tile (a 0..1 ramp; shows where each tile starts)
if (DebugView > 0.5)
{
    glow = 0.0;
    if (DebugView < 1.5)
        col = amtRaw;
    else if (DebugView < 2.5)
        col = (winTile > 0.5) ? float3(litR, litG, 0.0) : float3(0.15, 0.15, 0.15);
    else
        col = float3(fmod(floor(fl + 0.5), 2.0), fmod(floor(v + 0.001), 2.0), fr);
}
return float4(col, glow);
