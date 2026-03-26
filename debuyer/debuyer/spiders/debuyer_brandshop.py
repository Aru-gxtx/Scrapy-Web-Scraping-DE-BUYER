import scrapy


class DebuyerBrandshopSpider(scrapy.Spider):
    name = "debuyer-brandshop"
    allowed_domains = ["www.debuyer-brandshop.com"]
    start_urls = ["https://www.debuyer-brandshop.com/en/search?p=1&order=score&search=de+Buyer"]

    def parse(self, response):
        # Extract product containers
        products = response.css('div.cms-listing-col[role="listitem"]')
        for product in products:
            # Extract product detail page link
            detail_url = product.css('a.product-name::attr(href)').get()
            if detail_url:
                yield response.follow(detail_url, callback=self.parse_product)

        # Pagination: follow next page if available
        # The correct selector for the next page button is 'li.page-item.page-next > a.page-link::attr(href)'
        next_page = response.css('li.page-item.page-next > a.page-link::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_product(self, response):
        def extract_first(selector, default=None):
            return response.css(selector).get(default=default)

        def extract_text(selector, default=None):
            return response.css(selector).xpath('string()').get(default=default).strip() if response.css(selector) else default

        # Helper to extract property from the properties table
        def extract_property(label):
            rows = response.css('.product-detail-properties-table tr')
            for row in rows:
                th = row.css('th::text').get()
                if th and label.lower() in th.lower():
                    return row.css('td span::text, td::text').get(default='').strip()
            return None

        # Main fields
        item_no = extract_first('.product-detail-ordernumber[itemprop="sku"]::text')
        mfr_catalog_no = extract_first('.product-detail-manufacturer-number::text')
        brand_name = extract_first('.product-detail-manufacturer-name::text')
        item_desc = extract_text('.product-detail-short-description')
        image_link = extract_first('.gallery-slider-image::attr(src)')
        overview = extract_text('.product-detail-description-text')
        color = extract_property('Colour')
        material = None
        # Try to extract material from overview
        import re
        material_match = re.search(r'<li><strong>Material:</strong>\s*([^<]+)</li>', response.text)
        if material_match:
            material = material_match.group(1).strip()
        # Fallback: look for Material in overview text
        if not material and overview:
            mat_idx = overview.lower().find('material:')
            if mat_idx != -1:
                material = overview[mat_idx+9:].split('\n')[0].strip()

        # Extract dimensions from properties or overview
        length = width = height = volume = diameter = None
        # Try to parse from overview <ul> (e.g., H = 21 cm - Ø 5 cm)
        dim_match = re.search(r'H\s*=\s*([\d.,]+)\s*cm\s*-\s*Ø\s*([\d.,]+)\s*cm', response.text)
        if dim_match:
            height = dim_match.group(1)
            diameter = dim_match.group(2)
        # Try to extract from properties table if available
        if not color:
            color = extract_property('Color')
        if not diameter:
            diameter = extract_property('Diameter')
        if not height:
            height = extract_property('Height')
        if not length:
            length = extract_property('Length')
        if not width:
            width = extract_property('Width')
        if not volume:
            volume = extract_property('Volume')

        # EAN Code, Pattern, Barcode: try meta tags or properties
        ean_code = extract_first('meta[itemprop="gtin13"]::attr(content)')
        barcode = ean_code  # Often the same
        pattern = extract_property('Pattern')

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
