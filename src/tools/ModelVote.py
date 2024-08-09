import httpc
import random
from Tool import Tool
import concurrent.futures
from utils import Utils
from config import ConfigType, Config

class ModelVote(Tool):
    def __init__(self, app):
        super().__init__("Model Vote", "Increase Like/Dislike count of a model", app)

    def run(self):
        self.model_id = ConfigType.integer(self.config, "model_id")
        self.dislike = ConfigType.boolean(self.config, "dislike")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")
        self.max_generations = Config.input_max_generations()

        if not self.model_id:
            raise Exception("model_id must not be null.")

        cookies = self.get_cookies(self.max_generations)
        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]
        self.vote = not self.dislike

        req_sent = 0
        req_failed = 0
        total_req = len(cookies)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.send_model_vote, cookie, random.choice(proxies_lines)) for cookie in cookies]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    is_success, response_text = future.result()
                except Exception as e:
                    is_success, response_text = False, str(e)

                if is_success:
                    req_sent += 1
                else:
                    req_failed += 1

                self.print_status(req_sent, req_failed, total_req, response_text, is_success, "New votes")

    @Utils.handle_exception(3)
    def send_model_vote(self, cookie, proxies_line):
        """
        Send a vote to a model
        """
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()
            csrf_token = self.get_csrf_token(cookie, client)

            req_url = f"https://www.roblox.com/voting/vote?assetId={self.model_id}&vote={'true' if self.vote else 'false'}"
            req_cookies = {".ROBLOSECURITY": cookie}
            req_headers = httpc.get_roblox_headers(user_agent, csrf_token)

            response = client.post(req_url, headers=req_headers, cookies=req_cookies)

        try:
            success = response.status_code == 200 and response.json()["Success"]
        except KeyError:
            raise Exception("Failed to access Success key. " + Utils.return_res(response))

        return success, Utils.return_res(response)
