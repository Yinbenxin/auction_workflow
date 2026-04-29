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
      component: () => import('../views/auth/LoginView.vue'),
    },
    {
      path: '/auctions',
      name: 'AuctionList',
      component: () => import('../views/auctions/AuctionListView.vue'),
    },
    {
      path: '/auctions/:id',
      name: 'AuctionDetail',
      component: () => import('../views/auctions/AuctionDetailView.vue'),
    },
    {
      path: '/auctions/:id/strategies',
      name: 'StrategyList',
      component: () => import('../views/strategies/StrategyListView.vue'),
    },
    {
      path: '/auctions/:id/strategies/new',
      name: 'StrategyCreate',
      component: () => import('../views/strategies/StrategyFormView.vue'),
    },
    {
      path: '/auctions/:id/strategies/:vid/edit',
      name: 'StrategyEdit',
      component: () => import('../views/strategies/StrategyFormView.vue'),
    },
    {
      path: '/auctions/:id/task-config',
      name: 'TaskConfig',
      component: () => import('../views/task-configs/TaskConfigView.vue'),
    },
    {
      path: '/auctions/:id/review',
      name: 'Review',
      component: () => import('../views/reviews/ReviewView.vue'),
    },
    {
      path: '/auctions/:id/executions',
      name: 'ExecutionLog',
      component: () => import('../views/executions/ExecutionLogView.vue'),
    },
    {
      path: '/auctions/:id/monitors',
      name: 'Monitor',
      component: () => import('../views/monitors/MonitorView.vue'),
    },
    {
      path: '/auctions/:id/modifications',
      name: 'Modification',
      component: () => import('../views/modifications/ModificationView.vue'),
    },
    {
      path: '/auctions/:id/retrospective',
      name: 'Retrospective',
      component: () => import('../views/retrospectives/RetrospectiveView.vue'),
    },
    {
      path: '/retrospectives/:rid/rectifications',
      name: 'Rectification',
      component: () => import('../views/retrospectives/RectificationView.vue'),
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
