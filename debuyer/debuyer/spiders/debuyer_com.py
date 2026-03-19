
import scrapy



class DebuyerComSpider(scrapy.Spider):
    name = "debuyer.com"
    allowed_domains = ["www.debuyer.com"]
    start_urls = ["https://www.debuyer.com/en/13-bakeware"]

    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'ROBOTSTXT_OBEY': False,
        'COOKIES_ENABLED': True,
    }


    def start_requests(self):
        yield scrapy.Request(
            url="https://www.debuyer.com/en/13-bakeware",
            callback=self.parse,
            meta={"playwright": True},
        )

    def parse(self, response):
        # Step 1: Find all subcategory links on the main bakeware page
        subcat_links = response.css('section.category-miniature a::attr(href)').getall()
        for link in subcat_links:
            yield scrapy.Request(
                url=link,
                callback=self.parse_subcategory,
                meta={"playwright": True},
            )


    def parse_subcategory(self, response):
        # Step 2: For each subcategory, paginate and extract product links
        product_cards = response.css('article.product-miniature')
        for card in product_cards:
            product_url = card.css('a::attr(href)').get()
            if product_url:
                yield scrapy.Request(
                    url=product_url,
                    callback=self.parse_product,
                    meta={"playwright": True},
                )

        # Pagination: look for next page link
        next_page = response.css('li.page-item a[rel="next"]::attr(href)').get()
        if next_page:
            yield scrapy.Request(
                url=next_page,
                callback=self.parse_subcategory,
                meta={"playwright": True},
            )

    def parse_product(self, response):
        def extract_first(sel, default=None):
            return sel.get().strip() if sel else default

        # Item No. / Reference
        reference = response.css('div.product-reference::text').re_first(r'([\w\-]+)')
        # Brand Name (assume de Buyer)
        brand = 'de Buyer'
        # Product Name
        name = extract_first(response.css('h1.product-title::text'))
        # Price
        price = extract_first(response.css('span[itemprop="price"]::attr(content)')) or extract_first(response.css('span.price::text'))
        # Product URL
        product_url = response.url
        # Main Image Link
        image_link = response.css('div.product-cover ul.product-images-cover a::attr(href)').get()
        if not image_link:
            image_link = response.css('div.product-cover img::attr(src)').get()
        # Overview (short description)
        overview = extract_first(response.css('div.product-short-desc p::text'))
        # Item Description (long description)
        description = response.css('div.product-description').xpath('string()').get()
        if description:
            description = description.strip()
        # Dimensions and other details (best effort)
        details = response.css('div.product-features li')
        length = width = height = volume = diameter = color = material = pattern = ean_code = barcode = mfr_catalog_no = None
        for li in details:
            text = li.xpath('string()').get().strip()
            if 'Length' in text:
                length = text.split(':',1)[-1].strip()
            elif 'Width' in text:
                width = text.split(':',1)[-1].strip()
            elif 'Height' in text:
                height = text.split(':',1)[-1].strip()
            elif 'Volume' in text:
                volume = text.split(':',1)[-1].strip()
            elif 'Diameter' in text:
                diameter = text.split(':',1)[-1].strip()
            elif 'Color' in text:
                color = text.split(':',1)[-1].strip()
            elif 'Material' in text:
                material = text.split(':',1)[-1].strip()
            elif 'Pattern' in text:
                pattern = text.split(':',1)[-1].strip()
            elif 'EAN' in text:
                ean_code = text.split(':',1)[-1].strip()
            elif 'Barcode' in text:
                barcode = text.split(':',1)[-1].strip()
            elif 'Catalog' in text:
                mfr_catalog_no = text.split(':',1)[-1].strip()

        yield {
            'item_no': reference,
            'mfr_catalog_no': mfr_catalog_no,
            'brand': brand,
            'name': name,
            'description': description,
            'overview': overview,
            'image_link': image_link,
            'length': length,
            'width': width,
            'height': height,
            'volume': volume,
            'diameter': diameter,
            'color': color,
            'material': material,
            'pattern': pattern,
            'ean_code': ean_code,
            'barcode': barcode,
            'price': price,
            'product_url': product_url,
        }
