/**
 * ModificationView 测试套件
 * 覆盖角色按钮可见性、REJECTED 状态展示
 */

import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ModificationView from '@/views/ModificationView.vue'

describe('ModificationView', () => {

  it('交易员角色应看到"提交申请"和"应急执行"按钮', () => {
    // 以交易员身份渲染组件
    const wrapper = mount(ModificationView, {
      props: {
        strategyId: 'strat-003',
        currentUserRole: 'TRADER',
        modificationStatus: 'DRAFT',
      },
    })

    expect(wrapper.find('[data-testid="submit-application-btn"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="emergency-execute-btn"]').exists()).toBe(true)

    // 交易员不应看到审批按钮
    expect(wrapper.find('[data-testid="approve-btn"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="review-pass-btn"]').exists()).toBe(false)
  })

  it('策略负责人角色应看到"审批通过"和"驳回"按钮', () => {
    // 以策略负责人身份渲染组件
    const wrapper = mount(ModificationView, {
      props: {
        strategyId: 'strat-003',
        currentUserRole: 'STRATEGY_MANAGER',
        modificationStatus: 'PENDING_APPROVAL',
      },
    })

    expect(wrapper.find('[data-testid="approve-btn"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="reject-btn"]').exists()).toBe(true)

    // 策略负责人不应看到交易员专属按钮
    expect(wrapper.find('[data-testid="submit-application-btn"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="emergency-execute-btn"]').exists()).toBe(false)
  })

  it('复核人角色应看到"复核通过"和"驳回"按钮', () => {
    // 以复核人身份渲染组件
    const wrapper = mount(ModificationView, {
      props: {
        strategyId: 'strat-003',
        currentUserRole: 'REVIEWER',
        modificationStatus: 'PENDING_REVIEW',
      },
    })

    expect(wrapper.find('[data-testid="review-pass-btn"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="review-reject-btn"]').exists()).toBe(true)

    // 复核人不应看到审批按钮
    expect(wrapper.find('[data-testid="approve-btn"]').exists()).toBe(false)
  })

  it('REJECTED 状态应显示驳回原因且不显示执行按钮', async () => {
    const rejectionReason = '价格超出授权范围，需重新评估'

    const wrapper = mount(ModificationView, {
      props: {
        strategyId: 'strat-003',
        currentUserRole: 'TRADER',
        modificationStatus: 'REJECTED',
        rejectionReason,
      },
    })

    await flushPromises()

    // 应显示驳回原因
    const reasonBlock = wrapper.find('[data-testid="rejection-reason"]')
    expect(reasonBlock.exists()).toBe(true)
    expect(reasonBlock.text()).toContain(rejectionReason)

    // REJECTED 状态下不应显示执行按钮
    expect(wrapper.find('[data-testid="execute-btn"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="emergency-execute-btn"]').exists()).toBe(false)
  })
})
