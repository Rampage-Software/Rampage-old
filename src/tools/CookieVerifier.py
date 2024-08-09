import httpc
from Tool import Tool
import concurrent.futures
from utils import Utils
import random
import string
import time
import mailparser
from urllib.parse import unquote
from config import ConfigType

class CookieVerifier(Tool):
    def __init__(self, app):
        super().__init__("Cookie Verifier", "Verify your cookies!", app)

    def run(self):
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")

        cookies = self.get_cookies()
        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        req_worked = 0
        req_failed = 0
        total_req = len(cookies)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.verify_cookie, cookie, random.choice(proxies_lines)) for cookie in cookies]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    is_verified, response_text = future.result()
                except Exception as e:
                    is_verified, response_text = False, str(e)

                if is_verified:
                    req_worked += 1
                else:
                    req_failed += 1

                self.print_status(req_worked, req_failed, total_req, response_text, is_verified, "Verified")

    @Utils.handle_exception(3, False)
    def is_verified(self, cookie, user_agent, client):
        """
        Checks if a cookie is verified
        """
        req_url = "https://accountsettings.roblox.com/v1/email"
        req_cookies = {".ROBLOSECURITY": cookie}
        req_headers = httpc.get_roblox_headers(user_agent)

        response = client.get(req_url, headers=req_headers, cookies=req_cookies)

        if response.status_code != 200:
            raise Exception(f"Failed to check if cookie verified {Utils.return_res(response)}")

        try:
            is_verified = response.json()["verified"]
        except KeyError:
            raise Exception(f"Failed to access verified key {Utils.return_res(response)}")

        return is_verified

    @Utils.handle_exception(3, False)
    def create_address(self, client):
        """
        Creates a random email address
        """
        # get domain
        req_url = "https://api.mail.tm/domains"
        response = client.get(req_url)

        if response.status_code != 200:
            raise Exception(f"Failed to get domain {Utils.return_res(response)}")

        try:
            domain = response.json()["hydra:member"][0]["domain"]
        except KeyError:
            raise Exception(f"Failed to access domain key {Utils.return_res(response)}")

        # create email address
        address = ( ''.join(random.choice(string.ascii_lowercase) for i in range(10)) ) + "@" + domain
        req_url = "https://api.mail.tm/accounts"
        req_json = {"address": address, "password": "privatools"}
        response = client.post(req_url, json=req_json)

        if response.status_code != 201:
            raise Exception(f"Failed to create email {Utils.return_res(response)}")

        try:
            address = response.json()["address"]
        except KeyError:
            raise Exception(f"Failed to access address key {Utils.return_res(response)}")

        # get auth token
        req_url = "https://api.mail.tm/token"
        req_json = {"address": address, "password": "privatools"}
        response = client.post(req_url, json=req_json)

        try:
            token = response.json()["token"]
        except KeyError:
            raise Exception(f"Failed to access token key {Utils.return_res(response)}")

        if response.status_code != 200:
            raise Exception(f"Failed to get token {Utils.return_res(response)}")

        return address, token

    @Utils.handle_exception(3, False)
    def set_roblox_email(self, cookie, user_agent, client, csrf_token, email_addr):
        """
        Sets the roblox email address
        """
        req_url = "https://accountsettings.roblox.com/v1/email"
        req_cookies = {".ROBLOSECURITY": cookie}
        req_headers = httpc.get_roblox_headers(user_agent, csrf_token)
        req_json={"emailAddress": email_addr}

        response = client.post(req_url, headers=req_headers, cookies=req_cookies, json=req_json)

        return response.status_code == 200, Utils.return_res(response)

    @Utils.handle_exception(10, False)
    def get_email_id(self, token, client):
        """
        Gets the id of the latest email
        """
        time.sleep(1.5)
        req_url = "https://api.mail.tm/messages"
        req_params = {"page": 1}
        req_headers = {"Authorization": f"Bearer {token}"}
        response = client.get(req_url, params=req_params, headers=req_headers)

        if response.status_code != 200:
            raise Exception(f"Failed to get email id {Utils.return_res(response)}")

        try:
            mails = response.json()["hydra:member"]
        except KeyError:
            raise Exception(f"Failed to access hydra:member key {Utils.return_res(response)}")

        if len(mails) == 0:
            raise Exception("No mails found")

        return mails[0]["id"]

    @Utils.handle_exception(3, False)
    def get_email(self, token, mail_id, client):
        """
        Gets the email
        """
        req_url = f"https://api.mail.tm/sources/{mail_id}"
        req_headers = {"Authorization": f"Bearer {token}"}
        response = client.get(req_url, headers=req_headers)

        if response.status_code != 200:
            raise Exception(f"Failed to get email {Utils.return_res(response)}")

        try:
            data = response.json()["data"]
            mail = mailparser.parse_from_string(data)
        except KeyError:
            raise Exception(f"Failed to fetch data email {Utils.return_res(response)}")
        return mail

    @Utils.handle_exception(3, False)
    def click_verif_link(self, mail, cookie, user_agent, csrf_token, client):
        """
        Simulates clicking on the verification link
        """
        ticket = unquote(mail.body.split("?ticket=")[1].split('"')[0])

        req_url = "https://accountinformation.roblox.com/v1/email/verify"
        req_cookies = {".ROBLOSECURITY": cookie}
        req_headers = httpc.get_roblox_headers(user_agent, csrf_token)
        req_json = {"ticket": ticket}
        response = client.post(req_url, json=req_json, headers=req_headers, cookies=req_cookies)

        if response.status_code != 200:
            raise Exception(f"Failed to click verification link {Utils.return_res(response)}")

    @Utils.handle_exception(3)
    def verify_cookie(self, cookie, proxies_line):
        """
        Verifies a cookie
        """
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies) as client:
            user_agent = httpc.get_random_user_agent()
            csrf_token = self.get_csrf_token(cookie, client)

            # make sure email is not already verified
            is_verified = self.is_verified(cookie, user_agent, client)
            if is_verified:
                return True, "Email is already verified"

            address, token = self.create_address(client)

            # set roblox email
            is_valid, response_text = self.set_roblox_email(cookie, user_agent, client, csrf_token, address)
            if not is_valid:
                raise Exception(response_text)

            # get roblox email
            mail_id = self.get_email_id(token, client)
            mail = self.get_email(token, mail_id, client)
            # click on verification link
            self.click_verif_link(mail, cookie, user_agent, csrf_token, client)

        return True, "The email address has been verified."
