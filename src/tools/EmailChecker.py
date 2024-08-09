from Tool import Tool
import os
from utils import Utils
import httpc
import random
import concurrent.futures
from CaptchaSolver import CaptchaSolver
from config import ConfigType

class EmailChecker(Tool):
    def __init__(self, app):
        super().__init__("Email Checker", "Send password reset requests with a list of emails", app)

        self.emails_file_path = os.path.join(self.files_directory, "emails.txt")

        Utils.ensure_files_exist([self.emails_file_path])

    def run(self):
        self.captcha_solver = ConfigType.string(self.config, "captcha_solver")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")

        if not self.captcha_solver:
            raise Exception("captcha_solver must not be null.")

        f = open(self.emails_file_path, 'r+')
        lines = f.read().splitlines()
        f.close()

        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        working_emails = 0
        failed_emails = 0
        total_emails = len(lines)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.check_email, line, random.choice(proxies_lines)) for line in lines]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    is_working, response_text = future.result()
                except Exception as e:
                    is_working, response_text = False, str(e)

                if is_working:
                    working_emails += 1
                else:
                    failed_emails += 1

                self.print_status(working_emails, failed_emails, total_emails, response_text, is_working, "Reset Requested")

    @Utils.handle_exception(3)
    def check_email(self, email, proxies_line):
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            captcha_solver = CaptchaSolver(self.captcha_solver, self.captcha_tokens.get(self.captcha_solver))

            user_agent = httpc.get_random_user_agent()
            csrf_token = self.get_csrf_token(None, client)

            req_url = "https://auth.roblox.com/v2/passwords/reset/send"
            req_headers = httpc.get_roblox_headers(user_agent, csrf_token)
            req_json = {
                "target": email,
                "targetType": "Email"
            }

            init_res = client.post(req_url, headers=req_headers, json=req_json)

            final_res = captcha_solver.solve_captcha(init_res, "ACTION_TYPE_WEB_RESET_PASSWORD", proxies_line, client)

        success = final_res.status_code == 200

        return success, "Email: " + email + " " + Utils.return_res(final_res)
