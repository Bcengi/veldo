# Dependencies

Veldo's UI uses only public open-source packages from the npm registry, and writes all of its own
code. Nothing is copied or adapted from another company's product.

## Admitting a package

1. Take the version from the registry on the day: `npm view <package> version`, and its license:
   `npm view <package> license` (read the license file when the field says "SEE LICENSE").
2. Check the origin: the publisher and where it is developed. No Chinese-origin UI library.
3. Check the tier: a package whose vendor sells a paid tier of the same library is not admitted
   without a recorded owner decision.
4. Add the package to `dependency-policy.json` with `version`, `license`, `origin`, `tier` and
   `why`. Direct packages are listed by name; transitive packages are covered by the license allow
   list and the origin and tier deny lists, which the dependency-policy suite applies to every entry
   of `package-lock.json`.
5. Install with `npm install --save-exact`, so the lockfile and `package.json` agree exactly.

## The policy check

The VELDO-0145 Python suite reads `package-lock.json` and `dependency-policy.json` and fails when:

- a package in the lockfile has a license outside the allow list,
- a package matches the deny list (Chinese-origin UI libraries, packages with free and paid tiers),
  unless an owner decision names it,
- a direct dependency is missing from the policy or its version differs,
- a served asset in `dist/` was not produced by the build (for example a font or script from
  elsewhere).

## Notes on choices

- **PrimeVue 4, not 5.** PrimeVue 5 moved to PrimeTek's commercial "PrimeUI License" (a free
  community tier and a paid tier) and depends on a license manager package. PrimeVue 4.5.x is MIT.
  The vendor also sells paid add-ons for version 4 (templates, blocks, a designer), which is a free
  and paid tier around the library; the owner named PrimeVue 4 (Telegram 37228) and the decision is
  recorded in the policy file and in the proof's open questions.
- **Unstyled PrimeVue.** The styled mode injects `<style>` elements at run time, which the API's
  security policy forbids. Unstyled mode plus Veldo's pass-through preset avoids that and keeps the
  identity Veldo's own.
- **monaco-editor** is loaded only on the run screen, only when an edit is on screen, and with only
  its base editor worker.
