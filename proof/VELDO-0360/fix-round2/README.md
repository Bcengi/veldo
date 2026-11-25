# Fix round 2

Review N1: finishing one node used the teardown reaper, which killed adopted descendants of other running nodes and could turn a normal gate red.

Node completion now takes one snapshot of child PIDs, excludes inherited children and active node roots, and calls waitpid with WNOHANG. It never signals a live process or waits for its exit. A child already reaped elsewhere is harmless. Node and mutation worker cgroups still drain before collection and grant release. The final CLI teardown keeps its kill-then-wait drain, including cancellation and exception exits. Both scheduler copies match.

Eight native controls passed in a private delegated service capped at 256 MiB. The new two-node control forks a separate-session helper through an intermediate parent, waits for that parent to exit, and verifies that the scheduler adopted the helper. The first node cannot finish before that adoption. After its completion and grant release, the second node exchanges a socket request and reply with the helper, observes its exit through a pidfd, releases its child claim and passes. Both nodes pass. The control uses socket, filesystem and process exit events, with no sleeps or new clocks.

The round 1 active mutation controls remain green: cancellation, external coordinator death and a sampling exception each drain two workers and two separate-session descendants, remove every nested worker and node cgroup, and reap all five PIDs before releasing grants. Cancellation retains the first exit-7 failure and the partial mutation receipt. No rescue was needed.

The mutation driver checks all 43 registered VELDO-0360 cases with green no-ops and rejection at every declared row. Six new cases cover restoring the destructive completion call, child discovery, child exclusions, nonblocking waits, zombie collection and child-exit races. The destructive completion mutant is rejected at sibling-survives. A syscall-boundary control rejects blocking flags before starting the live handshake, so that falsifier cannot deadlock the control. Original and mutant digests and exact diffs are recorded alongside the named rows.

Targeted scheduler diagnostics: suite 114 has 27 passing rows, suite 157 has 50, and suite 161 has 65. Selector exit 2 denotes a partial run, not a gate verdict. Lint and template synchronization passed. Census: 2843 sites, no additions. Personal setup: 0. Stale mutation anchors: 0 of 4016. The unconfined declaration, verification shell and wall-clock baseline are unchanged. No live-capture-bound module changed.

No canonical gate, full leg, load generator or sub-agent ran. Full-gate validation, independent review and owner approval at landing remain pending. The binding records implementation commit, tree and SHA-256 digests; this is targeted evidence only.
