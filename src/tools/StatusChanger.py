from Tool import Tool
import httpc
import random
import concurrent.futures
from utils import Utils
from config import ConfigType

class StatusChanger(Tool):
    def __init__(self, app):
        super().__init__("Status Changer", "Change the status of a large number of accounts", app)

    def run(self):
        self.new_status = ConfigType.string(self.config, "new_status")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")

        cookies = self.get_cookies()
        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        req_worked = 0
        req_failed = 0
        total_req = len(cookies)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.change_status, cookie, random.choice(proxies_lines)) for cookie in cookies]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    is_changed, response_text = future.result()
                except Exception as e:
                    is_changed, response_text = False, str(e)

                if is_changed:
                    req_worked += 1
                else:
                    req_failed += 1

                self.print_status(req_worked, req_failed, total_req, response_text, is_changed, "Changed")

    @Utils.handle_exception(3)
    def change_status(self, cookie, proxies_line):
        """
        Changes the status of a user
        """
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()
            csrf_token = self.get_csrf_token(cookie, client)

            req_url = "https://accountinformation.roblox.com/v1/description"
            req_cookies = {".ROBLOSECURITY": cookie}
            req_headers = httpc.get_roblox_headers(user_agent, csrf_token, "application/x-www-form-urlencoded")
            req_data = {"description": self.new_status }

            response = client.post(req_url, headers=req_headers, cookies=req_cookies, data=req_data)

        return (response.status_code == 200), Utils.return_res(response)
