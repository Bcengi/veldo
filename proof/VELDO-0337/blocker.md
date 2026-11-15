# VELDO-0337 build blocker

No production implementation was made. All three acceptance criteria and their
falsifiers remain unproven. The specification remains ready pending a footprint
and emitter decision from the owner.

The footprint permits production changes only in control_launch.py and its
synced copy. That receiver cannot observe the recorded review verdict on the
existing synchronous path:

1. Receiver._finish records the dispatch exit and its engine artifact binding.
   That binding describes engine completion, not the signed review verdict.
2. Launch.wait calls _end_receiver, which reaps the receiver, before returning.
3. Runtime._run waits for that result and returns the decoded worker answer.
4. Runtime.review validates the review body and signs the receipt only then.
   Without a supplied assignment it calls FloorAuthority.record_review.
5. With a supplied assignment Runtime.review returns the signed receipt without
   recording it. Dispatcher._review_floor records it afterwards.

The production locations are engine/.veldo/control_launch.py (Launch.wait and
Receiver._finish), engine/.veldo/control_launch_work.py (Runtime._run and
Runtime.review), and engine/.veldo/dispatch.py (_review_floor, _record_review,
and FloorAuthority.record_review). The latter two modules and their synced
copies are outside this ticket's footprint.

The reproduction receiver_order.py drives production Launch.wait and
Runtime.review with explicit stand-ins for the child, floor, signer, and worker
result. Both paths show the receiver reaped before a verdict can be recorded.
The floor stand-in is not a real store, and this is not an acceptance test.
The first exploratory invocation omitted the child stand-in's returncode and
raised AttributeError. The saved reproduction includes that field and passes.

A signal based on the engine's complete artifact would precede review receipt
validation and could fire when the verdict is rejected or never stored. A read
of the floor at receiver exit would find no verdict on the ordinary path.
Waiting there for the verdict would prevent the caller from reaching the write.

Requested owner decision: extend the footprint to the verdict-recording path
and define the post-commit emitter, or keep the footprint and leave the build
blocked. No permission to extend the footprint has been assumed. Any eventual
implementation must use the item-naming ledger signal with versions and the
recorded owner, exclude owner_keep items, and retain the existing rules,
keeper, and removers.

Baseline fast checks passed: python3 .veldo/validate.py all,
bash scripts/check_docs.sh, and bash scripts/check_template_sync.sh (321 pairs).
No acceptance suite, falsifier, heavy suite, or full gate was run. The lead's
verification command remains ./scripts/verify.sh. The known live captures were
not changed. No production code or protected data was changed.
