import scrapy 
import re
from scrapy.crawler import CrawlerProcess
import argparse
import os 
from src.utils import del_file_if_exists


class ScieloSpider(scrapy.Spider):
    name = "scielo_spider"
    custom_settings = {
        'DOWNLOAD_DELAY': 3, # amount of time (in secs) waiting before downloading consecutive pages
        'FEED_EXPORT_ENCODING': 'utf-8'
    }


    def start_requests(self):
        yield scrapy.Request(self.start_url)

    def parse(self, response):
        ITEM_SELECTOR = 'div.results > div.item'
        TOTAL_NUM_PAGES_SELECTOR = './/input[@class="form-control goto_page"]/following-sibling::text()'
        CURRENT_PAGE_SELECTOR = './/input[@class="form-control goto_page"]/@value'

        total_num_pages = response.xpath(TOTAL_NUM_PAGES_SELECTOR).extract_first()
        total_num_pages = int(total_num_pages.strip().replace("of", "").strip())
        current_page = int(response.xpath(CURRENT_PAGE_SELECTOR).extract_first())
        stop_page = self.stop_page if self.stop_page > 0 else total_num_pages

        print("Page {}/{} (stopping at {})".format(current_page, total_num_pages, stop_page))

        for publication in response.css(ITEM_SELECTOR):            
            DOI_SELECTOR = './/span[@class="DOIResults"]/a/text()'
            ABSTRACT_SELECTOR = './/div[@class="abstract"]'
            TEXT_URL_SELECTOR = './/a[@class="showTooltip"]/@href'
            DATE_SELECTOR = './/div[@class="line source"]/span[@style="margin: 0"]'

            doi_link = publication.xpath(DOI_SELECTOR).extract_first()
            if doi_link is None: 
                continue 
            doi = doi_link.replace("https://doi.org/", "").replace("/", "_")
            item = {"doi": doi}

            date = publication.xpath(DATE_SELECTOR)
            if len(date) != 2: # date should be month, year
                item["date"] = "unknown"
            else:
                month = date[0].xpath("text()").extract_first().strip()
                year = date[1].xpath("text()").extract_first().strip()[:-1]
                item["date"] = month + " " + year

            all_abstracts = publication.xpath(ABSTRACT_SELECTOR)
            if len(all_abstracts) == 0:
                continue
            for abstract in all_abstracts:
                abstract_id = abstract.xpath('@id').extract_first() # last two chars of @id indicate the language
                abstract_text = abstract.xpath('text()').extract_first()
                if abstract_text is not None:
                    abstract_text = abstract_text.strip()
                    if len(abstract_text) > 0:
                        item["abstract_" + abstract_id[-2:]] = abstract_text

            # If publication has no spanish or portuguese abstract, skip
            if not ("abstract_es" in item.keys() or "abstract_pt" in item.keys()):
                continue 
            
            text_url = publication.xpath(TEXT_URL_SELECTOR).extract_first()
            if text_url is None:
                continue 
            yield scrapy.Request(
                response.urljoin(text_url),
                callback=self.parse_page,
                meta={'item': item}
            )

        if current_page < stop_page: # there are still pages to crawl
            next_page = current_page + 1
            num_publications = int(re.search(".+&count=(\d+)&.+", response.url).group(1)) # num of publications to return
            next_url = response.url.replace(
                re.search(".+&(from=\d+)&.+", response.url).group(1),
                f"from={num_publications * current_page + 1}"
            ) # increment index of starting publication
            next_url = next_url.replace(f"page={current_page}", f"page={next_page}") # increment page number
            yield scrapy.Request(
                response.urljoin(next_url),
                callback=self.parse
            )

    
    def parse_page(self, response):
        item = response.meta['item']
        # The page can be in English, Portuguese or Spanish
        # We look for the HTML element that contains the link to the PDF 
        # It is indicated by either 'Download PDF (<lang>)' or '<lang> (pdf)'
        languages = ["Portuguese", "Português", "Portugués", "Spanish", "Espanhol", "Español"]
        pdf_url = None

        for lang in languages:
            # Brasilian and Public Health Scielo have a different interface from the rest
            if "www.scielo.br" in response.url or "www.scielosp.org" in response.url:
                PDF_URL_SELECTOR = f".//a[contains(text(), 'Download PDF ({lang})')]/@href"
            else:
                PDF_URL_SELECTOR = f".//a[contains(text(), '{lang} (pdf)')]/@href"
            pdf_url = response.xpath(PDF_URL_SELECTOR).extract_first() 
            # There is generally only one PDF, grab the first one 
            if pdf_url is not None:
                break 

        # We look for the webpage's URL domain and prepend it to the PDF link
        m = re.search('(https?://[A-Za-z_0-9.-]+).*', response.url)
        if m:
            url_domain = m.group(1)
            if pdf_url is not None:
                item['pdf_url'] = url_domain + pdf_url
        else:
            item['pdf_url'] = None 
        
        return item

def crawl_scielo(args):           
    process = CrawlerProcess(settings={
        'USER_AGENT': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        "FEEDS": {
            args.output_file: {"format": "jsonlines"}
        }
        
    })

    process.crawl(ScieloSpider, start_url=args.start_url, stop_page=args.stop_page)
    process.start()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--start_url",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--output_file",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--stop_page",
        type=int,
        default=-1
    )
    parser.add_argument(
        "--overwrite_output", 
        action="store_true", 
        help="Overwrite the output file."
    )

    args = parser.parse_args()

    if os.path.exists(args.output_file):
        if args.overwrite_output:
            del_file_if_exists(args.output_file)
        else:
            raise ValueError(
                f"Output file ({args.output_file}) already exists and is not empty. Use --overwrite_output to overcome."
            )

    crawl_scielo(args)