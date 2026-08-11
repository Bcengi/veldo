# WARP-0711 baseline - where the gate's 117 seconds actually go

Measured 2026-07-25 on Dmitry's workstation (Linux 6.17.0-35-generic, python3.12), in a CLEAN CLONE at
`/tmp/gateprof` made with `git clone --shared` so it could not collide with the WARP-1210 round-7 build
occupying the main tree.

ABSOLUTE SECONDS ARE MACHINE-SPECIFIC. What the acceptance criteria bind to is the ATTRIBUTION: which stage
holds the cost, and what inside that stage holds it. Reproduce with the commands below before trusting any
figure here on different hardware.

## Per-stage wall clock

| stage | command | elapsed |
|---|---|---|
| unit | `python3 scripts/selftest.py` | **102.37s** |
| lint | `bash scripts/check_lint.sh` | **14.07s** |
| shape gate | `python3 .warp/shape_gate.py` | 0.28s |
| contracts | `python3 .warp/validate.py all` | 0.12s |
| docs | `bash scripts/check_docs.sh` | 0.08s |
| pack drift | `python3 scripts/check_pack_drift.py` | 0.05s |
| generated | `bash scripts/check_generated.sh` | 0.04s |
| template sync | `bash scripts/check_template_sync.sh` | 0.00s |
| **total** | | **117.1s** |

TWO STAGES HOLD 116.4 OF 117.1 SECONDS. The other six combined are 0.57s, which is noise. Any speedup that
does not come from the selftest or from lint cannot matter, and any speedup that comes from the other six is
rounding error being reported as an improvement.

Reproduce:
```
for s in "python3 scripts/selftest.py" "python3 .warp/validate.py all" "bash scripts/check_docs.sh" \
         "bash scripts/check_lint.sh" "bash scripts/check_generated.sh" "bash scripts/check_template_sync.sh" \
         "python3 scripts/check_pack_drift.py" "python3 .warp/shape_gate.py"; do
  /usr/bin/time -f "%e  $s" $s >/dev/null 2>>/tmp/stages.txt
done
```

## Inside the selftest: 75 percent of it is time.sleep

`cProfile` over `scripts/selftest.py`, sorted by cumulative time. Total under the profiler was 120.4s against
102.4s unprofiled, so profiler overhead is about 18 percent and the ranking is what to read, not the seconds.

```
264,179,209 function calls in 120.440 seconds

ncalls   tottime  cumtime  filename:lineno(function)
829/671   77.431   77.432  {built-in method time.sleep}
     14    0.000   31.451  runners/process/process_runner.py:291(run)
      5    0.000   24.006  runners/mobile/warp_android_runner.py:223(run)
      5    0.000   22.010  runners/mobile/warp_ios_runner.py:242(run)
     18    0.000   20.965  .warp/dashboard.py:146(render_text)
      6    0.000   17.729  runners/process/process_runner.py:244(assert_kill_tree)
    399    0.001   16.961  {built-in method builtins.all}
     19    0.002   15.750  runners/process/process_runner.py:132(_wait_exit)
10,777,972 2.375   14.068  /usr/lib/python3.12/ast.py:369(walk)
      6    0.000   14.003  runners/mobile/warp_android_runner.py:183(redrive)
      5    0.000   14.002  runners/mobile/warp_ios_runner.py:206(redrive)
```

**time.sleep is 77.4 seconds of EXCLUSIVE time across 829 calls.** tottime, not cumtime, so this is not a
double count: it is the process sitting idle. It is 75 percent of the stage and 66 percent of the whole gate.

Reproduce:
```
python3 -c "
import cProfile, pstats, sys, io
sys.argv=['selftest.py']
pr=cProfile.Profile(); pr.enable()
try: exec(open('scripts/selftest.py').read(), {'__name__':'__main__','__file__':'scripts/selftest.py'})
except SystemExit: pass
pr.disable()
s=io.StringIO(); pstats.Stats(pr, stream=s).sort_stats('cumulative').print_stats(18); print(s.getvalue())"
```

## Why it sleeps: the runners hardcode their waits, and the gate drives them against fakes

The sleeps are NOT in the tests. They are literals in the bodies of the three reference runner modules, and
the selftest drives those runners for real against FAKE drivers that return instantly. So the gate waits two
real seconds for a user interface that does not exist to settle, several hundred times.

Sites, by module (`grep -rn "time.sleep" plugin/templates/scripts/runners/`):

- `mobile/warp_android_runner.py` - **12 sites**: `time.sleep(step.get("settle", 2))` after launch,
  `time.sleep(step.get("settle", 1))` after tap, `time.sleep(0.5)` after text and after key,
  and the redrive sequence at 129, 138, 190, 193, 196, 204, 206 (rotate, force_stop, launch, home, network).
- `mobile/warp_ios_runner.py` - **9 sites**: the same shape at 187, 189, 191, 193, 213, 214, 222, 224, 225.
- `process/process_runner.py` - **4 sites**, all `time.sleep(POLL)` at 128, 139, 159, 171, inside
  `while time.monotonic() < deadline` loops in `_stayed_alive` and `_wait_exit`.

`POLL = 0.05` at `process_runner.py:66`, commented "seconds between liveness polls; the windows are the real
bounds". The windows are real wall clock, so the gate waits them out.

THE PATTERN THE HOUSE ALREADY HAS, and that these three modules were written without:

- `.warp/fleet.py:377` - `def __init__(self, interval=5.0, step=5.0, clock=time.time, sleep=time.sleep)`.
  Both the clock AND the sleep injected, with the real functions as defaults.
- `.warp/tracker_mirror_runner.py:172` - the OAuth token manager, `clock=None` then resolved.

So the fix is not an invention and not a shortcut. It is an existing house seam applied to the only modules in
the tree that sleep for real inside the gate. The constants keep their values; the waiting becomes injectable,
and therefore assertable for the first time.

## The two repeated computations

1. **The dashboard is re-rendered once per line.** `scripts/selftest.py:16977`:
   ```
   and all(_l in DB10.render_text(_M10_EVENTS) for _l in
           RPT10.support_lines(DB10.support_figures(_M10_EVENTS)))
   ```
   `render_text` is inside the generator expression, so it runs once per line of its own output. The profile
   shows 18 calls at about 1.2s each, 21.0s cumulative. This is a defect in the assertion, not a design cost.

2. **The syntax trees are walked 10.7 million times.** `ast.walk` cumulative 14.1s, driven by assertions that
   re-parse and re-walk the same module trees inside `all(...)` generator expressions
   (`scripts/selftest.py:13061, 13211, 14001, 15450, 15453, 16993`). The `builtins.all` line at 17.0s
   cumulative over 399 calls is the same story from the other side.

## Lint: 661 interpreter startups to syntax-check 662 files

`scripts/check_lint.sh` runs `python3 -m py_compile "$f"` in a loop, one process per file, serially, then
`bash -n` per shell file. The tracked file counts are **662 Python** and **172 shell**. Interpreter startup IS
the stage's cost.

Measured, same file sets, one process:

| | current | batched | 
|---|---|---|
| Python (662 files) | ~13.9s | **0.70s** |
| shell (172 files) | ~0.2s | **0.11s** |
| stage total | **14.07s** | **0.82s** |

That is 17x on the stage, from deleting 661 process spawns. Semantics preserved: same file set from the same
`git ls-files` patterns, every failure still named by path, non-zero exit on any failure, no bytecode written.

Reproduce:
```
time python3 -c "
import subprocess
files=subprocess.run(['git','ls-files','*.py'],capture_output=True,text=True).stdout.split()
fail=0
for f in files:
    try: compile(open(f,'rb').read(), f, 'exec')
    except SyntaxError as e: print('   FAIL:',f,e); fail=1
print(len(files),'files', 'pass' if not fail else 'FAIL')"
```

## What the target arithmetic is, stated so it can be checked rather than believed

| | now | after | mechanism |
|---|---|---|---|
| selftest | 102.4s | ~12s | injected waiter removes 77.4s; hoisted render and indexed trees remove most of the rest |
| lint | 14.1s | 0.8s | one interpreter instead of 662 (MEASURED, not projected) |
| other six | 0.6s | 0.6s | untouched |
| **total** | **117.1s** | **~13.5s** | **about 8.7x** |

Honest statement of the gap: this is about 8.7x, not exactly 10x. The remaining distance is inside the
selftest's residual compute, and this artifact does not claim a mechanism for it that has been measured.
The AC7 bar is therefore "under 15 seconds", and if the real result lands above it, the real number is what
the manifest states.

## What this baseline does NOT establish

- That no OTHER machine has a different bottleneck. The attribution (two stages, sleep dominant inside one)
  is structural and will hold; the seconds will not.
- That the selftest's residual ~25s of real compute has no further large win in it. It was not profiled below
  the top 18 frames.
- Anything about a subset runner. Every figure here is for the FULL suite, which is the only thing that
  currently exists to run, and that limitation is the separate complaint raised with Dmitry.
