import httpc
from Tool import Tool
from utils import Utils
import math
import random
import click
from config import ConfigType

class Gen2018Acc(Tool):
    def __init__(self, app):
        super().__init__("Gen 2018 Acc", "2018 old roblox account generator", app)

    def run(self):
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")

        user_id = 73223429
        default_pass = "insaneclient101"

        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]
        proxies_line = random.choice(proxies_lines)
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        user_agent = httpc.get_random_user_agent()

        with httpc.Session(proxies=proxies) as client:
            followers_count = self.get_followers_count(user_id, client, user_agent)
            follower_per_page = 18
            max_pages = math.ceil(followers_count / follower_per_page)
            max_loop_pages = 50 if max_pages > 50 else max_pages
            loop_pages = random.randint(0, max_loop_pages)

            cursor = None
            followers = []
            for i in range(loop_pages):
                cursor, followers = self.get_followers(user_id, cursor, follower_per_page, client, user_agent)

            username = followers[random.randint(0, len(followers)-1)]["name"]

        click.echo(f"2018 Account Generated: {username}:{default_pass}")

    @Utils.handle_exception(3)
    def get_followers_count(self, user_id, client, user_agent):
        """
        Get the amount of followers of a user
        """
        req_url = f"https://friends.roblox.com/v1/users/{user_id}/followers/count"
        req_headers = httpc.get_roblox_headers(user_agent)

        response = client.get(req_url, headers=req_headers)

        if response.status_code != 200:
            raise Exception(Utils.return_res(response))

        try:
            count = response.json()["count"]
        except KeyError:
            raise Exception("Failed to access count key. " + Utils.return_res(response))

        return count

    @Utils.handle_exception(3)
    def get_followers(self, user_id, cursor, follower_per_page, client, user_agent):
        """
        Get a page of followers
        """
        req_url = f"https://friends.roblox.com/v1/users/{user_id}/followers?sortOrder=Desc&limit={follower_per_page}{'&cursor='+cursor if cursor else ''}"
        req_headers = httpc.get_roblox_headers(user_agent)

        response = client.get(req_url, headers=req_headers)
        if response.status_code != 200:
            raise Exception(Utils.return_res(response))

        response_json = response.json()

        return response_json["nextPageCursor"], response_json["data"]
