import type { Contract, ContractAction } from '@/api/reads'

/** An owner action the API's contract publishes: either its route, or the specification that owns it when the
 * engine has no typed command for it yet. A screen offers an action only when it has a route; otherwise it
 * names the gap beside the control, so nothing is ever sent that writes nothing real. */
export interface ActionAvailability {
  name: string
  route: string | null
  spec: string | null
}

export function actionOf(contract: Contract | null, name: string): ActionAvailability {
  const action: ContractAction | undefined = contract?.actions.find((a) => a.name === name)
  return { name, route: action?.route ?? null, spec: action?.spec ?? null }
}

/** The sentence a screen shows beside an action the API does not carry yet. */
export function gapSentence(action: ActionAvailability): string {
  return `The API has no route for ${action.name} yet${action.spec ? ` (owned by ${action.spec})` : ''}; nothing was sent.`
}
