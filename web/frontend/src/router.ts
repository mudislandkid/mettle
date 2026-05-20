import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'analysis',
      component: () => import('./views/AnalysisView.vue'),
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('./views/HistoryView.vue'),
    },
    {
      path: '/project/:id',
      name: 'project-detail',
      component: () => import('./views/ProjectDetailView.vue'),
    },
    {
      path: '/project/:id/diff',
      name: 'project-diff',
      component: () => import('./views/ProjectDiffView.vue'),
    },
    {
      path: '/compare',
      name: 'project-compare',
      component: () => import('./views/ProjectCompareView.vue'),
    },
    {
      path: '/digest',
      name: 'digest',
      component: () => import('./views/DigestView.vue'),
    },
  ],
})

export default router
