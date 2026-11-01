import { computed, ref, shallowRef } from 'vue'
import {
  DEFAULT_TEAM,
  readTeam,
  saveDefaultTeam,
  saveTeam,
  type SaveAnswer,
  type TeamRecord,
} from '@/api/configuration'
import { ApiRefusal } from '@/api/refusal'
import type { AsyncState } from '@/composables/useAsync'
import { currentOf, editedFromOf, newRow, pendingOf, rowsOf, toTeam, type TeamDraft } from './team-draft'

const named = (error: unknown) =>
  error instanceof ApiRefusal ? error : new ApiRefusal(0, 'unavailable:network', 'unavailable')

/** The team form's state: a project's team (or the default team) as the team route reads it, the draft edited
 * from it, and each save's outcome. The current team is only ever what the team route reads back. */
export function useTeamForm() {
  const project = ref<string | null>(null)
  const record = shallowRef<TeamRecord | null>(null)
  const draft = ref<TeamDraft | null>(null)
  const state = ref<AsyncState>('idle')
  const refusal = shallowRef<ApiRefusal | null>(null)
  const saving = ref(false)
  const saveRefusal = shallowRef<ApiRefusal | null>(null)
  const answer = shallowRef<SaveAnswer | null>(null)
  const isDefault = computed(() => project.value === DEFAULT_TEAM)
  const current = computed(() => currentOf(record.value))
  const pending = computed(() => pendingOf(record.value))

  function reset(from: TeamRecord | null) {
    record.value = from
    draft.value = { rows: rowsOf(currentOf(from)?.team), editedFrom: editedFromOf(from, isDefault.value) }
  }

  async function open(name: string) {
    project.value = name
    state.value = 'loading'
    refusal.value = null
    saveRefusal.value = null
    answer.value = null
    try {
      reset(await readTeam(name))
      state.value = 'ready'
    } catch (error) {
      record.value = null
      draft.value = null
      refusal.value = named(error)
      state.value = 'error'
    }
  }

  /** Read the team again (after an answer in the decisions screen, for example): the draft starts over from
   * what the team route reads, and the last save's outcome is cleared with it. */
  async function reload() {
    if (!project.value) return
    try {
      reset(await readTeam(project.value))
      refusal.value = null
      saveRefusal.value = null
      answer.value = null
    } catch (error) {
      refusal.value = named(error)
    }
  }

  function addRole(name: string) {
    if (!draft.value || !name.trim() || draft.value.rows.some((r) => r.name === name.trim())) return false
    draft.value.rows.push(newRow(name.trim()))
    return true
  }

  function removeRole(name: string) {
    if (draft.value) draft.value.rows = draft.value.rows.filter((r) => r.name !== name)
  }

  async function save() {
    const d = draft.value
    const name = project.value
    if (!d || !name || saving.value) return
    saving.value = true
    saveRefusal.value = null
    answer.value = null
    try {
      const team = toTeam(d.rows)
      answer.value = isDefault.value
        ? await saveDefaultTeam(team, d.editedFrom)
        : await saveTeam(name, team, d.editedFrom)
      reset(await readTeam(name))
    } catch (error) {
      saveRefusal.value = named(error)
    } finally {
      saving.value = false
    }
  }

  return {
    project, record, draft, state, refusal, saving, saveRefusal, answer, isDefault, current, pending,
    open, reload, addRole, removeRole, save,
  }
}
