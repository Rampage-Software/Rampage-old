import os
import concurrent.futures
import httpc
import re
import click
import random
from Tool import Tool
from utils import Utils
from config import ConfigType

class CookieChecker(Tool):
    def __init__(self, app):
        super().__init__("Cookie Checker", "Checks if cookies are valid and shuffle and unduplicate them.", app)

        self.cache_file_path = os.path.join(self.cache_directory, "verified-cookies.txt")

    def run(self):
        self.check_pending = ConfigType.boolean(self.config, "check_pending")
        self.check_age = ConfigType.boolean(self.config, "check_age")
        self.check_premium = ConfigType.boolean(self.config, "check_premium")
        self.delete_invalid_cookies = ConfigType.boolean(self.config, "delete_invalid_cookies")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")

        cookies, lines = self.get_cookies(None, True)
        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        if self.delete_invalid_cookies:
            f = open(self.cache_file_path, 'w')
            f.seek(0)
            f.truncate()

        total_robux = 0
        total_pending_rbx = 0

        working_cookies = 0
        failed_cookies = 0
        total_cookies = len(cookies)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.test_cookie, cookie, random.choice(proxies_lines)) for cookie in cookies]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    is_working, cookie, response_text, robux_balance, pending_robux = future.result()
                except Exception as e:
                    is_working, response_text = False, str(e)

                if is_working:
                    working_cookies += 1
                    total_robux += robux_balance
                    total_pending_rbx += pending_robux
                else:
                    failed_cookies += 1

                if self.delete_invalid_cookies and is_working:
                    # write line that contains cookie
                    pattern = re.compile(rf'.*{re.escape(cookie)}.*')
                    matched_lines = [line for line in lines if pattern.search(line)]
                    matched_line = matched_lines[0]

                    f.write(matched_line + "\n")
                    f.flush()

                self.print_status(working_cookies, failed_cookies, total_cookies, response_text, is_working, "Working")

        if self.delete_invalid_cookies:
            f.close()

            # replace file with cache
            with open(self.cookies_file_path, 'w') as destination_file:
                with open(self.cache_file_path, 'r') as source_file:
                    destination_file.seek(0)
                    destination_file.truncate()
                    destination_file.write(source_file.read())

        click.secho(f"\nTotal Robux: {total_robux}", fg="green")

        if self.check_pending:
            click.secho(f"Total Pending Robux: {total_pending_rbx}", fg="yellow")

    @Utils.handle_exception(3, False)
    def check_pending_robux(self, cookie, user_id, client, user_agent):
        """
        Gets pending robux from cookie
        """
        req_url = f"https://economy.roblox.com/v2/users/{user_id}/transaction-totals?timeFrame=Month&transactionType=summary"
        req_cookies = { ".ROBLOSECURITY": cookie }
        req_headers = httpc.get_roblox_headers(user_agent)

        response = client.get(req_url, headers=req_headers, cookies=req_cookies)

        try:
            result = response.json()

            return result["pendingRobuxTotal"]
        except Exception:
            raise Exception(Utils.return_res(response))

    @Utils.handle_exception(3, False)
    def check_cookie_age(self, user_id, client, user_agent):
        req_url = f"https://users.roblox.com/v1/users/{user_id}"
        req_headers = httpc.get_roblox_headers(user_agent)

        response = client.get(req_url, headers=req_headers)

        try:
            result = response.json()
            # format: 2023-09-10T04:47:57.407Z
            date = result["created"]

            # convert to time elapsed
            return Utils.get_time_elapsed(date)
        except Exception as e:
            raise Exception(str(e) + Utils.return_res(response))

    @Utils.handle_exception(3, False)
    def check_cookie_premium(self, cookie, user_id, client, user_agent):
        req_url = f"https://premiumfeatures.roblox.com/v1/users/{user_id}/validate-membership"
        req_headers = httpc.get_roblox_headers(user_agent)
        req_cookies = { ".ROBLOSECURITY": cookie }

        response = client.get(req_url, headers=req_headers, cookies=req_cookies)

        result = response.text

        if not result in ["true", "false"]:
            raise Exception(Utils.return_res(response))

        return result

    @Utils.handle_exception(3)
    def test_cookie(self, cookie, proxies_line):
        """
        Checks if a cookie is working
        """
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()
            req_url = "https://www.roblox.com/mobileapi/userinfo"
            req_cookies = { ".ROBLOSECURITY": cookie }
            req_headers = httpc.get_roblox_headers(user_agent)

            response = client.get(req_url, headers=req_headers, cookies=req_cookies)

            if "NewLogin" in response.text:
                return False, cookie, Utils.return_res(response), None, None

            if response.status_code != 200:
                raise Exception(Utils.return_res(response))

            result = response.json()

            user_id = result["UserID"]
            username = result["UserName"]
            robux_balance = result["RobuxBalance"]

            # optional checks
            pending_robux = self.check_pending_robux(cookie, user_id, client, user_agent) if self.check_pending else 0
            check_age = self.check_cookie_age(user_id, client, user_agent) if self.check_age else "N/A"
            check_premium = self.check_cookie_premium(cookie, user_id, client, user_agent) if self.check_premium else "N/A"

        user_info = f"UserID: {user_id} | Username: {username} | Robux Balance: {robux_balance}"

        if self.check_pending:
            user_info += f" | Pending Robux: {pending_robux}"

        if self.check_age:
            user_info += f" | Account Age: {check_age}"

        if self.check_premium:
            user_info += f" | Premium: {check_premium}"

        return True, cookie, user_info, robux_balance, pending_robux
