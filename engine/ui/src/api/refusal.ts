/** A refusal the API named, or the API being unreachable. Thrown by the client for every non-2xx answer. */
export class ApiRefusal extends Error {
  readonly status: number
  /** The full name, for example `stale_version:stale_presentation`. */
  readonly refusal: string
  /** The class: unauthenticated, unauthorized, invalid_input, stale_version, missing_evidence,
   * unavailable_service, unknown_outcome, or `unavailable` when no answer came back. */
  readonly error: string
  readonly ownerRequest: unknown

  constructor(status: number, refusal: string, error: string, ownerRequest: unknown = null) {
    super(refusal)
    this.name = 'ApiRefusal'
    this.status = status
    this.refusal = refusal
    this.error = error
    this.ownerRequest = ownerRequest
  }

  /** The part after the class, for example `stale_presentation`. */
  get reason(): string {
    const at = this.refusal.indexOf(':')
    return at < 0 ? this.refusal : this.refusal.slice(at + 1)
  }
}

export function isRefusal(value: unknown): value is ApiRefusal {
  return value instanceof ApiRefusal
}

export interface RefusalText {
  title: string
  fix: string
}

const BY_CLASS: Record<string, RefusalText> = {
  unauthenticated: { title: 'You are signed out', fix: 'Sign in with your passkey to continue.' },
  unauthorized: { title: 'Not allowed for your membership', fix: 'Ask a steward to widen your scope if you need this.' },
  invalid_input: { title: 'The request was not accepted', fix: 'Check the fields and try again.' },
  stale_version: { title: 'This changed since you opened it', fix: 'Reload to see the current version.' },
  missing_evidence: { title: 'Not found', fix: 'It may have been removed or never existed.' },
  unavailable_service: { title: 'The factory did not answer', fix: 'Nothing was changed. Try again in a moment.' },
  unknown_outcome: { title: 'The outcome is unknown', fix: 'Reload to see what the factory recorded before trying again.' },
  unavailable: { title: 'The API cannot be reached', fix: 'Check your connection to the tailnet, then try again.' },
}

const BY_REASON: Record<string, RefusalText> = {
  no_session: { title: 'Sign in to see this', fix: 'Factory data is shown only in a passkey session.' },
  session_expired: { title: 'Your session expired', fix: 'Sign in again with your passkey.' },
  signed_out: { title: 'You signed out', fix: 'Sign in again with your passkey.' },
  revoked: { title: 'Your passkey or membership was revoked', fix: 'Ask a steward if this is unexpected.' },
  credential_not_current: { title: 'This passkey is no longer current', fix: 'Sign in with a current passkey.' },
  credential_revoked: { title: 'This passkey was revoked', fix: 'Sign in with a current passkey.' },
  unknown_credential: {
    title: 'This passkey is not approved yet',
    fix: 'Approve it at the host with veldo factory passkey, then sign in.',
  },
  credential_not_effective: { title: 'This passkey is not active yet', fix: 'Try again once the host has enrolled it.' },
  challenge: { title: 'The sign-in took too long', fix: 'Start again; a challenge lasts two minutes.' },
  registration: { title: 'This registration has ended', fix: 'Start adding the passkey again.' },
  pending_limit: { title: 'Three passkeys are already waiting', fix: 'Approve or let them expire at the host first.' },
  no_project: { title: 'No project of this factory is in your scope', fix: 'Ask a steward to add one to your membership.' },
  out_of_scope: { title: 'Outside your scope', fix: 'Its project is not in your membership. Ask a steward if that is unexpected.' },
  not_owner: { title: 'This decision is not yours to answer', fix: 'Only the member it was presented to can answer it.' },
  stale_presentation: {
    title: 'The question changed after you opened it',
    fix: 'Review the current version, then answer that one.',
  },
  request_closed: { title: 'Already settled', fix: 'It was answered elsewhere, for example in Telegram.' },
  already_answered: { title: 'Already answered', fix: 'Another answer reached the factory first.' },
  already_settled: { title: 'Already settled', fix: 'Another answer reached the factory first.' },
  missing_rationale: { title: 'Add a rationale', fix: 'Say briefly why you chose this answer.' },
  unmatched_choice: { title: 'Pick one of the offered choices', fix: 'Only the choices shown can be sent.' },
  unknown_run: { title: 'No such run', fix: 'It may belong to another factory.' },
  cursor_past_end: { title: 'The record is shorter than expected', fix: 'Reload the run.' },
  ui_not_built: { title: 'The UI is not built on this host', fix: 'Build engine/ui before serving it.' },
  authority: { title: 'The factory did not answer', fix: 'Nothing was changed. Try again in a moment.' },
  // VELDO-0163: the role and team forms' refusals (VELDO-0127, VELDO-0089, VELDO-0151, VELDO-0162).
  agent_configuration: { title: 'The configuration was not accepted', fix: 'Check each item and its load mode, then save again.' },
  agent_owner: { title: 'Only a project owner can save a configuration', fix: 'Ask a steward if you need this.' },
  agent_revision: { title: 'No such configuration revision', fix: 'Open the role again to read its newest revision.' },
  mcp_server: { title: 'No such catalog server', fix: 'Check its id; the catalog form adds servers.' },
  stale_subject: {
    title: 'The team changed since you opened it',
    fix: 'Nothing was saved. Read the team again, then make your change on the current version.',
  },
  default_team: {
    title: 'The default team changed since you opened it',
    fix: 'Nothing was saved. Open the default team again, then make your change on its newest revision.',
  },
  default_team_owner: { title: 'Only the factory project owner keeps the default team', fix: 'Ask the owner to save it.' },
  incomplete_roster: { title: 'The team is incomplete', fix: 'Nothing was saved. Fill in what is missing, then save again.' },
  missing_staffing: {
    title: 'A required role is missing or unstaffed',
    fix: 'Nothing was saved. A team needs project_manager, elaboration, implementation and independent_review, each with workers.',
  },
  missing_capability_configuration: {
    title: 'A role names no capability configuration',
    fix: 'Nothing was saved. Name a configuration and its revision for every role.',
  },
  unresolved_capability_configuration: {
    title: 'A role names a configuration that does not exist',
    fix: 'Nothing was saved. Name a saved configuration revision (the Roles screen saves them).',
  },
}

/** Whether trying the same thing again can succeed: the API or the network did not answer. A named refusal
 * (out of scope, not found, signed out) answers the same way every time, so it gets no Try again. */
export function isRetryable(refusal: Pick<ApiRefusal, 'error'>): boolean {
  return refusal.error === 'unavailable' || refusal.error === 'unavailable_service'
}

/** The sentence and the fix shown for a refusal; the refusal's own name is always shown beside them. */
export function describeRefusal(refusal: Pick<ApiRefusal, 'refusal' | 'error'>): RefusalText {
  const parts = refusal.refusal.split(':')
  for (const part of parts.slice(1).reverse()) {
    const found = BY_REASON[part]
    if (found) return found
  }
  return BY_CLASS[refusal.error] ?? BY_CLASS.unknown_outcome!
}
