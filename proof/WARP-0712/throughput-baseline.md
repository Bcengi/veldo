# WARP-0712 throughput baseline - what delivery actually costs, measured from git

Derived 2026-07-25 from the repository's own history at commit 520badd, NOT from recollection. This artifact
exists because the ETA this item is justified by was previously given from memory and was wrong by a factor of
two and a half: 3 hours per item quoted against a real mean of 1.19.

Every figure below carries the command that produced it. Read the LIMITATIONS section before quoting any of
them, because two of these numbers are proxies rather than measurements and the difference matters.

## The headline figures

| measure | value |
|---|---|
| distinct item ids appearing in commit subjects | 145 |
| total commits | 337 |
| project wall clock, first commit to last | 234.6h (9.8 days) |
| sum of per-item first-to-last-commit spans | 173.0h |
| MEAN span per item | **1.19h** |
| top 6 items by span | 86.9h, being 50 percent of the span total for 4 percent of the items |

Reproduce the mean:
```
git log --pretty=format:"%at|%s" --reverse | awk -F'|' '{
  match($2,/WARP-[0-9]+|PLAN-[0-9]+/); id=(RSTART>0)?substr($2,RSTART,RLENGTH):"x";
  if(id!="x"){if(!(f[id]))f[id]=$1; l[id]=$1; n[id]++}
} END{for(i in f){t+=(l[i]-f[i])/3600; c++} printf "%d items, %.1fh, mean %.2fh\n", c, t, t/c}'
```

## The rework distribution, and the disambiguation that changes its meaning

Commits per item, counting the PRIMARY id of each subject (the first id it names, so a work item's commits are
attributed to the work item and not to the plan it mentions):

| commits | items |
|---|---|
| 1 | 21 |
| 2 | **108** |
| 3 | 10 |
| 4 | 1 |
| 5 | 1 |
| 6 | 3 |
| 20 | 1 (WARP-1210) |

Sums to 145. **139 of 145 items, 96 percent, completed in ONE TO THREE COMMITS.** The maximum anywhere else is
SIX (WARP-1208, WARP-0614, PLAN-0011), and THERE IS NOTHING BETWEEN 6 AND 20. WARP-1210 is a lone outlier
separated from the next-highest item by a factor of 3.3.

Reproduce:
```
git log --pretty=format:"%s" | awk '{match($0,/WARP-[0-9]+|PLAN-[0-9]+/);
  if(RSTART>0) print substr($0,RSTART,RLENGTH)}' | sort | uniq -c | awk '{print $1}' | sort -n | uniq -c
```

A NOTE ON HOW THIS TABLE WAS GOT WRONG FIRST, because the method says to record that: an earlier pass counted
with `grep -oE`, which counts every MENTION of an id, and produced a spurious tail of eleven items at 12 to 36
commits, ten of them plan ids. The counts were mentions of a plan inside its work items' subjects.

The discarded mention-count ranking, kept so the error stays legible rather than erased:

```
  36 mentions  PLAN-0003       17 mentions  PLAN-0008
  27 mentions  PLAN-0011       15 mentions  PLAN-0007
  22 mentions  PLAN-0012       15 mentions  PLAN-0006
  20 mentions  WARP-1210       14 mentions  PLAN-0009
  17 mentions  PLAN-0010       13 mentions  PLAN-0004
                               12 mentions  PLAN-0005
```

WHY A MENTION-COUNT MISLEADS, verified on PLAN-0004, which appears in 13 subjects but is the PRIMARY id of only
3:

```
7e8a72c PLAN-0004 revision 4: descope control-plane track      <- primary
3a7390d PLAN-0004 rev3: resolve D1 + D2                        <- primary
a52cd5b PLAN-0003 + PLAN-0004 created                          <- primary
06ee38f WARP-0405: cost and token budget governance (X5 of PLAN-0004)   <- a WORK ITEM's commit
4421947 WARP-0401: The Executor v1 (X1 of PLAN-0004)                    <- a WORK ITEM's commit
...and seven more of the same shape
```

So a mention-count attributes a work item's commits to its plan. Counting the PRIMARY id per subject instead
(`awk match()`, first id only) gives PLAN-0004 three commits, not thirteen. THE CORRECT STATEMENT IS THEREFORE
NARROWER THAN THE TABLE SUGGESTS: commit count is a usable rework proxy for a WARP item, and a mention-count is
not a rework proxy for anything.

Among WARP items the maximum is SIX commits (WARP-1208, WARP-0614), with one exception:

**WARP-1210 at 20 commits is the sole genuine rework outlier in the project.** Eight build rounds, seven
independent reviews failed, six of them on measurably false sentences rather than on design.

The consequence for planning is the opposite of alarming: REWORK IS NOT SYSTEMIC. One item went pathological
and the other 144 behaved. So the 1.19h mean is representative rather than an average across a bimodal mess,
and 45 remaining items is about 53 HOURS SERIAL.

## Top 6 by span, split into recoverable and not

| item | commits | span | reading |
|---|---|---|---|
| WARP-1210 | 20 | 19.8h | REAL REWORK - eight rounds, seven failed reviews |
| PLAN-0004 | 2 | 19.1h | TWO commits, so the span is almost entirely idle, not work |
| PLAN-0011 | 6 | 13.5h | a plan revised across its work items, plus idle |
| PLAN-0012 | 2 | 13.2h | TWO commits, so the span is almost entirely idle, not work |
| WARP-0623 | 4 | 11.1h | modest rework plus a live-proof run |
| WARP-1212 | 2 | 10.2h | TWO commits, so the span is almost entirely idle, not work |

Commit counts are primary-id counts. Three of the six have exactly TWO commits, which is the signature of an
idle span rather than of effort.

Only WARP-1210, and to a small degree WARP-0623, represent time a better method would have saved. Counting all
86.9h as recoverable waste would overstate the opportunity, and this artifact does not.

## LIMITATIONS, stated because two figures above are proxies

1. **A SPAN IS NOT ACTIVE EFFORT.** It is first commit to last commit for an id, so it includes every idle gap,
   including overnight ones. WARP-1212's 10.2h across two commits is almost entirely idle. Treat spans as a
   planning proxy, never as a measure of work done.
2. **SPANS CAN OVERLAP**, so the 173.0h sum is not a wall-clock total. It is 74 percent of the 234.6h project
   span, which bounds the overlap as modest but real and is consistent with work having been largely
   SERIALIZED - which is precisely the condition this item exists to remove.
3. **THE 234.6h WALL CLOCK SPANS 9.8 DAYS**, so the project has been running far more than a working day per
   day. Any human-day conversion of the 53h estimate must say which it means.
4. **145 ids is not 145 delivered specs.** It counts every id appearing in a commit subject, including plans and
   including items whose commits were spec-only.
5. Nothing here measures token cost, which the parallel-lane plan multiplies by roughly the lane count and
   which is the binding constraint the owner has already hit twice today.

## What this justifies, and what it does not

JUSTIFIED: the claim that the average item is healthy and the programme is limited by SERIALIZATION rather than
by per-item speed. 45 items at a 1.19h mean is about 53h serial; over four lanes that is roughly 13h of wall
clock, so a 3 to 4 day completion is reachable WITHOUT anyone working faster and WITHOUT skipping a review.

NOT JUSTIFIED by anything measured here: that four lanes will actually achieve four times the throughput. Lane
efficiency is unproven, the landing step is serialized by design (the serialized lander exists for a reason),
and the token ceiling is a real limit this artifact does not model. The claim this item makes is that
decomposing the suite REMOVES THE FILE-LEVEL BLOCKER to parallelism, which is a structural claim about
conflicts and is demonstrated by AC7 over two real queued items. It is not a claim about a speedup multiple.
