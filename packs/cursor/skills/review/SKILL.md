---
description: Run the fresh-context independent Veldo review and emit the verdict.
---

Review the change for: $ARGUMENTS

Invoke the veldo-reviewer subagent with ONLY: the specification, the final
diff, the proof manifest, and the repository instructions. Never the
implementation conversation. The reviewer emits a veldo.verdict/v1 verdict;
save it as proof/<spec-id>/verdict.json and validate it
(python3 .veldo/validate.py verdict <file>).

Bind the verdict to the proof it reviewed: set proof_digest to `python3 -c "import json,sys; sys.path.insert(0,'.veldo'); import validate; print(validate.proof_digest(json.load(open('proof/<spec>/manifest.json'))))"` so the verdict cannot be reused for a different proof. A fail returns the change to implementation. After two failed cycles on the
same specification, stop and bring in the human: at that point the defect is
almost always in the specification.

Surface prior lessons. Before reviewing, work out the change's context from the
diff: its touched paths, its plan id, and any spec tags. Run
`python3 .veldo/lessons.py relevant --path <p> [--path <p> ...] [--plan <id>] [--tag <t>]`
and include its output in what the reviewer must check, so a failure mode that
broke once is re-checked on any change that touches the same scope. On a
failing verdict, record the finding as a new lesson with
`python3 .veldo/lessons.py add --category review_finding --path <glob> --text "<what to check next time>" --source <spec-id>`
(use --tag <plan-or-spec-id> instead of --path for a lesson scoped to a plan),
so the store learns from every caught regression. The store and relevant() are
mechanical; deciding the context and writing the lesson text are your judgment.
