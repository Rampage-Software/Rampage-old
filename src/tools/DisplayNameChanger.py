import httpc
from Tool import Tool
import concurrent.futures
from utils import Utils
import click
import random
from config import ConfigType

class DisplayNameChanger(Tool):
    def __init__(self, app):
        super().__init__("Display Name Changer", "Change Display Name of your bots", app)

    def run(self):
        self.new_display_names = ConfigType.list(self.config, "new_display_names")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")

        if not self.new_display_names:
            raise Exception("new_display_names must not be null.")

        cookies = self.get_cookies()
        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        click.secho("Warning: Display names can only be changed once every week", fg="yellow")

        req_sent = 0
        req_failed = 0
        total_req = len(cookies)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.change_display_name, cookie, random.choice(proxies_lines)) for cookie in cookies]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    is_success, response_text = future.result()
                except Exception as e:
                    is_success, response_text = False, str(e)

                if is_success:
                    req_sent += 1
                else:
                    req_failed += 1

                self.print_status(req_sent, req_failed, total_req, response_text, is_success, "Changed")

    @Utils.handle_exception(3)
    def change_display_name(self, cookie, proxies_line):
        """
        Changes the display name of a user
        """
        new_display_name = random.choice(self.new_display_names)

        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()
            csrf_token = self.get_csrf_token(cookie, client)
            user_info = self.get_user_info(cookie, client, user_agent)
            user_id = user_info["UserID"]

            req_url = f"https://users.roblox.com/v1/users/{user_id}/display-names"
            req_cookies = {".ROBLOSECURITY": cookie}
            req_headers = httpc.get_roblox_headers(user_agent, csrf_token)
            req_json = {"newDisplayName": new_display_name}

            response = client.patch(req_url, headers=req_headers, cookies=req_cookies, json=req_json)

        return (response.status_code == 200), Utils.return_res(response)
