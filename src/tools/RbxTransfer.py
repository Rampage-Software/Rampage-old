import concurrent.futures
import click
import httpc
import re
from Tool import Tool
from utils import Utils
from config import ConfigType

class RbxTransfer(Tool):
    def __init__(self, app):
        super().__init__("Rbx Transfer", "Transfer the robux of your cookies to your main cookie.", app)

    def run(self):
        self.main_cookie = ConfigType.string(self.config, "main_cookie")
        self.use_proxy_for_main_cookie = ConfigType.boolean(self.config, "use_proxy_for_main_cookie")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")

        if not self.main_cookie:
            raise Exception("main_cookie must not be null.")

        cookies = self.get_cookies()
        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        try:
            get_user_info = self.get_main_info(proxies_lines)
        except Exception as e:
            if "NewLogin" in str(e):
                raise Exception("Your main cookie is not valid. Please provide a valid main cookie.")

            raise Exception(f"Failed to get main user info: {str(e)}")

        self.main_user_id = get_user_info["UserID"]
        self.main_username = get_user_info["UserName"]
        self.main_game_id = get_user_info["GameID"]

        click.secho(f"Main game id: {self.main_game_id} (will be used for transfer)", fg='yellow')

        click.secho("Gathering robux balances of cookies...", fg='green')

        rbx_cookies = []
        rbx_before_taxes = 0
        rbx_after_taxes = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.get_rbx_balance, cookie, proxies_lines) for cookie in cookies]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    robux_balance, username, cookie = future.result()
                    click.secho(f"{robux_balance} robux found on {username}", fg='blue' if robux_balance > 1 else 'bright_black')

                    if robux_balance > 1:
                        rbx_cookies.append((cookie, robux_balance, username))
                        rbx_before_taxes += robux_balance
                        rbx_after_taxes += round(robux_balance * 0.7)
                except Exception as e:
                    click.secho(str(e), fg='red')

        click.echo("============================")
        click.secho(f"Total robux before taxes: {rbx_before_taxes}", fg='green')
        click.secho(f"Total robux after taxes: {rbx_after_taxes}", fg='green')
        click.echo("============================")

        if not rbx_cookies:
            click.secho("No cookies with robux found.", fg='red')
            return;

        output = input(click.style(f"Are you sure you want to transfer the cookies' R$ to {self.main_username}? (y/n): ", fg="yellow"))

        if output.lower() != "y":
            return;

        # order ascending by robux balance
        rbx_cookies.sort(key=lambda x: x[1])

        # transfer robux
        proxies = self.get_random_proxies(proxies_lines) if self.use_proxy_for_main_cookie else None

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()

            csrf_token = self.init_transfer(client, user_agent)

            click.secho(f"Gamepass created with id: {self.gamepass_id}", fg='yellow')

            gamepass_price = 2
            for cookie, robux_balance, username in rbx_cookies:
                try:
                    if gamepass_price != robux_balance:
                        self.change_price(robux_balance, user_agent, csrf_token, client)

                    response_text = self.buy_gamepass(cookie, robux_balance, proxies_lines)
                    click.secho(f"{username} bought gamepass with {robux_balance} R$ "+response_text, fg='green')
                except Exception as e:
                    click.secho(f"{username} failed to transfer robux. "+str(e), fg='red')

    @Utils.handle_exception(2, False)
    def get_game_id(self, cookie, user_id, user_agent, client):
        """
        Gets the game owned by cookie
        """
        req_url = f"https://games.roblox.com/v2/users/{user_id}/games?sortOrder=Asc&limit=50"
        req_cookies = {".ROBLOSECURITY": cookie}
        req_headers = httpc.get_roblox_headers(user_agent)

        response = client.get(req_url, headers=req_headers, cookies=req_cookies)

        try:
            game_id = response.json()["data"][0]["id"]
        except Exception:
            raise Exception(Utils.return_res(response))

        return game_id

    @Utils.handle_exception(2)
    def get_main_info(self, proxies_lines):
        proxies = self.get_random_proxies(proxies_lines) if self.use_proxy_for_main_cookie else None

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()

            get_user_info = self.get_user_info(self.main_cookie, client, user_agent)

            user_id = get_user_info["UserID"]
            game_id = self.get_game_id(self.main_cookie, user_id, user_agent, client)

        return {**get_user_info, "GameID": game_id}

    @Utils.handle_exception(2)
    def get_rbx_balance(self, cookie, proxies_lines):
        proxies = self.get_random_proxies(proxies_lines)

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()

            get_user_info = self.get_user_info(cookie, client, user_agent)
            robux_balance = get_user_info["RobuxBalance"]
            username = get_user_info["UserName"]

        return robux_balance, username, cookie

    @Utils.handle_exception(3, False)
    def create_gamepass(self, user_agent, csrf_token, client):
        req_url = "https://apis.roblox.com/game-passes/v1/game-passes"
        req_headers = httpc.get_roblox_headers(user_agent, csrf_token)
        del req_headers["Content-Type"]
        req_cookies = {".ROBLOSECURITY": self.main_cookie}

        files = {
            "Name": (None, "privatools transfer"),
            "Description": (None, "by privatools transfer tool"),
            "UniverseId": (None, str(self.main_game_id))
        }

        response = client.post(req_url, headers=req_headers, cookies=req_cookies, files=files)

        try:
            gamepass_id = response.json()["gamePassId"]
        except Exception:
            raise Exception("Unable to access gamePassId " +Utils.return_res(response))

        return gamepass_id

    @Utils.handle_exception(2, False)
    def get_product_data(self, user_agent, client):
        req_url = f"https://www.roblox.com/game-pass/{self.gamepass_id}/privatools-transfer"
        req_cookies = {".ROBLOSECURITY": self.main_cookie}
        req_headers = httpc.get_roblox_headers(user_agent)

        response = client.get(req_url, headers=req_headers, cookies=req_cookies)

        try:
            product_id = re.search(r'data-product-id="(\d+)"', response.text).group(1)
        except Exception as e:
            raise Exception("Failed to get product data: "+str(e))

        return product_id

    @Utils.handle_exception(3)
    def init_transfer(self, client, user_agent):
        csrf_token = self.get_csrf_token(self.main_cookie, client)

        self.gamepass_id = self.create_gamepass(user_agent, csrf_token, client)
        self.change_price(2, user_agent, csrf_token, client)
        self.product_id = self.get_product_data(user_agent, client)

        return csrf_token

    @Utils.handle_exception(3, False)
    def change_price(self, price, user_agent, csrf_token, client):
        req_url = f"https://apis.roblox.com/game-passes/v1/game-passes/{self.gamepass_id}/details"
        req_headers = httpc.get_roblox_headers(user_agent, csrf_token)
        del req_headers["Content-Type"]
        req_cookies = {".ROBLOSECURITY": self.main_cookie}
        req_files = {
            "IsForSale": (None, "true"),
            "Price": (None, str(price))
        }

        response = client.post(req_url, headers=req_headers, cookies=req_cookies, files=req_files)

        if response.status_code != 200:
            raise Exception(Utils.return_res(response))

    @Utils.handle_exception(2)
    def buy_gamepass(self, cookie, price, proxies_lines):
        proxies = self.get_random_proxies(proxies_lines)

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()
            csrf_token = self.get_csrf_token(cookie, client)

            req_url = f"https://economy.roblox.com/v1/purchases/products/{self.product_id}"
            req_cookies = {".ROBLOSECURITY": cookie}
            req_headers = httpc.get_roblox_headers(user_agent, csrf_token)

            req_json={"expectedCurrency": 1, "expectedPrice": price, "expectedSellerId": self.main_user_id}
            response = client.post(req_url, headers=req_headers, cookies=req_cookies, json=req_json)

            if response.status_code != 200:
                raise Exception(Utils.return_res(response))

            result = response.json()

            if not result.get("purchased"):
                raise Exception(Utils.return_res(response))

        return response.text