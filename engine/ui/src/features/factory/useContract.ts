import { shallowRef } from 'vue'
import { readContract, type Contract } from '@/api/reads'
import { actionOf } from '@/features/contract/gaps'

let cached: Promise<Contract | null> | null = null

/** The API's published UI action contract (reads.contract), read once per page load. A refused read leaves
 * every action unavailable, never available. */
export function useContract() {
  const contract = shallowRef<Contract | null>(null)
  cached ??= readContract().catch(() => {
    cached = null
    return null
  })
  void cached.then((c) => (contract.value = c))
  return { contract, action: (name: string) => actionOf(contract.value, name) }
}
