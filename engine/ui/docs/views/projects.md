# Projects and objectives

Routes `/projects` and `/projects/<project>`. Reads `reads.objectives` (projects, objectives, the intake's
proposals and questions), live. Acts through `messages.send` only.

Desktop: the searchable project list (name, purpose, state and every objective's outcome), the selected
project's objectives with their state, scope, required evidence, features and assessment, and the message box
beside them. Phone: stacked project cards; a project opens full width with a back link; the Message button
stays on screen and opens the message box as a sheet.

The message box shows the intake's own records of messages (proposals and the questions the intake asked
back). Send posts the text (and the project shown, when one is) to `messages.send`; the answer shown is what
the intake recorded (`outcome`, proposal id). The conversation gains the message only when the re-read brings
the intake's record of it.

States: loading, empty ("No project yet"), error (the read's refusal), ready; the send's own refusal beside
Send.
