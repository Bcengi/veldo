# Repositories and identities

Route `/repositories`. Reads `repositories.read`, live: the repository records (VELDO-0161, VELDO-0143) and the
Git identities (VELDO-0142), a metadata-only read.

Read-only. Git identities: label and id, author (name and email), remote host and owner, projects root, default
visibility and how many repositories are bound to it. Repositories: name, identity, path, remote, origin
(created or adopted) and state (provisioning, active or failed), a failed one with its named reason and the step
it failed at. Tables on a desktop, cards with the same fields on a phone.

An identity's credential references (its API token and push credential) are never served: the API serves an
identity's metadata fields only. A member whose scope is not universal sees the repositories of its projects and
only the identities those repositories are bound to.
