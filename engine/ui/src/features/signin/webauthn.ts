import type { Assertion, RegistrationBegun } from '@/api/auth'

/** Unpadded base64url, as the API speaks it. */
export function toB64url(data: ArrayBuffer | Uint8Array): string {
  const bytes = data instanceof Uint8Array ? data : new Uint8Array(data)
  let text = ''
  for (const byte of bytes) text += String.fromCharCode(byte)
  return btoa(text).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

export function fromB64url(text: string): Uint8Array<ArrayBuffer> {
  const padded = text.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (text.length % 4)) % 4)
  const raw = atob(padded)
  const out = new Uint8Array(new ArrayBuffer(raw.length))
  for (let i = 0; i < raw.length; i += 1) out[i] = raw.charCodeAt(i)
  return out
}

export function passkeysAvailable(): boolean {
  return typeof window !== 'undefined' && 'PublicKeyCredential' in window && !!navigator.credentials
}

export interface Created {
  credential_id: string
  public_key: string
  algorithm: number
  client_data_json: string
}

/** The registration ceremony for a pending registration the API began. */
export async function createPasskey(begun: RegistrationBegun, label: string): Promise<Created> {
  const credential = (await navigator.credentials.create({
    publicKey: {
      challenge: fromB64url(begun.challenge),
      rp: { id: begun.rp_id, name: 'Veldo factory' },
      user: { id: fromB64url(begun.user_handle), name: label, displayName: label },
      pubKeyCredParams: begun.algorithms.map((alg) => ({ type: 'public-key' as const, alg })),
      authenticatorSelection: { residentKey: 'required', requireResidentKey: true, userVerification: 'required' },
      attestation: 'none',
      timeout: 120000,
    },
  })) as PublicKeyCredential | null
  if (!credential) throw new Error('no passkey was created')
  const response = credential.response as AuthenticatorAttestationResponse
  const key = response.getPublicKey()
  if (!key) throw new Error('this browser does not expose the new public key')
  return {
    credential_id: toB64url(credential.rawId),
    public_key: toB64url(key),
    algorithm: response.getPublicKeyAlgorithm(),
    client_data_json: toB64url(response.clientDataJSON),
  }
}

/** A sign-in ceremony over `challenge`, limited to one credential when `credentialId` is given. */
export async function assertPasskey(challenge: string, rpId: string, credentialId?: string): Promise<Assertion> {
  const credential = (await navigator.credentials.get({
    publicKey: {
      challenge: fromB64url(challenge),
      rpId,
      userVerification: 'required',
      allowCredentials: credentialId ? [{ type: 'public-key', id: fromB64url(credentialId) }] : [],
      timeout: 120000,
    },
  })) as PublicKeyCredential | null
  if (!credential) throw new Error('no passkey was used')
  const response = credential.response as AuthenticatorAssertionResponse
  return {
    credential_id: toB64url(credential.rawId),
    client_data_json: toB64url(response.clientDataJSON),
    authenticator_data: toB64url(response.authenticatorData),
    signature: toB64url(response.signature),
    user_handle: response.userHandle ? toB64url(response.userHandle) : '',
  }
}

/** A browser's own words for a ceremony the person cancelled or that timed out. */
export function ceremonyMessage(error: unknown): string {
  const name = (error as DOMException)?.name
  if (name === 'NotAllowedError') return 'The passkey prompt was closed or timed out. Try again when ready.'
  if (name === 'InvalidStateError') return 'This device already holds a passkey for this factory.'
  if (name === 'SecurityError') return 'This page is not on the factory origin, so passkeys are refused here.'
  return (error as Error)?.message || 'The passkey ceremony did not finish.'
}
