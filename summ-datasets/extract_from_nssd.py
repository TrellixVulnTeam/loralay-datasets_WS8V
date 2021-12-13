import scrapy 
import re 
from scrapy.crawler import CrawlerProcess
import argparse
import os 
from src.utils import del_file_if_exists
import json
import random
import base64
import urllib

class NSSDSpider(scrapy.Spider):
    name = "nssd_spider"
    custom_settings = {
        'DOWNLOAD_DELAY': 3, # amount of time (in secs) waiting before downloading consecutive pages
        'FEED_EXPORT_ENCODING': 'utf-8',
        'LOG_LEVEL': 'INFO',
        'USER_AGENTS': [
            ('Mozilla/5.0 (X11; Linux x86_64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/57.0.2987.110 '
            'Safari/537.36'),  # chrome
            ('Mozilla/5.0 (X11; Linux x86_64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/61.0.3163.79 '
            'Safari/537.36'),  # chrome
            ('Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:55.0) '
            'Gecko/20100101 '
            'Firefox/55.0')  # firefox
        ]
    }

    def start_requests(self):
        ids_crawled = None 
        if self.resume_crawl is not None:
            ids_crawled = []
            with open(self.output_file) as f:
                for line in f:
                    item = json.loads(line)
                    ids_crawled.append(item["id"])
            print("Resuming crawl from {}... Skipping {} publications".format(
                self.start_url,
                len(ids_crawled),
            ))

        yield scrapy.Request(self.start_url, meta={'ids_crawled': ids_crawled}, headers={"User-Agent": random.choice(self.custom_settings['USER_AGENTS'])})
 

    def parse(self, response):
        ITEM_SELECTOR = 'div.simple_list > table > tr'
        TOTAL_NUM_PAGES_SELECTOR = './/span[@class="total"]/text()'
        CURRENT_PAGE_SELECTOR = './/input[@id="txtCurrentPageIndex"]/@value'

        current_page = int(response.xpath(CURRENT_PAGE_SELECTOR).extract_first())
        total = response.xpath(TOTAL_NUM_PAGES_SELECTOR).extract_first()
        total_num_pages = int(re.search("当前 \d+\/(\d+) 页", total).group(1))
        stop_page = self.stop_page if self.stop_page > 0 else total_num_pages

        print("Page {}/{} (stopping at {})".format(current_page, total_num_pages, stop_page))
        print("\t" + response.url)
        
        for publication in response.css(ITEM_SELECTOR)[1:]:
            LINK_TO_DETAILS_SELECTOR = './td/a[@class="title"]'
            DOWNLOAD_LINK_SELECTOR = './/a[@class="downl"]/@href'
            
            link_to_details = publication.xpath(LINK_TO_DETAILS_SELECTOR + '/@href').extract_first()
            pub_id = re.search(
                '\/articles\/article_detail\.aspx\?id=(([A-Za-z_0-9.-]+).*)', 
                link_to_details
            ).group(1)
            download_suffix = publication.xpath(DOWNLOAD_LINK_SELECTOR).extract_first()
            if download_suffix is None:
                continue
            download_link = 'http://www.nssd.cn' + download_suffix

            item = {
                "id": pub_id,
                "download_link": download_link,
            }

            if (
                response.meta["ids_crawled"] is not None 
                and item["id"] in response.meta["ids_crawled"]
            ):
                print("Skipping ", item["id"])
                continue 

            yield scrapy.Request(
                response.urljoin('http://www.nssd.cn' + link_to_details),
                callback=self.parse_details_page,
                meta={'item': item},
                headers={"User-Agent": random.choice(self.custom_settings['USER_AGENTS'])}
            )


        if current_page < stop_page:
            raw_q = re.search("http:\/\/www\.nssd\.cn\/articles\/articlesearch\.aspx\?q=(.*?)&", response.url).group(1)
            q = raw_q.replace("%3D", "=")
            q = q.replace("%2B", "+")
            # b = base64.b64decode(q).decode('utf-8')
            b = base64.b64decode(q.encode('utf-8') + b'==')
            json_obj = json.loads(b.decode('utf-8', 'ignore'))
            json_obj['page'] = int(json_obj['page'])
            json_obj['page'] += 1
            print(json_obj)
            new_q = urllib.parse.quote(
                base64.b64encode(json.dumps(json_obj, separators=(',', ':')).encode('utf-8'))
            )
            next_url = response.url.replace(raw_q, new_q)

            yield scrapy.Request(
                response.urljoin(next_url),
                callback=self.parse,
                meta=response.meta,
                headers={"User-Agent": random.choice(self.custom_settings['USER_AGENTS'])}
            )

    def parse_details_page(self, response):
        item = response.meta['item']

        item['abstract'] = response.xpath(".//p[@id='allAbstrack']/text()").extract_first()
        
        if item['abstract'] is not None:
            item['abstract'] = item['abstract'].strip()
        else:
            item['abstract'] = ''

        return item

def crawl_nssd(args):
    process = CrawlerProcess(settings={
        "FEEDS": {
            args.output_file: {"format": "jsonlines"}
        }
    })

    process.crawl(
        NSSDSpider, 
        start_url=args.start_url, 
        stop_page=args.stop_page,
        resume_crawl=args.resume_crawl,
        output_file=args.output_file
    )
    process.start()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--start_url",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--collection_prefix",
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
    parser.add_argument(
        "--resume_crawl", 
        action="store_true", 
    )

    args = parser.parse_args()

    if args.resume_crawl and args.overwrite_output:
        raise ValueError(
            f"Cannot use --resume and --overwrite_output at the same time."
        )

    if os.path.exists(args.output_file) and not args.resume_crawl:
        if args.overwrite_output:
            del_file_if_exists(args.output_file)
        else:
            raise ValueError(
                f"Output file ({args.output_file}) already exists and is not empty. Use --overwrite_output to overcome."
            )

    crawl_nssd(args)