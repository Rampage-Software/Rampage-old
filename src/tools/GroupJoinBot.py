import httpc
from Tool import Tool
import random
import concurrent.futures
from CaptchaSolver import CaptchaSolver
from utils import Utils
from config import ConfigType, Config
from BoundAuthToken import BATGenerator

class GroupJoinBot(Tool):
    def __init__(self, app):
        super().__init__("Group Join Bot", "Enhance the size of your group members", app)

    def run(self):
        self.group_id = ConfigType.integer(self.config, "group_id")
        self.captcha_solver = ConfigType.string(self.config, "captcha_solver")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")
        self.max_generations = Config.input_max_generations()

        if not self.group_id or not self.max_generations or not self.captcha_solver:
            raise Exception("group_id, max_generations and captcha_solver must not be null.")

        cookies = self.get_cookies(self.max_generations)
        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        req_worked = 0
        req_failed = 0
        total_req = len(cookies)

        with concurrent.futures.ThreadPoolExecutor(self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.send_group_join_request, cookie, random.choice(proxies_lines)) for cookie in cookies]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    has_joined, response_text = future.result()
                except Exception as e:
                    has_joined, response_text = False, str(e)

                if has_joined:
                    req_worked += 1
                else:
                    req_failed += 1

                self.print_status(req_worked, req_failed, total_req, response_text, has_joined, "New joins")

    @Utils.handle_exception()
    def send_group_join_request(self, cookie, proxies_line):
        """
        Send a join request to a group
        """
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies, spoof_tls=True) as client:
            captcha_solver = CaptchaSolver(self.captcha_solver, self.captcha_tokens.get(self.captcha_solver))
            user_agent = httpc.get_random_user_agent()
            csrf_token = self.get_csrf_token(cookie, client)
            session_cookies = self.get_session_cookies(cookie, user_agent, client)

            req_url = f"https://groups.roblox.com/v1/groups/{self.group_id}/users"
            req_cookies = session_cookies
            req_headers = httpc.get_roblox_headers(user_agent, csrf_token)
            req_json={"redemptionToken": "", "sessionId": ""}

            bat_gen = BATGenerator()
            bound_auth_token = bat_gen.generate_bound_auth_token(req_json)
            req_headers["x-bound-auth-token"] = bound_auth_token

            init_res = client.post(req_url, headers=req_headers, cookies=req_cookies, json=req_json)
            response = captcha_solver.solve_captcha(init_res, "ACTION_TYPE_GROUP_JOIN", proxies_line, client)

        return (response.status_code == 200), Utils.return_res(response)
