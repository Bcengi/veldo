import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import type { ReadAnswer } from '@/api/types'
import { ACTION_ROUTES, published } from '@/api/actions'
import AccountPacing from './AccountPacing.vue'
import { canCap, canPause, ceilingValue, historyOf, pacingOf } from './pacing'

afterEach(() => vi.unstubAllGlobals())

const account = (id: string, data: Record<string, unknown>) => ({ id: `account:${id}`, kind: 'account', version: 1, digest: 'd', data: { id, label: id, status: 'active', ...data } })
const read = {
  items: {
    account: [
      account('account-a', {
        windows: { five_hour: { utilization: 0.4, reset_at: 1000 }, seven_day: { utilization: null, reset_at: 5000 } },
        pause: { window: 'five_hour', until: 1000 },
        ceilings: { seven_day: { value: 50, until: 5000, utilization: 40 }, old: { value: 20, until: 50, utilization: 10 } },
      }),
      account('account-b', { windows: { five_hour: { utilization: 0.1, reset_at: 900 } }, pause: { window: 'five_hour', until: 90 }, ceilings: {} }),
    ],
    subscription_reservation: [],
  },
  pacing: [
    { seq: 9, type: 'end', account: 'account-a', window: 'five_hour', until: 1000, ended: [{ kind: 'pause', window: 'five_hour' }] },
    { seq: 3, type: 'pause', account: 'account-a', window: 'five_hour', until: 1000, principal: 'owner', route: 'telegram' },
    { seq: 5, type: 'ceiling', account: 'account-a', window: 'seven_day', until: 5000, value: 50, principal: 'owner', route: 'ui' },
    { seq: 7, type: 'resume', account: 'account-b', principal: 'owner', route: 'ui', ended: [{ kind: 'ceiling', window: 'five_hour' }] },
  ],
} as unknown as ReadAnswer

describe('pacing', () => {
  it('shows each window with utilization and reset, and only the pause and ceilings in force', () => {
    const [a, b] = pacingOf(read, 100)
    expect(a!.windows).toEqual([{ id: 'five_hour', utilization: 40, resetAt: 1000 }, { id: 'seven_day', utilization: null, resetAt: 5000 }])
    expect(a!.pause).toEqual({ window: 'five_hour', until: 1000 })
    expect(a!.ceilings.map((c) => c.window)).toEqual(['seven_day'])
    expect(b!.pause).toBeNull()
    expect(pacingOf(read, 1000)[0]!.pause).toBeNull()
  })
  it('reads the history in journal order', () => {
    expect(historyOf(read).map((e) => e.type)).toEqual(['pause', 'ceiling', 'resume', 'end'])
  })
  it('takes a percent from 1 to 100 or a relative +N, and nothing else', () => {
    expect(ceilingValue('50')).toBe(50)
    expect(ceilingValue('+10')).toBe('+10')
    expect(ceilingValue('0')).toBeNull()
    expect(ceilingValue('101')).toBeNull()
    expect(ceilingValue('ten')).toBeNull()
  })
  it('offers a ceiling only on a window with observed utilization and a reset ahead', () => {
    const [a] = pacingOf(read, 100)
    expect(canCap(a!.windows[0]!, 100)).toBe(true)
    expect(canCap(a!.windows[1]!, 100)).toBe(false)
    expect(canPause(a!.windows[1]!, 100)).toBe(true)
    expect(canPause(a!.windows[0]!, 2000)).toBe(false)
  })
  it('names a published route for each of the three commands and the read', () => {
    expect(published(ACTION_ROUTES.account_pause)).toBe(true)
    expect(published(ACTION_ROUTES.account_resume)).toBe(true)
    expect(published(ACTION_ROUTES.account_ceiling)).toBe(true)
    expect(published('accounts.pacing')).toBe(true)
  })
})

describe('AccountPacing states', () => {
  it('empty: no account', () => {
    setActivePinia(createPinia())
    const wrapper = mount(AccountPacing, { props: { pacing: { items: { account: [] } } as unknown as ReadAnswer, now: 100 } })
    expect(wrapper.find('[data-testid="pacing-empty"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="pacing-history-empty"]').exists()).toBe(true)
  })
  it('populated: the pause, the ceiling, the actions and the history', () => {
    setActivePinia(createPinia())
    const wrapper = mount(AccountPacing, { props: { pacing: read, now: 100 } })
    expect(wrapper.find('[data-pacing-account="account-a"] [data-testid="pacing-paused"]').text()).toContain('five_hour')
    expect(wrapper.find('[data-testid="pacing-ceiling"]').text()).toContain('50%')
    expect(wrapper.findAll('[data-pacing-account="account-a"] [data-testid="pacing-pause"]').length).toBe(2)
    expect(wrapper.find('[data-pacing-account="account-a"] [data-testid="pacing-resume"]').exists()).toBe(true)
    expect(wrapper.find('[data-pacing-account="account-b"] [data-testid="pacing-resume"]').exists()).toBe(false)
    expect(wrapper.findAll('[data-testid="pacing-history"] li').map((li) => li.attributes('data-type'))).toEqual(['pause', 'ceiling', 'resume', 'end'])
  })
  it('error: a typed ceiling out of range is refused by name and nothing is sent', async () => {
    setActivePinia(createPinia())
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    const wrapper = mount(AccountPacing, { props: { pacing: read, now: 100 } })
    await wrapper.find('[data-pacing-account="account-a"] [data-window="five_hour"] [data-testid="pacing-ceiling-value"]').setValue('0')
    await wrapper.find('[data-pacing-account="account-a"] [data-window="five_hour"] [data-testid="pacing-ceiling-set"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="refusal"]').attributes('data-refusal')).toBe('invalid_input:ceiling')
    expect(fetch).not.toHaveBeenCalled()
  })
})
