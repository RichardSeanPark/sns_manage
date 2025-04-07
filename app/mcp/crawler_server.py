# -*- coding: utf-8 -*-
import asyncio
import logging
from typing import List, Dict, Any
from contextlib import asynccontextmanager

# MCP Imports - Adjust based on actual mcp library structure
from mcp.server.fastmcp.server import FastMCP
from mcp.shared.context import RequestContext
from mcp.server.fastmcp.server import Context

# Playwright Imports
from playwright.async_api import async_playwright, Playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError

# Configuration Imports
from app.config import BROWSER_POOL_SIZE, PAGE_LOAD_TIMEOUT_MS, MAX_RETRIES

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Browser Pool Manager ---

class BrowserPoolManager:
    def __init__(self, pool_size: int = BROWSER_POOL_SIZE):
        self.pool_size = pool_size
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._browser_queue: asyncio.Queue[Browser] | None = None
        self._initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self):
        async with self._lock:
            if not self._initialized:
                logger.info("Initializing Playwright and Browser Pool...")
                try:
                    self._playwright = await async_playwright().start()
                    # Launch browser once
                    self._browser = await self._playwright.chromium.launch(headless=True)
                    # Create a queue and fill it with browser contexts or page generators if needed
                    # For simplicity, we might just reuse the single browser instance
                    # Or create multiple browser instances if pool_size > 1
                    self._browser_queue = asyncio.Queue(maxsize=self.pool_size)
                    # Filling the queue might depend on usage pattern (e.g., new context per request)
                    # For now, we'll manage pages from the single browser instance
                    logger.info(f"Browser pool initialized with size {self.pool_size}. Browser connected: {self._browser.is_connected()}")
                    self._initialized = True
                except Exception as e:
                    logger.error(f"Failed to initialize browser pool: {e}", exc_info=True)
                    # Ensure cleanup happens even if initialization fails partially
                    await self.shutdown()
                    raise

    async def shutdown(self):
        async with self._lock:
            if self._initialized:
                logger.info("Shutting down Playwright and Browser Pool...")
                if self._browser:
                    try:
                        await self._browser.close()
                        logger.info("Browser closed.")
                    except Exception as e:
                        logger.error(f"Error closing browser: {e}", exc_info=True)
                    self._browser = None
                if self._playwright:
                    try:
                        await self._playwright.stop()
                        logger.info("Playwright stopped.")
                    except Exception as e:
                        logger.error(f"Error stopping Playwright: {e}", exc_info=True)
                    self._playwright = None
                self._browser_queue = None
                self._initialized = False
                logger.info("Browser pool shut down.")

    @asynccontextmanager
    async def get_managed_browser(self) -> Browser:
        """Provides a browser instance from the pool (simplified: returns the single instance)."""
        if not self._initialized or not self._browser:
            await self.initialize()
        
        if not self._browser or not self._browser.is_connected():
             logger.error("Browser is not initialized or not connected.")
             raise ConnectionError("Browser is not available")
             
        # In a real pool, acquire/release logic would be here
        # For simplicity, just yield the existing browser
        logger.debug("Providing browser instance.")
        try:
            yield self._browser
        finally:
            # Release logic would go here in a real pool
            logger.debug("Browser instance usage finished.")

    async def get_available_count(self) -> int:
        """Returns the number of available browser instances (simplified)."""
        if not self._initialized or not self._browser_queue:
            return 0
        # Simplified: assumes the queue holds available browsers/contexts
        return self._browser_queue.qsize()

# --- MCP Server Setup ---

browser_pool = BrowserPoolManager()

# Lifespan events for MCP application
@asynccontextmanager
async def lifespan(app: FastMCP):
    logger.info("MCP Server lifespan startup...")
    await browser_pool.initialize()
    yield
    logger.info("MCP Server lifespan shutdown...")
    await browser_pool.shutdown()

# Initialize FastMCP with lifespan management
crawler_mcp_app = FastMCP(lifespan=lifespan)

# --- Helper Functions ---

async def _goto_with_retry(page: Page, url: str, timeout: int = PAGE_LOAD_TIMEOUT_MS, retries: int = MAX_RETRIES):
    """Navigate to a URL with retries on timeout."""
    for attempt in range(retries + 1):
        try:
            logger.info(f"Navigating to {url} (Attempt {attempt + 1}/{retries + 1})")
            response = await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            logger.info(f"Navigation successful to {url}, status: {response.status if response else 'N/A'}")
            return response
        except PlaywrightTimeoutError:
            logger.warning(f"Timeout navigating to {url} on attempt {attempt + 1}")
            if attempt == retries:
                logger.error(f"Failed to navigate to {url} after {retries + 1} attempts.")
                raise
            await asyncio.sleep(1) # Wait before retrying
        except Exception as e:
             logger.error(f"Error during navigation to {url}: {e}", exc_info=True)
             raise # Re-raise other critical errors
    return None # Should not be reached if retries exhausted

async def _extract_selector_with_retry(page: Page, selector: str, retries: int = MAX_RETRIES):
    """Extract text content from a selector with retries."""
    for attempt in range(retries + 1):
        try:
            logger.info(f"Extracting selector '{selector}' (Attempt {attempt + 1}/{retries + 1})")
            # Wait for selector to ensure element is present
            await page.wait_for_selector(selector, timeout=10000) # Short timeout for element presence
            elements = await page.query_selector_all(selector)
            content = [await el.text_content() or "" for el in elements] # Get text or empty string
            logger.info(f"Successfully extracted {len(content)} element(s) for selector '{selector}'")
            return content
        except PlaywrightTimeoutError:
            logger.warning(f"Timeout waiting for selector '{selector}' on attempt {attempt + 1}")
            if attempt == retries:
                logger.error(f"Failed to find selector '{selector}' after {retries + 1} attempts.")
                return None # Return None if selector not found after retries
            await asyncio.sleep(0.5) # Short wait before retrying
        except Exception as e:
             logger.error(f"Error extracting selector '{selector}': {e}", exc_info=True)
             return None # Return None on other errors
    return None # Should not be reached

# --- MCP Tools ---

@crawler_mcp_app.tool()
def launch_browser(ctx: Context):
    """Initializes the browser pool if not already started and reports status."""
    try:
        # Initialization might happen automatically via lifespan or context manager
        # This tool can act as a health check or explicit initializer
        if not browser_pool._initialized:
             logger.info("Tool 'launch_browser' triggered initialization.")
             # In a real scenario, calling initialize might be redundant if lifespan works
             # await browser_pool.initialize() # Potentially redundant
             # For safety, we can just check the status
             return {"status": "pending", "message": "Browser pool is initializing..."}
        
        available_count = browser_pool._browser_queue.qsize() if browser_pool._browser_queue else 0
        return {
            "status": "success",
            "message": f"Browser pool is initialized. Pool size: {browser_pool.pool_size}. Available now: {available_count}",
            "pool_size": browser_pool.pool_size,
            "available_now": available_count
        }
    except Exception as e:
        logger.error(f"Error in launch_browser tool: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

@crawler_mcp_app.tool(name="crawl_page", description="Crawls a given URL and returns basic page information.")
async def crawl_page(ctx: Context, url: str):
    """Navigates to a URL, captures title and status code."""
    if not url or not url.startswith(('http://', 'https://')):
        return {"status": "error", "message": "Invalid URL provided."}

    try:
        async with browser_pool.get_managed_browser() as browser:
            page = await browser.new_page()
            logger.info(f"Opened new page for crawling {url}")
            response = await _goto_with_retry(page, url)
            
            if response and response.status == 200:
                title = await page.title()
                await page.close()
                logger.info(f"Successfully crawled {url}. Title: {title}")
                return {"status": "success", "url": url, "page_title": title, "status_code": response.status}
            else:
                status_code = response.status if response else 500 # Default to 500 if no response
                await page.close()
                logger.warning(f"Failed to navigate to {url}, status code: {status_code}")
                return {"status": "error", "message": f"Failed to navigate to {url}", "status_code": status_code}
                
    except ConnectionError as ce:
         logger.error(f"Browser connection error during crawl: {ce}", exc_info=True)
         return {"status": "error", "message": f"Browser connection error: {ce}"}
    except Exception as e:
        logger.error(f"Error crawling page {url}: {e}", exc_info=True)
        # Ensure page is closed even on error if it exists
        try:
            if page: await page.close()
        except Exception as close_err:
             logger.error(f"Error closing page after crawl error: {close_err}", exc_info=True)
        return {"status": "error", "message": str(e)}

@crawler_mcp_app.tool(name="extract_content", description="Navigates to a URL and extracts content based on CSS selectors.")
async def extract_content(ctx: Context, url: str, selectors: List[str]):
    """Extracts text content for a list of CSS selectors from a given URL."""
    if not url or not url.startswith(('http://', 'https://')):
        return {"status": "error", "message": "Invalid URL provided."}
    if not selectors:
        return {"status": "error", "message": "No selectors provided for extraction."}

    extracted_content: Dict[str, List[str] | None] = {sel: None for sel in selectors}
    page = None # Define page outside try to ensure close in finally
    
    try:
        async with browser_pool.get_managed_browser() as browser:
            page = await browser.new_page()
            logger.info(f"Opened new page for extracting content from {url}")
            response = await _goto_with_retry(page, url)

            if not response or response.status != 200:
                 status_code = response.status if response else 500
                 await page.close()
                 logger.warning(f"Cannot extract content. Failed to navigate to {url}, status: {status_code}")
                 return {"status": "error", "message": f"Failed to navigate to {url} for extraction", "status_code": status_code}

            # If navigation is successful, proceed with extraction
            logger.info(f"Navigation to {url} successful. Extracting selectors: {selectors}")
            for selector in selectors:
                content = await _extract_selector_with_retry(page, selector)
                extracted_content[selector] = content # Store list or None
            
            await page.close()
            logger.info(f"Finished extracting content from {url}")
            # Check if all selectors failed
            if all(v is None for v in extracted_content.values()):
                 return {"status": "warning", "message": "Navigation successful, but failed to extract any content for the given selectors.", "extracted_content": extracted_content}
            else:
                 return {"status": "success", "url": url, "extracted_content": extracted_content}

    except ConnectionError as ce:
         logger.error(f"Browser connection error during extraction: {ce}", exc_info=True)
         return {"status": "error", "message": f"Browser connection error: {ce}"}
    except Exception as e:
        logger.error(f"Error extracting content from {url}: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
    finally:
         if page:
             try:
                 await page.close()
             except Exception as close_err:
                 logger.error(f"Error closing page after extraction attempt: {close_err}", exc_info=True)

@crawler_mcp_app.tool(name="interact_with_page", description="Performs a sequence of interactions (clicks, inputs) on a page.")
def interact_with_page(ctx: Context, url: str, actions: List[Dict[str, Any]]):
    """Placeholder for page interaction tool."""
    logger.warning("Tool 'interact_with_page' is not implemented yet.")
    return {"status": "pending", "message": "Tool not implemented yet."}

@crawler_mcp_app.tool(name="follow_links", description="Finds and follows links matching a pattern on a page.")
def follow_links(ctx: Context, url: str, pattern: str):
    """Placeholder for link following tool."""
    logger.warning("Tool 'follow_links' is not implemented yet.")
    return {"status": "pending", "message": "Tool not implemented yet."}

# Add this app to the main FastAPI app in main.py
# Example in main.py:
# from app.mcp.crawler_server import crawler_mcp_app
# app.mount("/mcp", crawler_mcp_app) 