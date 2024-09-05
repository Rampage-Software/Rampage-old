import os
from tools import AutoDiscordRpc,CommentBot,CookieChecker,CookieFlagChecker,CookieGenerator,CookieRefresher,CookieRegionUnlocker,CookieVerifier,DisplayNameChanger,EmailChecker,FavoriteBot,FollowBot,FriendRequestBot,GamepassCreator,GameVisits,GameVote,GroupAllyBot,GroupClothesStealer,GroupJoinBot,GroupScraper,GroupWallSpammer,ItemBuyer, MassClothesDownloader, MassClothesUnduplicator, MassClothesUploader,MessageBot,MessageUsersScraper,ModelFavorite,ModelSales,ModelVote,PasswordChanger,ProxyChecker,ProxyScraper,RbxTransfer,ReportBot,SolverBalanceChecker,StatusChanger,TShirtGenerator,UP2UPC,UPC2C,UsernameSniper,VipServerScraper,RbxSpaceAutoLister,ChatSpammer
from Tool import Tool
from utils import Utils
import json
from data.config import config
from data.version import version
import httpc
import time
import click
import pygetwindow as gw
import sys
import subprocess

class App():
    def __init__(self):
        self.old_files_directory = os.path.join(os.path.dirname(__file__), "../files")
        self.files_directory = os.path.join(os.path.expanduser('~/documents'), "./privatools-files")
        self.cache_directory = os.path.join(self.files_directory, "./.versacache")
        self.proxies_file_path = os.path.join(self.files_directory, "proxies.txt")
        self.cookies_file_path = os.path.join(self.files_directory, "cookies.txt")
        self.config_file_path = os.path.join(self.files_directory, "config.json")

        self.proxies_loaded = None
        self.cookies_loaded = None

        Utils.ensure_directories_exist([self.cache_directory, self.files_directory])
        Utils.ensure_files_exist([self.proxies_file_path, self.cookies_file_path])

        self.ensure_config_file()

        self.global_settings = {}
        self.color = "red"
        self.discord_webhook = None
        self.auto_files_launch = True

        self.load_global_settings()

        self.tools = [t(self) for t in Tool.__subclasses__()]

    @staticmethod
    def get_version():
        return version

    def get_tool_from(self, tool_identifier):
        """
        Returns the tool from its name or number
        """
        if tool_identifier.isdigit():
            tool_name = self.tools[int(tool_identifier) - 1].name
        else:
            # match the closest tool name
            tool_name = Utils.get_closest_match(tool_identifier, [tool.name for tool in self.tools])

        if tool_name is None:
            raise Exception("Tool not found")

        return self.get_tool_from_name(tool_name)

    def get_tool_from_name(self, tool_name):
        """
        Returns the tool from its name
        """
        tool = next((t for t in self.tools if t.name == tool_name), None)
        return tool

    def ensure_config_file(self):
        """
        Ensure config file exists and is valid
        """
        config_file_path = os.path.join(self.files_directory, "config.json")
        # make sure config file exists
        if not os.path.exists(config_file_path):
            with open(config_file_path, "w") as json_file:
                json.dump(config, json_file, indent=4)
        else:
            # make sure config file contains all keys and not more
            with open(config_file_path, "r+") as json_file:
                try:
                    file_config = json.load(json_file)
                except json.JSONDecodeError:
                    print(f"Config file is not a valid JSON file. Please fix it here and restart the program: {config_file_path}")
                    input("Press enter to exit...")
                    exit()

                for key in config:
                    if key not in file_config:
                        file_config[key] = config[key]
                    else:
                        for subkey in config[key]:
                            if subkey not in file_config[key]:
                                file_config[key] = {subkey: config[key][subkey], **file_config[key]}

                            # make sure subkeys starting with // are not overwritten
                            if subkey.startswith("//"):
                                file_config[key][subkey] = config[key][subkey]

                # make sure there are no extra keys
                for key in list(file_config):
                    if key not in config:
                        del file_config[key]
                    else:
                        for subkey in list(file_config[key]):
                            if subkey not in config[key]:
                                del file_config[key][subkey]

                # keep order of config's keys
                file_config = {k: file_config[k] for k in config}
                # keep order of config's subkeys
                for key in file_config:
                    file_config[key] = {k: file_config[key][k] for k in config[key]}

                json_file.seek(0)
                json_file.truncate()
                json.dump(file_config, json_file, indent=4)

    def load_global_settings(self):
        """
        Inject global settings directly into the class
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
            print(f"Config file is not a valid JSON file. Please fix it here and restart the program: {self.config_file_path}")
            input("Press enter to exit...")
            exit()

        props = x["GlobalSettings"]
        for prop in props:
            setattr(self, prop, props[prop])

        if not self.color in ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white", "bright_black", "bright_red", "bright_green", "bright_yellow", "bright_blue", "bright_magenta", "bright_cyan", "bright_white"]:
            self.color = "red"

    def update_config_prop(self, prop_name, config):
        with open(self.config_file_path, "r+") as json_file:
            file_config = json.load(json_file)
            file_config[prop_name.replace(" ", "")] = config
            json_file.seek(0)
            json_file.truncate()
            json.dump(file_config, json_file, indent=4)

    def get_key_config(self, key):
        try:
            f = open(self.config_file_path)
        except FileNotFoundError:
            raise Exception("Config file not found. Make sure to have it in files/config.json")

        data = f.read()
        f.close()
        x = json.loads(data)

        return x[key]

    def get_solver_config(self):
        return self.get_key_config("FunCaptchaSolvers")

    def set_solver_config(self, config):
        self.update_config_prop("FunCaptchaSolvers", config)

    def get_global_settings(self):
        return self.get_key_config("GlobalSettings")

    def set_global_settings(self, config):
        self.update_config_prop("GlobalSettings", config)
        self.load_global_settings()

    def set_tool_config(self, tool, tool_config):
        tool.config = tool_config
        self.update_config_prop(tool.name, tool.config)

    def get_proxies_loaded(self):
        try:
            f = open(self.proxies_file_path, 'r')
        except FileNotFoundError:
            amount = 0

        proxies_list = f.readlines()
        f.close()
        proxies_list = [*set(proxies_list)] # remove duplicates
        amount = len(proxies_list)

        self.proxies_loaded = amount

        return amount

    def get_cookies_loaded(self):
        amount = len(self.tools[0].get_cookies(ignore_zero_cookie=True))

        if amount != self.cookies_loaded:
            self.cookies_loaded = amount

        return amount

    def start_files_dir(self):
        os.startfile(self.files_directory)

    def verify_license(self):
        try:
            with open(self.config_file_path) as f:
                data = f.read()
        except FileNotFoundError:
            raise Exception("Config file not found. Make sure to have it in files/config.json")

        x = json.loads(data)
        key = x["License"]["key"]

        print(key)

        req_url = "https://www.3rr0r.lol/api/verify.js"
        req_headers = {
            "Content-Type": "application/json"
        }
        req_params = {
            "key": key,
            "hwid": Utils.get_hwid()
        }

        response = httpc.get(req_url, headers=req_headers, params=req_params)

        if response.status_code == 429:
            raise Exception("Rate limited. Try again later")

        if response.status_code not in [200, 400]:
            print("Response: ", response.text)
            raise Exception("Failed to verify license key or HWID. We are currently experiencing issues. Try again later")

        result = response.json()
        return response.status_code == 200

    def set_license_key(self, key):
        self.update_config_prop("License", {
            "key": key
        })

    def exit_on_re(self):
        click.secho("\nReverse engineering program detected. THIS will be reported. Closing Versatools.", fg="red")
        os._exit(1)

    def watch_re_in_tasklist(self):
        """
        Check if no reverse engineering program is opened
        Not very effective but better than nothing
        """
        while True:
            bad_processes = [
                "wireshark", "fiddler", "x96dbg", "x64dbg", "dnspy"
            ]

            for bad_process in bad_processes:
                # check windows title
                if len(gw.getWindowsWithTitle(bad_process)) > 0:
                    print(f"Reverse engineering program detected: {bad_process}")
                    self.exit_on_re()

            time.sleep(1)

    def check_auto_update(self):
        """
        Check if there is a new version available
        """

        req_url = "https://raw.githubusercontent.com/Its3rr0rsWRLD/RAMPAGE/main/version.txt"
        response = httpc.get(req_url)

        if response.status_code != 200:
            return False
        
        latest_version = response.text.strip()

        if latest_version != self.get_version():
            return latest_version
        
        return False

    def update(self):
        req_url = "https://raw.githubusercontent.com/Its3rr0rsWRLD/RAMPAGE/main/Privatools.exe"
        response = httpc.get(req_url)

        if response.status_code != 200:
            raise Exception("Failed to download update. Try again later. " + response.text)

        update_file_path = os.path.join(self.cache_directory, "privatools.exe")

        with open(update_file_path, 'wb') as update_file:
            update_file.write(response.content)

        current_script_path = os.path.abspath(sys.argv[0])

        if not os.path.exists(current_script_path):
            raise Exception(f"Error: Current script path '{current_script_path}' does not exist.")

        # Path for the updater script
        updater_script_path = os.path.join(self.cache_directory, "update_script.bat")

        # Create the updater script
        with open(updater_script_path, 'w') as updater_script:
            updater_script.write(f"""
@echo off
timeout /nobreak /t 1 >nul

:: Replace the current file with the downloaded file
move /y "{update_file_path}" "{current_script_path}"
if errorlevel 1 (
    echo Update failed. Please manually replace "{current_script_path}" with "{update_file_path}".
) else (
    echo Update applied successfully. Please restart the application.
    pause
)

:: Prompt the user to restart the application
echo Update applied successfully. Please restart the application.
pause

:: Exit the updater script
exit /b 0
""")

        # Run the updater script using a new Python process
        subprocess.Popen([updater_script_path], shell=True)

        # Exit the current script
        sys.exit()

    def start_rpc_thread(self):
        rpc = self.get_tool_from_name("Auto Discord RPC")
        rpc.run(True)

    def __str__(self) -> str:
        return "Privatools main class"
