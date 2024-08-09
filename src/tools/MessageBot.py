import httpc
from Tool import Tool
import concurrent.futures
from utils import Utils
import random
import os
from config import ConfigType, Config

class MessageBot(Tool):
    def __init__(self, app):
        super().__init__("Message Bot", "Spam someone with the same message", app)

        self.message_users_id = os.path.join(self.files_directory, "./message-users-id.txt")

        Utils.ensure_files_exist([self.message_users_id])

    def run(self):
        self.use_scraped_users = ConfigType.boolean(self.config, "use_scraped_users")
        self.recipient_id = ConfigType.integer(self.config, "recipient_id")
        self.subject = ConfigType.string(self.config, "subject")
        self.body = ConfigType.string(self.config, "body")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")
        self.max_generations = Config.input_max_generations()

        if self.recipient_id is None or not self.subject or not self.body:
            raise Exception("recipient_id, subject and body must not be null.")

        self.proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        if self.use_scraped_users:
            # get scraped users id
            f = open(self.message_users_id, 'r')
            users_id = f.read().splitlines()
            f.close()

            self.spam_scraped_users(users_id)
        else:
            self.spam_specific_user()

    def spam_scraped_users(self, users_id):
        """
        Spam a list of users with the message
        """
        users_id = users_id[:self.max_generations]

        cookies = self.get_cookies()

        msg_sent = 0
        msg_failed = 0
        total_cookies = len(cookies)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.send_message, user_id, random.choice(cookies), random.choice(self.proxies_lines)) for user_id in users_id]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    is_sent, response_text = future.result()
                except Exception as e:
                    is_sent, response_text = False, str(e)

                if is_sent:
                    msg_sent += 1
                else:
                    msg_failed += 1

                self.print_status(msg_sent, msg_failed, total_cookies, response_text, is_sent, "Messages sent")

    def spam_specific_user(self):
        """
        Spam a specific user with the same message
        """

        cookies = self.get_cookies(self.max_generations)
        msg_sent = 0
        msg_failed = 0
        total_cookies = len(cookies)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.send_message, self.recipient_id, cookie, random.choice(self.proxies_lines)) for cookie in cookies]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    is_sent, response_text = future.result()
                except Exception as e:
                    is_sent, response_text = False, str(e)

                if is_sent:
                    msg_sent += 1
                else:
                    msg_failed += 1

                self.print_status(msg_sent, msg_failed, total_cookies, response_text, is_sent, "Messages sent")

    @Utils.handle_exception(3, False)
    def allow_sending_msgs(self, cookie, client, user_agent, csrf_token):
        """
        Allow sending messages to anyone
        """
        req_url = "https://apis.roblox.com/user-settings-api/v1/user-settings"
        req_cookies = {".ROBLOSECURITY": cookie, "RBXEventTrackerV2":f"browserid={random.randint(190000000,200000000)}"}
        req_headers = httpc.get_roblox_headers(user_agent, csrf_token)
        req_json={"whoCanMessageMe": "All"}

        response = client.post(req_url, headers=req_headers, cookies=req_cookies, json=req_json)

        if response.status_code != 200:
            raise Exception(Utils.return_res(response))

    @Utils.handle_exception(3)
    def send_message(self, recipient_id, cookie, proxies_line):
        """
        Send a message to a user
        """
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()
            csrf_token = self.get_csrf_token(cookie, client)

            req_url = "https://privatemessages.roblox.com/v1/messages/send"
            req_cookies = {".ROBLOSECURITY": cookie}
            req_headers = httpc.get_roblox_headers(user_agent, csrf_token)
            req_json={"body": self.body, "recipientid": recipient_id, "subject": self.subject}

            response = client.post(req_url, headers=req_headers, cookies=req_cookies, json=req_json)
            result = response.json()

            if (not result.get("success") and result.get("shortMessage") == "SenderPrivacySettingsTooHigh"):
                self.allow_sending_msgs(cookie, client, user_agent, csrf_token)
                # try again
                response = client.post(req_url, headers=req_headers, cookies=req_cookies, json=req_json)
                result = response.json()
        try:
            success = response.status_code == 200 and result["success"]
        except KeyError:
            raise Exception("Failed to access success key" + Utils.return_res(response))

        return success, Utils.return_res(response)
