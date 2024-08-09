import httpc
import subprocess
import psutil
import random
import os
import win32event
from utils import Utils
import urllib.parse
from Proxy import Proxy

class RobloxClient(Proxy):
    def __init__(self, roblox_player_path):
        self.roblox_player_path = roblox_player_path

    def get_auth_ticket(self, cookie, user_agent, csrf_token):
        headers = httpc.get_roblox_headers(user_agent, csrf_token)

        cookies = { ".ROBLOSECURITY": cookie }

        response = httpc.post("https://auth.roblox.com/v1/authentication-ticket/", headers=headers, cookies=cookies)
        try:
            return response.headers["Rbx-Authentication-Ticket"]
        except KeyError:
            raise Exception("Rbx-auth-ticket not found. " + Utils.return_res(response))

    def kill(self, proc_pid):
        process = psutil.Process(proc_pid)
        for proc in process.children(recursive=True):
            proc.kill()
        process.kill()

    def launch_place(self, auth_ticket, place_id, timeout):
        cmd = self.get_join_cmd(auth_ticket, place_id)
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)

        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            if stderr:
               raise Exception("Failed to communicate with instance. " + str(stderr))
        except subprocess.TimeoutExpired:
            self.kill(proc.pid)

    def get_join_cmd(self, auth_ticket, place_id):
        browser_tracker_id = random.randint(200000000000, 210000000000)
        join_attempt_id = ""

        launcherurl = f'https://assetgame.roblox.com/game/PlaceLauncher.ashx?request=RequestGame&browserTrackerId={browser_tracker_id}&placeId={place_id}&isPlayTogetherGame=false&joinAttemptId={join_attempt_id}&joinAttemptOrigin=PlayButton'

        return f'"{self.roblox_player_path}" roblox-player:1+launchmode:play+gameinfo:{auth_ticket}+'\
            f'launchtime:{Utils.utc_sec()}+placelauncherurl:{urllib.parse.quote(launcherurl)}'\
                f'+browsertrackerid:{browser_tracker_id}+robloxLocale:en_en+gameLocale:en_en+channel:+LaunchExp:InApp'

    @staticmethod
    def find_roblox_player():
        user_home = os.path.expanduser("~")
        program_files_x86 = os.environ.get("ProgramFiles(x86)")

        base_directories = [
            os.path.join(user_home, "AppData", "Local", "Roblox", "Versions"),
            os.path.join(program_files_x86, "Roblox", "Versions"),
        ]

        for base_directory in base_directories:
            for root, dirs, files in os.walk(base_directory):
                if "RobloxPlayerBeta.exe" in files:
                    return os.path.join(root, "RobloxPlayerBeta.exe")

        raise FileNotFoundError("Could not find path to Roblox executable")

    @staticmethod
    def remove_singleton_mutex():
        win32event.CreateMutex(None, 1, "ROBLOX_singletonMutex")