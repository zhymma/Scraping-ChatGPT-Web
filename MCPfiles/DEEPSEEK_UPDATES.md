# DeepSeek 爬虫更新说明

## 基于实际页面结构的优化

根据 DeepSeek 实际页面的 HTML 结构，已对爬虫进行以下更新：

### 1. 核心选择器更新

#### 输入框
```python
CHAT_INPUT_SELECTORS = [
    "textarea._27c9245",  # DeepSeek 主输入框
    "textarea[placeholder*='DeepSeek']",
    "textarea[placeholder*='消息']",
]
```

#### 消息容器
```python
MESSAGE_LIST_SELECTOR = "div.dad65929"  # 消息列表容器
ASSISTANT_MESSAGE_SELECTORS = [
    'div.ds-message._63c77b1',  # 主消息容器
    'div.ds-message',
]
```

#### 发送方式
- **推荐**：使用 `Enter` 键发送（更可靠）
- 备选：点击发送按钮

#### 新对话按钮
```python
'div._5a8ac7a:has-text("开启新对话")'  # DeepSeek 特定的新对话按钮
```

### 2. 引用提取逻辑

**关键区别**：DeepSeek 的引用链接直接在 HTML 中，无需悬停触发！

```python
# Kimi: 需要悬停 .rag-tag 元素使其转换为 <a> 标签
# DeepSeek: 引用已经是 <a> 标签，直接提取即可

# 示例 HTML:
<a href="http://www.changshu.gov.cn/..." target="_blank" rel="noreferrer">
  <span class="ds-markdown-cite">6</span>
</a>
```

**优化**：
- 移除了 hover_all_citations 函数（不需要）
- 直接从 `div.ds-markdown` 提取 `<a>` 标签
- 使用 `CITATION_LINK_SELECTOR = 'a[href][target="_blank"]'`

### 3. Web Search 结果提取

DeepSeek 显示"已阅读 X 个网页"按钮，点击后展开搜索结果面板。

#### 实现流程
1. 检测 `div._74c0879` 元素（包含"已阅读"文字）
2. 点击打开侧边栏
3. 从侧边栏提取搜索结果
4. 每个结果包含：`{href, title, snippet}`

#### 选择器
```python
WEB_SEARCH_BUTTON_SELECTOR = "div._74c0879"
# 侧边栏位于: div._519be07 或 div.dc433409
```

### 4. 消息定位策略

DeepSeek 的消息层级：
```
div.dad65929 (消息列表)
  └─ div:nth-child(1) (第一条消息)
  └─ div:nth-child(2) (第二条消息)
     └─ div.ds-message._63c77b1 (消息容器)
        └─ div.ds-markdown (内容)
           └─ p, a, table, etc. (格式化内容)
```

**优化**：
- 使用 `div.dad65929` 作为消息列表根节点
- 通过 `.last` 获取最新消息
- 从 `div.ds-markdown` 提取格式化内容

### 5. 响应完成检测

#### 指标
1. **停止按钮消失** - 生成结束
2. **文本稳定性** - 3 次检查无变化（约 1.2 秒）
3. **超时保护** - 10 秒无变化自动结束

#### 实现
```python
# 1. 检查是否还在生成
if is_generating(page):
    # 继续等待
    
# 2. 文本稳定性
if stable_ticks >= required_stable_ticks and not is_generating(page):
    # 完成
    
# 3. 超时保护
if time.time() - last_change_time > 10:
    # 假定完成
```

### 6. 主要改进点

#### 相比初始版本
1. ✅ 使用 DeepSeek 实际的 CSS 类名
2. ✅ 移除不必要的悬停逻辑
3. ✅ 添加 web search 结果提取
4. ✅ 改进消息定位策略
5. ✅ 使用 Enter 键发送（更可靠）

#### 相比 Kimi 版本
| 功能 | Kimi | DeepSeek |
|------|------|----------|
| 引用提取 | 需要悬停 `.rag-tag` → `<a>` | 直接提取 `<a>` 标签 ✅ |
| 消息容器 | `div.chat-content-item-assistant` | `div.ds-message._63c77b1` |
| 发送方式 | 点击按钮 | Enter 键 ✅ |
| Web Search | 侧边栏 `div.side-console` | 点击按钮展开 |

### 7. 数据输出格式

#### NDJSON
```json
{
  "website_name": "DEEPSEEK",
  "conversation_id": "94a53818-43c3-43f2-8a1e-11648107fc22",
  "item_url": "https://chat.deepseek.com/a/chat/s/...",
  "model_name": "",
  "mode_online": "true",
  "prompt_text": "今天的天气是？",
  "response_text": "要告诉你今天的天气...[网站名称](http://...)",
  "web_search_results": [
    {
      "href": "http://news.cnhubei.com/...",
      "title": "湖北多地天气",
      "snippet": "白天多云转晴..."
    }
  ],
  "response_language": "zh",
  "latency_ms": 5420,
  "status": "ok"
}
```

#### Markdown
```markdown
# Conversation 94a53818-43c3-43f2-8a1e-11648107fc22

- **Website**: DEEPSEEK
- **URL**: https://chat.deepseek.com/a/chat/s/...
- **Model**: 
- **Online Mode**: true
- **Language**: zh
- **Latency**: 5420 ms

## Prompt

今天的天气是？

## Response

要告诉你今天的天气...[网站名称](http://...)

## Web Search Results

### 1. 湖北多地天气

- **URL**: http://news.cnhubei.com/...
- **Snippet**: 白天多云转晴...

---
```

### 8. 使用建议

#### 首次运行
1. 运行爬虫并观察日志输出
2. 如果选择器失效，检查开发者工具（F12）
3. 更新文件顶部的选择器常量

#### 调试
```python
# 在函数中查找 [DEBUG] 日志：
print("[DEBUG] Generation started")
print("[DEBUG] Content started appearing")
print(f"[DEBUG] Extracted {len(citations)} citations")
```

#### 性能优化
- 默认超时：300 秒
- 强制停止：240 秒后自动点击停止
- 文本稳定性：1.2 秒无变化即视为完成

### 9. 已知问题和解决方案

#### 问题 1：找不到输入框
**原因**：未登录或页面未加载完成  
**解决**：确认 URL 不包含 "sign_in"，等待更长时间

#### 问题 2：引用提取为空
**原因**：选择器可能已变化  
**解决**：检查 `CITATION_LINK_SELECTOR`，确认为 `'a[href][target="_blank"]'`

#### 问题 3：Web Search 结果未提取
**原因**：侧边栏选择器不正确  
**解决**：更新 `extract_web_search_results()` 中的 `side_panel_selectors`

### 10. 测试检查清单

运行前确认：
- [x] 选择器已根据实际页面更新
- [x] 引用提取逻辑简化（移除悬停）
- [x] Web search 结果提取函数已添加
- [x] 新对话按钮选择器正确
- [x] 输出格式包含 web_search_results

运行中检查：
- [ ] 能否正确检测到聊天界面
- [ ] 能否成功发送消息
- [ ] 响应是否完整提取（含引用）
- [ ] Web search 结果是否正确提取
- [ ] 新对话功能是否正常

## 更新历史

- **2025-12-11**: 基于实际 DeepSeek HTML 结构优化选择器和提取逻辑
- **2025-12-11**: 初始版本创建（基于 Kimi 模板）
