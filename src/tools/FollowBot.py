import httpc
from Tool import Tool
import random
import time
import concurrent.futures
from CaptchaSolver import CaptchaSolver
from utils import Utils
from config import ConfigType, Config

class FollowBot(Tool):
    def __init__(self, app):
        super().__init__("Follow Bot", "Increase Followers count of a user", app)

    def run(self):
        self.user_id = ConfigType.integer(self.config, "user_id")
        self.timeout = ConfigType.integer(self.config, "timeout")
        self.debug_mode = ConfigType.boolean(self.config, "debug_mode")
        self.solve_pow = ConfigType.boolean(self.config, "solve_pow")
        self.captcha_solver = ConfigType.string(self.config, "captcha_solver")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")
        self.max_generations = Config.input_max_generations()

        if not self.user_id or not self.max_generations or not self.captcha_solver:
            raise Exception("user_id, max_generations and captcha_solver must not be null.")

        cookies = self.get_cookies(self.max_generations)
        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        req_worked = 0
        req_failed = 0
        total_req = len(cookies)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.send_follow_request, cookie, random.choice(proxies_lines)) for cookie in cookies]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    is_followed, response_text = future.result()
                except Exception as e:
                    is_followed, response_text = False, str(e)

                if is_followed:
                    req_worked += 1
                else:
                    req_failed += 1

                self.print_status(req_worked, req_failed, total_req, response_text, is_followed, "New followers", self.debug_mode)

    @Utils.handle_exception()
    def send_follow_request(self, cookie, proxies_line):
        """
        Send a follow request to a user
        """
        time.sleep(self.timeout)

        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies, spoof_tls=True, timeout=3) as client:
            captcha_solver = CaptchaSolver(self.captcha_solver, self.captcha_tokens.get(self.captcha_solver), self.debug_mode, self.solve_pow)
            user_agent = httpc.get_random_user_agent()
            csrf_token = self.get_csrf_token(cookie, client)

            session_cookies = self.get_session_cookies(cookie, user_agent, client)

            req_url = f"https://friends.roblox.com/v1/users/{self.user_id}/follow"
            req_cookies = session_cookies
            req_headers = httpc.get_roblox_headers(user_agent, csrf_token)

            init_res = client.post(req_url, headers=req_headers, cookies=req_cookies)

            response = captcha_solver.solve_captcha(init_res, "ACTION_TYPE_FOLLOW_USER", proxies_line, client)

        return (response.status_code == 200), Utils.return_res(response)