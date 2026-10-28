# Shell and navigation

`App.vue` shows only the sign-in screen until the session store says signed in; then `AppShell`:
a 232 px rail on desktop (wordmark, navigation, theme, who is signed in) and on phone a bottom bar
with the same destinations. The decisions entry carries an amber lamp and count while decisions wait.

## Adding a screen (VELDO-0131, 0159, 0163, 0179)

1. Add the route in `router/index.ts` with `meta: { session: true, title }`.
2. Add a `NavEntry` in `app/navigation.ts`. The bottom bar holds at most four entries marked `phone`;
   further destinations go in the rail and, on phone, in a list on the You screen.
3. Add the routes the screen calls to `api/routes.json` (the suite checks them against the API).
4. Write its page here.

## Session guard

The router restores the session once (`auth.session`); a route with `meta.session` redirects to
`/sign-in?next=...` without one. A session that ends while a screen is open (sign-out elsewhere,
expiry, revocation, a stream closed as `signed_out`) resets every store and returns to sign-in with
the refusal named.

## You

`/you`: the member, the passkey id, when the session ends, the theme switch, Sign out (`auth.sign_out`)
and Sign out on every device (`auth.sign_out_everywhere`).
