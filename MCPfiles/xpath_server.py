from mcp.server.fastmcp import FastMCP
import asyncio
from camoufox.async_api import AsyncCamoufox
import time
import os
import json
import re

mcp = FastMCP("Scrapy XPath Generator")
CAMOUFOX_FILE_PATH = (
    r"C:\Users\mzy\Documents\Codes\Scraping-ChatGPT-Web\MCPfiles\Camoufox_template.py"
)


@mcp.tool()
async def fetch_page_content(
    url: str, html_file_path: str, cookies_file_path: str
) -> str:
    global latest_html

    """Fetch page HTML using Camoufox stealth browser.Save the HTML code in the PATH specified."""
    print(f"[DEBUG] Fetching URL: {url}")
    try:
        async with AsyncCamoufox(humanize=True) as browser:
            page = await browser.new_page()
            await page.goto(url)
            time.sleep(10)
            latest_html = await page.content()
            cookies = await page.context.cookies()
            with open(html_file_path, "w", encoding="utf-8") as f:
                f.write(latest_html)
            with open(cookies_file_path, "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=2)
            print("[DEBUG] HTML stored for later use")
            return "HTML fetched and stored successfully."
    except Exception as e:
        print(f"[ERROR] {e}")
        return f"Error fetching page: {str(e)}"


@mcp.tool()
def generate_xpaths(template: str) -> dict:
    """Write XPATH selectors for the requested fields using the downloaded HTML file."""

    if not os.path.exists(HTML_FILE_PATH):
        return {"error": f"No HTML file found. Run fetch_page_content() first."}

    if template.lower() == "plp":
        fields = (
            "product title, product link, product price, product image, product code"
        )
    elif template.lower() == "pdp":
        fields = "product title, product price, product description, product image, product color, product size, product code"
    else:
        return {"error": "Unknown template type"}

    # Return the HTML and requested fields so Cursor can analyze them
    return {
        "message": "Print the XPath expressions for the requested fields using the variable latest_html.",
        "requested_fields": fields,
    }


@mcp.tool()
def write_camoufox_scraper(template: str, url: str, html_file_path: str) -> dict:
    print(
        f"[DEBUG] Writing scraper for template: {template} and URL: {url}. Saving the file in the path {html_file_path}"
    )
    """Reads file Camoufox_template.py and uses it to write a new Camoufox scraper with the requested fields and starting from the url. Save the HTML code in the PATH specified."""
    with open(CAMOUFOX_FILE_PATH, "r", encoding="utf-8") as f:
        latest_html = f.read()
    return {
        "message": "Using this template, write a working scraper with the requested fields and starting URL"
    }


@mcp.tool()
def strip_css(html_input_file: str, html_output_file: str):
    # Read the HTML file
    with open(html_input_file, "r", encoding="utf-8") as file:
        html_content = file.read()

    # Remove style tags and their content
    html_content = re.sub(r"<style[^>]*>.*?</style>", "", html_content, flags=re.DOTALL)

    # Remove CSS emotion attributes
    html_content = re.sub(r'data-emotion="css[^"]*"', "", html_content)

    # Remove class attributes with CSS references
    html_content = re.sub(r'class="css-[^"]*"', "", html_content)

    # Write the cleaned HTML to a new file
    with open(html_output_file, "w", encoding="utf-8") as file:
        file.write(html_content)

    return {f"CSS stripped successfully. New file created: {html_output_file}"}


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport="stdio")
