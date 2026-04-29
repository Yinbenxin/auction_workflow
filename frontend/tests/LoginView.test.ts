/**
 * LoginView 测试套件
 * 覆盖登录表单校验、成功跳转、失败提示
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import LoginView from '@/views/LoginView.vue'

// 模拟 auth store
const mockLogin = vi.fn()
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    login: mockLogin,
    error: null,
  }),
}))

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', component: { template: '<div />' } },
    { path: '/login', component: LoginView },
    { path: '/auctions', component: { template: '<div>竞拍列表</div>' } },
  ],
})

describe('LoginView', () => {
  beforeEach(() => {
    mockLogin.mockReset()
    router.push('/login')
  })

  it('用户名或密码为空时提交按钮应禁用', async () => {
    // 表单初始状态：用户名和密码均为空，提交按钮应处于 disabled 状态
    const wrapper = mount(LoginView, {
      global: { plugins: [router] },
    })

    const submitBtn = wrapper.find('[data-testid="submit-btn"]')
    expect(submitBtn.attributes('disabled')).toBeDefined()

    // 只填用户名，密码仍为空
    await wrapper.find('[data-testid="username-input"]').setValue('alice')
    expect(submitBtn.attributes('disabled')).toBeDefined()

    // 两者都填写后按钮应可用
    await wrapper.find('[data-testid="password-input"]').setValue('secret123')
    expect(submitBtn.attributes('disabled')).toBeUndefined()
  })

  it('登录成功后应跳转到竞拍列表页', async () => {
    // 模拟登录接口返回成功
    mockLogin.mockResolvedValueOnce({ success: true })

    const wrapper = mount(LoginView, {
      global: { plugins: [router] },
    })

    await wrapper.find('[data-testid="username-input"]').setValue('alice')
    await wrapper.find('[data-testid="password-input"]').setValue('secret123')
    await wrapper.find('[data-testid="submit-btn"]').trigger('click')
    await flushPromises()

    // 登录成功后路由应跳转到 /auctions
    expect(router.currentRoute.value.path).toBe('/auctions')
  })

  it('登录失败时应显示错误提示信息', async () => {
    // 模拟登录接口返回失败
    mockLogin.mockRejectedValueOnce(new Error('用户名或密码错误'))

    const wrapper = mount(LoginView, {
      global: { plugins: [router] },
    })

    await wrapper.find('[data-testid="username-input"]').setValue('alice')
    await wrapper.find('[data-testid="password-input"]').setValue('wrongpass')
    await wrapper.find('[data-testid="submit-btn"]').trigger('click')
    await flushPromises()

    // 错误提示应可见
    const errorMsg = wrapper.find('[data-testid="error-message"]')
    expect(errorMsg.exists()).toBe(true)
    expect(errorMsg.text()).toContain('用户名或密码错误')

    // 登录失败后不应跳转
    expect(router.currentRoute.value.path).toBe('/login')
  })
})
