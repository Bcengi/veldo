# Contributing

This project is built with the method it describes, which changes what a contribution looks like.
The short version: **the specification comes first, and the gate decides.**

## The loop

1. **Specification.** Open one before writing code. It declares what is being built, its risk class,
   its acceptance criteria, and its footprint. `engine/specs/TEMPLATE.md` is the shape, and `veldo init` lays it into your repository as
   `specs/TEMPLATE.md`. One concern per specification.
2. **Build.** Write the change and the tests that evidence each acceptance criterion, in the same
   change.
3. **Proof.** A proof bundle maps every criterion to the evidence that settles it, and records the
   checks that ran with their real results.
4. **Independent review.** A reviewer who did not build it reads the specification, the final diff
   and the proof, and returns a verdict. Not your reasoning narrative, the artifacts.
5. **The gate.** `bash scripts/verify.sh` must be green, run from the repository the method is
   installed in (the gate ships in `engine/` and in every pack, and `veldo init` lays it into
   yours). Green is the right to merge.

You do not need to run the full loop to report a bug or fix a typo. You do need to for anything that
changes behaviour.

## Two rules that are not negotiable

**A finding becomes a check, in the same change that answers it.** If review catches something, the
fix includes the mechanism that catches it again forever. Fixing the instance and moving on is how
the same defect arrives three more times.

**Never soften a claim to make it true.** If the documentation says something the code does not do,
either ship the capability or delete the sentence. Rewording it into something vaguer is the one
resolution this project does not accept.

## What gets a change rejected quickly

- A check that cannot fail. If you add an assertion, make it fail on purpose once and say so. An
  assertion that passes because it looked at nothing is worse than none, because it reports safety.
- A green gate reached by narrowing the gate.
- Em dashes and en dashes. Use the ASCII hyphen. The docs sweep enforces this and it is not personal.
- A pack that ships its own edited copy of an engine file. There is one base and packs extend it;
  a differing copy is a silent fork and the gate names it.

## Three failures per round is a decision, not a fourth attempt

If a change fails review three times, the next step is not another attempt at the code. It is a
decision about the change: split it, narrow it, or take the design question to a person. This is in
the method because thirteen rounds happened once.

## Licence

Contributions are accepted under the Apache License 2.0, the same terms as the project. By opening a
pull request you confirm you have the right to contribute the work under those terms.
