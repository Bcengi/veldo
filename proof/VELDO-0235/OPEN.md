# VELDO-0235: open items

## A. AC3's project view needs one file outside the footprint

AC3 asks the project view in the UI to name the destination in words. The footprint grants
`engine/ui/src/features/**`, where the view's data lives (`features/projects/projects.ts` now gives every project
`destination` and `destinationWords`, tested in `projects.spec.ts`), but the screen that renders a project is
`engine/ui/src/views/ProjectsView.vue`, which is outside it, so it is NOT edited here. Exact extra path and change,
for the reviewer to confirm as a footprint addition:

`engine/ui/src/views/ProjectsView.vue`, in the selected project's detail panel, after
`<p v-if="selected.purpose">{{ selected.purpose }}</p>`:

```html
              <p class="factory-meta" data-testid="project-destination">Landing: {{ selected.destinationWords }}</p>
```

and in each project card's `factory-meta` span, after the owner:

```html
                      <span>{{ project.destinationWords }}</span>
```

A project record names neither its remote nor its trunk (they are the land configuration's, which the API does not
serve), so the view reads "land and push to its remote" or "land locally on its trunk, nothing pushed"; the owner's
briefs, which the service writes from the land configuration, name both (`Destination: land and push to origin.`).

## B. Notes for the reviewer (no extra path)

- The factory asks the owner one landing question, Line.grant (`land_approval`): it is both the re-land grant of
  VELDO-0148 and, now, the question a destination change asks. Both name the destination.
- A local landing moves `refs/heads/<trunk>` with `git update-ref`; a working tree that has that branch checked out
  is not updated by it (the suite's caller checkout is detached).
- Suite 128 needs no systemd user manager: the coordinator ran its cases confined.
