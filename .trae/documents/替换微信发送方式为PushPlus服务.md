## 替换计划

### 1. 分析现有微信发送方式

#### search_01.py 中的方式
- 使用企业微信机器人的 webhook 方式
- 函数：`send_wechat_notification(webhook_url, message)`
- 发送 POST 请求，JSON 格式，包含 markdown 消息

#### itchat_test.py 中的方式
- 使用 PushPlus 服务
- 函数：`send_wechat(msg)`
- 发送 GET 请求到 PushPlus API
- 格式：`https://www.pushplus.plus/send?token={token}&title={title}&content={content}&template={template}`

### 2. 替换方案

#### 2.1 修改微信发送函数
- 在 `search_01.py` 中替换 `send_wechat_notification` 函数
- 使用 PushPlus 的 GET 请求方式
- 保留原函数名，确保调用处无需修改

#### 2.2 更新配置参数
- 将原有的 `wechat_config` 替换为 PushPlus 配置
- 添加 PushPlus token 配置项

#### 2.3 修改消息格式
- 将 markdown 格式转换为 PushPlus 支持的 HTML 格式

#### 2.4 测试发送逻辑
- 确保替换后的发送逻辑能正常工作

### 3. 具体实现步骤

1. **替换 `send_wechat_notification` 函数**
   - 删除原有的企业微信机器人发送逻辑
   - 实现 PushPlus 发送逻辑
   - 保留原函数签名，确保兼容性

2. **更新配置**
   - 将 `wechat_config` 中的 `webhook_url` 替换为 `token`
   - 添加 `title` 配置项

3. **修改消息生成**
   - 将 `generate_wechat_message` 函数返回的 markdown 转换为 HTML

4. **更新调用处**
   - 调整 `send_wechat_notification` 的调用参数

### 4. 预期效果

- 替换后，基金分析报告将通过 PushPlus 服务发送到微信
- 无需企业微信机器人，使用更简单的 PushPlus 服务
- 保持原有代码结构，调用处无需大量修改

### 5. 注意事项

- 需要用户在 PushPlus 官网注册账号并获取 token
- PushPlus 提供免费和付费服务，免费服务有发送次数限制
- 确保 PushPlus token 正确配置，否则消息发送失败