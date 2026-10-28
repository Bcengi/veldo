# Shared components

Shared components live in `src/components/`; components of one area live in `src/features/<area>/`
and are listed here too when another area may reuse them (the run terminal is reused by the
conversation screens of VELDO-0179). Each has its own page; read it before using or changing the
component, and update it in the same commit.

| Component | File | Page |
|---|---|---|

## Composables

| Composable | File | Page |
|---|---|---|

## Rule

Check this list before writing a new component: extend an existing one with a prop when the job is
the same. A new shared component gets a page here with its props, emits, slots, states, accessibility
notes, an example, and when not to use it.
