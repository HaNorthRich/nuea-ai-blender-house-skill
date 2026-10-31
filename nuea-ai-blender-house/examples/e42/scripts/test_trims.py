import bpy, copy
import os
exec(open(os.path.join(os.path.dirname(bpy.data.filepath), "scripts", "e42_load.py")).read())
def full():
    build_roof(); build_fascia_frame(); build_cpac_trims(); build_fascia('cpac'); build_metal_test(); build_metal_trims(); build_fascia('metal')
full()
print(selfcheck_roof()); print(selfcheck_trims()); print(selfcheck_metal()); print(selfcheck_fascia('cpac')); print(selfcheck_fascia('metal'))
def expect(name, fn, check):
    try:
        fn(); check()
        print("MISSED", name)
    except AssertionError as e:
        print("caught", name, "|", str(e)[:90])
def move(n, dz):
    def f():
        o = bpy.data.objects[n]; o.location.z += dz; bpy.context.view_layer.update()
    return f
def undo(n, dz):
    o = bpy.data.objects[n]; o.location.z -= dz; bpy.context.view_layer.update()
def param(d, k, v, rebuild):
    """Build with the wrong value, then put the spec back BEFORE the check (the check must judge against the spec)."""
    old = d[k]
    def f():
        d[k] = v; rebuild(); d[k] = old
    return f, rebuild
# placement mutations (no rebuild)
for n, dz, chk in (("RC_Hip2_05", 0.005, selfcheck_trims), ("RC_Ridge_A_01", -0.005, selfcheck_trims),
                   ("RD_Rail_Hip3", -0.005, selfcheck_trims)):
    expect(f"{n} moved {dz * 1000:+.0f} mm", move(n, dz), chk); undo(n, dz)
# deletions
def dele(n):
    def f():
        o = bpy.data.objects[n]; bpy.data.objects.remove(o)
    return f
expect("hip cap missing", dele("RC_Hip1_04"), selfcheck_trims); build_cpac_trims()
expect("hip end missing", dele("RC_Hip3_00_end"), selfcheck_trims); build_cpac_trims()
expect("three-way missing", dele("RC_ThreeWay_0"), selfcheck_trims); build_cpac_trims()
# parameter mutations (rebuild)
for d, k, v, rb, chk in ((DRY, "step", 1.5, build_cpac_trims, selfcheck_trims),
                         (DRY, "inside", 0.0, build_cpac_trims, selfcheck_trims),
                         (MS, "hip_batten", 0.15, lambda: (build_metal_test(), build_metal_trims()), selfcheck_metal),
                         (MS, "hip_gap", 0.0, lambda: (build_metal_test(), build_metal_trims()), selfcheck_metal),
                         (FLASH, "nose", 0.0, build_metal_trims, selfcheck_metal),
                         (MS, "ridge_gap", 0.30, lambda: (build_metal_test(), build_metal_trims()), selfcheck_metal)):
    f, back = param(d, k, v, rb)
    expect(f"{k}={v}", f, chk); back()
# battens: top pair gap
f, back = param(BATTEN, "ridge_gap", 0.20, lambda: (build_roof(), build_cpac_trims()))
expect("batten ridge_gap=0.20", f, selfcheck_roof); back()
# joints: a member not cut to what it runs into, a weld missing
import builtins
real = _cope
def nocope(o, d, cutters, keep):
    return [], []
def f():
    global _cope
    _cope = nocope; build_roof(); _cope = real
expect("frame member not cut", f, selfcheck_roof); build_roof(); build_cpac_trims()
expect("weld missing", dele("WD_Rafter_2_03"), selfcheck_roof); build_roof(); build_cpac_trims()
def g():
    global _cope
    _cope = nocope; build_metal_test(); build_metal_trims(); _cope = real
expect("purlin not cut", g, selfcheck_metal); build_metal_test(); build_metal_trims()
expect("purlin weld missing", dele(next(o.name for o in bpy.data.collections[C_MS].objects if o.name.startswith("WD_Purlin"))), selfcheck_metal)
build_metal_test(); build_metal_trims()
# fascia
full()
expect("bird stop dropped 1 cm", move("FA_BIRD_1", -0.01), lambda: selfcheck_fascia("cpac")); full()
for d, k, v, chk in ((FASCIA, "tile_over", 0.0, lambda: selfcheck_fascia("cpac")),
                     (FASCIA, "sheet_over", 0.30, lambda: selfcheck_fascia("metal"))):
    f, back = param(d, k, v, full)
    expect(f"fascia {k}={v}", f, chk); back()
expect("fascia angles missing", dele("RF_FasciaAngles"), lambda: selfcheck_fascia("cpac")); full()
expect("fascia board moved 5 mm", move("FA_B8_2", 0.005), lambda: selfcheck_fascia("cpac")); full()
print(selfcheck_roof()); print(selfcheck_trims()); print(selfcheck_metal()); print(selfcheck_fascia('cpac')); print(selfcheck_fascia('metal'))
print("TESTS DONE")
