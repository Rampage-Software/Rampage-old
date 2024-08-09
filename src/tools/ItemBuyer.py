import httpc
import random
from Tool import Tool
import concurrent.futures
from utils import Utils
import re
from config import ConfigType, Config

class ItemBuyer(Tool):
    def __init__(self, app):
        super().__init__("Item Buyer", "Have your cookies buy an item from the catalog", app)

    def run(self):
        self.item_id = ConfigType.integer(self.config, "item_id")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")
        self.max_generations = Config.input_max_generations()

        if not self.item_id:
            raise Exception("item_id must not be null.")

        cookies = self.get_cookies(self.max_generations)
        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        product_id, expected_price, expected_seller_id, expected_currency = self.get_product_data(random.choice(cookies), random.choice(proxies_lines))

        req_worked = 0
        req_failed = 0
        total_req = len(cookies)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.buy_item, product_id, expected_price, expected_seller_id, expected_currency, cookie, random.choice(proxies_lines)) for cookie in cookies]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    has_bought, response_text = future.result()
                except Exception as e:
                    has_bought, response_text =  False, str(e)

                if has_bought:
                    req_worked += 1
                else:
                    req_failed += 1

                self.print_status(req_worked, req_failed, total_req, response_text, has_bought, "Bought")

    @Utils.handle_exception(2)
    def get_product_data(self, cookie, proxies_line):
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()

            req_url = f"https://www.roblox.com/catalog/{self.item_id}"
            req_cookies = {".ROBLOSECURITY": cookie}
            req_headers = httpc.get_roblox_headers(user_agent)

            response = client.get(req_url, headers=req_headers, cookies=req_cookies)

            if response.status_code == 302:
                req_url = re.search(r'href="(.+)"', response.text).group(1)
                response = client.get(req_url, headers=req_headers, cookies=req_cookies)

        if response.status_code != 200:
            raise Exception(Utils.return_res(response))

        try:
            product_id = re.search(r'data-product-id="(\d+)"', response.text).group(1)
            expected_price = re.search(r'data-expected-price="(\d+)"', response.text).group(1)
            expected_seller_id = re.search(r'data-expected-seller-id="(\d+)"', response.text).group(1)
            expected_currency = re.search(r'data-expected-currency="(\d+)"', response.text).group(1)
        except Exception:
            raise Exception("Failed to get product data")

        return product_id, expected_price, expected_seller_id, expected_currency

    def buy_item(self, product_id, expected_price, expected_seller_id, expected_currency, cookie, proxies_line):
        """
        Buy an item from the catalog
        """
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()
            csrf_token = self.get_csrf_token(cookie, client)

            req_url = "https://economy.roblox.com/v1/purchases/products/" + product_id
            req_cookies = {".ROBLOSECURITY": cookie}
            req_headers = httpc.get_roblox_headers(user_agent, csrf_token)
            req_json={"expectedCurrency": expected_currency, "expectedPrice": expected_price, "expectedSellerId": expected_seller_id}

            response = client.post(req_url, headers=req_headers, cookies=req_cookies, json=req_json)

        success = (response.status_code == 200) and response.json()["purchased"]

        return success, Utils.return_res(response)