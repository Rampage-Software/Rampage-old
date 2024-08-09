import os
import concurrent.futures
import httpc
import random
import threading
from Tool import Tool
from utils import Utils, Infinite
from config import ConfigType

class UsernameSniper(Tool):
    def __init__(self, app):
        super().__init__("Username Sniper", "Search for the shortest Roblox username available", app)

        self.usernames_file_path = os.path.join(self.files_directory, "usernames.txt")
        Utils.ensure_files_exist([self.usernames_file_path])

    def run(self):
        self.username_length = ConfigType.integer(self.config, "username_length")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")

        if not self.username_length:
            raise Exception("username_length must not be null.")

        if self.username_length < 3 or self.username_length > 20:
            raise Exception("Usernames can be between 3 and 20 characters long.")

        self.proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        self.worked_gen = 0
        self.failed_gen = 0
        self.total_gen = 0

        self.file_lock = threading.Lock()
        self.output_lock = threading.Lock()

        self.executor = Infinite(self.thread_function, self.max_threads)
        self.executor.start()

    def thread_function(self):
        try:
            is_available, username, response_text = self.check_username(random.choice(self.proxies_lines))
        except Exception as e:
            is_available, response_text = False, str(e)

        if is_available:
            self.worked_gen += 1

            with self.file_lock:
                with open(self.usernames_file_path, 'a') as f:
                    f.write(username+"\n")
                    f.flush()
        else:
           self.failed_gen += 1

        self.total_gen += 1

        with self.output_lock:
            self.print_status(self.worked_gen, self.failed_gen, self.total_gen, response_text, is_available, "Available")

    def generate_random_username(self, length):
        characters = 'abcdefghijklmnopqrstuvwxyz0123456789_'
        username = ''.join(random.choice(characters) for _ in range(length))

        while username[0] == '_' or username[-1] == '_' or username.count('_') > 1:
            username = ''.join(random.choice(characters) for _ in range(length))

        return username

    @Utils.handle_exception(2)
    def check_username(self, proxies_line) -> tuple:
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        username = self.generate_random_username(self.username_length)

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()
            csrf_token = self.get_csrf_token(None, client)

            req_headers = httpc.get_roblox_headers(user_agent, csrf_token)
            req_url = "https://auth.roblox.com/v1/usernames/validate"
            req_json = {
                "username": username,
                "context": "Signup",
                "birthday": "1999-01-01T05:00:00.000Z"
            }

            result = client.post(req_url, headers=req_headers, json=req_json)

        is_available = "Username is valid" in result.text

        return is_available, username, f"{username} {result.text}"
