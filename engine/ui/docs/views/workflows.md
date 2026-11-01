# Workflows

Routes `/workflows` (the first workflow) and `/workflows/<workflow>`. Reads `reads.configuration` (the workflow
heads) and `reads.workflow` (the head revision's definition and layout). Acts through `workflows.save` only.

The canvas (`FlowCanvas`, Veldo's own SVG control) shows steps and transitions labeled with their port. Pan by
dragging the background or with the pan buttons; zoom with the buttons or the wheel; drag a step, or focus it
and use the arrow keys, to move it. The palette adds a step of each kind. The ordered list of steps does
everything by keyboard and touch: select a step or a transition, move a step up or down. The property sheet
(`FlowProperties`, beside the canvas on a desktop, a sheet on a phone) holds every setting of the selected
step, always shown: the capability configuration of an assignment, where each port goes, the entry step, and
delete; and a transition's target.

The header shows the version and Saved / Edited, not saved / Saving / Saved as version N. Save sends the
definition and layout edited from the version shown; a save from an older version is refused `stale_version`
beside Save with "Load the current version"; any other refusal is shown there too. Saving stores data and runs
nothing. A workflow outside the member's scope shows the empty state.
