import { request } from './client'
import type { SessionView } from './types'

export interface Challenge {
  challenge: string
  rp_id: string
  timeout_ms: number
  user_verification: string
}

export interface RegistrationBegun {
  registration_id: string
  challenge: string
  user_handle: string
  rp_id: string
  algorithms: number[]
  user_verification: string
  resident_key: string
  attestation: string
}

export interface PendingRegistration {
  pending_id: string
  outcome: 'pending_steward_enrollment'
  label?: string
  fingerprint?: string
  expires_at?: number
  [field: string]: unknown
}

export interface Assertion {
  credential_id: string
  client_data_json: string
  authenticator_data: string
  signature: string
  user_handle: string
}

export const readSession = () => request<SessionView>('auth.session')
export const challenge = () => request<Challenge>('auth.challenge', { body: {} })
export const signIn = (assertion: Assertion) =>
  request<SessionView>('auth.sign_in', { body: { ...assertion } })
export const signOut = () => request<{ outcome: string }>('auth.sign_out', { body: {} })
export const signOutEverywhere = () =>
  request<{ outcome: string; sessions_ended: number }>('auth.sign_out_everywhere', { body: {} })
export const beginRegistration = (label: string) =>
  request<RegistrationBegun>('auth.registration_begin', { body: { label } })
export const offerCredential = (body: {
  registration_id: string
  credential_id: string
  public_key: string
  algorithm: number
  client_data_json: string
}) => request<{ possession_challenge: string; user_handle: string }>('auth.registration_credential', { body })
export const provePossession = (body: { registration_id: string } & Assertion) => {
  const { credential_id: _unused, ...rest } = body
  return request<PendingRegistration>('auth.registration_possession', { body: rest })
}
