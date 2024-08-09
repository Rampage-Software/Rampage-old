import random
import httpc
from utils import Utils

class Proxy():
    def __init__(self):
        self.supported_proxy_protocols = ["http"]

    def test_proxy(self, proxies: dict, timeout:int) -> bool:
        """
        Checks if a proxy is working
        """
        try:
            response = httpc.get('https://www.roblox.com', proxies=proxies, timeout=timeout)
            if response.status_code != 200:
                return False
        except Exception:
            return False

        return True

    def write_proxy_line(self, proxy_type:str, proxy_ip:str, proxy_port:int, proxy_user:str = None, proxy_pass:str = None) -> str:
        """
        Write a correctly formatted proxy line for proxies.txt file
        """
        proxy_type = None if proxy_type == "http" else proxy_type

        if (proxy_user is not None and proxy_pass is not None):
            auth = True
        elif (proxy_user is None and proxy_pass is None):
            auth = False
        else:
            raise ValueError("Invalid Parameters. If proxy has auth, make sure to provide username and password")

        return f"{proxy_type + ':' if proxy_type else ''}{proxy_ip}:{proxy_port}{':' + proxy_user + ':' + proxy_pass if auth else ''}"

    def check_proxies_file_format(self, file_path: str) -> bool:
        """
        Makes sure proxies.txt file format is good before checking/using proxies
        """
        try:
            f = open(file_path)
        except FileNotFoundError:
            raise FileNotFoundError("files/proxies.txt path not found. Create it, add proxies and try again")

        lines = f.readlines()
        f.close()

        for i, line in enumerate(lines):
            line = Utils.clear_line(line)
            line_number = i + 1

            # make sure no line is empty
            if line == "":
                lines.remove(line)
                continue

            try:
                proxy_type_provided, proxy_type, proxy_ip, proxy_port, proxy_user, proxy_pass = self.get_proxy_values(line)
            except ValueError as e:
                raise SyntaxError(str(e), (
                    file_path,
                    line_number,
                    None,
                    line
                ))

            # make sure proxy_type is supported
            if proxy_type not in self.supported_proxy_protocols:
                raise SyntaxError("Proxy type not supported", (
                    file_path,
                    line_number,
                    None,
                    line
                ))

            # validate proxy_port
            if not (0 <= proxy_port and proxy_port <= 65536):
                lines.remove(line)
                continue

        # if 0 proxy found, display error message
        if len(lines) == 0:
            raise Exception("No proxy found in files/proxies.txt. Please add some and try again")

        return True

    def get_proxy_values(self, line: str) -> tuple:
        """
        Gets all proxy values from a line according to different line formats
        """
        line_split = line.split(":")
        num_item = len(line_split)

        proxy_type = None
        proxy_user = None
        proxy_pass = None

        # get proxy_type, proxy_ip, proxy_port, proxy_user (if provided), proxy_pass (if provided)
        if num_item in [2, 4]:
            proxy_type_provided = False
            proxy_type = "http"
            proxy_ip = line_split[0]
            proxy_port = line_split[1]
            if num_item == 4:
                proxy_user = line_split[2]
                proxy_pass = line_split[3]
        elif num_item in [3, 5]:
            proxy_type_provided = True
            proxy_type = line_split[0].lower()
            proxy_ip = line_split[1]
            proxy_port = line_split[2]
            if num_item == 5:
                proxy_user = line_split[3]
                proxy_pass = line_split[4]
        else:
            raise ValueError("Incorrect proxy line format")

        try:
            proxy_port = int(proxy_port)
        except:
            raise ValueError("Proxy port must be a number")

        return proxy_type_provided, proxy_type, proxy_ip, proxy_port, proxy_user, proxy_pass

    def get_proxies(self, proxy_type: str, proxy_ip: str, proxy_port: int, proxy_user: str = None, proxy_pass: str = None) -> dict:
        """
        Returns a dict of proxies
        """
        if (proxy_user is not None and proxy_pass is not None):
            auth = True
        elif (proxy_user is None and proxy_pass is None):
            auth = False
        else:
            raise ValueError("Invalid Parameters. If proxy has auth, make sure to provide username and password")

        if auth:
            proxy = f"{proxy_type}://{proxy_user}:{proxy_pass}@{proxy_ip}:{proxy_port}/"
        else:
            proxy = f"{proxy_type}://{proxy_ip}:{proxy_port}/"

        proxies = {
            "http": proxy,
            "https": proxy
        }

        return proxies

    def get_proxies_lines(self) -> dict:
        """
        Gets random proxy dict
        """
        try:
            f = open(self.app.proxies_file_path, 'r')
        except FileNotFoundError:
            raise FileNotFoundError("files/proxies.txt path not found. Create it, add proxies and try again")

        proxies_lines = f.readlines()
        f.close()

        if len(proxies_lines) == 0:
            raise Exception("No proxies found in files/proxies.txt. Please add some and try again")

        proxies_lines = [Utils.clear_line(line) for line in proxies_lines]

        return proxies_lines

    def convert_line_to_proxy(self, line: str) -> list:
        """
        Converts lines to proxies
        """
        proxy_type_provided, proxy_type, proxy_ip, proxy_port, proxy_user, proxy_pass = self.get_proxy_values(line)

        return self.get_proxies(proxy_type, proxy_ip, proxy_port, proxy_user, proxy_pass)

    def get_random_proxies(self, proxies_lines):
        if len(proxies_lines) == 0:
            return None

        proxies_line = random.choice(proxies_lines)
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        return proxies