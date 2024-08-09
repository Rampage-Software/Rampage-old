import httpc
import random
from Tool import Tool
import concurrent.futures
from utils import Utils
from config import ConfigType

class RbxSpaceAutoLister(Tool):
    def __init__(self, app):
        super().__init__("RbxSpace Auto Lister", "Auto list your cookies on rbxspace.net", app)

    def run(self):
        self.rbxspace_authorization = ConfigType.string(self.config, "rbxspace_authorization")
        self.queue_id = ConfigType.integer(self.config, "queue_id")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")

        if not self.rbxspace_authorization or not self.queue_id:
            raise Exception("rbxspace_authorization and item_id must not be null.")

        self.queue_id = self.queue_id - 1 # count start at 0

        cookies = self.get_cookies()
        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        req_worked = 0
        req_failed = 0
        total_req = len(cookies)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.list_on_space, cookie, random.choice(proxies_lines)) for cookie in cookies]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    has_listed, response_text = future.result()
                except Exception as e:
                    has_listed, response_text =  False, str(e)

                if has_listed:
                    req_worked += 1
                else:
                    req_failed += 1

                self.print_status(req_worked, req_failed, total_req, response_text, has_listed, "Listed")

    @Utils.handle_exception(2)
    def list_on_space(self, cookie, proxies_line):
        req_url = "https://market.rbxspace.net/api/v1/suppliers/add_transfer_cookie"
        req_headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTcxMDcxNTEzNCwianRpIjoiMjBmMDNkNTItNDdiYy00YTI5LTg3MTktZDhiZTBiNzBlYWUzIiwibmJmIjoxNzEwNzE1MTM0LCJ0eXBlIjoiYWNjZXNzIiwic3ViIjp7ImlkIjoiNjU4Mzc3ZWJkNmVlYjJiNDdjMThiZDc3IiwidXNlcm5hbWUiOiJnYXJyeSIsInVzZXJuYW1lX2xvd2VyIjoiZ2FycnkiLCJkaXNjb3JkX3VzZXJuYW1lIjoiZ2Fycnl5YmQjMCIsImJhbGFuY2UiOjAuMCwiYXZhdGFyX2lkIjo3LCJpcF9hZGRyZXNzZXMiOlsiMTM1Ljg0LjI1LjQiLCIyMDkuMTI3LjI0LjM5IiwiMTk5LjIwMi43Ni44NyIsIjIwOS4xMjcuMjQuNTEiLCIyMDkuMTI3LjI0LjM1IiwiMjA5LjEyNy4yNC4xOSJdLCJzdGF0dXMiOiJhY3RpdmUiLCJlbWFpbCI6ImRhdmlkamFjcXVlc3Byb0Bwcm90b24ubWUiLCJkaXNjb3JkX2lkIjoiMTExMjE0NDI3ODg0ODgxMTA2OCIsInVzZXJfaW5mb19kYXRhIjp7Im51bWJlcl9yb2J1eCI6IjEwMDAtMzAwMCIsImhvd19nZXQiOiJyb2J1eCBzaXRlIGh0dHBzOi8vcGxhbmV0cmJ4LmNvbSJ9LCJyYXRlIjowLjB9LCJleHAiOjE3MTA4MDE1MzR9.-YVh_hdb6pAdtbZW14_7zMKpE8Z6CtdaMJwHv8jEhLE",
        }
        req_json={"cookie": cookie, "queue": self.queue_id}

        if self.use_proxy:
            req_json["ip"] = proxies_line.split(":")[0]
            req_json["port"] = proxies_line.split(":")[1]

            if len(proxies_line.split(":")) == 4:
                req_json["user"] = proxies_line.split(":")[2]
                req_json["password"] = proxies_line.split(":")[3]

        response = httpc.post(req_url, headers=req_headers, json=req_json)

        if response.status_code != 200:
            raise Exception(Utils.return_res(response))

        result = response.json()

        if not result.get("status"):
            raise Exception(Utils.return_res(response))

        return True, response.text.replace("\n", "")