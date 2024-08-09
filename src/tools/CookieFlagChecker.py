import concurrent.futures
import httpc
import random
import re
import os
from Tool import Tool
from utils import Utils
from config import ConfigType

class CookieFlagChecker(Tool):
    def __init__(self, app):
        super().__init__("Cookie Flag Checker", "Checks if cookies are unflagged.", app)

        self.cache_file_path = os.path.join(self.cache_directory, "unflagged-cookies.txt")

    def run(self):
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")
        self.delete_flagged_cookies = ConfigType.boolean(self.config, "delete_flagged_cookies")

        cookies, lines = self.get_cookies(None, True)
        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        unflagged_cookies = 0
        flagged_cookies = 0
        total_cookies = len(cookies)

        if self.delete_flagged_cookies:
            f = open(self.cache_file_path, 'w')
            f.seek(0)
            f.truncate()

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.test_flag_cookie, cookie, random.choice(proxies_lines)) for cookie in cookies]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    is_unflagged, response_text = future.result()
                except Exception as e:
                    is_unflagged, response_text = False, str(e)

                if is_unflagged:
                    unflagged_cookies += 1
                else:
                    flagged_cookies += 1
                
                if self.delete_flagged_cookies and is_unflagged:
                    cookie = future.result()[2]
                    pattern = re.compile(rf'.*{re.escape(cookie)}.*')
                    matched_lines = [line for line in lines if pattern.search(line)]
                    matched_line = matched_lines[0]

                    f.write(matched_line + "\n")
                    f.flush()

                self.print_status(unflagged_cookies, flagged_cookies, total_cookies, response_text, is_unflagged, "Unflagged")
                
        if self.delete_flagged_cookies:
            f.close()

            # replace file with cache
            with open(self.cookies_file_path, 'w') as destination_file:
                with open(self.cache_file_path, 'r') as source_file:
                    destination_file.seek(0)
                    destination_file.truncate()
                    destination_file.write(source_file.read())

    @Utils.handle_exception(2)
    def test_flag_cookie(self, cookie, proxies_line):
        """
        Checks if a cookie is flagged
        """
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()

            # get user info
            session_cookies = self.get_session_cookies(cookie, user_agent, client)

            # send follow request
            req_url = "https://friends.roblox.com/v1/users/1/follow"
            req_cookies = session_cookies
            csrf_token = self.get_csrf_token(cookie, client)
            req_headers = httpc.get_roblox_headers(user_agent, csrf_token)

            result = client.post(req_url, headers=req_headers, cookies=req_cookies)

            return result.status_code == 200, Utils.return_res(result)