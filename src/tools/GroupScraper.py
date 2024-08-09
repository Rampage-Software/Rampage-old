import os
import httpc
import threading
from Tool import Tool
import random
import click
from utils import Utils, Infinite
from config import ConfigType

class GroupScraper(Tool):
    def __init__(self, app):
        super().__init__("Group Scraper", "Scrape and auto claim ownerless groups.", app)

        self.file_groups_id = os.path.join(self.files_directory, "./groups-id.txt")

        Utils.ensure_files_exist([self.file_groups_id])

    def run(self):
        self.cookie_claimer = ConfigType.string(self.config, "cookie_claimer")
        self.start_group_id = ConfigType.integer(self.config, "start_group_id")
        self.end_group_id = ConfigType.integer(self.config, "end_group_id")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")

        if not self.cookie_claimer or not self.start_group_id or not self.end_group_id:
            raise Exception("cookie_claimer, start_group_id and end_group_id must not be null.")

        self.proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        self.found = 0
        self.unclaimable = 0
        self.req_failed = 0

        self.file_lock = threading.Lock()
        self.output_lock = threading.Lock()

        self.executor = Infinite(self.thread_function, self.max_threads)
        self.executor.start()

    def thread_function(self):
        proxies_line = random.choice(self.proxies_lines)

        try:
            found_groups_ids, unclaimable, failed, response_text = self.scrape_group(proxies_line)
            scraped = True

            if len(found_groups_ids) > 0:
                with self.file_lock:
                    with open(self.file_groups_id, "a") as f:
                        f.write("\n".join(found_groups_ids) + "\n")

                color = "green"
            else:
                color = "yellow"

        except Exception as e:
            scraped, response_text = False, str(e)
            color = "red"

        if scraped:
            self.found += len(found_groups_ids)
            self.unclaimable += unclaimable
            self.req_failed += failed

        with self.output_lock:
            self.print_status(self.found, self.unclaimable, self.req_failed, response_text, color)

    def print_status(self, found, unclaimable, req_failed, response_text, color):
        """
        Prints the status of a request
        """
        click.secho("\033[1A\033[K"+response_text, fg=color)

        total_req = found + req_failed + unclaimable

        output = click.style(f"Found: {str(found)}", fg="green")
        output += " | "
        output += click.style(f"Unclaimable: {str(unclaimable)}", fg="yellow")
        output += " | "
        output += click.style(f"Failed: {str(req_failed)}", fg="red")
        output += " | "
        output += f"Total: {str(total_req)}"

        click.echo(output)

    @Utils.handle_exception(1)
    def scrape_group(self, proxies_line):
        """
        Fetch a group's information
        """
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()

            group_ids = ','.join(str(random.randint(self.start_group_id, self.end_group_id)) for _ in range(100))
            req_url = f'https://groups.roblox.com/v2/groups?groupIds={group_ids}'
            req_headers = httpc.get_roblox_headers(user_agent)

            response = client.get(req_url, headers=req_headers)

            if response.status_code != 200:
                raise Exception(f"Failed to fetch groups." + Utils.return_res(response))

            data = response.json()

            found_groups_ids = []
            unclaimable = 0
            failed = 0

            for group in data["data"]:
                owner = group["owner"]
                if owner:
                    unclaimable += 1
                    continue

                group_id = group["id"]

                ownerless_response = client.get(f'https://groups.roblox.com/v1/groups/{group_id}')

                if ownerless_response.status_code != 200:
                    failed += 1
                    continue

                ownerless_data = ownerless_response.json()
                if not ownerless_data["publicEntryAllowed"] or ownerless_data.get("isLocked", False):
                    unclaimable += 1
                    continue

                found_groups_ids.append(group_id)
                response_text = self.claim_group(group_id)

        if len(found_groups_ids) == 0:
            response_text = f"No groups found. {unclaimable} unclaimable. {failed} failed."

        return found_groups_ids, unclaimable, failed, response_text

    @Utils.handle_exception(3, False)
    def claim_group(self, group_id):
        user_agent = httpc.get_random_user_agent()

        req_url = f"https://groups.roblox.com/v1/groups/{group_id}/claim-ownership"
        csrf_token = self.get_csrf_token(self.cookie_claimer)
        req_headers = httpc.get_roblox_headers(user_agent, csrf_token)
        req_cookies = { ".ROBLOSECURITY": self.cookie_claimer }

        response = httpc.post(req_url, headers=req_headers, cookies=req_cookies)

        if "This group already has an owner" in response.text:
            return Utils.return_res(response)

        if response.status_code != 200:
            raise Exception(f"Failed to claim group {group_id}." + Utils.return_res(response))

        return Utils.return_res(response)
