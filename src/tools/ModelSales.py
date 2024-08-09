import concurrent.futures
import httpc
import random
from Tool import Tool
from utils import Utils
from config import ConfigType, Config

class ModelSales(Tool):
    def __init__(self, app):
        super().__init__("Model Sales", "Buy your Roblox models tons of times", app)

    def run(self):
        self.asset_id = ConfigType.integer(self.config, "asset_id")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")
        self.max_generations = Config.input_max_generations()

        if not self.asset_id:
            raise Exception("asset_id must not be null.")

        cookies = self.get_cookies(self.max_generations)
        self.proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        req_sent = 0
        req_failed = 0
        total_req = len(cookies)

        product_id = self.get_product_id(random.choice(cookies), random.choice(self.proxies_lines))

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.buy_product, product_id, cookie, random.choice(self.proxies_lines)) for cookie in cookies]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    is_bought, response_text = future.result()
                except Exception as e:
                    is_bought, response_text = False, str(e)

                if is_bought:
                    is_success = True
                    req_sent += 1
                else:
                    is_success = False
                    req_failed += 1

                self.print_status(req_sent, req_failed, total_req, response_text, is_success, "Bought")

    @Utils.handle_exception(2)
    def get_product_id(self, cookie, proxies_line):
        """
        Get the product ID of an asset
        """
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None
        user_agent = httpc.get_random_user_agent()

        req_url = f"https://apis.roblox.com/toolbox-service/v1/items/details?assetIds={self.asset_id}"
        req_cookies = {".ROBLOSECURITY": cookie}
        req_headers = httpc.get_roblox_headers(user_agent)

        response = httpc.get(req_url, headers=req_headers, cookies=req_cookies, proxies=proxies)

        try:
            product_id = response.json()["data"][0]["product"]["productId"]
        except:
            raise Exception(Utils.return_res(response))

        return product_id

    @Utils.handle_exception(3)
    def buy_product(self, product_id, cookie, proxies_line):
        """
        Buy a product
        """
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()
            csrf_token = self.get_csrf_token(cookie, client)

            req_url = f"https://apis.roblox.com/creator-marketplace-purchasing-service/v1/products/{product_id}/purchase"
            req_cookies = {".ROBLOSECURITY": cookie}
            req_headers = httpc.get_roblox_headers(user_agent, csrf_token)
            req_json = {"assetId": self.asset_id, "assetType": 10, "expectedPrice": 0, "searchId": ""}

            response = client.post(req_url, headers=req_headers, json=req_json, cookies=req_cookies)

            try:
                is_bought = (response.status_code == 200 and response.json()["purchased"] is True)
            except KeyError:
                return False, "Failed to access purchased key " + Utils.return_res(response)

        return is_bought, Utils.return_res(response)
