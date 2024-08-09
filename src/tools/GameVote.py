import httpc
import random
from Tool import Tool
import concurrent.futures
from utils import Utils
import threading
import click
from RobloxClient import RobloxClient
from config import ConfigType, Config

class GameVote(Tool):
    def __init__(self, app):
        super().__init__("Game Vote", "Increase Like/Dislike count of a game", app)

    def run(self):
        self.game_id = ConfigType.integer(self.config, "game_id")
        self.timeout = ConfigType.integer(self.config, "timeout")
        self.dislike = ConfigType.boolean(self.config, "dislike")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")
        self.max_generations = Config.input_max_generations()

        if not self.game_id or self.timeout is None:
            raise Exception("game_id and timeout must not be null.")

        cookies = self.get_cookies(self.max_generations)
        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        self.vote = not self.dislike
        self.roblox_player_path = RobloxClient.find_roblox_player()

        click.secho("Warning: on Windows 11, it may not be possible to run multiple roblox instances", fg="yellow")

        if self.max_threads == None or self.max_threads > 1:
            threading.Thread(target=Tool.run_until_exit, args=(RobloxClient.remove_singleton_mutex,)).start()

        req_sent = 0
        req_failed = 0
        total_req = len(cookies)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.send_game_vote, cookie, random.choice(proxies_lines)) for cookie in cookies]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    is_success, response_text = future.result()
                except Exception as e:
                    is_success, response_text = False, str(e)

                if is_success:
                    req_sent += 1
                else:
                    req_failed += 1

                self.print_status(req_sent, req_failed, total_req, response_text, is_success, "New votes")

    @Utils.handle_exception(3)
    def send_game_vote(self, cookie, proxies_line):
        """
        Send a vote to a game
        """
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()
            csrf_token = self.get_csrf_token(cookie, client)

            rblx_client = RobloxClient(self.roblox_player_path)
            auth_ticket = rblx_client.get_auth_ticket(cookie, user_agent, csrf_token)
            rblx_client.launch_place(auth_ticket, self.game_id, self.timeout)

            req_url = f"https://www.roblox.com/voting/vote?assetId={self.game_id}&vote={'true' if self.vote else 'false'}"
            req_cookies = {".ROBLOSECURITY": cookie}
            req_headers = httpc.get_roblox_headers(user_agent, csrf_token)

            response = client.post(req_url, headers=req_headers, cookies=req_cookies)

        try:
            success = (response.status_code == 200 and response.json()["Success"])
        except KeyError:
            raise Exception("Failed to access Success key. " + Utils.return_res(response))

        return success, Utils.return_res(response)
