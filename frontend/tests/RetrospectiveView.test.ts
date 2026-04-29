/**
 * RetrospectiveView 测试套件
 * 覆盖11个必填项校验、应急说明显示、提交失败缺失字段提示
 */

import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import RetrospectiveView from '@/views/RetrospectiveView.vue'

// 11个必填字段的 data-testid 列表
const REQUIRED_FIELDS = [
  'auction-result',
  'final-price',
  'final-quantity',
  'strategy-evaluation',
  'execution-deviation',
  'market-analysis',
  'risk-review',
  'lessons-learned',
  'improvement-suggestions',
  'responsible-person',
  'completion-date',
]

describe('RetrospectiveView', () => {

  it('11个必填项全部填写后提交按钮才可用', async () => {
    const wrapper = mount(RetrospectiveView, {
      props: { auctionId: 'auction-001', hasEmergencyModification: false },
    })

    const submitBtn = wrapper.find('[data-testid="submit-retrospective-btn"]')

    // 初始状态：提交按钮禁用
    expect(submitBtn.attributes('disabled')).toBeDefined()

    // 逐一填写前10个字段，按钮仍禁用
    for (let i = 0; i < REQUIRED_FIELDS.length - 1; i++) {
      await wrapper.find(`[data-testid="${REQUIRED_FIELDS[i]}"]`).setValue(`测试内容${i}`)
    }
    expect(submitBtn.attributes('disabled')).toBeDefined()

    // 填写最后一个字段后按钮应可用
    await wrapper
      .find(`[data-testid="${REQUIRED_FIELDS[REQUIRED_FIELDS.length - 1]}"]`)
      .setValue('2026-05-01')
    await flushPromises()
    expect(submitBtn.attributes('disabled')).toBeUndefined()
  })

  it('有应急修改时应显示应急说明输入框', async () => {
    // 无应急修改时不显示
    const wrapperNormal = mount(RetrospectiveView, {
      props: { auctionId: 'auction-001', hasEmergencyModification: false },
    })
    expect(wrapperNormal.find('[data-testid="emergency-explanation"]').exists()).toBe(false)

    // 有应急修改时应显示
    const wrapperEmergency = mount(RetrospectiveView, {
      props: { auctionId: 'auction-002', hasEmergencyModification: true },
    })
    await flushPromises()
    const emergencyField = wrapperEmergency.find('[data-testid="emergency-explanation"]')
    expect(emergencyField.exists()).toBe(true)
    expect(emergencyField.attributes('required')).toBeDefined()
  })

  it('提交失败时应显示具体缺失字段名', async () => {
    // 模拟提交时服务端返回缺失字段错误
    const mockSubmit = vi.fn().mockRejectedValueOnce({
      response: {
        status: 422,
        data: {
          missing_fields: ['strategy_evaluation', 'lessons_learned'],
        },
      },
    })

    const wrapper = mount(RetrospectiveView, {
      props: { auctionId: 'auction-001', hasEmergencyModification: false },
      global: {
        provide: { submitRetrospective: mockSubmit },
      },
    })

    // 填写部分字段后提交
    await wrapper.find('[data-testid="auction-result"]').setValue('成交')
    await wrapper.find('[data-testid="submit-retrospective-btn"]').trigger('click')
    await flushPromises()

    // 应显示缺失字段的具体名称
    const errorBlock = wrapper.find('[data-testid="missing-fields-error"]')
    expect(errorBlock.exists()).toBe(true)
    expect(errorBlock.text()).toContain('strategy_evaluation')
    expect(errorBlock.text()).toContain('lessons_learned')
  })
})
