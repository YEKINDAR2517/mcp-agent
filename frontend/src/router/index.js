import { createRouter, createWebHistory } from 'vue-router'
// import ChatView from '../views/ChatView.vue'
// import ServerManager from '../views/ServerManager.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    redirect: '/chat'
  },
  {
    path: '/chat',
    name: 'NewChat',
    component: () => import('../views/ChatView.vue')
  },
  {
    path: '/chat/:chatId',
    name: 'ChatDetail',
    component: () => import('../views/ChatView.vue'),
    props: true
  },
  {
    path: '/servers',
    name: 'ServerManager',
    component: () => import('../views/ServerManager.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由变化时打印日志
// router.beforeEach((to, from, next) => {
//   console.trace(`路由变化: from ${from.fullPath} to ${to.fullPath}`)
//   next()
// })

export default router 