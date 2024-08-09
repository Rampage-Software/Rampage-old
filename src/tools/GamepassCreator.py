import os
from Tool import Tool
import httpc
import random
import concurrent.futures
from utils import Utils
from config import ConfigType

class GamepassCreator(Tool):
    def __init__(self, app):
        super().__init__("Gamepass Creator", "Useful for Pls donate farming.", app)

        self.assets_files_directory = os.path.join(self.files_directory, "./assets")
        self.gamepasses_files_directory = os.path.join(self.files_directory, "./assets/gamepasses")
        self.gamepass_default_img_path = os.path.join(self.gamepasses_files_directory, "default.jpg")

        Utils.ensure_directories_exist([ self.assets_files_directory, self.gamepasses_files_directory ])

    def run(self):
        self.prices = ConfigType.list(self.config, "prices")
        self.gamepass_names = ConfigType.list(self.config, "names")
        self.use_one_image = ConfigType.boolean(self.config, "use_one_image")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")

        if not self.prices or not self.gamepass_names:
            raise Exception("prices and names must not be null.")

        if len(self.prices) != len(self.gamepass_names):
            raise Exception("Prices and names must be the same length")

        # check if the gamepasses image(s) exist
        if self.use_one_image:
            if not os.path.exists(self.gamepass_default_img_path):
                raise Exception(f"Gamepass image default.jpg does not exist. Make sure to put it in {self.gamepasses_files_directory}")
        else:
            for price in self.prices:
                gamepass_img_path = os.path.join(self.gamepasses_files_directory, f"{price}.jpg")
                if not os.path.exists(gamepass_img_path):
                    raise Exception(f"Gamepass image {price}.jpg does not exist. Make sure to put all gamepasses images in {self.gamepasses_files_directory}")

        cookies = self.get_cookies()
        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        req_sent = 0
        req_failed = 0
        total_req = len(cookies)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.create_gamepasses, cookie, random.choice(proxies_lines)) for cookie in cookies]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    has_created, response_text = future.result()
                except Exception as e:
                    has_created, response_text = False, str(e)

                if has_created:
                    req_sent += 1
                else:
                    req_failed += 1

                self.print_status(req_sent, req_failed, total_req, response_text, has_created, "Created gamepasses")

    @Utils.handle_exception(2, False)
    def get_game_id(self, cookie, user_id, client, user_agent):
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

    @Utils.handle_exception(3, False)
    def create_gamepass(self, cookie, user_agent, csrf_token, gamepass_name, price, game_id, gamepass_img_path, client):
        req_url = "https://apis.roblox.com/game-passes/v1/game-passes"
        req_headers = httpc.get_roblox_headers(user_agent, csrf_token)
        del req_headers["Content-Type"]
        req_cookies = {".ROBLOSECURITY": cookie}

        with open(gamepass_img_path, "rb") as f:
            image_file = f.read()

        files = {
            "Name": (None, f"{gamepass_name} {price} R$"),
            "Description": (None, "For pls donate"),
            "UniverseId": (None, str(game_id)),
            "File": ("gamepass.png", image_file, "image/jpeg"),
        }

        response = client.post(req_url, headers=req_headers, cookies=req_cookies, files=files)

        try:
            gamepass_id = response.json()["gamePassId"]
        except Exception:
            raise Exception("Unable to access gamePassId " +Utils.return_res(response))

        return gamepass_id

    @Utils.handle_exception(3, False)
    def change_price(self, user_agent, csrf_token, cookie, price, gamepass_id, client):
        req_url = f"https://apis.roblox.com/game-passes/v1/game-passes/{gamepass_id}/details"
        req_headers = httpc.get_roblox_headers(user_agent, csrf_token)
        del req_headers["Content-Type"]
        req_cookies = {".ROBLOSECURITY": cookie}
        req_files = {
            "IsForSale": (None, "true"),
            "Price": (None, str(price))
        }

        response = client.post(req_url, headers=req_headers, cookies=req_cookies, files=req_files)

        if response.status_code != 200:
            raise Exception(Utils.return_res(response))

    @Utils.handle_exception(3)
    def create_gamepasses(self, cookie, proxies_line):
        """
        Send a friend request to a user
        """
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()

            user_info = self.get_user_info(cookie, client, user_agent)
            user_id = user_info["UserID"]

            game_id = self.get_game_id(cookie, user_id, client, user_agent)
            csrf_token = self.get_csrf_token(cookie, client)

            for i, price in enumerate(self.prices):
                gamepass_name = self.gamepass_names[i]
                gamepass_img_path = os.path.join(self.gamepasses_files_directory, f"{price}.jpg") if not self.use_one_image else self.gamepass_default_img_path
                gamepass_id = self.create_gamepass(cookie, user_agent, csrf_token, gamepass_name, price, game_id, gamepass_img_path, client)

                self.change_price(user_agent, csrf_token, cookie, price, gamepass_id, client)

        return True, "Gamepasses created for " + user_info["UserName"]
