import json
import random
import httpc
from abc import ABC, abstractmethod
from Proxy import Proxy
from utils import Utils
import click
import re
import string
from datetime import datetime
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
import base64
import time
import secrets

class Tool(Proxy, ABC):
    def __init__(self, name: str, description: str,  app: object):
        super().__init__()

        self.name = name
        self.description = description
        self.app = app
        self.results = None
        self.exit_flag = False
        self.executor = None

        self.config = {}
        self.captcha_tokens = {}

        # file paths
        self.cache_directory = app.cache_directory
        self.files_directory = app.files_directory
        self.cookies_file_path = app.cookies_file_path
        self.proxies_file_path = app.proxies_file_path
        self.config_file_path = app.config_file_path

        self.load_config()

    @abstractmethod
    def run(self):
        """
        Runs the tool
        """
        raise NotImplementedError("Domain Driven Design")

    def load_config(self):
        """
        Injects the config file attributes into the Tool class
        """
        try:
            f = open(self.config_file_path)
        except FileNotFoundError:
            raise Exception("Config file not found. Make sure to have it in files/config.json")

        data = f.read()
        f.close()
        try:
            x = json.loads(data)
        except json.JSONDecodeError:
            print(f"Config file is not a valid JSON file. Please fix it here and restart the program: {self.app.config_file_path}")
            input("Press enter to exit...")
            exit()
        # inject specific tool config
        try:
            props = x[(self.name).replace(" ", "")]
            for prop in props:
                self.config[prop] = props[prop]
        except KeyError:
            # ignore if tool has no config
            pass
        # inject captcha tokens
        props = x["FunCaptchaSolvers"]
        for prop in props:
            self.captcha_tokens[prop.replace("_token", "")] = props[prop]

        return self.config

    def get_csrf_token(self, cookie:str, client = httpc) -> str:
        """
        Retrieve a CSRF token from Roblox
        """
        cookies = {'.ROBLOSECURITY':cookie } if cookie is not None else None
        response = client.post("https://auth.roblox.com/v2/login", cookies=cookies)

        try:
            csrf_token = response.headers["X-Csrf-Token"]
        except KeyError:
            raise Exception(Utils.return_res(response))

        return csrf_token

    def get_user_info(self, cookie, client, user_agent):
        """
        Gets the user info from the Roblox API
        """
        req_url = "https://www.roblox.com/mobileapi/userinfo"
        req_cookies = { ".ROBLOSECURITY": cookie }
        req_headers = httpc.get_roblox_headers(user_agent)

        response = client.get(req_url, headers=req_headers, cookies=req_cookies)

        if (response.status_code != 200):
            raise Exception(Utils.return_res(response))

        try:
            result = response.json()

            user_info = {
                "UserID": result["UserID"],
                "UserName": result["UserName"],
                "RobuxBalance": result["RobuxBalance"],
                "ThumbnailUrl": result["ThumbnailUrl"],
                "IsAnyBuildersClubMember": result["IsAnyBuildersClubMember"],
                "IsPremium": result["IsPremium"]
            }
        except KeyError:
            raise Exception("Failed to get user info "+Utils.return_res(response))

        return user_info

    def get_cookies(self, amount = None, provide_lines = False, **kwargs) -> list:
        """
        Gets cookies from cookies.txt file
        """
        f = open(self.cookies_file_path, 'r+')
        lines = f.read().splitlines()
        f.close()

        # ignore duplicates
        lines = [*set(lines)]
        random.shuffle(lines)

        # take only the cookie (not u:p)
        pattern = re.compile(r'_\|WARNING:-DO-NOT-SHARE-THIS\.-.*')
        cookies = [match.group(0) for line in lines for match in [pattern.search(line)] if match]

        if len(cookies) == 0 and kwargs.get("ignore_zero_cookie") != True:
            raise Exception("No cookies found. Make sure to generate some first")

        if amount is not None and amount < len(cookies):
            cookies = cookies[:amount]

        if provide_lines:
            return cookies, lines

        return cookies

    def get_session_cookies(self, cookie, user_agent, client, save_bandwidth=False):
        current_date_time = datetime.now()
        formatted_date_time = current_date_time.strftime("%m/%d/%Y %I:%M:%S %p")

        # hard coded
        cookies = {
            "GuestData": "UserID=-2015934489",
            "_gcl_au": "1.1.972540853.1711507247",
            "__utmz": "200924205.1711507299.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)",
            "RBXEventTrackerV2": f"CreateDate=3/26/2024 10:06:57 PM&rbxid=5702860181&browserid=222113722681",
            "rbxas": "5e2227439f764c491442832ebcc94d111ea4ebfafb731568f54ea07d12d9878a",
            "__utma": "200924205.552093188.1711507299.1711507299.1711740117.2",
            "rbx-ip2": "",
            "RBXSource": f"rbx_acquisition_time=3/26/2024 9:40:52 PM&rbx_acquisition_referrer=https://www.roblox.com/&rbx_medium=Direct&rbx_source=www.roblox.com&rbx_campaign=&rbx_adgroup=&rbx_keyword=&rbx_matchtype=&rbx_send_info=1",
            "RBXImageCache": "timg=f0TikUd4dQueKLbSrlCZPw2gKU_S0FQNsIXhhr_9rCt41OXvH3yk-QGMZQUdhkqrLz9wWW37bTA-rxP7uvIup9PBZlLbpm3dFnMirLwcFrljQqu_eOgSGzc7zHqvyH_ZHMgTXh75Oirz4ynlq1Xsf8qG8ZeDrE4qlCr8B7zofAZjLn2FolE8nIDtgA3sFRm-coMMQo42U6tzSLB4uwQBGA",
            "__utmc": "200924205",
            "RBXSessionTracker":"sessionid=1345123c-2e2b-4f38-b1f0-0c79a0f50002",
            "__utmb": "200924205.0.10.1711740117"
        }

        # cookies = {
        #     **cookies,
        #     "GuestData": f"UserID={random.randint(-2_147_483_648, 2_147_483_647)}",
        #     "_gcl_au": ".".join([str(random.randint(1, 999)), str(random.randint(1, 999)), str(random.randint(100000000, 999999999)), str(random.randint(1000000000, 9999999999))]),
        #     "__utmz": ".".join([str(random.randint(100000000, 999999999)), str(random.randint(1000000000, 9999999999)), "1", "1", "|".join([f"utm{i}=(direct)" for i in ['csr', 'ccn', 'cmd']])]),
        #     "RBXEventTrackerV2": f"CreateDate={formatted_date_time}&rbxid={random.randint(0, 9999999999)}&browserid={random.randint(0, 999999999999)}",
        #     "rbxas": secrets.token_hex(32),
        #     "__utma": ".".join(map(str, [random.randint(100000000, 999999999), random.randint(1000000000, 9999999999), random.randint(1000000000, 9999999999), random.randint(1000000000, 9999999999), random.randint(1000000000, 9999999999), random.randint(0, 9)])),
        #     "RBXImageCache": "timg=" + ''.join(secrets.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_') for _ in range(191))
        # }

        if cookie and not save_bandwidth:
            req_url = "https://www.roblox.com/home"
            req_headers = httpc.get_roblox_headers(user_agent)
            req_cookies = {'.ROBLOSECURITY': cookie }

            result = client.get(req_url, headers=req_headers, cookies=req_cookies)

            try:
                rbx_ip2 = httpc.extract_cookie(result, "rbx-ip2")
                tracker_v2 = httpc.extract_cookie(result, "RBXEventTrackerV2")
                guest_data = httpc.extract_cookie(result, "GuestData")
                session_tracker = httpc.extract_cookie(result, "RBXSessionTracker")
            except Exception:
                raise Exception(Utils.return_res(result))

            cookies = {
                **cookies,
                ".ROBLOSECURITY": cookie,
                "rbx-ip2": rbx_ip2,
                "RBXEventTrackerV2": tracker_v2,
                "GuestData": guest_data,
                "RBXSessionTracker": session_tracker,
            }

        return cookies

    def get_fake_auth_bat(self):
        characters = string.ascii_letters + string.digits + '+/='
        random_string = ''.join(random.choice(characters) for _ in range(32))
        timestamp = str(int(time.time()))
        random_string2 = ''.join(random.choice(characters) for _ in range(64))

        return f"{random_string}|{timestamp}|{random_string2}"

    def export_public_key_as_spki(self, public_key):
        spki_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return base64.b64encode(spki_bytes).decode('utf-8')

    def generate_signing_key_pair_unextractable(self):
        private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
        public_key = private_key.public_key()

        return private_key, public_key

    def sign(self, private_key, data):
        signature = private_key.sign(data, ec.ECDSA(hashes.SHA256()))

        return base64.b64encode(signature).decode('utf-8')

    def getAuthIntent(self, user_agent, client):
        private_key, public_key = self.generate_signing_key_pair_unextractable()
        client_public_key = self.export_public_key_as_spki(public_key)
        client_epoch_timestamp = int(time.time())

        req_url = "https://apis.roblox.com/hba-service/v1/getServerNonce"
        csrf_token = self.get_csrf_token(None, client)
        req_headers = httpc.get_roblox_headers(user_agent, csrf_token)

        response = client.get(req_url, headers=req_headers)
        server_nonce = response.text.strip('"')
        payload = f"{client_public_key}|{str(client_epoch_timestamp)}|{server_nonce}"
        payload_bytes = bytes(payload, 'utf-8')
        sai_signature = self.sign(private_key, payload_bytes)

        return {
            "clientEpochTimestamp": client_epoch_timestamp,
            "clientPublicKey": client_public_key,
            "saiSignature": sai_signature,
            "serverNonce": server_nonce
        }

    def print_status(self, req_worked, req_failed, total_req, response_text, has_worked, action_verb, debug_mode = False):
        """
        Prints the status of a request
        """
        # debug mode prevents the output from being cleared
        first_output = response_text
        if not debug_mode:
            first_output = "\033[1A\033[K" + first_output

        click.secho(first_output, fg="red" if not has_worked else "green")

        output = click.style(f"{action_verb}: {str(req_worked)}", fg="green")
        output += " | "
        output += click.style(f"Failed: {str(req_failed)}", fg="red")
        output += " | "
        output += f"Total: {str(total_req)}"

        if not debug_mode:
            click.echo(output)

        if not self.app.discord_webhook in [None, ""]:
            self.send_webhook_status(self.app.discord_webhook, Utils.escape_ansi(output), Utils.escape_ansi(first_output), 0x00FF00 if has_worked else 0x4dff4d)

    def send_webhook_status(self, webhook_url, title, description, color):
        payload = {
            "content": None,
            "embeds": [
                {
                    "title": title,
                    "description": description,
                    "color": color
                }
            ],
            "attachments": []
        }
        headers = {
            'Content-Type': 'application/json'
        }
        httpc.post(webhook_url, data=json.dumps(payload), headers=headers)

    def signal_handler(self):
        """
        Handles the signal
        """
        if self.executor:
            self.executor.shutdown(wait=False, cancel_futures=True)

        self.exit_flag = True

    @staticmethod
    def run_until_exit(func):
        def wrapper(instance, *args, **kwargs):
            while True:
                result = func(instance, *args, **kwargs)

                if instance.exit_flag:
                    break
            return result
        return wrapper

    def __str__(self) -> str:
        return "A Privatools tool. " + self.description
