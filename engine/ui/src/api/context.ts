/** What every request needs from the session, held in memory only (never storage, the URL or the DOM). */
export const apiContext: {
  token: string | null
  domain: string | null
  onUnauthenticated: ((refusal: import('./refusal').ApiRefusal) => void) | null
} = { token: null, domain: null, onUnauthenticated: null }
