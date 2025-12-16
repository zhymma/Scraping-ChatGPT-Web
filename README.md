[1 tool called]

### 项目快速使用说明（中文版）

#### 1. 环境与依赖

- **Python 版本**：建议 Python 3.10+
- **安装依赖包**（一次性执行）：

```bash
pip install camoufox mcp scrapy screeninfo
python -m camoufox fetch  # 下载 Camoufox 内置浏览器
```

#### 2. 输入数据整理

- 所有爬虫都会自动读取**项目根目录**下名字形如 `*_input_prompts.txt` 的文件。  
- **每行一个问题 / 指令**，例如：

```text
我想买一些人气高的网红拉面产品，有什么日式拉面推荐吗？
我想买一副防辐射眼镜，主要用来打游戏和看剧，有什么性价比高的款式吗？
```

- 如果你已经有 `train_dataset.jsonl` / `test_dataset.jsonl`，可以直接用仓库里的脚本生成输入文件：

```bash
python generate_prompts.py
```

会在根目录生成：

- `train_input_prompts.txt`
- `test_input_prompts.txt`

#### 3. 运行 DeepSeek 爬虫

在项目根目录执行（单进程）：

```bash
python MCPfiles/deepseek_chat_scraper.py
```

- 脚本会自动扫描所有 `*_input_prompts.txt`，按文件名中的前缀当作任务名（如 `test_input_prompts.txt` → 任务名 `test`）。
- **首次运行需要手动登录**：
  - 会弹出一个新的 Camoufox 浏览器窗口。
  - 请在**这个新窗口**里登录 `chat.deepseek.com`，直到看到聊天输入框。
  - 脚本会自动检测登录完成并继续执行。
- 登录成功后，脚本会在每条问题前自动“新建对话”，发送问题并抓取最终回答和联网搜索结果。

- 如需 **多进程并行加速**，可以通过分片参数让多个进程同时跑不同子集的 prompts，例如开启 5 个进程：

```bash
python MCPfiles/deepseek_chat_scraper.py --shard-index 0 --shard-count 5
python MCPfiles/deepseek_chat_scraper.py --shard-index 1 --shard-count 5
python MCPfiles/deepseek_chat_scraper.py --shard-index 2 --shard-count 5
python MCPfiles/deepseek_chat_scraper.py --shard-index 3 --shard-count 5
python MCPfiles/deepseek_chat_scraper.py --shard-index 4 --shard-count 5
```

其中：`--shard-count` 是总分片数，`--shard-index` 是当前进程负责的分片编号（0 开始）。每个进程只会处理自己那一份 prompts，避免重复；多次运行时，只会补充 `status == "ok"` 之外的样本。

- 也可以让脚本自己 fork 出多个子进程并发跑（推荐，命令更短）：

```bash
python MCPfiles/deepseek_chat_scraper.py --spawn-workers 5
```

其中 `--spawn-workers 5` 表示由主进程自动启动 5 个子进程，内部自动分配 `--shard-index` / `--shard-count`，每个子进程处理不同子集的 prompts。

#### 4. 运行 Doubao 爬虫

在项目根目录执行（单进程）：

```bash
python MCPfiles/doubao_chat_scraper.py
```

行为与 DeepSeek 类似：

- 自动遍历 `*_input_prompts.txt` 中的每一行问题。
- **首次运行同样需要手动登录**：
  - 新的 Camoufox 窗口中登录 `www.doubao.com`，进入聊天界面即可。
- 每条问题前脚本会跳回 `https://www.doubao.com/chat/` 作为“新对话”，发送问题并抓取回答及「参考 X 篇资料」里的网页信息（如果有）。

- Doubao 同样支持分片 / 多进程并行，参数含义与 DeepSeek 完全一致：

```bash
# 单进程（默认）
python MCPfiles/doubao_chat_scraper.py

# 手动开 3 个分片进程
python MCPfiles/doubao_chat_scraper.py --shard-index 0 --shard-count 3
python MCPfiles/doubao_chat_scraper.py --shard-index 1 --shard-count 3
python MCPfiles/doubao_chat_scraper.py --shard-index 2 --shard-count 3

# 让脚本自己 fork 出 3 个子进程 （目前还不稳定，可能会卡死）
python MCPfiles/doubao_chat_scraper.py --spawn-workers 3
```

#### 5. 输出文件位置与格式

所有结果保存在 `output/` 目录下，按站点与任务名区分：

- **DeepSeek**
  - `output/deepseek_conversations_<task>.ndjson`  
  - `output/deepseek_conversations_<task>.md`
- **Doubao**
  - `output/doubao_conversations_<task>.ndjson`  
  - `output/doubao_conversations_<task>.md`

其中 `<task>` 就是输入文件名去掉 `_input_prompts.txt` 之后的部分，例如：

- `test_input_prompts.txt` → `deepseek_conversations_test.*` 与 `doubao_conversations_test.*`

`.ndjson` 适合后续程序处理，`.md` 方便人工阅读（包含原始问题、模型回答、是否联网、抓到的网页列表等）。