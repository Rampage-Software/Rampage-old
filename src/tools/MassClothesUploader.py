import os
import httpc
import random
from Tool import Tool
import concurrent.futures
from utils import Utils
import time
from config import ConfigType

class MassClothesUploader(Tool):
    def __init__(self, app):
        super().__init__("Mass Clothes Uploader", "Integrates with MassClothesDownloader to upload clothing", app)

        self.assets_files_directory = os.path.join(self.files_directory, "./assets")
        self.shirts_files_directory = os.path.join(self.files_directory, "./assets/shirts")
        self.pants_files_directory = os.path.join(self.files_directory, "./assets/pants")

        Utils.ensure_directories_exist([self.assets_files_directory, self.shirts_files_directory, self.pants_files_directory])

    def run(self):
        self.cookie = ConfigType.string(self.config, "cookie")
        self.robux_price = ConfigType.integer(self.config, "robux_price")
        self.description = ConfigType.string(self.config, "description")
        self.group_id = ConfigType.integer(self.config, "group_id")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")
        self.timeout = ConfigType.integer(self.config, "timeout")

        if not self.cookie or not self.robux_price or not self.description or not self.group_id or self.timeout is None:
            raise Exception("cookie, robux_price, description, group_id and timeout must not be null.")

        if self.robux_price < 5:
            raise Exception("Robux price must be at least 5.")

        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        shirts = os.listdir(self.shirts_files_directory)
        pants = os.listdir(self.pants_files_directory)
        assets = [{"file": shirt, "type": "shirt"} for shirt in shirts] + [{"file": pant, "type": "pant"} for pant in pants]

        if len(assets) == 0:
            raise Exception("No assets found. Make sure to download some first")

        req_worked = 0
        req_failed = 0
        total_req = len(assets)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.upload_asset, asset, random.choice(proxies_lines)) for asset in assets]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    has_uploaded, response_text = future.result()
                except Exception as err:
                    has_uploaded, response_text = False, str(err)

                if has_uploaded:
                    req_worked += 1
                else:
                    req_failed += 1

                self.print_status(req_worked, req_failed, total_req, response_text, has_uploaded, "Uploaded")

    @Utils.handle_exception()
    def upload_asset(self, asset, proxies_line):
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        time.sleep(self.timeout)

        with httpc.Session(proxies=proxies) as client:
            csrf_token = self.get_csrf_token(self.cookie, client)

            asset_file = asset["file"]
            asset_id = asset_file.replace(".png", "")
            asset_name = self.get_asset_name(asset_id, client, csrf_token)
            asset_type = asset["type"]
            asset_path = os.path.join(self.assets_files_directory, f"./{asset_type}s/{asset_file}")

            user_agent = httpc.get_random_user_agent()

            req_json = {
                "displayName": asset_name,
                "description": self.description,
                "assetType": "Shirt" if asset_type == "shirt" else "Pants",
                "creationContext":{
                    "creator": {
                        "groupId": self.group_id
                    },
                    "expectedPrice": 10
                }
            }

            req_url = "https://apis.roblox.com/assets/user-auth/v1/assets"
            req_cookies = { ".ROBLOSECURITY": self.cookie }

            req_headers = httpc.get_roblox_headers(user_agent, csrf_token)
            del req_headers["Content-Type"]

            with open(asset_path, "rb") as f:
                image_file = f.read()

            files = {
                "fileContent": ("robloxasset.png", image_file, "image/png"),
                "request": (None, str(req_json))
            }

            result = client.post(req_url, headers=req_headers, cookies=req_cookies, json=req_json, files=files)

            if (result.status_code != 200):
                if "is fully moderated." in result.text:
                    os.remove(asset_path)
                    return False, "Asset was moderated and deleted. " + Utils.return_res(result)

                return False, "Unable to upload asset. "+ Utils.return_res(result)

            response = result.json()

            operationId = response["operationId"]
            done = response["done"]

            # delete the img file
            os.remove(asset_path)

            while (done is not True):
                done, response = self.get_asset_id(operationId, client, user_agent)
                if (done is True):
                    asset_id = response["assetId"]
                else:
                    time.sleep(1)

            return self.publish_asset(asset_id, client, csrf_token, user_agent)

    @Utils.handle_exception(3, False)
    def publish_asset(self, asset_id, client, csrf_token, user_agent):
        req_url = f"https://itemconfiguration.roblox.com/v1/assets/{asset_id}/release"
        req_cookies = {".ROBLOSECURITY": self.cookie}
        req_json={"priceConfiguration": {"priceInRobux": self.robux_price}, "releaseConfiguration": {"saleAvailabilityLocations": [0, 1]}, "saleStatus": "OnSale"}

        req_headers = httpc.get_roblox_headers(user_agent, csrf_token)

        response = client.post(req_url, headers=req_headers, cookies=req_cookies, json=req_json)

        return (response.status_code == 200), Utils.return_res(response)

    @Utils.handle_exception(3, False)
    def get_asset_id(self, operationId, client, user_agent):
        req_url = f"https://apis.roblox.com/assets/user-auth/v1/operations/{operationId}"
        req_cookies = { ".ROBLOSECURITY": self.cookie }
        req_headers = httpc.get_roblox_headers(user_agent)

        result = client.get(req_url, headers=req_headers, cookies=req_cookies)
        if result.status_code != 200:
            Utils.return_res(result)

        response = result.json()
        done = response["done"]
        response = response.get("response") if done else False

        return done, response

    @Utils.handle_exception(3, False)
    def get_asset_name(self, asset_id, client, csrf_token):
        user_agent = httpc.get_random_user_agent()

        req_url = "https://catalog.roblox.com/v1/catalog/items/details"
        req_headers = httpc.get_roblox_headers(user_agent, csrf_token)
        req_json = {
          "items": [
            {
              "itemType": "Asset",
              "id": asset_id,
              "key":f"Asset_{asset_id}",
              "thumbnailType":"Asset"
            }
          ]
        }
        req_cookies = { ".ROBLOSECURITY": self.cookie }

        result = client.post(req_url, headers=req_headers, json=req_json, cookies=req_cookies)

        response = result.json()

        try:
            asset_name = response["data"][0]['name']
        except:
            raise Exception(f"Could not get asset name. {Utils.return_res(result)}")

        return asset_name