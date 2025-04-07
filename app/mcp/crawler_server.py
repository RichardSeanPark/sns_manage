import asyncio
import logging
from typing import Optional, List
from contextlib import asynccontextmanager

from mcp import FastMCP, RequestContext, ToolContext, ResourceContext
from playwright.async_api import async_playwright, Playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

logger = logging.getLogger(__name__)

# Retry configuration for Playwright operations
RETRY_ATTEMPTS = 3
RETRY_WAIT_SECONDS = 2

# --- Playwright Browser Pool Management ---

class BrowserPoolManager:
    """Manages a pool of Playwright Browser instances."""
    def __init__(self, pool_size: int = 3):
        if pool_size <= 0:
            raise ValueError("Pool size must be positive.")
        self.pool_size = pool_size
        self._playwright: Optional[Playwright] = None
        self._browser_queue: Optional[asyncio.Queue[Browser]] = None
        self._all_browsers: List[Browser] = []
        self._initialized = False

    async def _get_playwright(self) -> Playwright:
        """Initializes and returns the Playwright instance."""
        if self._playwright is None:
            logger.info("Initializing Playwright...")
            self._playwright = await async_playwright().start()
            logger.info("Playwright initialized.")
        return self._playwright

    async def initialize(self):
        """Initializes the browser pool."""
        if self._initialized:
            logger.info("Browser pool already initialized.")
            return
            
        logger.info(f"Initializing browser pool with size {self.pool_size}...")
        playwright = await self._get_playwright()
        self._browser_queue = asyncio.Queue(maxsize=self.pool_size)
        self._all_browsers = []
        
        try:
            for i in range(self.pool_size):
                # TODO: Get browser launch options (type, headless) from config
                logger.info(f"Launching browser instance {i+1}/{self.pool_size}...")
                browser = await playwright.chromium.launch(headless=True)
                await self._browser_queue.put(browser)
                self._all_browsers.append(browser)
                logger.info(f"Browser instance {i+1} launched and added to pool.")
            self._initialized = True
            logger.info("Browser pool initialization complete.")
        except Exception as e:
            logger.error(f"Failed to initialize browser pool: {e}", exc_info=True)
            # Cleanup partially created browsers if initialization fails
            await self.shutdown() 
            raise # Re-raise the exception

    async def get_browser(self, timeout: float = 60.0) -> Optional[Browser]:
        """Gets a browser instance from the pool. Waits if pool is empty."""
        if not self._initialized or not self._browser_queue:
            logger.error("Browser pool not initialized. Call initialize() first.")
            # Or should we initialize here? For now, require explicit init.
            await self.initialize() # Attempt to initialize if not done
            if not self._initialized or not self._browser_queue: # Check again
                 raise RuntimeError("Browser pool could not be initialized.")

        logger.debug("Attempting to get browser from pool...")
        try:
            browser = await asyncio.wait_for(self._browser_queue.get(), timeout=timeout)
            logger.debug(f"Acquired browser: {browser}")
             # Simple check if browser is still usable
            if not browser.is_connected():
                logger.warning(f"Browser {browser} is disconnected. Attempting to replace.")
                # Try to launch a replacement
                try:
                   playwright = await self._get_playwright()
                   new_browser = await playwright.chromium.launch(headless=True) # TODO: Use config
                   self._all_browsers.remove(browser) # Remove old browser from list
                   self._all_browsers.append(new_browser) # Add new one
                   logger.info(f"Launched replacement browser: {new_browser}")
                   # Put the new browser back and try getting again (or just return it?)
                   # For simplicity, return the new one directly this time.
                   # In more robust scenarios, might retry getting from queue.
                   # Need to be careful about pool size logic here.
                   # Returning directly avoids potential deadlock if pool remains full.
                   return new_browser 
                except Exception as replace_err:
                   logger.error(f"Failed to launch replacement browser: {replace_err}. Releasing original disconnected browser.", exc_info=True)
                   # If replacement fails, put the disconnected one back for now to avoid deadlock
                   # Or just raise an error? Raising might be safer.
                   self._browser_queue.put_nowait(browser) # Put disconnected back to maintain count
                   raise RuntimeError(f"Failed to acquire a connected browser: {replace_err}") from replace_err
            else:
                 self._browser_queue.task_done() # Mark as processed from queue perspective
                 return browser
        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for available browser from pool (timeout={timeout}s).")
            return None
        except Exception as e:
            logger.error(f"Error getting browser from pool: {e}", exc_info=True)
            return None # Or raise?

    async def release_browser(self, browser: Browser):
        """Releases a browser instance back to the pool."""
        if not self._initialized or not self._browser_queue:
             logger.warning("Attempted to release browser to an uninitialized pool.")
             # Try closing it if pool is gone
             if browser.is_connected(): await browser.close()
             return

        if browser:
            # Check if the browser is still connected before putting back
            if browser.is_connected():
                logger.debug(f"Releasing browser back to pool: {browser}")
                await self._browser_queue.put(browser)
            else:
                logger.warning(f"Attempted to release disconnected browser {browser}. Discarding and attempting to replenish.")
                self._all_browsers.remove(browser) # Remove from list
                # Attempt to launch a replacement to maintain pool size
                try:
                    playwright = await self._get_playwright()
                    new_browser = await playwright.chromium.launch(headless=True) # TODO: Use config
                    self._all_browsers.append(new_browser)
                    await self._browser_queue.put(new_browser)
                    logger.info(f"Launched and added replacement browser {new_browser} to pool.")
                except Exception as e:
                    logger.error(f"Failed to launch replacement browser during release: {e}", exc_info=True)
                    # Pool size might decrease temporarily if replenishment fails

    async def shutdown(self):
        """Closes all browsers in the pool and stops Playwright."""
        logger.info("Shutting down browser pool...")
        self._initialized = False # Mark as uninitialized first
        
        # Close browsers currently in the queue
        if self._browser_queue:
            while not self._browser_queue.empty():
                try:
                    browser = self._browser_queue.get_nowait()
                    if browser.is_connected():
                        logger.debug(f"Closing browser from queue: {browser}")
                        await browser.close()
                except asyncio.QueueEmpty:
                    break # Should not happen with check, but safety
                except Exception as e:
                    logger.error(f"Error closing browser from queue during shutdown: {e}", exc_info=True)
            self._browser_queue = None # Clear queue

        # Close any browsers that might have been created but not in queue (or handle busy ones if tracked)
        # In this simple queue model, browsers are either in queue or 'borrowed'.
        # We rely on the lifespan/shutdown handler calling this *after* all tasks using browsers are done.
        # A more robust pool would track borrowed browsers.
        # For now, iterate through the master list.
        logger.info("Closing all tracked browser instances...")
        for browser in self._all_browsers:
             try:
                 if browser.is_connected():
                      logger.debug(f"Closing browser: {browser}")
                      await browser.close()
             except Exception as e:
                  logger.error(f"Error closing browser {browser} during shutdown: {e}", exc_info=True)
        self._all_browsers = []

        # Stop Playwright
        if self._playwright:
            logger.info("Stopping Playwright instance...")
            await self._playwright.stop()
            self._playwright = None
            logger.info("Playwright instance stopped.")
        logger.info("Browser pool shutdown complete.")

# Global instance of the pool manager
# TODO: Make pool_size configurable (e.g., via environment variable or config file)
browser_pool = BrowserPoolManager(pool_size=2) 

@asynccontextmanager
async def get_managed_browser():
    """Async context manager to get and release a browser from the pool."""
    browser = None
    try:
        browser = await browser_pool.get_browser()
        if browser is None:
             raise RuntimeError("Failed to acquire browser from pool.")
        yield browser
    finally:
        if browser:
            await browser_pool.release_browser(browser)


# --- MCP Server Lifespan ---
@asynccontextmanager
async def crawler_lifespan(app: FastMCP):
    """MCP lifespan handler for crawler server."""
    logger.info("Crawler MCP Server lifespan startup...")
    await browser_pool.initialize()
    yield # Server runs here
    logger.info("Crawler MCP Server lifespan shutdown...")
    await browser_pool.shutdown()


# --- MCP Server Setup ---
crawler_mcp_app = FastMCP(
    name="Web Crawler MCP Server",
    description="MCP server for managing web crawling tasks using Playwright.",
    version="0.1.0",
    lifespan=crawler_lifespan # Use the pool-managing lifespan
)

# --- MCP Tools ---

@crawler_mcp_app.tool(
    name="launch_browser",
    description="Ensures the browser pool is initialized. Returns pool status."
)
async def launch_browser(ctx: ToolContext) -> dict:
    """Ensures the browser pool is initialized."""
    try:
        if not browser_pool._initialized:
             logger.info("launch_browser tool triggering pool initialization.")
             await browser_pool.initialize()
        # Check status after attempting initialization
        if browser_pool._initialized:
             # Provide some basic pool status
             qsize = browser_pool._browser_queue.qsize() if browser_pool._browser_queue else 0
             return {"status": "success", "message": "Browser pool is initialized.", "pool_size": browser_pool.pool_size, "available_now": qsize}
        else:
             return {"status": "error", "message": "Failed to initialize browser pool."}
    except Exception as e:
        logger.error(f"Error initializing browser pool via tool: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"Failed to initialize browser pool: {str(e)}"}

# Define retry strategy for page load
@retry(stop=stop_after_attempt(RETRY_ATTEMPTS),
       wait=wait_fixed(RETRY_WAIT_SECONDS),
       retry=retry_if_exception_type((PlaywrightTimeoutError, Exception)), # Retry on timeout and general exceptions
       reraise=True) # Reraise the exception if all retries fail
async def _goto_with_retry(page: Page, url: str, timeout: int):
    logger.debug(f"Attempting to navigate to {url} (timeout={timeout}ms)")
    response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    logger.debug(f"Successfully navigated to {url}")
    return response

@crawler_mcp_app.tool(
    name="crawl_page",
    description="Navigates to the given URL using a browser from the pool.",
    params={
        "url": {"type": "string", "description": "The URL to navigate to.", "required": True}
    }
)
async def crawl_page(ctx: ToolContext, url: str) -> dict:
    """Navigates to a URL using a browser from the pool."""
    page: Optional[Page] = None
    try:
        async with get_managed_browser() as browser: # Use context manager
             page = await browser.new_page()
             logger.info(f"Navigating to URL: {url} using browser {browser}")
             
             # Use the retry wrapper for page.goto
             response = await _goto_with_retry(page, url, timeout=60000) 
             
             status_code = response.status if response else None
             page_title = await page.title()
             
             logger.info(f"Navigation complete. Status: {status_code}, Title: '{page_title}'")
             
             await page.close() 
             page = None 

             if status_code == 200:
                 return {
                     "status": "success", 
                     "message": f"Successfully navigated to {url}",
                     "page_title": page_title
                 }
             else:
                  return {
                     "status": "error", 
                     "message": f"Failed to navigate to {url}. Status code: {status_code}",
                     "status_code": status_code
                 }

    except Exception as e:
        logger.error(f"Error crawling page {url}: {str(e)}", exc_info=True)
        if page and not page.is_closed():
             await page.close() # Ensure page is closed on error
        # Browser release is handled by the context manager
        return {"status": "error", "message": f"Error crawling page {url}: {str(e)}"}

# Define retry strategy for element location/extraction (can be adjusted)
@retry(stop=stop_after_attempt(RETRY_ATTEMPTS),
       wait=wait_fixed(RETRY_WAIT_SECONDS),
       retry=retry_if_exception_type(Exception), # Retry on general exceptions during find/extract
       reraise=True)
async def _extract_selector_with_retry(page: Page, selector: str) -> List[Optional[str]]:
    logger.debug(f"Attempting to extract content for selector: {selector}")
    elements = await page.locator(selector).all()
    if not elements:
        logger.warning(f"Selector '{selector}' did not match any elements.")
        return [] # Return empty list for no match
    
    element_texts = [await element.text_content() for element in elements]
    logger.debug(f"Successfully extracted {len(element_texts)} items for selector '{selector}'")
    return element_texts # Return list including potential None values

@crawler_mcp_app.tool(
    name="extract_content",
    description="Crawls a page using a browser from the pool and extracts text content.",
    params={
        "url": {"type": "string", "description": "The URL to crawl.", "required": True},
        "selectors": {"type": "array", "items": {"type": "string"}, "description": "List of CSS selectors or XPath expressions.", "required": True}
    }
)
async def extract_content(ctx: ToolContext, url: str, selectors: list[str]) -> dict:
    """Crawls a page and extracts content using a browser from the pool."""
    page: Optional[Page] = None
    extracted_data = {}
    try:
        async with get_managed_browser() as browser: # Use context manager
            page = await browser.new_page()
            logger.info(f"Navigating to {url} for extraction using browser {browser}.")
            
            # Use the retry wrapper for page.goto
            await _goto_with_retry(page, url, timeout=60000)
            
            logger.info(f"Page loaded. Extracting content using selectors: {selectors}")

            for selector in selectors:
                try:
                    # Use retry wrapper for selector extraction
                    element_texts = await _extract_selector_with_retry(page, selector)
                    # Filter None values after potentially successful retry
                    extracted_data[selector] = [text for text in element_texts if text is not None]
                    if not extracted_data[selector] and element_texts: # Log if only None was returned
                         logger.warning(f"Selector '{selector}' matched elements but text content was None.")
                    elif not element_texts:
                        extracted_data[selector] = None # Explicitly set None if no elements matched after retry
                    
                    logger.info(f"Finished extraction for selector '{selector}'. Found {len(extracted_data[selector]) if extracted_data[selector] else 0} non-None items.")
                    
                except Exception as selector_error:
                    logger.error(f"Error processing selector '{selector}' on {url} after retries: {selector_error}", exc_info=True)
                    extracted_data[selector] = f"Error after retries: {str(selector_error)}"

            await page.close()
            page = None 
            return {"status": "success", "extracted_content": extracted_data}

    except Exception as e:
        logger.error(f"Error during content extraction for {url}: {str(e)}", exc_info=True)
        if page and not page.is_closed():
            await page.close()
        # Browser release is handled by the context manager
        return {"status": "error", "message": f"Error during content extraction for {url}: {str(e)}"}

@crawler_mcp_app.tool(
    name="interact_with_page",
    description="(Placeholder) Performs interactions on a webpage using a browser from the pool.",
    params={
        "url": {"type": "string", "description": "The URL to interact with.", "required": True},
        "actions": {"type": "array", "items": {"type": "object"}, "description": "List of actions.", "required": True}
    }
)
async def interact_with_page(ctx: ToolContext, url: str, actions: list[dict]) -> dict:
    """(Placeholder) Interacts with elements on a webpage using pool."""
    logger.warning("interact_with_page tool is not fully implemented yet.")
    # TODO: Implement interaction logic using a browser from the pool
    # async with get_managed_browser() as browser:
    #    page = await browser.new_page()
    #    await page.goto(url)
    #    ... perform actions ...
    #    await page.close()
    return {"status": "pending", "message": "Interaction tool not implemented."}

@crawler_mcp_app.tool(
    name="follow_links",
    description="(Placeholder) Finds/follows links on a page using a browser from the pool.",
    params={
        "url": {"type": "string", "description": "The starting URL.", "required": True},
        "pattern": {"type": "string", "description": "Regex pattern to match links.", "required": True}
    }
)
async def follow_links(ctx: ToolContext, url: str, pattern: str) -> dict:
    """(Placeholder) Finds and follows links using pool."""
    logger.warning("follow_links tool is not fully implemented yet.")
    # TODO: Implement link following logic using a browser from the pool
    # async with get_managed_browser() as browser:
    #    page = await browser.new_page()
    #    await page.goto(url)
    #    ... find/filter links ...
    #    await page.close()
    return {"status": "pending", "message": "Link following tool not implemented."}


# --- MCP Resources ---
# TODO: Add resources if needed


# --- Server Execution ---
async def run_crawler_mcp_server(host: str = "0.0.0.0", port: int = 8101):
    """Runs the Web Crawler MCP server (intended for standalone testing)."""
    # Note: For integration, this server logic might be handled differently,
    # e.g., mounting the crawler_mcp_app onto a main FastAPI app.
    
    config = uvicorn.Config(crawler_mcp_app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    
    logger.info(f"Starting Web Crawler MCP Server with Uvicorn at http://{host}:{port}")
    
    # Uvicorn handles the lifespan events defined in FastMCP now
    await server.serve() 
    
    # Code here will likely not be reached unless server.serve() returns/is awaited differently
    # or an error occurs before/during serve. Cleanup is handled by lifespan.
    logger.info("Web Crawler MCP Server Uvicorn process finished.")


if __name__ == "__main__":
    # Need uvicorn to run FastMCP with lifespan correctly
    try:
        import uvicorn
    except ImportError:
        print("Uvicorn is required to run this server directly. Install with: pip install uvicorn")
        exit(1)
        
    logging.basicConfig(level=logging.INFO)
    # Run using uvicorn programmatically
    # Note: The asyncio.run in the previous version won't work correctly with lifespan and MCP server logic.
    # We need a proper ASGI server like uvicorn.
    uvicorn.run(crawler_mcp_app, host="0.0.0.0", port=8101, log_level="info")
    # The code after uvicorn.run() might not execute if stopped via Ctrl+C
    logger.info("Crawler MCP Server stopped.") 