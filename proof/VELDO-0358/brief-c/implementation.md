# Brief C implementation notes

The mutation driver uses pidfds for exits and inotify for appended output.
poll accepts high descriptor numbers; its fixture waits on descriptor 2048.
Worker lifecycle sockets remain in the wait set so ownership acknowledgements
cannot deadlock behind a child waiting for its own acknowledgement. Complete
output lines rearm each worker independently. Shared controls and case admission
keep their measurements, now reported as estimates. No stage alarm is installed.
The legacy constructor deadline argument is inert for caller compatibility.

A worker that exhausts its progress bound receives SIGABRT with Python's
faulthandler enabled, which writes all thread stacks before termination.
The blocking-child fixture emits readiness from descriptor conversion inside
os.read. Any stack sampled after that event contains the blocking call's source
line, even if the child is descheduled immediately. Its clock advances only
after that event, and core files are disabled.
Ownership cleanup and reservation release still follow reaping. Metered worker
cgroups are killed and awaited through cgroup.events. Normal completion never
uses a measured duration as a verdict.

First-use runs stream child output under the same progress rule. Its Python
launcher exposes real shared.expect entry and return events on stderr, so a
long nested leg cannot look silent merely because passing rows normally do not
print. The parent forwards complete lines to its own parent. Measurements are
not read as budgets, and there is no ceiling.

The mutation observer records opened paths and terminal waits. Copied mutant
inputs map back to their original repository-relative paths. A missing first
census is conservatively unproven. The six-case verdict row supplies baseline
files; the integrated gate will read Brief B's authority baseline. New receipt
fields are kills (row and kill_by) and the case's kill_by classification.

The timers table starts empty. register(name, value, module, kind) declares a
contract timer or deadline; use qualified names such as
control_launch.ACCEPT_SECONDS. effective(name) reads the current value.
set_profile(except_name=None) selects the wait hang bound for all other entries,
including entries registered later. report() returns name, effective value,
module and kind; reset_profile() restores production values. Wave 1 owners add
their own entries and read them at the point where each timer is armed.

The canonical gate is excluded by the task instruction. Partial selftest runs
are developer verification and do not establish a gate or landing verdict.

The full mutation stage on implementation HEAD 30d6fa2a passed with 3,608 cases
registered, executed and rejected, zero reused, zero invalid results and zero
surviving workers. It ran all 1,200 controls and 3,608 mutants through the external
host-heavy wrapper. Elapsed time was 8,551.707 seconds, recorded only as data.
full-stage.txt binds the raw receipt by SHA256 and lists every case and killed
row: 3,608 cases and 3,969 rows are unproven because this branch has no authority
baseline yet. That list is the wave 2 input; the supplied-baseline fixture
separately proves assertion and terminal classifications.

current-tree-mutants.txt records all 35 Brief C registrations rejected on the
same tree with both controls clean. All 3,608 inventory definitions also passed
the exact-anchor check. Final lint, template sync and personal setup checks
passed; personal setup found zero findings. The final commit adds proof only.
