/**
 * TaskConfigView 测试套件
 * 覆盖9个配置字段、截图上传、二次确认弹窗
 */

import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import TaskConfigView from '@/views/TaskConfigView.vue'

describe('TaskConfigView', () => {

  it('表单应包含9个任务配置字段', () => {
    // 9个字段：任务顺序、启停状态、垫子策略、补量策略、
    // 价格偏移、时间窗口、最大申报量、最小申报量、备注
    const wrapper = mount(TaskConfigView, {
      props: { auctionId: 'auction-001' },
    })

    const expectedFields = [
      'task-order',
      'enable-status',
      'padding-strategy',
      'supplement-strategy',
      'price-offset',
      'time-window',
      'max-quantity',
      'min-quantity',
      'remarks',
    ]

    expectedFields.forEach((fieldId) => {
      const field = wrapper.find(`[data-testid="${fieldId}"]`)
      expect(field.exists(), `字段 ${fieldId} 应存在`).toBe(true)
    })
  })

  it('支持配置截图上传', async () => {
    const wrapper = mount(TaskConfigView, {
      props: { auctionId: 'auction-001' },
    })

    // 截图上传控件应存在
    const uploadInput = wrapper.find('[data-testid="screenshot-upload"]')
    expect(uploadInput.exists()).toBe(true)
    expect(uploadInput.attributes('type')).toBe('file')
    expect(uploadInput.attributes('accept')).toContain('image/')

    // 模拟文件上传
    const file = new File(['screenshot'], 'config.png', { type: 'image/png' })
    Object.defineProperty(uploadInput.element, 'files', {
      value: [file],
    })
    await uploadInput.trigger('change')
    await flushPromises()

    // 上传后应显示预览或文件名
    const preview = wrapper.find('[data-testid="screenshot-preview"]')
    expect(preview.exists()).toBe(true)
  })

  it('点击确认操作时应弹出二次确认弹窗', async () => {
    const wrapper = mount(TaskConfigView, {
      props: { auctionId: 'auction-001' },
    })

    // 初始状态弹窗不可见
    expect(wrapper.find('[data-testid="confirm-dialog"]').exists()).toBe(false)

    // 点击确认按钮
    await wrapper.find('[data-testid="confirm-btn"]').trigger('click')
    await flushPromises()

    // 二次确认弹窗应出现
    const dialog = wrapper.find('[data-testid="confirm-dialog"]')
    expect(dialog.exists()).toBe(true)
    expect(dialog.isVisible()).toBe(true)

    // 弹窗中应有"取消"和"确认"两个操作按钮
    expect(wrapper.find('[data-testid="dialog-cancel-btn"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="dialog-confirm-btn"]').exists()).toBe(true)
  })
})
