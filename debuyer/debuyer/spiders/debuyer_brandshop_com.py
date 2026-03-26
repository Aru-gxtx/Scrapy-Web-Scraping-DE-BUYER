import scrapy


class DebuyerBrandshopComSpider(scrapy.Spider):
    name = "debuyer-brandshop.com"
    allowed_domains = ["www.debuyer-brandshop.com"]
    start_urls = ["https://www.debuyer-brandshop.com"]

    def parse(self, response):
        category_links = response.css('.image-text-gallery-card a.cms-image-link::attr(href)').getall()
        for link in category_links:
            yield response.follow(link, callback=self.parse_category)

    def parse_category(self, response):
        product_links = response.css('.cms-listing-col[role="listitem"] a.product-name::attr(href)').getall()
        for link in product_links:
            yield response.follow(link, callback=self.parse_product)

        next_page = response.css('li.page-item.page-next > a.page-link::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse_category)

    def parse_product(self, response):
        def extract_first(selector, default=None):
            return response.css(selector).get(default=default)

        def extract_text(selector, default=None):
            return response.css(selector).xpath('string()').get(default=default).strip() if response.css(selector) else default

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
        import re
        material_match = re.search(r'<li><strong>Material:</strong>\s*([^<]+)</li>', response.text)
        if material_match:
            material = material_match.group(1).strip()
        if not material and overview:
            mat_idx = overview.lower().find('material:')
            if mat_idx != -1:
                material = overview[mat_idx+9:].split('\n')[0].strip()

        length = width = height = volume = diameter = None
        dim_match = re.search(r'H\s*=\s*([\d.,]+)\s*cm\s*-\s*Ø\s*([\d.,]+)\s*cm', response.text)
        if dim_match:
            height = dim_match.group(1)
            diameter = dim_match.group(2)
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

        ean_code = extract_first('meta[itemprop="gtin13"]::attr(content)')
        barcode = ean_code
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
