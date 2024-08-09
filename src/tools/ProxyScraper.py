from Tool import Tool
import concurrent.futures
import httpc
import re
from data.proxy_sites import proxy_sites
from utils import Utils
from config import ConfigType

class ProxyScraper(Tool):
    def __init__(self, app):
        super().__init__("Proxy Scraper", "Scrapes proxies from a list of websites", app)

    def run(self):
        self.max_sites = ConfigType.integer(self.config, "max_sites")
        self.custom_sites = ConfigType.list(self.config, "custom_sites")
        self.max_threads = ConfigType.integer(self.config, "max_threads")

        # open proxies file to start writing in it
        f = open(self.proxies_file_path, 'a')

        final_proxy_sites = proxy_sites if self.custom_sites == None else self.custom_sites
        max_proxy_sites = final_proxy_sites[:self.max_sites]

        working_req = 0
        failed_req = 0
        total_req = len(max_proxy_sites)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.scrape_proxies, url) for url in max_proxy_sites]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    is_working, response_text, proxies = future.result()
                except Exception as e:
                    is_working, response_text = False, str(e)

                if is_working:
                    working_req += 1

                    for proxy in proxies:
                        f.write(proxy+"\n")

                    f.flush()
                else:
                    failed_req += 1

                self.print_status(working_req, failed_req, total_req, response_text, is_working, "Proxy sites scraped")

        f.close()

        # remove duplicates
        with open(self.proxies_file_path, 'r+') as f:
            proxies = f.readlines()
            proxies = [*set(proxies)]
            f.seek(0)
            f.truncate()
            f.writelines(proxies)

    @Utils.handle_exception()
    def scrape_proxies(self, proxy_site_url:str):
        """
        Scrapes proxies from a proxy site
        """
        req = httpc.get(proxy_site_url)
        res = req.text
        proxies_list = re.findall('(?:[\d]{1,3})\.(?:[\d]{1,3})\.(?:[\d]{1,3})\.(?:[\d]{1,3})\:(?:[\d]{2,5})', res)

        return True, proxy_site_url, proxies_list