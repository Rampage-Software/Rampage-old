import os
import httpc
import random
from Tool import Tool
import concurrent.futures
from utils import Utils
import random
from PIL import Image
from config import ConfigType, Config

class MassClothesDownloader(Tool):
    def __init__(self, app):
        super().__init__("Mass Clothes Downloader", "Download most trending clothes from Roblox catalog", app)

        self.assets_files_directory = os.path.join(self.files_directory, "./assets")
        self.shirts_files_directory = os.path.join(self.files_directory, "./assets/shirts")
        self.pants_files_directory = os.path.join(self.files_directory, "./assets/pants")

        self.template_path = os.path.join(self.assets_files_directory, "template.png")

        Utils.ensure_directories_exist([self.assets_files_directory, self.shirts_files_directory, self.pants_files_directory])

    def run(self):
        self.remove_trademark = ConfigType.boolean(self.config, "remove_trademark")
        self.sorts = ["relevance", "favouritedalltime", "favouritedallweek", "favouritedallday", "bestsellingalltime", "bestsellingweek", "bestsellingday", "recentlycreated", "pricehightolow", "pricelowtohigh"]
        self.sort = ConfigType.string(self.config, "sort")
        self.keyword = ConfigType.string(self.config, "keyword")
        self.asset_type = ConfigType.string(self.config, "asset_type")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")
        self.max_generations = Config.input_max_generations()

        if not self.keyword:
            raise Exception("keyword must not be null.")

        if self.sort not in self.sorts:
            raise Exception(f"Invalid sort config key \"{self.sort}\"")

        if self.asset_type not in ["shirt", "pants"]:
            raise Exception("Invalid asset type. Must be either \"shirt\" or \"pants\"")

        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]
        assets = self.get_assets_amount(random.choice(proxies_lines))

        req_worked = 0
        req_failed = 0
        total_req = len(assets)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.download_asset, asset, random.choice(proxies_lines)) for asset in assets]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    has_downloaded, response_text = future.result()
                except Exception as err:
                    has_downloaded, response_text = False, str(err)

                if has_downloaded:
                    req_worked += 1
                else:
                    req_failed += 1

                self.print_status(req_worked, req_failed, total_req, response_text, has_downloaded, "Downloaded")

    @Utils.handle_exception(2, False)
    def get_assets_page(self, cursor, client, user_agent):
        """
        Get a page of assets
        """
        self.asset_name = "ClassicShirts" if self.asset_type == "shirt" else "ClassicPants"

        salesTypeFilter = None
        sortAggregation = None
        sortType = None

        if self.sort == "relevance":
            salesTypeFilter = 1
        elif self.sort == "favouritedalltime":
            salesTypeFilter = 1
            sortAggregation = 5
            sortType = 1
        elif self.sort == "favouritedallweek":
            salesTypeFilter = 1
            sortAggregation = 3
            sortType = 1
        elif self.sort == "favouritedallday":
            salesTypeFilter = 1
            sortAggregation = 1
            sortType = 1
        elif self.sort == "bestsellingalltime":
            salesTypeFilter = 1
            sortAggregation = 5
            sortType = 2
        elif self.sort == "bestsellingweek":
            salesTypeFilter = 1
            sortAggregation = 3
            sortType = 2
        elif self.sort == "bestsellingday":
            salesTypeFilter = 1
            sortAggregation = 1
            sortType = 2
        elif self.sort == "recentlycreated":
            salesTypeFilter = 1
            sortType = 3
        elif self.sort == "pricehightolow":
            salesTypeFilter = 1
            sortType = 5
        elif self.sort == "pricelowtohigh":
            salesTypeFilter = 1
            sortType = 4

        req_url = f"https://catalog.roblox.com/v1/search/items"
        req_headers = httpc.get_roblox_headers(user_agent)
        req_params = {
            "category": "Clothing",
            "limit": 120,
            "minPrice": 5,
            "salesTypeFilter": salesTypeFilter,
            "sortAggregation": sortAggregation,
            "sortType": sortType,
            "subcategory": self.asset_name,
            "cursor": cursor,
            "keyword": self.keyword
        }

        response = client.get(req_url, headers=req_headers, params=req_params)

        if response.status_code != 200:
            raise Exception("Failed to get assets page. " + Utils.return_res(response))

        result = response.json()

        data = result.get("data")
        cursor = result.get("nextPageCursor")

        return data, cursor

    @Utils.handle_exception(3)
    def get_assets_amount(self, proxies_line):
        """
        Get x amount of assets
        """
        assets = []
        cursor = None

        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None
        user_agent = httpc.get_random_user_agent()

        with httpc.Session(proxies=proxies) as client:
            while len(assets) < self.max_generations:
                data, cursor = self.get_assets_page(cursor, client, user_agent)

                if self.asset_type == "shirt":
                    for asset in data:
                        asset["shirt"] = True

                assets += data
                random.shuffle(assets)

                if not cursor:
                    break

        assets = assets[:self.max_generations]
        return assets

    @Utils.handle_exception(3)
    def download_asset(self, asset, proxies_line):
        """
        Download an asset
        """
        # get directory
        directory = self.shirts_files_directory if asset.get("shirt") else self.pants_files_directory

        asset_id = asset["id"]

        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()
            headers = httpc.get_roblox_headers(user_agent)

            assetdelivery = client.get(f'https://assetdelivery.roblox.com/v1/assetId/{asset_id}', headers=headers).json()['location']
            assetid = str(client.get(assetdelivery, headers=headers).content).split('<url>http://www.roblox.com/asset/?id=')[1].split('</url>')[0]
            png = client.get(f'https://assetdelivery.roblox.com/v1/assetId/{assetid}', headers=headers).json()['location']
            image = client.get(png, headers=headers).content
            asset_path = os.path.join(directory, f"{asset_id}.png")

        with open(asset_path, 'wb') as f:
            f.write(image)

        if self.remove_trademark:
            self.remove_trademark_from_asset(asset_path)

        return True, "Generated in files/assets"

    @Utils.handle_exception(2, False)
    def remove_trademark_from_asset(self, asset_path):
        self.ensure_template_exists()

        trademarked_img = Image.open(asset_path)
        template = Image.open(self.template_path)

        trademarked_img.paste(template, (0,0), mask = template)
        trademarked_img.save(asset_path)

    @Utils.handle_exception(2, False)
    def ensure_template_exists(self):
        if not os.path.exists(self.template_path):
            with open(self.template_path, 'wb') as f:
                png = httpc.get(f'https://i.ibb.co/cXJs5Rj/asset-template.png').content
                f.write(png)
