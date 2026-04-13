# Scrapy Web Scraping DE BUYER
Web scraper using scrapy for DE BUYER cookwares _(pls don't block me cloufare, json, captcha fr)_

## Populate the Excel workbook

Use `populate_de_buyer_xlsx.py` to create a new workbook that keeps `sources/DE BUYER.xlsx` untouched and appends matched product data starting at column O.
The script matches rows by MFR and prefers the scraped JSON exports in `debuyer/` for richer product fields, with `debuyer/all_products.xlsx` as a fallback lookup.

```bash
python populate_de_buyer_xlsx.py --source sources/DE BUYER.xlsx --products debuyer/all_products.xlsx --output sources/DE BUYER_populated.xlsx
```
