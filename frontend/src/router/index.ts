import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/auctions',
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/LoginView.vue'),
    },
    {
      path: '/auctions',
      name: 'AuctionList',
      component: () => import('../views/AuctionListView.vue'),
    },
    {
      path: '/auctions/:id',
      name: 'AuctionDetail',
      component: () => import('../views/AuctionDetailView.vue'),
    },
    {
      path: '/auctions/:id/strategies',
      name: 'StrategyList',
      component: () => import('../views/StrategyListView.vue'),
    },
    {
      path: '/auctions/:id/task-config',
      name: 'TaskConfig',
      component: () => import('../views/TaskConfigView.vue'),
    },
    {
      path: '/auctions/:id/review',
      name: 'Review',
      component: () => import('../views/ReviewView.vue'),
    },
    {
      path: '/auctions/:id/executions',
      name: 'ExecutionLog',
      component: () => import('../views/ExecutionLogView.vue'),
    },
    {
      path: '/auctions/:id/monitors',
      name: 'Monitor',
      component: () => import('../views/MonitorView.vue'),
    },
    {
      path: '/auctions/:id/modifications',
      name: 'Modification',
      component: () => import('../views/ModificationView.vue'),
    },
    {
      path: '/auctions/:id/retrospective',
      name: 'Retrospective',
      component: () => import('../views/RetrospectiveView.vue'),
    },
    {
      path: '/retrospectives/:rid/rectifications',
      name: 'Rectification',
      component: () => import('../views/RectificationView.vue'),
    },
  ],
})

// 路由守卫：未登录跳转 /login
router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')
  if (to.name !== 'Login' && !token) {
    next({ name: 'Login' })
  } else {
    next()
  }
})

export default router
