// 本文件是 Vue 应用的入口，负责：创建实例 → 注册路由和 UI 库 → 挂载到页面

import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import Antd from 'ant-design-vue' // Ant Design Vue UI 组件库
import 'ant-design-vue/dist/reset.css'
import App from './App.vue' // 根组件（提供顶栏、底栏布局）
import Home from './views/Home.vue' // 首页：表单填写
import Result from './views/Result.vue' // 结果页：行程展示

// 路由配置：URL 和页面的映射关系
const router = createRouter({
  history: createWebHistory(), // 无 # 号的 HTML5 History 模式
  routes: [
    {
      path: '/', // 访问 / 显示首页
      name: 'Home',
      component: Home
    },
    {
      path: '/result', // 访问 /result 显示结果页
      name: 'Result',
      component: Result
    }
  ]
})

const app = createApp(App)

app.use(router) // 注册路由，使 <router-view> 和 router.push() 可用
app.use(Antd) // 注册 Ant Design 组件库，使所有页面可直接使用 <a-button> 等组件

app.mount('#app') // 将整个 Vue 应用挂载到 index.html 里的 <div id="app"> 上

