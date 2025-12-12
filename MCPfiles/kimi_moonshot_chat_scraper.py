#!/usr/bin/env python
from camoufox.sync_api import Camoufox
from scrapy.http import HtmlResponse
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import time
import os
import json
import random
from screeninfo import get_monitors


KIMI_HOME_URL = "https://kimi.moonshot.cn/chat"
USER_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), ".camoufox_profile", "kimi"
)
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
SESSION_COOKIES_FILE = os.path.join(os.path.dirname(__file__), "kimi_cookies.json")
SESSION_STORAGE_FILE = os.path.join(os.path.dirname(__file__), "kimi_storage.json")

# Tunable selectors. Adjust if Kimi UI updates. Prefer stable roles/labels over CSS classes.
CHAT_INPUT_SELECTORS: List[str] = [
    "div.chat-content-container div[role='textbox']",
    'div[role="textbox"]',
    'div[contenteditable="true"]',
    "textarea",
]
SEND_BUTTON_SELECTORS: List[str] = [
    'button[aria-label*="发送"]',
    'button[aria-label*="Send"]',
    'button[data-testid="send"]',
    'button:has(svg[aria-label*="Send"])',
]
# Assistant message container; we fallback to "last visible rich content block".
ASSISTANT_MESSAGE_SELECTORS: List[str] = [
    '[data-role="assistant"]',
    'div[class*="assistant"]',
    '[data-testid="assistant-message"]',
]
# Within assistant message, anchors are used as citations/sources.
CITATION_LINK_SELECTOR = "a[href]"

# Kimi-specific send/stop button structure shared by you
SEND_BUTTON_ROOT = "div.send-button"
SEND_BUTTON_CONTAINER_DISABLED = "div.send-button-container.disabled"
STOP_ICON_SELECTOR = 'div.send-button svg[name="stop"]'
SEND_ICON_SELECTOR = 'div.send-button svg[name="Send"]'


def ensure_dirs() -> None:
    if not os.path.exists(USER_DATA_DIR):
        os.makedirs(USER_DATA_DIR, exist_ok=True)
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    # MCPfiles already exists; no need to create for session files


def read_prompts(path: str) -> List[str]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines()]
    return [p for p in lines if p]


def pick_first_visible(page, selectors: List[str]):
    for selector in selectors:
        loc = page.locator(selector)
        try:
            if loc.count() > 0:
                first = loc.first
                if first.is_visible():
                    return first
        except Exception:
            continue
    return None


def is_chat_ui_ready(page) -> bool:
    """
    Returns True only when the authenticated chat UI is visible,
    not just any textbox on the login screen.
    """
    try:
        # Ensure we're on the CN chat path
        current_url = page.url or ""
        if "moonshot.cn" not in current_url:
            return False
        if "/chat" not in current_url:
            return False

        chat_container = page.locator("div.chat-content-container")
        if chat_container.count() == 0 or not chat_container.first.is_visible():
            return False
        # Require a textbox within the chat container
        chat_textbox = chat_container.locator(
            "div[role='textbox'], div[contenteditable='true']"
        )
        if chat_textbox.count() == 0:
            return False
        # Require the send button area present (may be disabled but should exist)
        send_root = page.locator(SEND_BUTTON_ROOT)
        if send_root.count() == 0:
            return False
        return True
    except Exception:
        return False


def wait_for_login(page, timeout_seconds: int = 300) -> bool:
    print("[INFO] Please login within 30 seconds...")
    # Wait 30 seconds for user to login
    time.sleep(15)

    print("[INFO] Checking for chat input box...")
    start = time.time()
    remaining = timeout_seconds - 30
    while time.time() - start < remaining:
        # Simple check: just look for any visible textbox
        elem = pick_first_visible(page, CHAT_INPUT_SELECTORS)
        if elem:
            print("[INFO] Chat input detected, ready to send prompts")
            return True
        time.sleep(1)

    print("[WARN] Chat input not found after timeout")
    return False


def get_conversation_id_from_url(url: str) -> str:
    # Kimi often uses /chat/<id> or query params; return the last non-empty path segment.
    try:
        path = url.split("://", 1)[-1].split("/", 1)[-1]
        parts = [p for p in path.split("?")[0].split("/") if p]
        if parts:
            return parts[-1]
    except Exception:
        pass
    return ""


def detect_language(text: str) -> str:
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff":
            return "zh"
    return "en"


def load_cookies_into_context(page, cookies_path: str) -> None:
    try:
        if os.path.exists(cookies_path):
            with open(cookies_path, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            if isinstance(cookies, list) and len(cookies) > 0:
                page.context.add_cookies(cookies)
    except Exception:
        pass


def save_cookies_from_context(page, cookies_path: str) -> None:
    try:
        cookies = page.context.cookies()
        with open(cookies_path, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_storage_from_file(page, storage_path: str) -> None:
    try:
        if not os.path.exists(storage_path):
            return
        with open(storage_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        local_items = data.get("localStorage", {})
        session_items = data.get("sessionStorage", {})
        if local_items:
            page.evaluate(
                """(items) => { for (const [k,v] of Object.entries(items)) localStorage.setItem(k, v) }""",
                local_items,
            )
        if session_items:
            page.evaluate(
                """(items) => { for (const [k,v] of Object.entries(items)) sessionStorage.setItem(k, v) }""",
                session_items,
            )
    except Exception:
        pass


def save_storage_to_file(page, storage_path: str) -> None:
    try:
        ls = page.evaluate("""() => Object.fromEntries(Object.entries(localStorage))""")
        ss = page.evaluate(
            """() => Object.fromEntries(Object.entries(sessionStorage))"""
        )
        with open(storage_path, "w", encoding="utf-8") as f:
            json.dump(
                {"localStorage": ls, "sessionStorage": ss},
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception:
        pass


def is_generating(page) -> bool:
    try:
        icon = page.locator(STOP_ICON_SELECTOR)
        return icon.count() > 0 and icon.first.is_visible()
    except Exception:
        return False


def is_send_disabled(page) -> bool:
    # Disabled when container has 'disabled' class
    try:
        cont = page.locator(SEND_BUTTON_CONTAINER_DISABLED)
        return cont.count() > 0 and cont.first.is_visible()
    except Exception:
        return False


def is_send_icon_visible(page) -> bool:
    try:
        icon = page.locator(SEND_ICON_SELECTOR)
        return icon.count() > 0 and icon.first.is_visible()
    except Exception:
        return False


def html_to_markdown(html: str) -> str:
    """
    Simple HTML to Markdown converter focused on preserving inline citations.
    Handles common tags: <a>, <br>, <p>, <div>, <ol>, <ul>, <li>, etc.
    """
    import re

    # Remove script/style tags
    html = re.sub(
        r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE
    )

    # Convert <a href="...">text</a> to [site_name](url) format
    def replace_link(match):
        full_tag = match.group(0)
        # Extract href
        href_match = re.search(r'href=["\']([^"\']+)["\']', full_tag)
        href = href_match.group(1) if href_match else ""
        # Extract data-site-name
        site_match = re.search(r'data-site-name=["\']([^"\']+)["\']', full_tag)
        site_name = site_match.group(1) if site_match else ""
        # Get inner text
        inner = re.sub(r"<[^>]+>", "", match.group(1)).strip()

        if not href:
            return inner if inner else ""
        # Prefer site_name, fallback to inner text, ultimate fallback to "source"
        display = site_name or inner or "source"
        return f"[{display}]({href})"

    # Also handle <div class="rag-tag" data-site-name="..."> (unconverted citations)
    def replace_div_citation(match):
        full_tag = match.group(0)
        site_match = re.search(r'data-site-name=["\']([^"\']+)["\']', full_tag)
        site_name = site_match.group(1) if site_match else "引用"
        # Return just the site name in brackets (no URL available)
        return f"[{site_name}]"

    # Match <a ...>...</a>
    html = re.sub(
        r"<a[^>]*>(.*?)</a>", replace_link, html, flags=re.DOTALL | re.IGNORECASE
    )

    # Match <div class="rag-tag"...>...</div> for unconverted citations
    html = re.sub(
        r'<div[^>]*class=["\'][^"\']*rag-tag[^"\']*["\'][^>]*>.*?</div>',
        replace_div_citation,
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Convert <br> to newline
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)

    # Convert </p>, </div> to double newline for paragraphs
    html = re.sub(r"</(p|div)>", "\n\n", html, flags=re.IGNORECASE)

    # Convert <li> to "- " for lists
    html = re.sub(r"<li[^>]*>", "\n- ", html, flags=re.IGNORECASE)
    html = re.sub(r"</li>", "", html, flags=re.IGNORECASE)

    # Convert ordered lists
    html = re.sub(r"<ol[^>]*>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</ol>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<ul[^>]*>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</ul>", "\n", html, flags=re.IGNORECASE)

    # Convert headings
    for i in range(6, 0, -1):
        html = re.sub(
            f"<h{i}[^>]*>(.*?)</h{i}>",
            "#" * i + r" \1\n\n",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )

    # Remove all other tags
    html = re.sub(r"<[^>]+>", "", html)

    # Decode HTML entities
    html = html.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    html = html.replace("&nbsp;", " ").replace("&quot;", '"').replace("&#39;", "'")

    # Clean up multiple newlines
    html = re.sub(r"\n{3,}", "\n\n", html)
    html = re.sub(r" +", " ", html)

    return html.strip()


def hover_all_citations_and_extract_markdown(page, container) -> Tuple[str, List[str]]:
    """
    Hover all rag-tag elements to trigger div->a transformation,
    then extract the full response as markdown with inline citations preserved.
    Returns (markdown_text_with_links, list_of_citation_hrefs).
    """
    citations_hrefs = []

    try:
        # Find all rag-tag elements
        rag_tags = container.locator(".rag-tag")
        initial_count = rag_tags.count()
        print(f"[DEBUG] Found {initial_count} rag-tag elements to process")

        # Use JavaScript to batch trigger events - much faster than physical hover!
        print("[DEBUG] Triggering hover events via JavaScript...")

        for round_num in range(2):  # Do 2 rounds to catch any that didn't convert
            if round_num > 0:
                print(f"[DEBUG] Round {round_num + 1}: Retrying unconverted tags...")

            page.evaluate(
                """
                (container) => {
                    const tags = container.querySelectorAll('.rag-tag');
                    console.log(`Processing ${tags.length} rag-tag elements...`);
                    
                    tags.forEach((tag, index) => {
                        // Scroll into view
                        tag.scrollIntoView({block: 'center', behavior: 'instant'});
                        
                        // Trigger mouseover events
                        const mouseoverEvent = new MouseEvent('mouseover', {
                            view: window,
                            bubbles: true,
                            cancelable: true,
                            clientX: tag.getBoundingClientRect().left + 5,
                            clientY: tag.getBoundingClientRect().top + 5
                        });
                        tag.dispatchEvent(mouseoverEvent);
                        
                        const mouseenterEvent = new MouseEvent('mouseenter', {
                            view: window,
                            bubbles: true,
                            cancelable: true
                        });
                        tag.dispatchEvent(mouseenterEvent);
                        
                        // Small delay between each tag (simulate real user)
                        // Note: This is synchronous delay in JS, not blocking Python
                    });
                    
                    // Trigger mouseout on all to dismiss any tooltips
                    setTimeout(() => {
                        tags.forEach(tag => {
                            const mouseoutEvent = new MouseEvent('mouseout', {
                                view: window,
                                bubbles: true,
                                cancelable: true
                            });
                            tag.dispatchEvent(mouseoutEvent);
                        });
                    }, 100);
                }
            """,
                container.element_handle(),
            )

            # Wait for API calls to complete and DOM to update
            wait_time = 0.5 if round_num == 0 else 0.7
            print(f"[DEBUG] Waiting {wait_time}s for API calls and DOM updates...")
            time.sleep(wait_time)

        # Now extract the HTML from markdown-container
        md_container = container.locator(
            "div.markdown-container, .markdown-container .markdown"
        )
        if md_container.count() == 0:
            md_container = container.locator("div.segment-content-box")

        if md_container.count() > 0:
            html_content = md_container.first.inner_html()

            # Convert HTML to markdown with inline links
            markdown_text = html_to_markdown(html_content)

            # Extract all hrefs for citations list
            a_tags = md_container.locator("a[href]")
            citation_count = a_tags.count()

            # Also count remaining div.rag-tag elements
            remaining_divs = md_container.locator("div.rag-tag").count()
            print(
                f"[DEBUG] After hover: {citation_count} <a> tags, {remaining_divs} unconverted <div> tags"
            )

            for i in range(citation_count):
                try:
                    href = a_tags.nth(i).get_attribute("href")
                    if href:
                        citations_hrefs.append(href)
                except Exception:
                    continue

            return markdown_text, list(dict.fromkeys(citations_hrefs))
        else:
            return container.inner_text().strip(), []
    except Exception as e:
        print(f"[WARN] Failed to extract markdown with citations: {e}")
        try:
            return container.inner_text().strip(), []
        except Exception:
            return "", []


def wait_for_stream_completion_and_get_text_v2(
    page, assistant_message_count_before: int, timeout_seconds: int = 300
) -> Tuple[str, List[str]]:
    start = time.time()
    last_text = ""
    stable_ticks = 0
    last_change_time = start
    max_stream_seconds = max(60, min(240, int(timeout_seconds * 0.8)))
    required_stable_ticks = 3  # ~1.2s with 0.4s sleep

    def get_latest_assistant():
        # Kimi-specific: last assistant item inside chat list
        try:
            chat_list = page.locator("div.chat-content-list")
            if chat_list.count() > 0:
                asst_items = chat_list.locator(
                    "div.chat-content-item.chat-content-item-assistant"
                )
                if asst_items.count() > 0:
                    return asst_items.last
        except Exception:
            pass
        # Fallback to generic selectors
        for selector in ASSISTANT_MESSAGE_SELECTORS:
            loc = page.locator(selector)
            try:
                if loc.count() > assistant_message_count_before:
                    return loc.nth(loc.count() - 1)
            except Exception:
                continue
        return page.locator(
            "div:has-text('Kimi'), div.markdown-body, article, section"
        ).last

    def extract_assistant_text(container) -> str:
        # Prefer markdown content
        try:
            md = container.locator(
                "div.markdown-container, .markdown-container .markdown"
            )
            if md.count() > 0 and md.first.is_visible():
                txt = md.first.inner_text().strip()
                if txt:
                    return txt
        except Exception:
            pass
        # Then try segment content box
        try:
            seg = container.locator("div.segment-content-box")
            if seg.count() > 0 and seg.first.is_visible():
                txt = seg.first.inner_text().strip()
                if txt:
                    return txt
        except Exception:
            pass
        # Fallback to container text
        try:
            return (container.inner_text() or "").strip()
        except Exception:
            return ""

    # Wait until generation starts
    start_phase_deadline = time.time() + min(30, timeout_seconds * 0.2)
    while time.time() < start_phase_deadline:
        if is_generating(page):
            break
        try:
            container = get_latest_assistant()
            text_now = extract_assistant_text(container) if container else ""
            if text_now and len(text_now) > len(last_text):
                last_text = text_now
                last_change_time = time.time()
                break
        except Exception:
            pass
        time.sleep(0.25)

    # Wait for completion
    while time.time() - start < timeout_seconds:
        container = get_latest_assistant()
        try:
            text = extract_assistant_text(container) if container else ""
        except Exception:
            text = ""
        if text and text == last_text:
            stable_ticks += 1
        else:
            stable_ticks = 0
            last_text = text
            if text:
                last_change_time = time.time()

        if is_generating(page) and (time.time() - start > max_stream_seconds):
            try:
                page.locator(STOP_ICON_SELECTOR).first.click()
            except Exception:
                pass

        if (
            (not is_generating(page))
            and is_send_icon_visible(page)
            and (stable_ticks >= required_stable_ticks)
            and len(text) > 0
        ):
            break

        if (not is_generating(page)) and (time.time() - last_change_time > 10):
            break

        time.sleep(0.4)

    citations: List[str] = []
    try:
        container = (
            get_latest_assistant()
            or pick_first_visible(page, ASSISTANT_MESSAGE_SELECTORS)
            or page.locator("article, section, div.markdown-body").last
        )
        for i in range(container.locator(CITATION_LINK_SELECTOR).count()):
            try:
                href = (
                    container.locator(CITATION_LINK_SELECTOR)
                    .nth(i)
                    .get_attribute("href")
                )
                if href:
                    citations.append(href)
            except Exception:
                continue
    except Exception:
        pass
    return last_text, list(dict.fromkeys(citations))


def extract_web_search_results_if_any(
    page, assistant_message_count_before: int
) -> List[Dict[str, str]]:
    """
    Detect Kimi web-search toolcall in the latest assistant message, open the side panel,
    and extract the list of result URLs with basic text. Additionally, try to fetch page
    text for richer Markdown output.
    """
    results: List[Dict[str, str]] = []

    # Locate last assistant message in chat list
    def get_latest_assistant():
        try:
            chat_list = page.locator("div.chat-content-list")
            if chat_list.count() > 0:
                asst_items = chat_list.locator(
                    "div.chat-content-item.chat-content-item-assistant"
                )
                if asst_items.count() > 0:
                    return asst_items.last
        except Exception:
            pass
        # Fallbacks
        generic = page.locator(
            "div[data-role='assistant'], [data-testid='assistant-message']"
        )
        if generic.count() > assistant_message_count_before:
            return generic.nth(generic.count() - 1)
        return None

    container = get_latest_assistant()
    if not container:
        return results

    # Check if toolcall container-block exists (web search used)
    try:
        tool_block = container.locator("div.segment-content-box div.container-block")
        if tool_block.count() == 0:
            return results  # no web search
    except Exception:
        return results

    side_panel = page.locator("div.side-console-container.normal")
    # If panel already visible, skip clicking; else try click then wait
    try:
        panel_ready = side_panel.count() > 0 and side_panel.first.is_visible()
    except Exception:
        panel_ready = False

    if not panel_ready:
        try:
            clickable = container.locator(
                "div.segment-content-box div.container-block > div > div"
            ).first
            if clickable and clickable.is_visible():
                clickable.click()
        except Exception:
            pass

        start_wait = time.time()
        while time.time() - start_wait < 10:
            try:
                if side_panel.count() > 0 and side_panel.first.is_visible():
                    break
            except Exception:
                pass
            time.sleep(0.25)

    if side_panel.count() == 0:
        return results

    # Extract search result entries
    try:
        sites = side_panel.locator("div.side-console .sites a.site")
        num = sites.count()
        for i in range(num):
            node = sites.nth(i)
            try:
                href = node.get_attribute("href") or ""
                name = ""
                title = ""
                snippet = ""
                try:
                    name = node.locator(".name").first.inner_text().strip()
                except Exception:
                    pass
                try:
                    title = node.locator("p.title").first.inner_text().strip()
                except Exception:
                    pass
                try:
                    snippet = node.locator("p.snippet").first.inner_text().strip()
                except Exception:
                    pass

                # Optionally visit the page to extract main text
                page_text = ""
                if href:
                    try:
                        newp = page.context.new_page()
                        newp.goto(href, timeout=20000)
                        try:
                            newp.wait_for_load_state()
                        except Exception:
                            pass
                        # Prefer article/main/body text
                        text_locators = [
                            "article",
                            "main",
                            "div#content, div[id*='content']",
                            "body",
                        ]
                        for sel in text_locators:
                            try:
                                loc = newp.locator(sel)
                                if loc.count() > 0 and loc.first.is_visible():
                                    page_text = (loc.first.inner_text() or "").strip()
                                    if page_text:
                                        break
                            except Exception:
                                continue
                    except Exception:
                        pass
                    finally:
                        try:
                            newp.close()
                        except Exception:
                            pass

                results.append(
                    {
                        "href": href,
                        "name": name,
                        "title": title,
                        "snippet": snippet,
                        "page_text": page_text,
                    }
                )
            except Exception:
                continue
    except Exception:
        pass

    return results


def wait_for_stream_completion_and_get_text(
    page, assistant_message_count_before: int, timeout_seconds: int = 300
) -> Tuple[str, List[str]]:
    start = time.time()
    last_text = ""
    stable_ticks = 0

    def get_latest_assistant():
        # Get the last assistant container if present, else fallback to last content block
        for selector in ASSISTANT_MESSAGE_SELECTORS:
            loc = page.locator(selector)
            try:
                if loc.count() > assistant_message_count_before:
                    return loc.nth(loc.count() - 1)
            except Exception:
                continue
        # Fallback: last message-like block (risk of mixing roles)
        fallback = page.locator(
            "div:has-text('Kimi'), div.markdown-body, article, section"
        ).last
        return fallback

    # Wait until generation starts (stop icon visible OR content starts growing)
    start_phase_deadline = time.time() + min(30, timeout_seconds * 0.2)
    while time.time() < start_phase_deadline:
        if is_generating(page):
            break
        # Content growth fallback
        try:
            container = get_latest_assistant()
            text_now = container.inner_text().strip() if container else ""
            if text_now and len(text_now) > len(last_text):
                last_text = text_now
                break
        except Exception:
            pass
        time.sleep(0.25)

    # Now wait for completion: stop icon disappears, plus short text stabilization)
    while time.time() - start < timeout_seconds:
        container = get_latest_assistant()
        try:
            text = container.inner_text().strip() if container else ""
        except Exception:
            text = ""
        if text and text == last_text:
            stable_ticks += 1
        else:
            stable_ticks = 0
            last_text = text
        # Completion criteria: generating stopped and text stabilized briefly
        if (not is_generating(page)) and (stable_ticks >= 3) and len(text) > 0:
            break
        time.sleep(0.4)

    # Extract citations
    citations: List[str] = []
    try:
        container = (
            pick_first_visible(page, ASSISTANT_MESSAGE_SELECTORS)
            or page.locator("article, section, div.markdown-body").last
        )
        for i in range(container.locator(CITATION_LINK_SELECTOR).count()):
            try:
                href = (
                    container.locator(CITATION_LINK_SELECTOR)
                    .nth(i)
                    .get_attribute("href")
                )
                if href:
                    citations.append(href)
            except Exception:
                continue
    except Exception:
        pass
    return last_text, list(dict.fromkeys(citations))


def send_prompt_and_collect(
    page, prompt_text: str, website_name: str = "KIMI"
) -> Dict[str, Optional[str]]:
    input_box = pick_first_visible(page, CHAT_INPUT_SELECTORS)
    if not input_box:
        raise RuntimeError(
            "Chat input not found. Please ensure you are logged in and on the chat page."
        )

    # Count assistant messages before sending
    assistant_before = 0
    for selector in ASSISTANT_MESSAGE_SELECTORS:
        try:
            assistant_before = max(assistant_before, page.locator(selector).count())
        except Exception:
            continue

    # Input prompt and send
    input_box.click()
    page.keyboard.type(prompt_text)
    page.keyboard.press("Enter")

    send_ts = time.time()
    response_text, citations = wait_for_stream_completion_and_get_text_v2(
        page, assistant_before
    )
    latency_ms = int((time.time() - send_ts) * 1000)

    url = page.url
    conversation_id = get_conversation_id_from_url(url)

    # Extract response with inline citations by hovering and converting HTML to markdown
    markdown_with_citations = response_text  # fallback
    inline_citation_hrefs = []
    try:
        # Get the last assistant container
        chat_list = page.locator("div.chat-content-list")
        if chat_list.count() > 0:
            asst_items = chat_list.locator(
                "div.chat-content-item.chat-content-item-assistant"
            )
            if asst_items.count() > 0:
                last_asst = asst_items.last
                markdown_with_citations, inline_citation_hrefs = (
                    hover_all_citations_and_extract_markdown(page, last_asst)
                )
                print(
                    f"[DEBUG] Extracted markdown with {len(inline_citation_hrefs)} inline citations"
                )
    except Exception as e:
        print(f"[WARN] Failed to extract markdown with citations: {e}")

    # If web search was used, open the side panel and collect sources
    search_results = extract_web_search_results_if_any(page, assistant_before)

    # Extract URLs from search results and inline citations
    search_urls = (
        [r["href"] for r in search_results if r.get("href")] if search_results else []
    )

    # Try to infer model name and online mode from visible toggles
    model_name = ""
    mode_online = ""
    try:
        model_toggle = page.locator(
            '[aria-label*="模型"], [aria-label*="Model"], [data-testid*="model"]'
        ).first
        if model_toggle and model_toggle.is_visible():
            model_name = model_toggle.inner_text().strip()
    except Exception:
        pass
    try:
        online_toggle = page.locator(
            ':is([aria-label*="联网"], [aria-label*="Search"], [aria-pressed])'
        ).first
        if online_toggle and online_toggle.is_visible():
            pressed = online_toggle.get_attribute("aria-pressed")
            mode_online = "true" if pressed == "true" else "false"
    except Exception:
        pass

    item: Dict[str, Optional[str]] = {
        "website_name": website_name,
        "conversation_id": conversation_id,
        "item_url": url,
        "model_name": model_name,
        "mode_online": mode_online,
        "prompt_text": prompt_text,
        "response_text": markdown_with_citations,  # markdown with inline citation links
        "web_search_results": search_results
        or [],  # structured search results with URL, title, snippet, etc.
        "response_language": detect_language(markdown_with_citations),
        "latency_ms": latency_ms,
        "status": "ok" if markdown_with_citations else "empty",
        "error_message": "" if markdown_with_citations else "No response text captured",
    }

    return item


def write_outputs(
    ndjson_path: str, md_path: str, items: List[Dict[str, Optional[str]]]
) -> None:
    if not items:
        return

    # Determine write mode: append if files exist, otherwise create new
    ndjson_mode = "a" if os.path.exists(ndjson_path) else "w"
    md_mode = "a" if os.path.exists(md_path) else "w"

    # Write NDJSON (append or create)
    with open(ndjson_path, ndjson_mode, encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

    # Write markdown with full conversation content (append or create)
    with open(md_path, md_mode, encoding="utf-8") as f:
        for it in items:
            conv_id = it.get("conversation_id") or "unknown"
            f.write(f"# Conversation {conv_id}\n\n")
            f.write(f"- **Website**: {it.get('website_name')}\n")
            f.write(f"- **URL**: {it.get('item_url')}\n")
            f.write(f"- **Model**: {it.get('model_name')}\n")
            f.write(f"- **Online Mode**: {it.get('mode_online')}\n")
            f.write(f"- **Language**: {it.get('response_language')}\n")
            f.write(f"- **Latency**: {it.get('latency_ms')} ms\n")

            f.write("## Prompt\n\n")
            f.write((it.get("prompt_text") or "").strip() + "\n\n")

            f.write("## Response\n\n")
            f.write((it.get("response_text") or "").strip() + "\n\n")

            # Write web search results if available
            web_search_results = it.get("web_search_results", [])
            if web_search_results:
                f.write("## Web Search Results\n\n")
                for idx, result in enumerate(web_search_results, 1):
                    title = result.get("title") or result.get("name") or "Search Result"
                    href = result.get("href", "")
                    snippet = result.get("snippet", "")
                    site_name = result.get("name", "")

                    f.write(f"### {idx}. {title}\n\n")
                    if href:
                        f.write(f"- **URL**: {href}\n")
                    if site_name:
                        f.write(f"- **Site**: {site_name}\n")
                    # if snippet:
                    #     f.write(f"- **Snippet**: {snippet}\n")
                    f.write("\n")

            f.write("---\n\n")


def human_think_time(min_s: float = 0.8, max_s: float = 2.2) -> None:
    time.sleep(random.uniform(min_s, max_s))


def click_new_conversation(page) -> bool:
    """
    Click the 'New Conversation' button to start a fresh conversation.
    Returns True if successful, False otherwise.
    """
    try:
        print("[INFO] Clicking 'New Conversation' button...")

        # Multiple selectors to find the new conversation button
        new_conv_selectors = [
            'div.action-label:has(svg[name="AddConversation"])',
            'svg[name="AddConversation"]',
            'button:has-text("新建会话")',
            'div:has-text("新建会话")',
        ]

        clicked = False
        for selector in new_conv_selectors:
            try:
                btn = page.locator(selector).first
                if btn.is_visible(timeout=5000):
                    btn.click(timeout=5000)
                    clicked = True
                    print("[INFO] New conversation button clicked")
                    break
            except Exception:
                continue

        if not clicked:
            print("[WARN] Could not find new conversation button, continuing anyway...")
            return False

        # Wait for the new conversation to load
        time.sleep(1.0)

        # Wait for chat input to be ready
        for selector in CHAT_INPUT_SELECTORS:
            try:
                elem = page.locator(selector).first
                if elem.is_visible(timeout=5000):
                    print("[INFO] New conversation ready")
                    return True
            except Exception:
                continue

        print("[WARN] New conversation may not be fully loaded")
        return True

    except Exception as e:
        print(f"[WARN] Failed to start new conversation: {e}")
        return False


def extract_task_name(input_file: str) -> str:
    """Extract task name from input file name.
    e.g., 'task1_input_prompts.txt' -> 'task1'
    """
    basename = os.path.basename(input_file)
    # Remove '_input_prompts.txt' or '.txt' suffix
    if basename.endswith("_input_prompts.txt"):
        return basename[: -len("_input_prompts.txt")]
    elif basename.endswith(".txt"):
        return basename[:-4]
    else:
        return basename


def load_processed_prompts(ndjson_path: str) -> set:
    """Load already processed prompts from existing NDJSON file.
    Returns a set of prompt_text that have been processed.
    """
    if not os.path.exists(ndjson_path):
        return set()

    processed = set()
    try:
        with open(ndjson_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        item = json.loads(line)
                        prompt_text = item.get("prompt_text", "").strip()
                        if prompt_text and item["status"] != "error":
                            processed.add(prompt_text)
                    except json.JSONDecodeError:
                        continue
        print(f"[INFO] Found {len(processed)} already processed prompts")
        return processed
    except Exception as e:
        print(f"[WARN] Failed to load processed prompts: {e}")
        return set()


def main() -> None:
    ensure_dirs()

    # Find all input files matching pattern *_input_prompts.txt
    project_root = os.path.dirname(os.path.dirname(__file__))
    import glob

    input_files = glob.glob(os.path.join(project_root, "*_input_prompts.txt"))

    if not input_files:
        print("[WARN] No input files found matching pattern '*_input_prompts.txt'")
        print("[INFO] Looking for 'input_prompts.txt' as fallback...")
        fallback = os.path.join(project_root, "input_prompts.txt")
        if os.path.exists(fallback):
            input_files = [fallback]
        else:
            return

    print(
        f"[INFO] Found {len(input_files)} input file(s): {[os.path.basename(f) for f in input_files]}"
    )

    # Process each input file as a separate task
    for input_file in input_files:
        task_name = extract_task_name(input_file)
        print(f"\n{'='*60}")
        print(f"[INFO] Processing task: {task_name}")
        print(f"[INFO] Input file: {input_file}")
        print(f"{'='*60}\n")

        prompts = read_prompts(input_file)
        if not prompts:
            print(f"[WARN] No prompts found in {input_file}, skipping...")
            continue

        # Generate output file names based on task name
        output_ndjson = os.path.join(
            OUTPUT_DIR, f"kimi_conversations_{task_name}.ndjson"
        )
        output_md = os.path.join(OUTPUT_DIR, f"kimi_conversations_{task_name}.md")

        # Load already processed prompts to avoid duplication
        processed_prompts = load_processed_prompts(output_ndjson)

        # Filter out already processed prompts
        new_prompts = [p for p in prompts if p.strip() not in processed_prompts]

        if not new_prompts:
            print(f"[INFO] All prompts in {task_name} have been processed. Skipping...")
            continue

        if len(new_prompts) < len(prompts):
            print(
                f"[INFO] Skipping {len(prompts) - len(new_prompts)} already processed prompts"
            )
            print(f"[INFO] Processing {len(new_prompts)} new prompts")

        process_task(task_name, new_prompts, output_ndjson, output_md)


def process_task(
    task_name: str, prompts: List[str], output_ndjson: str, output_md: str
) -> None:
    """Process a single task with its prompts."""

    with Camoufox(
        humanize=True,
        geoip=False,
        locale="zh-CN",
    ) as browser:
        page = browser.new_page(
            locale="zh-CN",
            extra_http_headers={
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        )

        # Load cookies before navigation (if any)
        load_cookies_into_context(page, SESSION_COOKIES_FILE)

        page.goto(KIMI_HOME_URL)
        page.wait_for_load_state()

        # Restore storage after being on origin, then reload to apply
        load_storage_from_file(page, SESSION_STORAGE_FILE)

        # Force language preference to Chinese in localStorage
        try:
            page.evaluate(
                """() => {
                localStorage.setItem('locale', 'zh-CN');
                localStorage.setItem('language', 'zh');
                localStorage.setItem('kimi-language', 'zh-CN');
            }"""
            )
        except Exception:
            pass

        try:
            page.goto(KIMI_HOME_URL)
            page.wait_for_load_state()
        except Exception:
            pass

        print(
            "[INFO] Waiting for manual login (up to 5 minutes). Once you see the chat input, you're good."
        )
        if not wait_for_login(page, timeout_seconds=300):
            print("[ERROR] Login not detected within timeout. Please login and rerun.")
            return

        # Persist session after successful login
        save_cookies_from_context(page, SESSION_COOKIES_FILE)
        save_storage_to_file(page, SESSION_STORAGE_FILE)

        total_processed = 0
        for idx, prompt in enumerate(prompts):
            print(f"\n[INFO] Processing prompt {idx + 1}/{len(prompts)}")
            try:
                item = send_prompt_and_collect(
                    page, prompt_text=prompt, website_name="KIMI"
                )
            except Exception as e:
                url = page.url
                item = {
                    "website_name": "KIMI",
                    "conversation_id": get_conversation_id_from_url(url),
                    "item_url": url,
                    "session_user": "",
                    "model_name": "",
                    "mode_online": "True",
                    "prompt_text": prompt,
                    "response_text": "",
                    "response_citations": [],
                    "response_language": "",
                    "latency_ms": 0,
                    "status": "error",
                    "error_message": str(e),
                    "message_id": "",
                    "parent_message_id": "",
                    "tokens_prompt": "",
                    "tokens_completion": "",
                    "tokens_total": "",
                }

            # Save immediately after each prompt (防止崩溃丢失数据)
            print(f"[INFO] Saving result {idx + 1}/{len(prompts)}...")
            write_outputs(output_ndjson, output_md, [item])
            total_processed += 1
            print(f"[INFO] ✓ Saved to {os.path.basename(output_ndjson)}")

            # Start a new conversation for the next prompt (except after the last one)
            if idx < len(prompts) - 1:
                human_think_time(0.7, 1.0)
                click_new_conversation(page)
                human_think_time(0.5, 1.0)

        # Save session state at the end
        save_cookies_from_context(page, SESSION_COOKIES_FILE)
        save_storage_to_file(page, SESSION_STORAGE_FILE)

        print(f"\n{'='*60}")
        print(f"[INFO] ✓ Task '{task_name}' completed!")
        print(f"[INFO] Processed {total_processed} prompts")
        print(f"[INFO] Results saved to:")
        print(f"  - {output_ndjson}")
        print(f"  - {output_md}")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
