# Working economy: full detail without the token bill (Workflow B)

Read before starting a construction model, and again whenever a stage passes ~30 headless runs.

## What the bill was made of (SS-02, 95 m², ST00–ST18 + conduit, one session over 4 days)

Measured from the session transcript (4 พ.ย. 69):

| Item | Amount | What it means |
|---|---|---|
| Model turns | 3,139 | each turn re-reads the whole context |
| Cache reads | 1.74 B tokens (≈ 555 k per turn) | the context sat near its limit for most turns: this is most of the bill |
| Output (incl. thinking) | 11.6 M tokens | much of it was geometry worked out in prose (bend room, clearances) |
| Headless Blender runs | 309 | most fixed one failing assert per run |
| Read results | 26.6 M chars | whole drawing sheets read as images, more than once |
| `look` images | 6.7 M chars | renders used as checks |

The detail was not the cost. Four habits were:

1. **One endless session.** Every turn paid for every earlier stage's logs, probes and images.
2. **Thinking in prose about numbers** the code could compute: S-bend angles, fillet room, which lane is free.
3. **One error per run.** Python stops at the first assert; each fix cost a full run plus the turns around it.
4. **A late change of assumption.** The 1/2" conduit was 16 mm until Thai Watsadu said 20 mm. Every route and test coordinate was redone.

## The rules (keep every one; none of them lowers the detail)

1. **One stage per session.** Close the stage with its checks and suite green, write the handoff into the stage spec, then `/clear`.
   - The stage spec holds what the next stage needs: the result, the numbers, the decisions, the open questions.
   - The next session reads the project's ST00 spec and the stage spec it touches. It does not reread every earlier spec or script.
2. **Read each drawing sheet once into `FACTS.md`** (levels, faces, grid, schedules, as tables), cropped to the part you need.
   Later stages read `FACTS.md`, not the PDF. Measure the model with `scripts/probe.py` (a compact table to a file), not with
   ad-hoc scripts whose output floods the context.
3. **Buy before you route.** Get the real product sizes (store pages, with links) before any table that depends on them:
   conduit OD, box size, pipe OD, sheet sizes. Ask the owner's decisions in one batch at the start of the stage.
4. **Let code do the arithmetic.** Use the formulas below, `scripts/probe.py` and the checker's numbers. Don't reason them out in text.
5. **Collect every failure in one run.** Wrap each per-item loop of a check in `checks.each(...)` (`scripts/checks.py`).
   One run then lists every failing piece with its tag. Fix them all, then run again.
6. **Iterate on a base file.** Build the earlier stages once (`build_all.py` with an output path). Each iteration runs only
   the stage being worked on (~30 s), with output filtered to the `CHECK`, `Error` and `line N` lines.
7. **During iteration, run only the mutations for the rules you touched.** Run the whole suite once when the stage closes.
   Run it in the background and wait for the notification.
8. **Images only at the end of a stage:** one or two Workbench renders at ≤ 1000 px, a crop where the question is. Numbers check the model.
9. **Stop rule.** If the same assert fails three runs running, stop patching. Write down what the geometry allows (probe it),
   change the design (move the device, add a box, take another wall), or ask the owner. Say why in the spec.

## Formulas that saved the most thinking

- **Fillet room:** a corner turning θ with radius r needs `r·tan(θ/2)` of straight on each side. Two corners on one segment need the sum.
- **S-bend** (offset h at radius r, two equal bends with no straight between): `θ = acos(1 − h / 2r)`. Corner points sit `h / tan θ` apart along
  the run. Use a slightly smaller θ (≈ 2°) so the fillet code has a few mm to spare.
- **90° sweep through a wall** from a chase at depth c behind the face: it comes out of the far face only if `r < wall + c`.
  A box on the far face can't take the sweep square; leave the bend in the void.
- **Lanes:** two conduits of diameter d stacked on one wall line need ≥ d + gap between centres. A riser can leave the wall line only
  where no lower lane is occupied.
- **Rafters on a slope:** bottom `z0 + (x − x0)·slope`. Find the web band at each box before choosing its height.

## A session's shape for one stage

1. Read: `FACTS.md`, the stage's `references/stage-*.md`, the spec of the previous stage (its handoff only).
2. Decide the batch of questions, ask them once, write the answers into the spec.
3. Write the stage's tables and builder. Build once on the base file. Run the check in collect mode.
4. Fix all failures in one edit, then run again. Add one mutation per new rule.
5. Close: full suite, quantities into the spec, one render, handoff note, and the skill's lessons for the stage. Then `/clear`.
