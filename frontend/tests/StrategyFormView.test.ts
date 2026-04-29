/**
 * StrategyFormView 测试套件
 * 覆盖应急风险级别必填字段、红线字段变更提示、状态锁定编辑
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import StrategyFormView from '@/views/StrategyFormView.vue'

describe('StrategyFormView', () => {

  it('risk_level=EMERGENCY 时应显示 pre_authorized_actions 必填字段', async () => {
    // 初始状态 risk_level 为普通级别，pre_authorized_actions 字段不可见
    const wrapper = mount(StrategyFormView, {
      props: { strategyId: 'strat-003' },
    })

    const preAuthField = wrapper.find('[data-testid="pre-authorized-actions"]')
    expect(preAuthField.exists()).toBe(false)

    // 将 risk_level 切换为 EMERGENCY
    const riskSelect = wrapper.find('[data-testid="risk-level-select"]')
    await riskSelect.setValue('EMERGENCY')
    await flushPromises()

    // EMERGENCY 级别下 pre_authorized_actions 字段应出现且标记为必填
    const preAuthFieldAfter = wrapper.find('[data-testid="pre-authorized-actions"]')
    expect(preAuthFieldAfter.exists()).toBe(true)
    expect(preAuthFieldAfter.attributes('required')).toBeDefined()
  })

  it('修改红线字段时应显示"需要额外确认"提示', async () => {
    // 红线字段：price、quantity、submit_time、trigger_condition
    const wrapper = mount(StrategyFormView, {
      props: { strategyId: 'strat-003' },
    })

    // 初始状态不应有额外确认提示
    expect(wrapper.find('[data-testid="reconfirm-warning"]').exists()).toBe(false)

    // 修改红线字段 price
    await wrapper.find('[data-testid="price-input"]').setValue('120')
    await flushPromises()

    // 应出现"需要额外确认"提示
    const warning = wrapper.find('[data-testid="reconfirm-warning"]')
    expect(warning.exists()).toBe(true)
    expect(warning.text()).toContain('需要额外确认')
  })

  it('CONFIRMED 状态时编辑按钮应禁用', async () => {
    // 传入 CONFIRMED 状态的策略
    const wrapper = mount(StrategyFormView, {
      props: {
        strategyId: 'strat-001',
        initialStatus: 'CONFIRMED',
      },
    })

    const editBtn = wrapper.find('[data-testid="edit-btn"]')
    expect(editBtn.exists()).toBe(true)
    expect(editBtn.attributes('disabled')).toBeDefined()
  })

  it('FINAL 状态时编辑按钮应禁用', async () => {
    // 传入 FINAL 状态的策略
    const wrapper = mount(StrategyFormView, {
      props: {
        strategyId: 'strat-002',
        initialStatus: 'FINAL',
      },
    })

    const editBtn = wrapper.find('[data-testid="edit-btn"]')
    expect(editBtn.exists()).toBe(true)
    expect(editBtn.attributes('disabled')).toBeDefined()
  })

  it('DRAFT 状态时编辑按钮应可用', async () => {
    // 传入 DRAFT 状态的策略
    const wrapper = mount(StrategyFormView, {
      props: {
        strategyId: 'strat-003',
        initialStatus: 'DRAFT',
      },
    })

    const editBtn = wrapper.find('[data-testid="edit-btn"]')
    expect(editBtn.exists()).toBe(true)
    expect(editBtn.attributes('disabled')).toBeUndefined()
  })
})
