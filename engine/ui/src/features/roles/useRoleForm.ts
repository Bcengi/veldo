import { ref, shallowRef } from 'vue'
import {
  latestRevision,
  readConfiguration,
  saveConfiguration,
  type ConfigurationRevision,
  type SaveAnswer,
} from '@/api/configuration'
import { ApiRefusal } from '@/api/refusal'
import type { AsyncState } from '@/composables/useAsync'
import { emptyDraft, fromRevision, settingProblem, toDefinition, type RoleDraft } from './role-draft'

const named = (error: unknown) =>
  error instanceof ApiRefusal ? error : new ApiRefusal(0, 'unavailable:network', 'unavailable')

/** The role form's state: the role opened at its newest revision, the draft edited from it, and each save's
 * outcome as the API answered it. A save is bound to the revision the draft was edited from; what the form
 * shows as saved is the revision read back through the configuration route, never the draft. */
export function useRoleForm() {
  const draft = ref<RoleDraft | null>(null)
  const state = ref<AsyncState>('idle')
  const refusal = shallowRef<ApiRefusal | null>(null)
  const saving = ref(false)
  const saveRefusal = shallowRef<ApiRefusal | null>(null)
  const problem = ref<string | null>(null)
  const saved = shallowRef<ConfigurationRevision | null>(null)
  const answer = shallowRef<SaveAnswer | null>(null)

  async function open(role: string) {
    state.value = 'loading'
    refusal.value = null
    saveRefusal.value = null
    problem.value = null
    saved.value = null
    try {
      const latest = await latestRevision(role)
      draft.value = latest ? fromRevision(await readConfiguration(role, latest)) : emptyDraft(role)
      state.value = 'ready'
    } catch (error) {
      draft.value = null
      refusal.value = named(error)
      state.value = 'error'
    }
  }

  async function save() {
    const d = draft.value
    if (!d || saving.value) return
    problem.value = d.settings.map(settingProblem).find((p) => p) ?? (d.role.trim() ? null : 'Name the role.')
    if (problem.value) return
    saving.value = true
    saveRefusal.value = null
    try {
      const definition = toDefinition(d)
      const result = await saveConfiguration(definition, d.editedFrom)
      answer.value = result
      const stored = await readConfiguration(definition.role, result.revision ?? 0)
      saved.value = stored
      draft.value = fromRevision(stored)
    } catch (error) {
      saveRefusal.value = named(error)
    } finally {
      saving.value = false
    }
  }

  return { draft, state, refusal, saving, saveRefusal, problem, saved, answer, open, save }
}
