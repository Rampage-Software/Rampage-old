import httpc
import random
from Tool import Tool
import concurrent.futures
from utils import Utils
import re
from config import ConfigType, Config

class ReportBot(Tool):
    def __init__(self, app):
        super().__init__("Report Bot", "Report massively something offending", app)

    def run(self):
        self.report_types = ["user", "game", "group"]
        self.report_type = ConfigType.string(self.config, "report_type")
        self.thing_id = ConfigType.integer(self.config, "thing_id")
        self.comment = ConfigType.string(self.config, "comment")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")
        self.max_generations = Config.input_max_generations()

        if self.report_type not in self.report_types:
            raise Exception(f"Invalid report type: {self.report_type}. Can only be: {self.report_types}")

        if not self.report_type or not self.thing_id or not self.comment:
            raise Exception("report_type, thing_id and comment must not be null.")

        cookies = self.get_cookies(self.max_generations)
        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        req_worked = 0
        req_failed = 0
        total_req = len(cookies)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.send_report, cookie, random.choice(proxies_lines)) for cookie in cookies]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    has_reported, response_text = future.result()
                except Exception as e:
                    has_reported, response_text =  False, str(e)

                if has_reported:
                    req_worked += 1
                else:
                    req_failed += 1

                self.print_status(req_worked, req_failed, total_req, response_text, has_reported, "Reported")

    @Utils.handle_exception()
    def send_report(self, cookie, proxies_line):
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()
            verif_token = self.get_verif_token(cookie, client, user_agent)
            req_url, redirect_url = self.get_report_url()

            req_cookies = {
                ".ROBLOSECURITY": cookie,
            }
            req_headers = httpc.get_roblox_headers(user_agent, None, "application/x-www-form-urlencoded")
            req_data = {
                "__RequestVerificationToken": verif_token,
                "ReportCategory": "9",
                "Comment": self.comment,
                "Id": str(self.thing_id),
                "RedirectUrl": redirect_url,
                "PartyGuid": '',
                "ConversationId": ''
            }

            response = client.post(req_url, headers=req_headers, cookies=req_cookies, data=req_data)

            if response.status_code != 200:
                raise Exception(Utils.return_res(response))

            # get message <h4>here</h4>
            try:
                message = re.search(r'<div id="report-body" class="section-content">\s*<div id="report-header" class="section-header">\s*<h4>(.*?)<\/h4>', response.text).group(1)
            except AttributeError:
                return False, f"{Utils.return_res(response)} Failed to get report response."

            return True, message

    def get_report_url(self):
        if self.report_type == "user":
            redirect_url = f"https://www.roblox.com/users/{self.thing_id}/profile"
            req_url = f"https://www.roblox.com/abusereport/userprofile?id={self.thing_id}&redirecturl={redirect_url}"
        elif self.report_type == "game":
            redirect_url = f"https://www.roblox.com/games/{self.thing_id}"
            req_url = f"https://www.roblox.com/abusereport/asset?id={self.thing_id}&redirecturl={redirect_url.replace('https://www.roblox.com', '')}"
        elif self.report_type == "group":
            redirect_url = f"https://www.roblox.com/groups/{self.thing_id}"
            req_url = f"https://www.roblox.com/abuseReport/group?id={self.thing_id}&RedirectUrl={redirect_url}"
        else:
            raise Exception(f"Invalid report type: {self.report_type}. Can only be: {self.report_types}")

        return req_url, redirect_url

    @Utils.handle_exception(2, False)
    def get_verif_token(self, cookie, client, user_agent):
        """
        Get the verification token for a report
        """
        req_url, redirect_url = self.get_report_url()
        req_cookies = {".ROBLOSECURITY": cookie}
        req_headers = httpc.get_roblox_headers(user_agent)

        response = client.get(req_url, headers=req_headers, cookies=req_cookies)

        if response.status_code != 200:
            raise Exception(Utils.return_res(response))

        # IN: <input name="__RequestVerificationToken" type="hidden" value="here" />
        verif_token = re.search(r'<input name="__RequestVerificationToken" type="hidden" value="(.*)" />', response.text).group(1)
        if not verif_token:
            raise Exception("Failed to get verification token")

        return verif_token
