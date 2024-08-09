import concurrent.futures
import httpc
import os
import re
import random
from Tool import Tool
from utils import Utils
from config import ConfigType, Config

class AdsScraper(Tool):
    def __init__(self, app):
        super().__init__("Ads Scraper", "Scrapes ads.", app)

        self.ad_formats = ["vertical", "horizontal", "square"]

        self.assets_files_directory = os.path.join(self.files_directory, "./assets")
        self.ads_directory = os.path.join(self.assets_files_directory, "./ads")
        self.vertical_ads_directory = os.path.join(self.ads_directory, "./vertical")
        self.horizontal_ads_directory = os.path.join(self.ads_directory, "./horizontal")
        self.square_ads_directory = os.path.join(self.ads_directory, "./square")

        Utils.ensure_directories_exist([self.assets_files_directory, self.ads_directory, self.vertical_ads_directory, self.horizontal_ads_directory, self.square_ads_directory])

    def run(self):
        self.ad_format = ConfigType.string(self.config, "ad_format")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")
        self.max_generations = Config.input_max_generations()

        if self.ad_format not in self.ad_formats and self.ad_format != "random":
            raise Exception(f"Invalid ad type \"{self.ad_format}\". Must be either \"random\", \"vertical\", \"horizontal\" or \"square\"")

        self.is_random = self.ad_format == "random"

        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        worked_gen = 0
        failed_gen = 0
        total_gen = self.max_generations

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.scrape_ad, random.choice(proxies_lines)) for gen in range(self.max_generations)]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    has_generated, response_text = future.result()
                except Exception as e:
                    has_generated, response_text = False, str(e)

                if has_generated:
                    worked_gen += 1
                else:
                    failed_gen += 1

                self.print_status(worked_gen, failed_gen, total_gen, response_text, has_generated, "Scraped")

    @Utils.handle_exception()
    def scrape_ad(self, proxies_line):
        if self.is_random:
            self.ad_format = random.choice(self.ad_formats)

        if (self.ad_format == "vertical"):
            directory = self.vertical_ads_directory
            scrape_url = "https://www.roblox.com/user-sponsorship/2"
        elif (self.ad_format == "horizontal"):
            directory = self.horizontal_ads_directory
            scrape_url = "https://www.roblox.com/user-sponsorship/1"
        elif (self.ad_format == "square"):
            directory = self.square_ads_directory
            scrape_url = "https://www.roblox.com/user-sponsorship/3"

        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()
            headers = httpc.get_roblox_headers(user_agent)

            result = client.get(scrape_url, headers=headers)
            response = result.text

            # thanks to github.com/MyDiscordBotcom/Roblox-Ad-Scraper for the regex
            regex = '<img src=\"(.*?)\" alt=\"(.*?)\"'
            ad_img_url = re.search(regex, response).group(1)
            ad_img = client.get(ad_img_url, headers=headers).content
            ad_alt = re.search(regex, response).group(2)

            asset_path = os.path.join(directory, f"{ad_alt}.png")

            with open(asset_path, 'wb') as f:
                f.write(ad_img)

        return True, f"Scraped ad \"{ad_alt}\""