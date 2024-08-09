import concurrent.futures
import httpc
import os
from Tool import Tool
from utils import Utils
import click
import random
from config import ConfigType, Config

class MessageUsersScraper(Tool):
    def __init__(self, app):
        super().__init__("Message Users Scraper", "Scrapes messageable users.", app)

        self.message_users_id = os.path.join(self.files_directory, "./message-users-id.txt")

        Utils.ensure_files_exist([self.message_users_id])

    def run(self):
        self.group_id = ConfigType.integer(self.config, "group_id")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")
        self.max_generations = Config.input_max_generations()

        if not self.group_id:
            raise Exception("group_id must not be null.")

        cookies = self.get_cookies(self.max_generations)
        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        click.secho("Collecting users id from group... ", fg="green")
        users_id = self.get_users_id_amount(random.choice(proxies_lines))
        click.secho("Filtering messageable users... Please wait")

        f = open(self.message_users_id, 'a')

        worked_gen = 0
        failed_gen = 0
        total_gen = len(users_id)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.check_if_messageable, user_id, random.choice(cookies), random.choice(proxies_lines)) for user_id in users_id]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    is_messageable, response_text, user_id = future.result()
                except Exception as e:
                    is_messageable, response_text = False, str(e)

                if is_messageable:
                    worked_gen += 1

                    f.write(str(user_id)+"\n")
                    f.flush()
                else:
                    failed_gen += 1

                self.print_status(worked_gen, failed_gen, total_gen, response_text, is_messageable, "Messageable")
        f.close()

    @Utils.handle_exception(2)
    def check_if_messageable(self, user_id, cookie, proxies_line):
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        req_url = f"https://privatemessages.roblox.com/v1/messages/{user_id}/can-message"
        cookies = {
            ".ROBLOSECURITY": cookie
        }

        result = httpc.get(req_url, cookies=cookies, proxies=proxies)
        response = result.json()

        can_message = response.get("canMessage")

        if can_message is None:
            raise Exception(Utils.return_res(result))

        return can_message, result.text, user_id

    @Utils.handle_exception(3, False)
    def get_users_page(self, cursor, proxies, user_agent):
        """
        Get a page of users
        """
        req_url = f"https://groups.roblox.com/v1/groups/{self.group_id}/users"
        req_headers = httpc.get_roblox_headers(user_agent)
        req_params = {
            "limit": 100,
            "sortOrder": "Desc",
            "cursor": cursor,
        }

        response = httpc.get(req_url, headers=req_headers, params=req_params, proxies=proxies)
        result = response.json()

        data = result.get("data")
        cursor = result.get("nextPageCursor")

        if data == None:
            raise Exception(Utils.return_res(response))

        # take only the user id
        data = [user["user"]["userId"] for user in data]

        return data, cursor

    @Utils.handle_exception()
    def get_users_id_amount(self, proxies_line):
        """
        Get x amount of users id
        """
        users_id = []
        cursor = None

        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None
        user_agent = httpc.get_random_user_agent()

        i = 1
        while len(users_id) < self.max_generations:
            data, cursor = self.get_users_page(cursor, proxies, user_agent)

            users_id += data

            if cursor:
                click.secho(f"Page #{i} | {len(users_id)} users id scraped. next cursor: {cursor[:5]}...", fg="blue")
            else:
                break

            i += 1

        users_id = users_id[:self.max_generations]

        click.secho(f"Finished scraping. {len(users_id)} users id scraped.", fg="green")

        return users_id