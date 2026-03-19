import scrapy


class DebuyerUsaSpider(scrapy.Spider):
    name = "debuyer-usa"
    allowed_domains = ["www.debuyer-usa.com"]
    start_urls = ["https://www.debuyer-usa.com/collections/cookware"]


    def parse(self, response):
        # Use li.grid__item for each product
        products = response.css('li.grid__item')
        if not products:
            self.logger.warning('No product cards found on %s. Sample HTML: %s', response.url, response.text[:2000])
            return

        for item in products:
            link = item.css('a.full-unstyled-link::attr(href)').get()
            name = item.css('a.full-unstyled-link::text').get()
            price = item.css('.price-item--sale::text, .price-item--regular::text').get()
            if link:
                url = response.urljoin(link)
                # Pass name and price to product page for full details
                yield response.follow(url, self.parse_product, cb_kwargs={
                    'product_url': url,
                    'name': name.strip() if name else None,
                    'price': price.strip() if price else None,
                })
            else:
                self.logger.warning("No product link found in item. Printing item HTML:")
                self.logger.info(item.get())

        # Pagination: follow next page if exists
        next_page = response.css('link[rel="next"]::attr(href)').get()
        if next_page:
            next_page = response.urljoin(next_page)
            yield response.follow(next_page, self.parse)

    def parse_product(self, response, product_url=None, name=None, price=None):
        import re
        import json
        # Product name (fallback to passed value)
        page_name = response.css('div.product__title h1::text').get()
        if page_name:
            name = page_name.strip()
        # Price (fallback to passed value)
        page_price = response.css('.price-item--sale::text, .price-item--regular::text').get()
        if page_price:
            price = page_price.strip()

        # Description/Overview
        description = response.css('meta[name="description"]::attr(content)').get()
        if not description:
            description = response.css('meta[property="og:description"]::attr(content)').get()

        # Brand Name
        brand = response.css('meta[property="og:site_name"]::attr(content)').get() or 'de Buyer'

        # Try to extract variants JSON from JS
        variants = []
        variants_json = None
        m = re.search(r'const variants = (\[.*?\]);', response.text, re.DOTALL)
        if m:
            try:
                variants_json = m.group(1)
                variants = json.loads(variants_json)
            except Exception:
                variants = []

        # Fallback: try to extract from window.customerHub.activeProduct
        if not variants:
            m2 = re.search(r'window.customerHub.activeProduct\s*=\s*{.*?variants:\s*(\[.*?\])[,\n]', response.text, re.DOTALL)
            if m2:
                try:
                    variants_json = m2.group(1)
                    variants = json.loads(variants_json)
                except Exception:
                    variants = []

        # Use the first variant for most fields
        variant = variants[0] if variants else {}
        sku = variant.get('sku') or response.css('p.product__sku::text').re_first(r'\d+[\.\d]*')
        barcode = variant.get('barcode')
        diameter = variant.get('title')
        image = None
        if variant.get('featured_image') and variant['featured_image'].get('src'):
            image = response.urljoin(variant['featured_image']['src'].replace('//', 'https://'))
        elif variant.get('imageUrl'):
            image = variant['imageUrl']
        else:
            # fallback to first image in HTML
            images = response.css('div.product-media-container img::attr(src), li.product__media-item img::attr(src)').getall()
            for img in images:
                if img:
                    image = response.urljoin(img)
                    break

        # Item No. and Mfr Catalog No. are both SKU
        item_no = sku
        mfr_catalog_no = sku

        # EAN Code and Barcode are both barcode
        ean_code = barcode

        # Item Description and Overview are both description
        item_description = description
        overview = description

        desc_html = response.css('div.product__description').get() or ''
        def extract_dimension(pattern, html):
            m = re.search(pattern, html, re.IGNORECASE)
            return m.group(1).strip() if m else None
        length = extract_dimension(r'Length:?\s*([\d\.]+\s*(?:cm|mm|in|inch|"))', desc_html)
        width = extract_dimension(r'Width:?\s*([\d\.]+\s*(?:cm|mm|in|inch|"))', desc_html)
        height = extract_dimension(r'Height:?\s*([\d\.]+\s*(?:cm|mm|in|inch|"))', desc_html)
        volume = extract_dimension(r'Volume:?\s*([\d\.]+\s*(?:l|ml|oz))', desc_html)
        material = extract_dimension(r'Material:?\s*([A-Za-z\s]+)', desc_html)
        color = extract_dimension(r'Color:?\s*([A-Za-z\s]+)', desc_html)
        pattern_val = extract_dimension(r'Pattern:?\s*([A-Za-z\s]+)', desc_html)

        yield {
            'product_url': product_url or response.url,
            'name': name,
            'price': price,
            'item_no': item_no,
            'mfr_catalog_no': mfr_catalog_no,
            'brand_name': brand,
            'item_description': item_description,
            'image_link': image,
            'overview': overview,
            'length': length,
            'width': width,
            'height': height,
            'volume': volume,
            'diameter': diameter,
            'color': color,
            'material': material,
            'ean_code': ean_code,
            'pattern': pattern_val,
            'barcode': barcode,
        }
