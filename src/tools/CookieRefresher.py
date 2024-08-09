import os
import concurrent.futures
import random
import httpc
import re
from Tool import Tool
from utils import Utils
from config import ConfigType

class CookieRefresher(Tool):
    def __init__(self, app):
        super().__init__("Cookie Refresher", "Refresh your .ROBLOSECURITY cookies!", app)

        self.new_cookies_file_path = os.path.join(self.files_directory, "refreshed-cookies.txt")

    def run(self):
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")

        cookies, lines = self.get_cookies(None, True)
        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        f = open(self.new_cookies_file_path, 'w')
        f.seek(0)
        f.truncate()

        req_sent = 0
        req_failed = 0
        total_req = len(cookies)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.refresh_cookie, cookie, random.choice(proxies_lines)) for cookie in cookies]

            for future in concurrent.futures.as_completed(self.results):
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

                self.print_status(req_sent, req_failed, total_req, response_text, has_worked, "Refreshed")

        f.close()

        # replace cookies
        with open(self.cookies_file_path, 'w') as destination_file:
            with open(self.new_cookies_file_path, 'r') as source_file:
                destination_file.seek(0)
                destination_file.truncate()
                destination_file.write(source_file.read())

        os.remove(self.new_cookies_file_path)

    @Utils.handle_exception(2)
    def refresh_cookie(self, cookie, proxies_line):
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()
            csrf_token = self.get_csrf_token(cookie, client)

            # Creating a new cookie
            reauthcookieurl = "https://www.roblox.com/authentication/signoutfromallsessionsandreauthenticate"
            req_headers = httpc.get_roblox_headers(user_agent, csrf_token)

            data = client.post(reauthcookieurl, cookies={'.ROBLOSECURITY': cookie}, headers=req_headers)

        if data.status_code != 200:
            raise Exception(Utils.return_res(data))

        try:
            new_cookie = httpc.extract_cookie(data, ".ROBLOSECURITY")
        except Exception:
            raise Exception(Utils.return_res(data))

        return True, new_cookie, cookie
