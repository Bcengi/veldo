# Shell and navigation

`App.vue` shows only the sign-in screen until the session store says signed in; then `AppShell`.

Desktop: a 248 px rail with the wordmark, the factory's name (the session's domain), the destinations
(Overview, Runs, Decisions with a count badge, You), the hosts with a lamp each (live while a run runs
there) and who is signed in. Phone: a bottom bar with the same four destinations; the decisions entry
carries the same count badge. The theme switch lives on the You screen only.

The shell reads the runs and decisions stores once on mount, so the badge and the hosts are live from
the first screen.

## Adding a screen (VELDO-0131, 0159, 0163, 0179)

1. Add the route in `router/index.ts` with `meta: { session: true, title }`.
2. Add a `NavEntry` in `app/navigation.ts`. The bottom bar holds at most four entries marked `phone`;
   further destinations go in the rail and, on a phone, in a list on the You screen.
3. Add the routes the screen calls to `api/routes.json` (the suite checks them against the API).
4. Write its page here.

## Session guard

The router restores the session once (`auth.session`); a route with `meta.session` redirects to
`/sign-in?next=...` without one. After sign-in, `next` is followed only when it is a path of this origin
(`^/(?![/\\])`, `safeNext`), else the overview. A session that ends while a screen is open (sign-out
elsewhere, expiry, revocation, a stream closed as `signed_out`) resets every store and returns to
sign-in with the refusal named.

## You

`/you`, a centered 920 px screen: Signed in (the member, the factory, when the session ends, the passkey
id as a copyable detail) and This device (the theme switch, Sign out with `auth.sign_out`, Sign out on
every device with `auth.sign_out_everywhere`).

Factory setup (VELDO-0159) lists the destinations that are in the rail but not the phone's bottom bar:
"MCP servers and credentials" opens [the server form](servers.md).
Factory setup (VELDO-0163) links to the Roles and Team screens, which the phone's bottom bar has no room for.
