import os
import random
import concurrent.futures
import httpc
from Tool import Tool
from CaptchaSolver import CaptchaSolver
from utils import Utils
from config import ConfigType

class UP2UPC(Tool):
    def __init__(self, app):
        super().__init__("UP Converter", "Convert user password list to UPC format", app)

        self.user_pass_file_path = os.path.join(self.files_directory, "user-pass.txt")
        Utils.ensure_files_exist([self.user_pass_file_path])

    def run(self):
        self.delete_converted_up = ConfigType.boolean(self.config, "delete_converted_up")
        self.ignore_captchas = ConfigType.boolean(self.config, "ignore_captchas")
        self.captcha_solver = ConfigType.string(self.config, "captcha_solver")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")

        if not self.captcha_solver:
            raise Exception("captcha_solver must not be null.")

        user_pass_list = self.get_user_pass()
        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        if len(user_pass_list) == 0:
            raise Exception("No user-pass found in files/user-pass.txt")

        f = open(self.cookies_file_path, 'a')

        worked_gen = 0
        failed_gen = 0
        total_gen = len(user_pass_list)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.convert_up, user_pass, random.choice(proxies_lines)) for user_pass in user_pass_list]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    has_converted, response_text, user_pass = future.result()
                except Exception as e:
                    has_converted, response_text = False, str(e)

                if has_converted:
                    worked_gen += 1
                    f.write(response_text+"\n")
                    f.flush()

                    # remove userpass from user_pass_list array
                    user_pass_list.remove(user_pass)
                else:
                    failed_gen += 1

                self.print_status(worked_gen, failed_gen, total_gen, response_text, has_converted, "Converted")
        f.close()

        if self.delete_converted_up:
            with open(self.user_pass_file_path, 'w') as f:
                for user_pass in user_pass_list:
                    f.write(user_pass+"\n")

    def get_user_pass(self) -> list:
        f = open(self.user_pass_file_path, 'r')
        lines = f.read().splitlines()
        f.close()

        # ignore duplicates
        user_pass_list = [*set(lines)]

        return user_pass_list

    @Utils.handle_exception(3, False)
    def send_signin_request(self, username, password, user_agent, csrf_token, client):
        req_url = "https://auth.roblox.com/v2/login"
        req_headers = httpc.get_roblox_headers(user_agent, csrf_token)
        req_cookies = self.get_session_cookies(None, user_agent, client, True)
        req_json={
            "ctype": "Username",
            "cvalue": username,
            "password": password
        }
        result = client.post(req_url, headers=req_headers, json=req_json, cookies=req_cookies)

        return result

    @Utils.handle_exception()
    def convert_up(self, user_pass, proxies_line) -> tuple:
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None
        username, password = user_pass.split(":", 1)

        with httpc.Session(proxies=proxies) as client:
            captcha_solver = CaptchaSolver(self.captcha_solver, self.captcha_tokens.get(self.captcha_solver))
            user_agent = httpc.get_random_user_agent()
            csrf_token = self.get_csrf_token(None, client)

            sign_in_res = self.send_signin_request(username, password, user_agent, csrf_token, client)

            if not self.ignore_captchas:
                sign_in_res = captcha_solver.solve_captcha(sign_in_res, "ACTION_TYPE_WEB_LOGIN", proxies_line, client)

        try:
            cookie = httpc.extract_cookie(sign_in_res, ".ROBLOSECURITY")
        except Exception:
            raise Exception(Utils.return_res(sign_in_res))

        return True, f"{username}:{password}:{cookie}", user_pass
