/**
 * RectificationView 测试套件
 * 覆盖整改事项分组展示、必填字段校验、角色权限控制
 */

import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import RectificationView from '@/views/RectificationView.vue'

// 模拟整改事项数据
const mockRectificationItems = [
  { id: 'r-001', title: '价格策略优化', status: 'PENDING', assignee: 'user-alice', deadline: '2026-05-10', measure: '重新评估价格区间' },
  { id: 'r-002', title: '复核流程完善', status: 'IN_PROGRESS', assignee: 'user-bob', deadline: '2026-05-15', measure: '增加复核节点' },
  { id: 'r-003', title: '监控告警配置', status: 'COMPLETED', assignee: 'user-charlie', deadline: '2026-05-05', measure: '配置阈值告警' },
]

describe('RectificationView', () => {

  it('整改事项列表应按状态分组展示', async () => {
    const wrapper = mount(RectificationView, {
      props: {
        auctionId: 'auction-001',
        currentUserRole: 'RETROSPECTIVE_MANAGER',
        items: mockRectificationItems,
      },
    })

    await flushPromises()

    // 应存在三个状态分组
    expect(wrapper.find('[data-testid="group-PENDING"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="group-IN_PROGRESS"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="group-COMPLETED"]').exists()).toBe(true)

    // 各分组内的条目数量应正确
    expect(wrapper.findAll('[data-testid^="item-PENDING-"]')).toHaveLength(1)
    expect(wrapper.findAll('[data-testid^="item-IN_PROGRESS-"]')).toHaveLength(1)
    expect(wrapper.findAll('[data-testid^="item-COMPLETED-"]')).toHaveLength(1)
  })

  it('创建整改项时责任人、措施、截止时间为必填', async () => {
    const wrapper = mount(RectificationView, {
      props: {
        auctionId: 'auction-001',
        currentUserRole: 'RETROSPECTIVE_MANAGER',
        items: [],
      },
    })

    // 打开创建表单
    await wrapper.find('[data-testid="create-item-btn"]').trigger('click')
    await flushPromises()

    // 只填写标题，不填必填字段，点击保存
    await wrapper.find('[data-testid="new-item-title"]').setValue('新整改事项')
    await wrapper.find('[data-testid="save-item-btn"]').trigger('click')
    await flushPromises()

    // 三个必填字段应显示校验错误
    expect(wrapper.find('[data-testid="assignee-error"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="measure-error"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="deadline-error"]').exists()).toBe(true)

    // 填写全部必填字段后错误应消失
    await wrapper.find('[data-testid="new-item-assignee"]').setValue('user-alice')
    await wrapper.find('[data-testid="new-item-measure"]').setValue('具体整改措施')
    await wrapper.find('[data-testid="new-item-deadline"]').setValue('2026-05-20')
    await wrapper.find('[data-testid="save-item-btn"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="assignee-error"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="measure-error"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="deadline-error"]').exists()).toBe(false)
  })

  it('复盘负责人可见"确认完成"按钮，其他角色不可见', async () => {
    // 复盘负责人应看到"确认完成"按钮
    const wrapperManager = mount(RectificationView, {
      props: {
        auctionId: 'auction-001',
        currentUserRole: 'RETROSPECTIVE_MANAGER',
        items: mockRectificationItems,
      },
    })
    await flushPromises()
    expect(wrapperManager.find('[data-testid="confirm-complete-btn"]').exists()).toBe(true)

    // 交易员不应看到"确认完成"按钮
    const wrapperTrader = mount(RectificationView, {
      props: {
        auctionId: 'auction-001',
        currentUserRole: 'TRADER',
        items: mockRectificationItems,
      },
    })
    await flushPromises()
    expect(wrapperTrader.find('[data-testid="confirm-complete-btn"]').exists()).toBe(false)

    // 复核人不应看到"确认完成"按钮
    const wrapperReviewer = mount(RectificationView, {
      props: {
        auctionId: 'auction-001',
        currentUserRole: 'REVIEWER',
        items: mockRectificationItems,
      },
    })
    await flushPromises()
    expect(wrapperReviewer.find('[data-testid="confirm-complete-btn"]').exists()).toBe(false)
  })
})
