import httpc
import random
from Tool import Tool
import concurrent.futures
from utils import Utils
from config import ConfigType, Config
from CaptchaSolver import CaptchaSolver

class GroupWallSpammer(Tool):
    def __init__(self, app):
        super().__init__("Group Wall Spammer", "Spam group walls with a message", app)

    def run(self):
        self.message = ConfigType.string(self.config, "message")
        self.start_group_id = ConfigType.integer(self.config, "start_group_id")
        self.captcha_solver = ConfigType.string(self.config, "captcha_solver")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")
        self.max_generations = Config.input_max_generations()

        if not self.message or not self.start_group_id or not self.max_generations or not self.captcha_solver:
            raise Exception("message, start_group_id, max_generations and captcha_solver must not be null.")

        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]
        cookies = self.get_cookies()

        req_worked = 0
        req_failed = 0
        total_req = self.max_generations

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.send_message, i+self.start_group_id, random.choice(proxies_lines), random.choice(cookies)) for i in range(self.max_generations)]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    has_req, response_text = future.result()
                except Exception as e:
                    has_req, response_text =  False, str(e)

                if has_req:
                    req_worked += 1
                else:
                    req_failed += 1

                self.print_status(req_worked, req_failed, total_req, response_text, has_req, "Spammed")

    @Utils.handle_exception()
    def send_message(self, group_id_to_spam, proxies_line, cookie):
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            captcha_solver = CaptchaSolver(self.captcha_solver, self.captcha_tokens.get(self.captcha_solver))
            user_agent = httpc.get_random_user_agent()
            csrf_token = self.get_csrf_token(cookie, client)

            req_url = f"https://groups.roblox.com/v1/groups/{group_id_to_spam}/wall/posts"
            req_cookies = {".ROBLOSECURITY": cookie}
            req_headers = httpc.get_roblox_headers(user_agent, csrf_token)
            req_json = {"body": self.message}

            init_res = client.post(req_url, headers=req_headers, json=req_json, cookies=req_cookies)
            response = captcha_solver.solve_captcha(init_res, "ACTION_TYPE_GROUP_WALL_POST", proxies_line, client)

        return (response.status_code == 200), Utils.return_res(response)
