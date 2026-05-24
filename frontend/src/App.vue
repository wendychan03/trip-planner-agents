<!-- 根组件：提供所有页面共用的壳（顶栏 + 内容区 + 底栏） -->
<template>
  <div id="app">
    <a-layout style="min-height: 100vh">
      <a-layout-header style="background: #001529; padding: 0 50px">
        <div style="color: white; font-size: 24px; font-weight: bold">
          🌍 HelloAgents智能旅行助手
        </div>
      </a-layout-header>
      <a-layout-content style="padding: 24px">
        <!-- 根据 URL 切换页面：/ → Home.vue，/result → Result.vue -->
        <router-view />
      </a-layout-content>
      <a-layout-footer style="text-align: center">
        HelloAgents智能旅行助手 ©2025 基于HelloAgents框架
      </a-layout-footer>
    </a-layout>
  </div>
</template>

<script setup lang="ts">
</script>

<style>
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    'Noto Sans', sans-serif;
}
</style>

