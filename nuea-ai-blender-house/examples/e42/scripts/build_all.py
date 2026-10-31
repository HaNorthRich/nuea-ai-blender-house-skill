# Build the E42 house from an empty Blender, stage by stage in construction order, each stage checked as it lands:
#     blender -b --factory-startup --python-exit-code 1 -P build_all.py
# The .blend goes next to this folder (or to $E42_OUT). The skill's scripts come from $SKILL_SCRIPTS, else the skill
# folder this example sits in (examples/e42/scripts → ../../../scripts), else ~/.claude/skills/nuea-ai-blender-house/scripts.
import os
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
E42_DIR = HERE
_up = os.path.normpath(os.path.join(HERE, "..", "..", "..", "scripts"))
SKILL_SCRIPTS = os.environ.get("SKILL_SCRIPTS") or (_up if os.path.exists(os.path.join(_up, "helpers.py")) else None)
exec(open(os.path.join(HERE, "e42_load.py")).read())

BUILD_STAGES = (   # (not STAGES: e42_struct has one, and every module shares this namespace)
    ("ST00–ST05 grid, footings, stubs, ground beams, columns, slab",
     lambda: (build_grid(), build_footings(), build_stubs(), build_ground_beams(), build_columns(), build_ground_slab()),
     lambda: selfcheck()),
    ("ST06 walls, plaster, beads, wall plate", build_walls, selfcheck_walls),
    ("ST07 roof frame, fascia, CPAC covering and caps",
     lambda: (build_roof(), build_fascia_frame(), build_cpac_trims(), build_fascia("cpac")),
     lambda: (selfcheck_roof(), selfcheck_trims(), selfcheck_fascia("cpac"))),
    ("ST08 ceilings", build_ceilings, selfcheck_ceilings),
    ("ST09 primer", build_primer, selfcheck_primer),
    ("ST10 paint coat 1", build_finish, selfcheck_finish),
    ("ST11 steps, waterproofing, tiles, skirting", lambda: (build_steps(), build_tiles()), selfcheck_tiles),
    ("ST12 electrical and conduit", build_elec, selfcheck_elec),
    ("ST13 paint coat 2", build_coat2, selfcheck_coat2),
    ("ST14 doors, windows, aluminium", build_units, selfcheck_units),
)
t0 = time.time()
for name, build, check in BUILD_STAGES:
    build()
    print(f"[{time.time() - t0:5.0f} s] {name}: {check()}")
out = os.environ.get("E42_OUT") or os.path.join(HERE, "..", "e42_house.blend")
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out))
print("BUILD DONE", os.path.abspath(out))
