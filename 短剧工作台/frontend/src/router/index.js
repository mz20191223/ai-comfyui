import { createRouter, createWebHashHistory } from 'vue-router'

// meta.title 用于顶栏面包屑与侧边栏高亮，改标题只改这里
const routes = [
  { path: '/', name: 'projects', meta: { title: '项目列表' }, component: () => import('../views/Projects.vue') },
  { path: '/tasks', name: 'tasks', meta: { title: '任务中心' }, component: () => import('../views/TaskCenter.vue') },
  { path: '/settings', name: 'settings', meta: { title: '接口与设置' }, component: () => import('../views/Settings.vue') },
  { path: '/p/:pid/script', name: 'script', meta: { title: '剧本' }, component: () => import('../views/Script.vue') },
  { path: '/p/:pid/board', name: 'board', meta: { title: '镜头看板' }, component: () => import('../views/ShotBoard.vue') },
  { path: '/p/:pid/shot/:sid', name: 'shot', meta: { title: '镜头详情' }, component: () => import('../views/ShotDetail.vue') },
  { path: '/p/:pid/assets', name: 'assets', meta: { title: '资产库' }, component: () => import('../views/Assets.vue') },
  { path: '/p/:pid/timeline', name: 'timeline', meta: { title: '合成' }, component: () => import('../views/Timeline.vue') },
]

export default createRouter({
  history: createWebHashHistory(),
  routes,
})
