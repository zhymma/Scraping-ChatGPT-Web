# AI-Cursor-Scraping-Assistant

A powerful tool that leverages Cursor AI and MCP (Model Context Protocol) to easily generate web scrapers for various types of websites. This project helps you quickly analyze websites and generate proper Scrapy or Camoufox scrapers with minimal effort.

## Project Overview

This project contains two main components:

1. **Cursor Rules** - A set of rules that teach Cursor AI how to analyze websites and create different types of Scrapy spiders
2. **MCP Tools** - A collection of Model Context Protocol tools that enhance Cursor's capabilities for web scraping tasks

## Prerequisites

- [Cursor AI](https://cursor.sh/) installed
- Python 3.10+ installed
- Basic knowledge of web scraping concepts

## Installation

Clone this repository to your local machine:

```bash
git clone https://github.com/TheWebScrapingClub/AI-Cursor-Scraping-Assistant.git
cd AI-Cursor-Scraping-Assistant
```

Install the required dependencies:

```bash
pip install mcp camoufox scrapy
```

If you plan to use Camoufox, you'll need to fetch its browser binary:

```bash
python -m camoufox fetch
```

## Setup

### Setting Up MCP Server

The MCP server provides tools that help Cursor AI analyze web pages and generate XPath selectors. To start the MCP server:

1. Navigate to the MCPfiles directory:
   ```bash
   cd MCPfiles
   ```

2. Update the `CAMOUFOX_FILE_PATH` in `xpath_server.py` to point to your local `Camoufox_template.py` file.

3. Start the MCP server:
   ```bash
   python xpath_server.py
   ```

4. In Cursor, connect to the MCP server by configuring it in the settings or using the MCP panel.

### Cursor Rules

The cursor-rules directory contains rules that teach Cursor AI how to analyze websites and create different types of scrapers. These rules are automatically loaded when you open the project in Cursor.

## Detailed Cursor Rules Explanation

The `cursor-rules` directory contains a set of MDC (Markdown Configuration) files that guide Cursor's behavior when creating web scrapers:

### `prerequisites.mdc`
This rule handles initial setup tasks before creating any scrapers:
- Gets the full path of the current project using `pwd`
- Stores the path in context for later use by other rules
- Confirms the execution of preliminary actions before proceeding

### `website-analysis.mdc`
This comprehensive rule guides Cursor through website analysis:
- Identifies the type of Scrapy spider to build (PLP, PDP, etc.)
- Fetches and stores homepage HTML and cookies
- Strips CSS using the MCP tool to simplify HTML analysis
- Checks cookies for anti-bot protection (Akamai, Datadome, PerimeterX, etc.)
- For PLP scrapers: fetches category pages, analyzes structure, looks for JSON data
- For PDP scrapers: fetches product pages, analyzes structure, looks for JSON data
- Detects schema.org markup and modern frameworks like Next.js

### `scrapy-step-by-step-process.mdc`
This rule provides the execution flow for creating scrapers:
- Outlines the sequence of steps to follow
- References other rule files in the correct order
- Ensures prerequisite actions are completed before scraper creation
- Guides Cursor to analyze the website before generating code

### `scrapy.mdc`
This extensive rule contains Scrapy best practices:
- Defines recommended code organization and directory structure
- Details file naming conventions and module organization
- Provides component architecture guidelines
- Offers strategies for code splitting and reuse
- Includes performance optimization recommendations
- Covers security practices, error handling, and logging
- Provides specific syntax examples and code snippets

### `scraper-models.mdc`
This rule defines the different types of scrapers that can be created:
- **E-commerce PLP**: Details the data structure, field definitions, and implementation steps
- **E-commerce PDP**: Details the data structure, field definitions, and implementation steps
- Field mapping guidelines for all scraper types
- Step-by-step instructions for creating each type of scraper
- Default settings recommendations
- Anti-bot countermeasures for different protection systems

## Usage

Here's how to use the AI-Cursor-Scraping-Assistant:

1. Open the project in Cursor AI
2. Make sure the MCP server is running
3. Ask Cursor to create a scraper with a prompt like:
   ```
   Write an e-commerce PLP scraper for the website gucci.com
   ```

Cursor will then:
1. Analyze the website structure
2. Check for anti-bot protection
3. Extract the relevant HTML elements
4. Generate a complete Scrapy spider based on the website type

## Available Scraper Types

You can request different types of scrapers:

- **E-commerce PLP (Product Listing Page)** - Scrapes product catalogs/category pages
- **E-commerce PDP (Product Detail Page)** - Scrapes detailed product information

For example:
```
Write an e-commerce PDP scraper for nike.com
```

## Advanced Usage

### Camoufox Integration

The project includes a Camoufox template for creating stealth scrapers that can bypass certain anti-bot measures. The MCP tools help you:

1. Fetch page content using Camoufox
2. Generate XPath selectors for the desired elements
3. Create a complete Camoufox scraper based on the template

### Chatbox Conversation Scrapers

#### Kimi (moonshot.cn)

A ready-to-run Camoufox scraper for Kimi is provided at `MCPfiles/kimi_moonshot_chat_scraper.py`. It:
- Reads prompts from `*_input_prompts.txt` files (one prompt per line)
- Supports multi-task workflows (task1, task2, etc.)
- Waits for manual login
- Sends each prompt to Kimi and captures the final response and citations
- Extracts web search results if used
- Writes structured records to `output/kimi_conversations_<task>.ndjson` and a readable log to `output/kimi_conversations_<task>.md`

Run:

```bash
python MCPfiles/kimi_moonshot_chat_scraper.py
```

#### DeepSeek (chat.deepseek.com)

A Camoufox scraper for DeepSeek is provided at `MCPfiles/deepseek_chat_scraper.py`. It:
- Based on the Kimi scraper template with generic selectors
- Reads prompts from `*_input_prompts.txt` files (one prompt per line)
- Supports multi-task workflows and skip processed prompts
- Waits for manual login (up to 5 minutes)
- Creates a new conversation for each prompt
- Captures streaming responses with citations
- Writes structured records to `output/deepseek_conversations_<task>.ndjson` and `output/deepseek_conversations_<task>.md`

Run:

```bash
python MCPfiles/deepseek_chat_scraper.py
```

**Note**: You may need to adjust the selectors in `deepseek_chat_scraper.py` after inspecting the actual DeepSeek UI. See `MCPfiles/DEEPSEEK_README.md` for detailed instructions.

#### Doubao (www.doubao.com)

A Camoufox scraper for Doubao is provided at `MCPfiles/doubao_chat_scraper.py`. It:
- Is based on the Kimi/DeepSeek scraper template with Doubao-specific selectors
- Reads prompts from `*_input_prompts.txt` files (one prompt per line)
- Supports multi-task workflows and skips already processed prompts
- Waits for manual login (up to 5 minutes)
- Tries to start a fresh conversation for each prompt (best-effort)
- Captures streaming responses and, when present, web search references opened via the “参考 X 篇资料” side panel
- Writes structured records to `output/doubao_conversations_<task>.ndjson` and `output/doubao_conversations_<task>.md`

Run:

```bash
python MCPfiles/doubao_chat_scraper.py
```

Notes:
- Doubao automatically decides when to perform online search; there is no manual “online mode” toggle.
- The `mode_online` field in the output is set to `"true"` when web search references were detected for that answer, otherwise `"false"`.

#### Common Features

Both scrapers include:
- Persistent session management (cookies + storage)
- Automatic prompt reuse detection (skip already processed)
- Crash-resistant design (saves after each prompt)
- Human-like delays between actions
- Automatic conversation ID extraction
- Language detection (Chinese/English)
- Response latency measurement

Notes:
- Scripts use persistent profile directories at `.camoufox_profile/<site>` to keep your session
- If login is not detected within timeout, scripts exit; log in and rerun
- Selectors are configurable at the top of each script in case the UI changes

### Custom Scrapers

You can extend the functionality by adding new scraper types to the cursor-rules files. The modular design allows for easy customization.

## Project Structure

```
AI-Cursor-Scraping-Assistant/
├── MCPfiles/
│   ├── xpath_server.py     # MCP server with web scraping tools
│   └── Camoufox_template.py # Template for Camoufox scrapers
├── cursor-rules/
│   ├── website-analysis.mdc    # Rules for analyzing websites
│   ├── scrapy.mdc              # Best practices for Scrapy
│   ├── scrapy-step-by-step-process.mdc # Guide for creating scrapers
│   ├── scraper-models.mdc      # Templates for different scraper types
│   └── prerequisites.mdc       # Setup requirements
└── README.md
```

## TODO: Future Enhancements

The following features are planned for future development:

### Proxy Integration
- Add proxy support when requested by the operator
- Implement proxy rotation strategies
- Support for different proxy providers
- Handle proxy authentication
- Integrate with popular proxy services

### Improved XPath Generation and Validation
- Add validation mechanisms for generated XPath selectors
- Implement feedback loop for selector refinement
- Control flow management for reworking selectors
- Auto-correction of problematic selectors
- Handle edge cases like dynamic content and AJAX loading

### Other Planned Features
- Support for more scraper types (news sites, social media, etc.)
- Integration with additional anti-bot bypass techniques
- Enhanced JSON extraction capabilities
- Support for more complex navigation patterns
- Multi-page scraping optimizations

## References

This project is based on articles from The Web Scraping Club:

- [Claude & Cursor AI Scraping Assistant](https://substack.thewebscraping.club/p/claude-cursor-ai-scraping-assistant)
- [Cursor MCP Web Scraping Assistant](https://substack.thewebscraping.club/p/cursor-mcp-web-scraping-assistant)

For more information on web scraping techniques and best practices, visit [The Web Scraping Club](https://thewebscrapingclub.com).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 