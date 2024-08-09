import httpc
import random
from Tool import Tool
import concurrent.futures
from utils import Utils
from config import ConfigType, Config

class GroupAllyBot(Tool):
    def __init__(self, app):
        super().__init__("Group Ally Bot", "Mass send ally requests to groups", app)

    def run(self):
        self.start_group_id = ConfigType.integer(self.config, "start_group_id")
        self.your_group_id = ConfigType.integer(self.config, "your_group_id")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")
        self.max_generations = Config.input_max_generations()

        if  not self.start_group_id or not self.your_group_id:
            raise Exception("start_group_id and your_group_id must not be null.")

        cookies = self.get_cookies()
        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        req_worked = 0
        req_failed = 0
        total_req = self.max_generations

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.send_ally_request, i+int(self.start_group_id), random.choice(proxies_lines), random.choice(cookies)) for i in range(self.max_generations)]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    has_req, response_text = future.result()
                except Exception as e:
                    has_req, response_text =  False, str(e)

                if has_req:
                    req_worked += 1
                else:
                    req_failed += 1

                self.print_status(req_worked, req_failed, total_req, response_text, has_req, "Ally Requested")

    @Utils.handle_exception()
    def send_ally_request(self, group_id_to_ally, proxies_line, cookie):
        """
        Send a ally request to a group
        """

        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()
            csrf_token = self.get_csrf_token(cookie, client)

            req_url = f"https://groups.roblox.com/v1/groups/{self.your_group_id}/relationships/allies/{group_id_to_ally}"
            req_cookies = {".ROBLOSECURITY": cookie}
            req_headers = httpc.get_roblox_headers(user_agent, csrf_token)

            response = client.post(req_url, headers=req_headers, cookies=req_cookies)

        return (response.status_code == 200), Utils.return_res(response)
