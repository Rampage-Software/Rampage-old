import httpc
from Tool import Tool
import concurrent.futures
from CaptchaSolver import CaptchaSolver
from data.comments import comments
import random
from utils import Utils
from config import ConfigType, Config

class CommentBot(Tool):
    def __init__(self, app):
        super().__init__("Comment Bot", "Increase/Decrease comments count of an asset", app)

    def run(self):
        self.message = ConfigType.string(self.config, "message")
        self.asset_id = ConfigType.integer(self.config, "asset_id")
        self.captcha_solver = ConfigType.string(self.config, "captcha_solver")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")
        self.max_generations = Config.input_max_generations()

        if not self.asset_id or not self.max_generations or not self.captcha_solver:
            raise Exception("asset_id, max_generations and captcha_solver must not be null.")

        cookies = self.get_cookies(self.max_generations)

        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        req_sent = 0
        req_failed = 0
        total_req = len(cookies)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.send_comment, cookie, random.choice(proxies_lines)) for cookie in cookies]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    is_success, response_text = future.result()
                except Exception as err:
                    is_success, response_text = False, str(err)

                if is_success:
                    req_sent += 1
                else:
                    req_failed += 1

                self.print_status(req_sent, req_failed, total_req, response_text, is_success, "Commented")

    def get_random_message(self):
        """
        Get a random message from the comments list
        """
        return random.choice(comments)

    @Utils.handle_exception()
    def send_comment(self, cookie, proxies_line):
        """
        Send a comment to an asset
        """
        captcha_solver = CaptchaSolver(self.captcha_solver, self.captcha_tokens.get(self.captcha_solver))

        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        message = self.message if self.message else self.get_random_message()

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()
            csrf_token = self.get_csrf_token(cookie, client)
            session_cookies = self.get_session_cookies(cookie, user_agent, client)

            req_url = "https://www.roblox.com/comments/post"
            req_cookies = session_cookies
            req_headers = httpc.get_roblox_headers(user_agent, csrf_token, "application/x-www-form-urlencoded; charset=UTF-8")
            req_data = {"assetId": str(self.asset_id), "text": message}

            init_res = client.post(req_url, headers=req_headers, data=req_data, cookies=req_cookies)
            response = captcha_solver.solve_captcha(init_res, "ACTION_TYPE_ASSET_COMMENT", proxies_line, client)

        success = response.status_code == 200 and not response.json().get("ErrorCode")

        return success, Utils.return_res(response)
