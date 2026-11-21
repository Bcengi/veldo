# Shell and navigation

`App.vue` shows only the sign-in screen until the session store says signed in; then `AppShell`.

`App.vue` wraps both in Nuxt UI's `UApp` (its tooltip and overlay providers; no toaster).

Desktop (Telegram 38255): a narrow icon rail (52 px, a thin right border) with the Veldo lamp, the
destinations as icons grouped by subtle separators (operate: Overview, Runs, Decisions; the factory; setup),
the appearance switch and the account avatar at the bottom; each icon names its destination for screen
readers and in its tooltip. The panel toggle in every screen's top bar (`ScreenHeader`, state in
`app/rail.ts`, kept across navigation for the page's lifetime, not stored) expands it to the labeled 240 px
sidebar with the wordmark and the factory's name (the session's domain),
the destinations with their icons (Decisions with a count badge, a Nuxt UI `UBadge`), the hosts with a
lamp each (live while a run runs there) and their activity, a "Dark appearance" switch (Nuxt UI
`USwitch`), and the account footer: the member's initials in a `UAvatar` and "Signed in as", opening the
You screen. Phone: a bottom bar with the four phone destinations; the decisions entry carries the same
count badge. The sidebar's switch and the You screen's switch set the one theme preference
(`useTheme`).

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

`/you`, a centered 920 px screen of cards: Signed in (the member's avatar and name, the factory, when
the session ends, the passkey id as a copyable detail) and Appearance and this device (the theme switch,
Sign out with `auth.sign_out`, Sign out on every device with `auth.sign_out_everywhere`).

Factory setup (VELDO-0159) lists the destinations that are in the rail but not the phone's bottom bar:
"MCP servers and credentials" opens [the server form](servers.md).
Factory setup (VELDO-0163) links to the Roles and Team screens, which the phone's bottom bar has no room for.
Factory (VELDO-0131) lists the factory screens the bottom bar has no room for: Projects, Backlog, Workers,
Gate and review, Usage, Configuration, MCP catalog, Repositories and identities, and Workflows; the rail lists them too.
It begins with Conversations (VELDO-0179, [conversations.md](conversations.md)), which the rail lists in its operate group.
