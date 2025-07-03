# 前端API工具使用说明

## 问题解决

当后端返回409（Conflict）等HTTP错误状态码时，Next.js控制台会显示红色错误信息。这通常发生在：

1. 机械臂忙碌时返回409状态码
2. 用户输入验证失败返回400状态码
3. 资源未找到返回404状态码

## 解决方案

使用统一的API工具 (`web/app/utils/api.ts`) 来处理HTTP请求，区分业务错误和真正的系统错误。

## 基本用法

### 1. 导入API工具

```typescript
import { apiGet, apiPost, robotArmGrab } from '../utils/api'
```

### 2. GET请求

```typescript
const response = await apiGet<SystemStatus>('/api/status')
if (response.success) {
  console.log('系统状态:', response.data)
  setSystemStatus(response.data!)
} else {
  console.warn('获取状态失败:', response.error)
  // 不会在控制台显示红色错误
}
```

### 3. POST请求

```typescript
const response = await apiPost('/api/robot_arm/home')
if (response.success) {
  console.log('机械臂归位成功:', response.data?.message)
} else if (response.isBusinessError) {
  console.warn('业务错误:', response.error)
  // 409, 400等状态码，不在控制台报红色错误
} else {
  console.error('系统错误:', response.error)
  // 500等真正的服务器错误
}
```

### 4. 机械臂操作专用

```typescript
const result = await robotArmGrab(target)
if (result.success) {
  console.log('机械臂操作成功')
} else if (result.isBusy) {
  console.log(`机械臂正忙 (${result.currentStatus}): ${result.message}`)
  // 友好的用户提示，不是错误
} else {
  console.warn('机械臂操作失败:', result.message)
}
```

## 状态码处理

- **200-299**: 成功响应，`response.success = true`
- **400, 404, 409, 422**: 业务错误，`response.isBusinessError = true`，不在控制台报红色错误
- **500+**: 服务器错误，在控制台显示警告信息
- **网络错误**: 在控制台显示错误信息

## 优势

1. **避免控制台爆红**: 业务错误不会显示为红色错误
2. **统一错误处理**: 所有API请求使用相同的错误处理逻辑
3. **类型安全**: 支持TypeScript泛型
4. **业务错误区分**: 清楚区分业务错误和系统错误
5. **用户友好**: 提供更好的用户体验

## 注意事项

- 使用FormData时，工具会自动处理Content-Type
- 业务错误状态码可在 `BUSINESS_ERROR_CODES` 数组中配置
- 静默请求可使用 `apiRequestSilent` 函数 