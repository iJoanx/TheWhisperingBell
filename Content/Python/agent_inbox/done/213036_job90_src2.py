import os
p = r"C:\Program Files\Epic Games\UE_5.8\Engine\Source\Runtime\Engine\Private\Character.cpp"
L = open(p, encoding="utf-8", errors="ignore").read().splitlines()
print("\n".join("%d %s" % (i+1, L[i]) for i in range(2420, 2456)))
p2 = r"C:\Program Files\Epic Games\UE_5.8\Engine\Source\Runtime\Engine\Private\Components\CharacterMovementComponent.cpp"
L2 = open(p2, encoding="utf-8", errors="ignore").read().splitlines()
import re
for i, l in enumerate(L2):
    if re.search(r"bAllowTickPose|ShouldTickPose|EnableServerAutonomousTickPose|ServerTickPose|ListenServerAnim|bServerTicksAnim|AutonomousTickPose", l) and i not in range(12030, 12045):
        print("CMC %d: %s" % (i+1, " | ".join(x.strip() for x in L2[max(0,i-1):i+2])[:300]))
p3 = r"C:\Program Files\Epic Games\UE_5.8\Engine\Source\Runtime\Engine\Classes\GameFramework\Character.h"
L3 = open(p3, encoding="utf-8", errors="ignore").read().splitlines()
for i, l in enumerate(L3):
    if re.search(r"TickPose|AutonomousTick|ServerAnim", l):
        print("CH.h %d: %s" % (i+1, " | ".join(x.strip() for x in L3[max(0,i-3):i+2])[:400]))
