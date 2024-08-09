import httpc
import random
from Tool import Tool
import concurrent.futures
from utils import Utils
from config import ConfigType, Config

class ChatSpammer(Tool):
    def __init__(self, app):
        super().__init__("Chat Spammer", "Spam user with a specific message.", app)

    def run(self):
        self.message = ConfigType.string(self.config, "message")
        self.recipient_id = ConfigType.integer(self.config, "recipient_id")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")
        self.max_generations = Config.input_max_generations()

        cookies = self.get_cookies()
        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        req_sent = 0
        req_failed = 0
        total_req = self.max_generations

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.send_message, random.choice(cookies), random.choice(proxies_lines)) for i in range(self.max_generations)]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    is_working, response_text = future.result()
                except Exception as e:
                    is_working, response_text = False, str(e)

                if is_working:
                    req_sent += 1
                else:
                    req_failed += 1

                self.print_status(req_sent, req_failed, total_req, response_text, is_working, "Chat Spammed")

    @Utils.handle_exception(2, False)
    def get_conversation_id(self, client, user_agent, cookie):
        """
        Get the conversation ID of a user
        """
        req_url = "https://chat.roblox.com/v2/get-user-conversations?pageNumber=1&pageSize=30"
        req_headers = httpc.get_roblox_headers(user_agent)
        req_cookies = {".ROBLOSECURITY": cookie}

        response = client.get(req_url, headers=req_headers, cookies=req_cookies)

        if response.status_code != 200:
            raise Exception(Utils.return_res(response))

        result = response.json()

        try:
            conversation_id = None

            # find targetID that matches recipient_id, then get the conversation_id
            for conversation in result:
                if conversation["participants"][0]["targetId"] == self.recipient_id and conversation["conversationType"] == "OneToOneConversation":
                    conversation_id = conversation["id"]
                    break
        except KeyError:
            return None

        return conversation_id

    @Utils.handle_exception(3)
    def send_message(self, cookie, proxies_line):
        """
        Send a message to a user
        """
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()

            conversation_id = self.get_conversation_id(client, user_agent, cookie)

            if conversation_id is None:
                return False, "Conversation ID not found. Bot might not be friend with target user"

            csrf_token = self.get_csrf_token(cookie, client)

            req_url = "https://chat.roblox.com/v2/send-message"
            req_headers = httpc.get_roblox_headers(user_agent, csrf_token)
            req_cookies = {".ROBLOSECURITY": cookie}

            req_data = {
                "message": self.message,
                "conversationId": conversation_id
            }

            response = client.post(req_url, headers=req_headers, cookies=req_cookies, json=req_data)

            if response.status_code != 200:
                raise Exception(Utils.return_res(response))

            return True, response.text
