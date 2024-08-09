from Tool import Tool
from utils import Utils
import random
import concurrent.futures
import threading
import click
from RobloxClient import RobloxClient
import httpc
from config import ConfigType, Config

class GameVisits(Tool):
    def __init__(self, app):
        super().__init__("Game Visits", "Boost game visits", app)

    def run(self):
        self.timeout = ConfigType.integer(self.config, "timeout")
        self.place_id = ConfigType.integer(self.config, "place_id")
        self.max_threads = ConfigType.integer(self.config, "max_threads")
        self.max_generations = Config.input_max_generations()

        if self.timeout is None or not self.place_id:
            raise Exception("timeout and place_id must not be null.")

        click.secho("Warning: on Windows 11, it may not be possible to run multiple roblox instances", fg="yellow")

        roblox_player_path = RobloxClient.find_roblox_player()

        if self.max_threads == None or self.max_threads > 1:
            threading.Thread(target=Tool.run_until_exit, args=(RobloxClient.remove_singleton_mutex,)).start()

        cookies = self.get_cookies()

        req_sent = 0
        req_failed = 0
        total_req = self.max_generations

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.visit_game, roblox_player_path, random.choice(cookies)) for i in range(self.max_generations)]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    is_success, response_text = future.result()
                except Exception as e:
                    is_success, response_text = False, str(e)

                if is_success:
                    req_sent += 1
                else:
                    req_failed += 1

                self.print_status(req_sent, req_failed, total_req, response_text, is_success, "New visits")

    @Utils.handle_exception()
    def visit_game(self, roblox_player_path, cookie):
        csrf_token = self.get_csrf_token(cookie)
        user_agent = httpc.get_random_user_agent()

        rblx_client = RobloxClient(roblox_player_path)
        auth_ticket = rblx_client.get_auth_ticket(cookie, user_agent, csrf_token)
        rblx_client.launch_place(auth_ticket, self.place_id, self.timeout)

        return True, "Cookie visited the game"