# DeepSeek Chat Scraper

基于 Kimi 爬虫的模板创建的 DeepSeek 聊天爬虫。

## 功能特点

- ✅ 使用 Camoufox 进行强反检测浏览器自动化
- ✅ 支持手动登录，会话持久化（cookies + storage）
- ✅ 多任务支持（自动扫描 `*_input_prompts.txt` 文件）
- ✅ 智能跳过已处理的提示词
- ✅ 实时保存结果（防止崩溃丢失数据）
- ✅ 每个提示词创建独立对话（保持上下文干净）
- ✅ 自动检测响应完成（停止按钮监测 + 文本稳定性检查）
- ✅ 提取响应中的引用链接
- ✅ 输出 NDJSON 和 Markdown 两种格式

## 数据结构

每个对话项包含以下字段：

```json
{
  "website_name": "DEEPSEEK",
  "conversation_id": "从 URL 提取的对话 ID",
  "item_url": "完整对话 URL",
  "model_name": "检测到的模型名称（如果可见）",
  "mode_online": "在线模式状态（DeepSeek 可能没有）",
  "prompt_text": "用户输入的问题",
  "response_text": "AI 的响应（Markdown 格式，含内联引用）",
  "web_search_results": [],
  "response_language": "检测到的语言（zh/en）",
  "latency_ms": "响应时间（毫秒）",
  "status": "ok 或 error",
  "error_message": "错误详情（如果 status 是 error）"
}
```

## 使用方法

### 1. 准备输入文件

在项目根目录创建输入文件（命名格式：`任务名_input_prompts.txt`）：

```
task1_input_prompts.txt
task2_input_prompts.txt
```

每行一个提示词，例如：

```
What is machine learning?
Explain quantum computing
How does blockchain work?
```

### 2. 运行爬虫

```bash
cd MCPfiles
python deepseek_chat_scraper.py
```

### 3. 手动登录

- 脚本会自动打开 DeepSeek 网站
- 你有 5 分钟时间手动登录
- 登录成功后，脚本会自动检测到聊天界面并开始处理

### 4. 查看结果

结果保存在 `output/` 目录：

```
output/
├── deepseek_conversations_task1.ndjson    # 结构化数据（JSON Lines）
└── deepseek_conversations_task1.md        # 可读格式
```

## 输出格式

### NDJSON（结构化数据）

每行一个 JSON 对象，方便程序处理：

```json
{"website_name":"DEEPSEEK","conversation_id":"abc123","prompt_text":"What is AI?","response_text":"Artificial Intelligence...","latency_ms":3500,"status":"ok"}
```

### Markdown（人类可读）

```markdown
# Conversation abc123

- **Website**: DEEPSEEK
- **Model**: DeepSeek-V3
- **Language**: en
- **Latency**: 3500 ms

## Prompt

What is AI?

## Response

Artificial Intelligence is...

---
```

## 会话管理

爬虫会保存会话信息，下次运行时自动登录：

- `deepseek_cookies.json` - 浏览器 cookies
- `deepseek_storage.json` - localStorage 和 sessionStorage

## 断点续传

如果爬虫中途中断：

1. 已处理的结果已保存在 NDJSON 文件中
2. 重新运行时，会自动跳过已处理的提示词
3. 只处理新的或之前失败的提示词

## 选择器调整

**重要提示**：DeepSeek 的页面结构可能与预设的选择器不同。如果遇到问题：

1. 登录 DeepSeek 并打开开发者工具（F12）
2. 检查以下元素的实际选择器：
   - 输入框：`textarea` 或 `div[contenteditable="true"]`
   - 发送按钮：查找包含 "Send" 或发送图标的按钮
   - 停止按钮：查找包含 "Stop" 或停止图标的按钮
   - 响应容器：包含 AI 响应的 div 或 article 元素

3. 在 `deepseek_chat_scraper.py` 中更新相应的选择器列表：
   ```python
   CHAT_INPUT_SELECTORS: List[str] = [
       # 添加你发现的选择器
   ]
   ```

## 性能优化

- **人性化延迟**：动作间随机延迟 0.7-2.2 秒
- **会话重用**：跨提示词重用浏览器会话
- **并发限制**：单线程处理（避免被封）
- **智能等待**：基于内容长度的自适应超时
- **文本稳定性检测**：避免过早提取响应

## 故障排除

### 问题：找不到聊天输入框

**解决方案**：
1. 检查是否已成功登录
2. 确认 URL 不包含 "sign_in" 或 "login"
3. 更新 `CHAT_INPUT_SELECTORS` 列表

### 问题：响应提取不完整

**解决方案**：
1. 增加文本稳定性阈值（`required_stable_ticks`）
2. 增加超时时间
3. 检查停止按钮选择器是否正确

### 问题：无法检测响应完成

**解决方案**：
1. 使用浏览器开发者工具检查停止按钮的实际选择器
2. 更新 `STOP_BUTTON_SELECTORS` 列表
3. 观察 UI 变化，调整检测逻辑

### 问题：登录检测失败

**解决方案**：
1. 增加手动登录等待时间（修改 `timeout_seconds`）
2. 检查 `is_chat_ui_ready()` 函数的逻辑
3. 确认登录后的 URL 模式

## 最佳实践

### 推荐做法 ✓

- 使用持久会话文件减少登录频率
- 每个提示词启动新对话（保持上下文干净）
- 立即保存每个结果（防止崩溃丢失数据）
- 实现提示词重用检测（跳过已处理）
- 支持多任务工作流（task1、task2 等）
- 添加随机人性化延迟
- 处理中英文界面

### 避免做法 ✗

- 硬编码固定等待时间（使用动态检测）
- 在一个长对话中处理所有提示词
- 只在最后保存结果（有数据丢失风险）
- 忽略网络问题的错误处理
- 使用脆弱的 CSS 类选择器
- 处理已完成的提示词
- 并行运行多个任务（可能触发限流）

## 与 Kimi 爬虫的区别

DeepSeek 爬虫基于 Kimi 爬虫，但有以下差异：

1. **URL**: `https://chat.deepseek.com/` vs `https://kimi.moonshot.cn/chat`
2. **选择器**: 使用通用选择器，需要根据实际页面调整
3. **引用处理**: DeepSeek 可能不需要悬停转换（待确认）
4. **网络搜索**: DeepSeek 可能没有显式的网络搜索 UI（待确认）
5. **模型切换**: DeepSeek 的模型选择器可能不同（待确认）

## 下一步改进

待实际测试后，可能需要实现：

- [ ] DeepSeek 特定的引用提取逻辑
- [ ] 网络搜索结果提取（如果 DeepSeek 有此功能）
- [ ] 更精确的模型名称检测
- [ ] DeepSeek 特定的完成检测逻辑
- [ ] 处理 DeepSeek 特定的 UI 元素

## 许可证

与项目主许可证相同。

## 贡献

欢迎提交问题和改进建议！如果你发现了更准确的选择器或更好的检测逻辑，请分享。
