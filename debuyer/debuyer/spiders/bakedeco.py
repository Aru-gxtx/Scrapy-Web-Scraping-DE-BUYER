import scrapy
import re

class BakedecoSpider(scrapy.Spider):
    name = "bakedeco"
    allowed_domains = ["www.bakedeco.com"]
    # Manually change pagination since I can't make scrapy do it without getting blocked
    start_urls = ["https://www.bakedeco.com/nav/search.asp?keywords=de+Buyer&pPgNo=15"]

    custom_settings = {
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 60 * 1000,
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
    }

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                callback=self.parse,
                meta={"playwright": True, "playwright_include_page": True},
            )

    def parse(self, response):
        self.logger.info(f"Scraping page: {response.url}")
        page = response.meta.get("playwright_page")
        try:
            # Wait for product grid or fallback element
            if page:
                import asyncio
                try:
                    coro = page.wait_for_selector('#kuResultsView a[href*="/detail.asp?id="], a[href*="/detail.asp?id="', timeout=10000)
                    if asyncio.iscoroutine(coro):
                        asyncio.get_event_loop().run_until_complete(coro)
                except Exception as e:
                    self.logger.warning(f"Playwright wait_for_selector failed: {e}")
        except Exception as e:
            self.logger.warning(f"Playwright wait_for_selector outer failed: {e}")
        finally:
            # Always close Playwright page to avoid resource leaks
            if page:
                try:
                    coro = page.close()
                    import asyncio
                    if asyncio.iscoroutine(coro):
                        asyncio.get_event_loop().run_until_complete(coro)
                except Exception as e:
                    self.logger.warning(f"Playwright page.close() failed: {e}")

        # Product link extraction
        product_links = set()
        product_links.update(response.css('#kuResultsView a[href*="/detail.asp?id="]::attr(href)').getall())
        product_links.update(response.css('.kuResultsView a[href*="/detail.asp?id="]::attr(href)').getall())
        product_links.update(response.css('a[href*="/detail.asp?id="]::attr(href)').getall())
        self.logger.info(f"Found {len(product_links)} product links on this page.")
        for link in product_links:
            url = response.urljoin(link)
            yield scrapy.Request(url, callback=self.parse_product)

        # Track visited pages to avoid infinite loops
        if not hasattr(self, 'visited_pages'):
            self.visited_pages = set()
        self.visited_pages.add(response.url)

        # Optional: Limit max pages to avoid infinite crawl
        if hasattr(self, 'max_pages') and len(self.visited_pages) >= self.max_pages:
            self.logger.warning(f"Reached max_pages={self.max_pages}, stopping crawl.")
            return

        # --- Pagination logic with detailed logging ---
        next_page = None
        next_page = response.css('a[aria-label="Next"]::attr(href)').get()
        self.logger.info(f"[Pagination] aria-label=Next: {next_page}")
        if not next_page:
            # Try text-based selector
            next_page = response.xpath('//a[contains(text(), "Next")]/@href').get()
            self.logger.info(f"[Pagination] text=Next: {next_page}")
        if not next_page:
            # Try numeric page links (fallback)
            page_links = response.css('a[href*="pPgNo="]::attr(href)').getall()
            for link in page_links:
                abs_link = response.urljoin(link)
                if abs_link not in self.visited_pages:
                    next_page = link
                    self.logger.info(f"[Pagination] fallback numeric: {next_page}")
                    break
        if not next_page:
            self.logger.warning("No next page found. Pagination ends.")

        if next_page:
            next_page_url = response.urljoin(next_page)
            yield scrapy.Request(
                next_page_url,
                callback=self.parse,
                meta={"playwright": True, "playwright_include_page": True},
            )

    def parse_product(self, response):
        def extract_first(selector, default=None):
            return response.css(selector).get(default=default)

        def extract_text(selector, default=None):
            return response.css(selector).xpath('string()').get(default=default).strip() if response.css(selector) else default

        item_no = None
        mfr_catalog_no = None
        brand_name = None
        item_desc = None
        image_link = None
        overview = None
        length = width = height = volume = diameter = color = material = ean_code = pattern = barcode = None

        # Try to extract Item No. from text like 'Item No. 511332'
        item_no_match = re.search(r'Item No\.?\s*([\w-]+)', response.text)
        if item_no_match:
            item_no = item_no_match.group(1)

        # Try to extract Brand Name from logo alt or meta
        brand_name = extract_first('img.kuBrandImage::attr(alt)')
        if not brand_name:
            brand_name = extract_first('meta[name="keywords"]::attr(content)')

        # Item Description: try meta description or product title
        item_desc = extract_first('meta[name="description"]::attr(content)')
        if not item_desc:
            item_desc = extract_text('h1')

        # Image Link
        image_link = extract_first('img#mainImage::attr(src)')
        if not image_link:
            image_link = extract_first('img[alt*="de Buyer"]::attr(src)')

        # Overview: try to extract main product description
        overview = extract_text('div#productDescription, div.productDescription, div#description, div.description')

        yield {
            'url': response.url,
            'item_no': item_no,
            'mfr_catalog_no': mfr_catalog_no,
            'brand_name': brand_name,
            'item_description': item_desc,
            'image_link': image_link,
            'overview': overview,
            'length': length,
            'width': width,
            'height': height,
            'volume': volume,
            'diameter': diameter,
            'color': color,
            'material': material,
            'ean_code': ean_code,
            'pattern': pattern,
            'barcode': barcode,
        }
