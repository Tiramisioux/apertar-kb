# Copies the named top-level functions out of CameraController.cpp, verbatim, so the host test
# compiles the real T34 code without libcamera (as T33's extract.py did for the App).
# Usage: python3 core_ladder_probe_extract.py <CameraController.cpp> <out.inc>
import sys

src, out = sys.argv[1], sys.argv[2]
names = ["resolutionMatches", "isImx585LowResolutionAlias", "isImx585HighResolutionAlias",
         "ladderTopsJson", "ladderCompressionOf", "applyLadderCompression", "ladderRungOf",
         "ladderRunsIn", "ladderCompressionApplies", "runningLadderRung",
         "ladderRunningText", "ladderSizeOf", "ladderCropOf", "ladderPoolModes", "probedSensorArea"]
lines = open(src).read().split("\n")
chunks = []
for name in names:
    starts = [i for i, l in enumerate(lines)
              if not l.startswith((" ", "\t", "//", "#")) and (" " + name + "(") in l and not l.rstrip().endswith(";")]
    assert len(starts) == 1, (name, starts)
    i = starts[0]
    j = i
    while lines[j] != "}":
        j += 1
    chunks.append("\n".join(lines[i:j + 1]))
open(out, "w").write("\n\n".join(chunks) + "\n")
print("extracted", len(chunks), "functions")
