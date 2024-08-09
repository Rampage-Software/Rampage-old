import os
import httpc
import random
import time
import click
from Tool import Tool
import concurrent.futures
from utils import Utils
import random
from PIL import Image
from config import ConfigType, Config

class GroupClothesStealer(Tool):
    def __init__(self, app):
        super().__init__("Group Clothes Stealer", "Steal clothes from a specific group", app)

        self.assets_files_directory = os.path.join(self.files_directory, "./assets")
        self.shirts_files_directory = os.path.join(self.files_directory, "./assets/shirts")
        self.pants_files_directory = os.path.join(self.files_directory, "./assets/pants")

        self.cache_template_path = os.path.join(self.cache_directory, "asset-template.png")

        Utils.ensure_directories_exist([self.assets_files_directory, self.shirts_files_directory, self.pants_files_directory])

    def run(self):
        self.group_id = ConfigType.integer(self.config, "group_id")
        self.remove_trademark = ConfigType.boolean(self.config, "remove_trademark")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")
        self.timeout = ConfigType.integer(self.config, "timeout")
        self.max_generations = Config.input_max_generations()

        if not self.group_id or not self.max_generations or not self.timeout:
            raise Exception("group_id, max_generations and timeout must not be null.")

        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]
        click.secho("Collecting assets from group... ", fg="green")
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
        req_url = f"https://catalog.roblox.com/v1/search/items"
        req_headers = httpc.get_roblox_headers(user_agent)
        req_params = {
            "category": "All",
            "creatorTargetId": self.group_id,
            "creatorType": "Group",
            "cursor": "",
            "limit": 50,
            "sortOrder": "Desc",
            "sortType": "Updated"
        }

        response = client.get(req_url, headers=req_headers, params=req_params)
        result = response.json()
        data = result.get("data")
        cursor = result.get("nextPageCursor")

        return data, cursor

    @Utils.handle_exception(3, False)
    def check_is_shirt(self, data, csrf_token, user_agent, client):
        req_url = f"https://catalog.roblox.com/v1/catalog/items/details"
        req_headers = httpc.get_roblox_headers(user_agent, csrf_token)
        req_json = {
            "items": data
        }

        response = client.post(req_url, headers=req_headers, json=req_json)

        if response.status_code != 200:
            raise Exception(Utils.return_res(response))

        data = response.json()

        try:
            items = data["data"]
        except KeyError:
            raise Exception("Failed to get items." + Utils.return_res(response))

        # remove items that are not shirts or pants
        items = [item for item in items if item.get("assetType") in [11, 12]]

        return items

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
            csrf_token = self.get_csrf_token(None, client)

            while len(assets) < self.max_generations:
                data, cursor = self.get_assets_page(cursor, client, user_agent)

                data = self.check_is_shirt(data, csrf_token, user_agent, client)

                assets += data

                if not cursor:
                    break

                click.secho(f"Collected {len(assets)} assets, next cursor: {cursor[:5]}...", fg="blue")

                if len(assets) < self.max_generations:
                    click.secho(f"Sleeping for {self.timeout} seconds...", fg="yellow")
                    time.sleep(self.timeout)

        assets = assets[:self.max_generations]

        click.secho(f"Finished collecting {len(assets)} assets", fg="green")

        return assets

    @Utils.handle_exception(3)
    def download_asset(self, asset, proxies_line):
        """
        Download an asset
        """
        # get directory
        directory = self.shirts_files_directory if asset.get("assetType") == 11 else self.pants_files_directory

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
        template = Image.open(self.cache_template_path)

        trademarked_img.paste(template, (0,0), mask = template)
        trademarked_img.save(asset_path)

    @Utils.handle_exception(2, False)
    def ensure_template_exists(self):
        if not os.path.exists(self.cache_template_path):
            with open(self.cache_template_path, 'wb') as f:
                png = httpc.get(f'https://i.ibb.co/cXJs5Rj/asset-template.png').content
                f.write(png)
