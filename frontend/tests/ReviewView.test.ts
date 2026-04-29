/**
 * ReviewView 测试套件
 * 覆盖13项复核清单、提交按钮状态、双人复核校验
 */

import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ReviewView from '@/views/ReviewView.vue'

describe('ReviewView', () => {

  it('应显示13项复核清单', () => {
    // 13项复核清单全部渲染
    const wrapper = mount(ReviewView, {
      props: {
        strategyId: 'strat-003',
        configuratorId: 'user-alice',
        reviewerId: 'user-bob',
      },
    })

    const checklistItems = wrapper.findAll('[data-testid^="checklist-item-"]')
    expect(checklistItems).toHaveLength(13)
  })

  it('未全部勾选复核清单时提交按钮应禁用', async () => {
    const wrapper = mount(ReviewView, {
      props: {
        strategyId: 'strat-003',
        configuratorId: 'user-alice',
        reviewerId: 'user-bob',
      },
    })

    // 初始状态：全部未勾选，提交按钮禁用
    const submitBtn = wrapper.find('[data-testid="submit-review-btn"]')
    expect(submitBtn.attributes('disabled')).toBeDefined()

    // 勾选前12项，仍未全部完成
    const checkboxes = wrapper.findAll('[data-testid^="checklist-item-"]')
    for (let i = 0; i < 12; i++) {
      await checkboxes[i].find('input[type="checkbox"]').setValue(true)
    }
    expect(submitBtn.attributes('disabled')).toBeDefined()

    // 勾选第13项后提交按钮应可用
    await checkboxes[12].find('input[type="checkbox"]').setValue(true)
    await flushPromises()
    expect(submitBtn.attributes('disabled')).toBeUndefined()
  })

  it('配置人与复核人相同时应显示错误提示', async () => {
    // 传入相同的配置人和复核人 ID
    const wrapper = mount(ReviewView, {
      props: {
        strategyId: 'strat-003',
        configuratorId: 'user-alice',
        reviewerId: 'user-alice',  // 同一人
      },
    })

    await flushPromises()

    // 应显示双人复核错误提示
    const errorMsg = wrapper.find('[data-testid="dual-review-error"]')
    expect(errorMsg.exists()).toBe(true)
    expect(errorMsg.text()).toContain('配置人与复核人不能为同一人')

    // 提交按钮应禁用
    const submitBtn = wrapper.find('[data-testid="submit-review-btn"]')
    expect(submitBtn.attributes('disabled')).toBeDefined()
  })
})
