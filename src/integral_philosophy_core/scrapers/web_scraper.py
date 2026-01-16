#!/usr/bin/env python3
"""
Recursive Web Scraper with JavaScript Processing
Downloads entire websites while preserving structure and links
Converts content to MarkdownTeX format for further processing
"""

import asyncio
import time
import re
import urllib.parse
from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import Set, Dict, List, Optional
import json
import logging

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
import selenium.common.exceptions as sel_exceptions

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class WebScraper:
    """Recursive web scraper with JavaScript processing and MarkdownTeX output"""

    def __init__(
        self, base_url: str, output_dir: str = "scraped_content", delay: float = 1.0
    ):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.output_dir = Path(output_dir)
        self.delay = delay
        self.visited_urls: Set[str] = set()
        self.downloaded_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.driver = None
        self.site_ast = {
            "pages": {},
            "links": {},
            "metadata": {
                "base_url": base_url,
                "domain": self.domain,
                "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_pages": 0,
            },
        }

        # Create output directories
        self.output_dir.mkdir(exist_ok=True)
        (self.output_dir / "pages").mkdir(exist_ok=True)
        (self.output_dir / "assets").mkdir(exist_ok=True)
        (self.output_dir / "meta").mkdir(exist_ok=True)

    def setup_driver(self) -> bool:
        """Initialize Chrome WebDriver with options"""
        try:
            options = Options()
            options.add_argument("--headless")  # Run in headless mode
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument(
                "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            )

            # Enable JavaScript
            options.add_argument("--enable-javascript")

            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(30)
            logger.info("WebDriver initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            return False

    def wait_for_page_load(self, timeout: int = 10) -> bool:
        """Wait for page to fully load including JavaScript"""
        try:
            # Wait for DOM to be ready
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            # Wait for additional JavaScript to execute
            time.sleep(2)

            # Wait for dynamic content if jQuery is present
            try:
                if self.driver.execute_script("return typeof jQuery !== 'undefined'"):
                    WebDriverWait(self.driver, timeout).until(
                        lambda d: d.execute_script("return jQuery.active == 0")
                    )
            except:
                pass

            return True

        except TimeoutException:
            logger.warning(f"Page load timeout for {self.driver.current_url}")
            return False
        except Exception as e:
            logger.warning(f"Error waiting for page load: {e}")
            return False

    def extract_links(self) -> List[str]:
        """Extract all links from current page"""
        links = []

        try:
            # Find all anchor elements
            anchor_elements = self.driver.find_elements(By.TAG_NAME, "a")

            for anchor in anchor_elements:
                try:
                    href = anchor.get_attribute("href")
                    if href and self.is_same_domain(href):
                        # Convert relative URLs to absolute
                        absolute_url = urljoin(self.driver.current_url, href)

                        # Remove fragments and query parameters for uniqueness
                        clean_url = (
                            urlparse(absolute_url)
                            ._replace(fragment="", query="")
                            .geturl()
                        )

                        if clean_url not in self.visited_urls:
                            links.append(absolute_url)

                except Exception as e:
                    logger.debug(f"Error processing link: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error extracting links from {self.driver.current_url}: {e}")

        return links

    def is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain"""
        try:
            parsed = urlparse(url)
            return parsed.netloc == self.domain or parsed.netloc == f"www.{self.domain}"
        except:
            return False

    def extract_content(self) -> Dict:
        """Extract content from current page and convert to MarkdownTeX"""
        try:
            # Execute JavaScript to get page information
            page_info = self.driver.execute_script("""
                return {
                    title: document.title,
                    description: document.querySelector('meta[name="description"]')?.content || '',
                    keywords: document.querySelector('meta[name="keywords"]')?.content || '',
                    language: document.documentElement.lang || 'en',
                    author: document.querySelector('meta[name="author"]')?.content || '',
                    canonical: document.querySelector('link[rel="canonical"]')?.href || '',
                    structure: {
                        headings: Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6')).map(h => ({
                            level: parseInt(h.tagName.substring(1)),
                            text: h.textContent.trim(),
                            id: h.id || ''
                        })),
                        lists: document.querySelectorAll('ul, ol').length,
                        tables: document.querySelectorAll('table').length,
                        images: document.querySelectorAll('img').length,
                        links: document.querySelectorAll('a').length
                    }
                };
            """)

            # Get main content
            main_content = self.get_main_content()

            # Convert to MarkdownTeX
            markdowntex_content = self.html_to_markdowntex(main_content)

            # Extract metadata
            metadata = {
                "url": self.driver.current_url,
                "title": page_info["title"],
                "description": page_info["description"],
                "keywords": page_info["keywords"],
                "language": page_info["language"],
                "author": page_info["author"],
                "canonical": page_info["canonical"],
                "structure": page_info["structure"],
                "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "content_length": len(markdowntex_content),
            }

            return {
                "metadata": metadata,
                "content": markdowntex_content,
                "raw_html": self.driver.page_source,
            }

        except Exception as e:
            logger.error(
                f"Error extracting content from {self.driver.current_url}: {e}"
            )
            return None

    def get_main_content(self) -> str:
        """Extract main content from page"""
        try:
            # Try to find main content areas
            main_selectors = [
                "main",
                "article",
                '[role="main"]',
                ".main-content",
                "#main",
                ".content",
                ".post-content",
                ".entry-content",
            ]

            for selector in main_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    return element.get_attribute("outerHTML")
                except:
                    continue

            # Fallback to body
            return self.driver.find_element(By.TAG_NAME, "body").get_attribute(
                "outerHTML"
            )

        except Exception as e:
            logger.error(f"Error getting main content: {e}")
            return self.driver.page_source

    def html_to_markdowntex(self, html_content: str) -> str:
        """Convert HTML to MarkdownTeX preserving structure and links"""

        # Basic HTML to Markdown conversion
        # This is a simplified version - in production, use html2text or similar

        # Extract and preserve inline LaTeX
        tex_patterns = [
            (r"\$\$([^$]+)\$\$", r"\\begin{equation}\1\\end{equation}"),
            (r"\$([^$]+)\$", r"\\(\1\\)"),
            (
                r"\\begin\{([^}]+)\}(.*?)\\end\{\1\}",
                lambda m: f"\\begin{{{m.group(1)}}}{m.group(2)}\\end{{{m.group(1)}}}",
            ),
        ]

        # Convert HTML structure
        markdown = html_content

        # Preserve LaTeX
        for pattern, replacement in tex_patterns:
            markdown = re.sub(pattern, replacement, markdown, flags=re.DOTALL)

        # HTML to Markdown basic conversion
        conversions = [
            (
                r"<h([1-6])[^>]*>(.*?)</h[1-6]>",
                lambda m: f"{'#' * int(m.group(1))} {m.group(2).strip()}\\n\\n",
            ),
            (r"<strong[^>]*>(.*?)</strong>", r"**\1**"),
            (r"<em[^>]*>(.*?)</em>", r"*\1*"),
            (r"<code[^>]*>(.*?)</code>", r"`\1`"),
            (r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r"[\2](\1)"),
            (r'<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*>', r"![\2](\1)"),
            (r"<p[^>]*>(.*?)</p>", r"\1\\n\\n"),
            (r"<br[^>]*>", r"\\n"),
            (r"<ul[^>]*>(.*?)</ul>", lambda m: self.convert_list(m.group(1), "ul")),
            (r"<ol[^>]*>(.*?)</ol>", lambda m: self.convert_list(m.group(1), "ol")),
            (r"<li[^>]*>(.*?)</li>", r"- \1\\n"),
        ]

        for pattern, replacement in conversions:
            markdown = re.sub(
                pattern, replacement, markdown, flags=re.DOTALL | re.IGNORECASE
            )

        # Clean up extra whitespace and HTML tags
        markdown = re.sub(r"<[^>]+>", "", markdown)
        markdown = re.sub(r"\\n\\s*\\n", "\\n\\n", markdown)
        markdown = markdown.strip() + "\\n"

        return markdown

    def convert_list(self, list_html: str, list_type: str) -> str:
        """Convert HTML lists to Markdown"""
        items = re.findall(r"<li[^>]*>(.*?)</li>", list_html, re.DOTALL | re.IGNORECASE)

        if list_type == "ol":
            return "\\n".join(
                f"{i + 1}. {item.strip()}" for i, item in enumerate(items)
            )
        else:
            return "\\n".join(f"- {item.strip()}" for item in items)

    def save_page(self, url: str, content: Dict) -> bool:
        """Save page content to file"""
        try:
            # Create filename from URL
            parsed_url = urlparse(url)
            path = parsed_url.path.strip("/")
            filename = path.replace("/", "_") or "index"
            if not filename.endswith(".md"):
                filename += ".md"

            file_path = self.output_dir / "pages" / filename

            # Save MarkdownTeX content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"# {content['metadata']['title']}\\n\\n")
                f.write(f"**URL:** {url}\\n\\n")
                f.write(f"**Language:** {content['metadata']['language']}\\n\\n")
                f.write(f"**Scraped:** {content['metadata']['scraped_at']}\\n\\n")
                f.write("---\\n\\n")
                f.write(content["content"])

            # Save metadata
            meta_path = self.output_dir / "meta" / f"{filename}.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(content["metadata"], f, indent=2, ensure_ascii=False)

            # Update site AST
            self.site_ast["pages"][url] = {
                "filename": filename,
                "metadata": content["metadata"],
                "links": [],
            }

            logger.info(f"Saved: {url} -> {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error saving page {url}: {e}")
            return False

    def scrape_page(self, url: str) -> bool:
        """Scrape a single page"""
        try:
            logger.info(f"Scraping: {url}")

            # Navigate to page
            self.driver.get(url)

            # Wait for page to load
            if not self.wait_for_page_load():
                logger.warning(f"Page load timeout: {url}")

            # Add delay to be respectful
            time.sleep(self.delay)

            # Extract content
            content = self.extract_content()
            if content:
                # Save page
                if self.save_page(url, content):
                    self.downloaded_urls.add(url)

                    # Extract links for recursive scraping
                    new_links = self.extract_links()
                    self.site_ast["pages"][url]["links"] = new_links

                    return new_links
                else:
                    self.failed_urls.add(url)
                    return []
            else:
                self.failed_urls.add(url)
                return []

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            self.failed_urls.add(url)
            return []

    def recursive_scrape(self, max_pages: int = 1000, max_depth: int = 10) -> None:
        """Recursively scrape entire website"""
        if not self.setup_driver():
            return

        try:
            # Start with base URL
            urls_to_scrape = [self.base_url]
            current_depth = 0

            while (
                urls_to_scrape
                and current_depth < max_depth
                and len(self.downloaded_urls) < max_pages
            ):
                logger.info(
                    f"Depth {current_depth}, URLs to scrape: {len(urls_to_scrape)}, Downloaded: {len(self.downloaded_urls)}"
                )

                new_urls_to_scrape = []

                for url in urls_to_scrape:
                    if (
                        url not in self.visited_urls
                        and len(self.downloaded_urls) < max_pages
                    ):
                        self.visited_urls.add(url)
                        new_links = self.scrape_page(url)
                        new_urls_to_scrape.extend(new_links)

                urls_to_scrape = list(set(new_urls_to_scrape))  # Remove duplicates
                current_depth += 1

            # Update site AST metadata
            self.site_ast["metadata"]["total_pages"] = len(self.downloaded_urls)
            self.site_ast["metadata"]["failed_pages"] = len(self.failed_urls)

            # Save site AST
            with open(self.output_dir / "site_ast.json", "w", encoding="utf-8") as f:
                json.dump(self.site_ast, f, indent=2, ensure_ascii=False)

            logger.info(
                f"Scraping complete. Downloaded {len(self.downloaded_urls)} pages, failed {len(self.failed_urls)}"
            )

        finally:
            if self.driver:
                self.driver.quit()

    def generate_sitemap(self) -> None:
        """Generate sitemap of scraped pages"""
        sitemap_path = self.output_dir / "sitemap.txt"

        with open(sitemap_path, "w", encoding="utf-8") as f:
            for url in sorted(self.downloaded_urls):
                f.write(f"{url}\\n")

        logger.info(f"Sitemap saved to {sitemap_path}")


def main():
    """Main function to run the web scraper"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Recursive web scraper with MarkdownTeX output"
    )
    parser.add_argument("url", help="Base URL to scrape")
    parser.add_argument(
        "-o", "--output", default="scraped_content", help="Output directory"
    )
    parser.add_argument(
        "-d",
        "--delay",
        type=float,
        default=1.0,
        help="Delay between requests (seconds)",
    )
    parser.add_argument(
        "-m", "--max-pages", type=int, default=1000, help="Maximum pages to scrape"
    )
    parser.add_argument(
        "--max-depth", type=int, default=10, help="Maximum depth to scrape"
    )

    args = parser.parse_args()

    scraper = WebScraper(args.url, args.output, args.delay)
    scraper.recursive_scrape(args.max_pages, args.max_depth)
    scraper.generate_sitemap()


if __name__ == "__main__":
    main()
