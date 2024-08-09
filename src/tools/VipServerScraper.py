import re
import httpc
import random
from Tool import Tool
from utils import Utils
import concurrent.futures
from config import ConfigType

class VipServerScraper(Tool):
    def __init__(self, app):
        super().__init__("Vip Server Scraper", "Scrape Roblox VIP servers", app)

    def run(self):
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")

        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]
        pages_game = self.get_pages_game(random.choice(proxies_lines))

        req_sent = 0
        req_failed = 0
        total_req = len(pages_game)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.get_vip_link, page_game, random.choice(proxies_lines)) for page_game in pages_game]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    is_success, response_text = future.result()
                except Exception as e:
                    is_success, response_text = False, str(e)

                if is_success:
                    req_sent += 1
                else:
                    req_failed += 1

                self.print_status(req_sent, req_failed, total_req, response_text, is_success, "Scraped")

    @Utils.handle_exception(2)
    def get_pages_game(self, proxies_line):
        user_agent = httpc.get_random_user_agent()
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            req_url = "https://robloxvipservers.net/servers"
            req_headers = httpc.get_roblox_headers(user_agent)

            response = client.get(req_url, headers=req_headers)

            if response.status_code != 200:
                raise Exception(Utils.return_res(response))

        pages = re.findall(r"games/game_page\?gameid=(\d+)", response.text)

        return pages

    @Utils.handle_exception()
    def get_vip_link(self, page_game, proxies_line):
        page_id = page_game.split("/")[0]

        user_agent = httpc.get_random_user_agent()
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            req_url = f"https://robloxvipservers.net/manager/manager_template?request={page_id}"
            req_headers = httpc.get_roblox_headers(user_agent)

            response = client.get(req_url, headers=req_headers)

        try:
            vip_link = re.findall(r'\'countdown\' href="(.+?)"', response.text)[0]
        except IndexError:
            return False, "VIP server link not found"

        try:
            game_name = re.findall(r'<h1>(.+?)</h1>', response.text)[0]
        except IndexError:
            return False, "Game Name not found"

        return (response.status_code == 200), f"{game_name}\x1B[0;0m\n{vip_link}"
