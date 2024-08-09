from Tool import Tool
import httpc
import random
import concurrent.futures
from utils import Utils
from config import ConfigType, Config

class FriendRequestBot(Tool):
    def __init__(self, app):
        super().__init__("Friend Request Bot", "Send a lot of friend requests to a user", app)

    def run(self):
        self.user_id = ConfigType.integer(self.config, "user_id")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")
        self.max_generations = Config.input_max_generations()

        if not self.user_id:
            raise Exception("user_id must not be null.")

        cookies = self.get_cookies(self.max_generations)
        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        req_sent = 0
        req_failed = 0
        total_req = len(cookies)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.send_friend_request, cookie, random.choice(proxies_lines)) for cookie in cookies]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    is_sent, response_text = future.result()
                except Exception as e:
                    is_sent, response_text = False, str(e)

                if is_sent:
                    req_sent += 1
                else:
                    req_failed += 1

                self.print_status(req_sent, req_failed, total_req, response_text, is_sent, "New requests")

    @Utils.handle_exception(3)
    def send_friend_request(self, cookie, proxies_line):
        """
        Send a friend request to a user
        """
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()
            csrf_token = self.get_csrf_token(cookie, client)

            req_url = f"https://friends.roblox.com/v1/users/{self.user_id}/request-friendship"
            req_cookies = {".ROBLOSECURITY": cookie}
            req_headers = httpc.get_roblox_headers(user_agent, csrf_token)

            response = client.post(req_url, headers=req_headers, cookies=req_cookies)

        try:
            success = (response.status_code == 200 and response.json()["success"])
        except KeyError:
            raise Exception("Failed to access success key. " + Utils.return_res(response))

        return success, Utils.return_res(response)
