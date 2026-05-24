# 前端开发顺序

遵循**依赖从底层到上层**的原则，每一步完成后都能跑起来验证。

---

### 第 1 步：类型定义 `types/index.ts`

**为什么先做**：所有后续代码都依赖类型。先和后端约定好 API 的请求/响应结构，写死下来。

```
做什么：定义 TripFormData、TripPlan、DayPlan 等 interface
验证：TypeScript 编译通过即可
耗时：~10 分钟
```

---

### 第 2 步：API 层 `services/api.ts`

**为什么接着做**：类型有了，马上把和后端的通信通道搭好。这一步决定了数据能不能进来。

```
做什么：创建 axios 实例 → 写 generateTripPlan() → 拦截器加日志
验证：用 curl 或 Postman 确认后端跑着，前端 console 里调一下 healthCheck() 看通不通
耗时：~20 分钟
```

---

### 第 3 步：路由 + App 壳 `main.ts` + `App.vue`

**为什么第三步做**：API 和类型有了，需要页面壳子来展示它们。先把两个"空页面"跑起来，路由跳得通。

```
做什么：
  main.ts → 注册路由（/ 和 /result）+ Ant Design
  App.vue → 顶栏 + <router-view> + 底栏
  Home.vue → 先写一个 <h1>Home</h1> 占位
  Result.vue → 先写一个 <h1>Result</h1> 占位
验证：npm run dev，浏览器里手动改 URL 看两个页面是否正常切换
耗时：~15 分钟
```

---

### 第 4 步：Home 页面 `views/Home.vue`

**为什么先做 Home**：它是数据的起点——用户在这里输入，Result 页面才能展示。而且它逻辑相对简单，可以边开发边调 API。

```
开发子顺序：
  ① 模板：表单布局（城市、日期、交通、住宿、偏好、额外要求）
  ② 脚本：reactive 绑定表单 → watch 自动算天数 → handleSubmit 调 API
  ③ 样式：渐变色背景、卡片圆角、按钮动画
验证：填表单 → 点击提交 → 看 console 有没有 API 请求发出、有没有报错
耗时：1-2 小时
```

---

### 第 5 步：Result 页面 `views/Result.vue`

**为什么最后做**：它依赖前面所有东西——类型、API、路由、sessionStorage 里的数据。而且是全项目最复杂的组件。

```
开发子顺序（按模块）：
  ① 基础展示：从 sessionStorage 读数据 → 显示概览 + 预算 + 天气
  ② 每日行程：a-collapse 折叠面板，嵌套景点列表 + 酒店 + 餐饮
  ③ 地图：initMap → addAttractionMarkers → drawRoutes
  ④ 编辑模式：toggleEdit → 快照保存 → save/cancel
  ⑤ 导出：exportAsImage → exportAsPDF
  ⑥ 图片：loadAttractionPhotos → getAttractionImage 占位图降级
验证：每完成一个子模块就在浏览器里操作一下，确认不报错
耗时：3-5 小时
```

---

## 依赖关系图

```
types/index.ts          ← 一切的基础
    │
    ▼
services/api.ts         ← 通信层
    │
    ▼
main.ts + App.vue       ← 应用骨架
    │
    ├──► Home.vue       ← 数据入口（先做）
    │       │
    │       └── sessionStorage ──┐
    │                            ▼
    └──► Result.vue      ← 数据消费（后做）
```

---

## 核心原则

**每做完一步，立刻验证，不堆到最后一起调。**
