import bpy
import os
exec(open(os.path.join(os.path.dirname(bpy.data.filepath), "scripts", "e42_load.py")).read())
D_ = E42_DIR + "/"
build_walls(); print("SLV clean", selfcheck_walls())
src = open(D_ + "e42_struct.py").read()
i = src.index("def _box_minus"); j = src.index("\ndef ", i + 5)
exec(src[i:j].replace(" - 1e-6:", ":").replace(" or min(i[k + 3] - i[k] for k in range(3)) < 1e-6", ""))   # the old strict compare
try:
    build_walls(); print("SLV MISSED old _box_minus")
except AssertionError as e:
    print("SLV caught old _box_minus |", e)
