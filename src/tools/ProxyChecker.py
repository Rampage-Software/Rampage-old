from Tool import Tool
import os
import concurrent.futures
from utils import Utils
import ipaddress
import httpc
from config import ConfigType

class ProxyChecker(Tool):
    def __init__(self, app):
        super().__init__("Proxy Checker", "Checks proxies from a list of http proxies", app)
        self.cache_file_path = os.path.join(self.cache_directory, "verified-proxies.txt")

    def run(self):
        self.check_timezone = ConfigType.boolean(self.config, "check_timezone")
        self.filter_timezone = ConfigType.string(self.config, "filter_timezone")
        self.ipinfo_api_key = ConfigType.string(self.config, "ipinfo_api_key")
        self.delete_failed_proxies = ConfigType.boolean(self.config, "delete_failed_proxies")
        self.timeout = ConfigType.integer(self.config, "timeout")
        self.max_threads = ConfigType.integer(self.config, "max_threads")

        if not self.timeout:
            raise Exception("Timeout must not be null.")
        if not self.check_timezone and self.filter_timezone:
            raise Exception("Cannot filter timezone without checking timezone.")

        self.check_proxies_file_format(self.proxies_file_path)

        if self.ipinfo_api_key and self.check_timezone:
            self.check_ipinfo_token(self.ipinfo_api_key)

        with open(self.proxies_file_path, 'r') as file:
            lines = list(set(file.read().splitlines()))  # Remove duplicates

        if self.delete_failed_proxies:
            # Clear the cache file if we are deleting failed proxies
            open(self.cache_file_path, 'w').close()

        working_proxies = 0
        failed_proxies = 0
        total_proxies = len(lines)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            future_to_proxy = {executor.submit(self.test_proxy_line, line): line for line in lines}

            for future in concurrent.futures.as_completed(future_to_proxy):
                is_working, proxy_type, proxy_ip, proxy_port, proxy_user, proxy_pass, timezone = future.result()

                proxy_line = self.write_proxy_line(proxy_type, proxy_ip, proxy_port, proxy_user, proxy_pass)
                response_text = proxy_line

                if timezone:
                    response_text += f" {timezone}"

                    if self.filter_timezone and self.filter_timezone.lower() not in timezone.lower():
                        response_text += " Skipped. Timezone not matching filter."
                        is_working = False

                if is_working:
                    working_proxies += 1
                else:
                    failed_proxies += 1

                if self.delete_failed_proxies and is_working:
                    with open(self.cache_file_path, 'a') as cache_file:
                        cache_file.write(proxy_line + "\n")

                self.print_status(working_proxies, failed_proxies, total_proxies, response_text, is_working, "Working")

        if self.delete_failed_proxies:
            with open(self.proxies_file_path, 'w') as destination_file, open(self.cache_file_path, 'r') as source_file:
                destination_file.write(source_file.read())

    def check_ipinfo_token(self, token: str):
        response = httpc.get(f"https://ipinfo.io/8.8.8.8?token={token}")
        if response.status_code != 200:
            raise Exception("Error from IpInfo: " + response.text)

    def test_proxy_line(self, line):
        """
        Checks if a proxy line is working
        """
        line = Utils.clear_line(line)
        proxy_type_provided, proxy_type, proxy_ip, proxy_port, proxy_user, proxy_pass = self.get_proxy_values(line)

        if proxy_type_provided:
            proxies = self.get_proxies(proxy_type, proxy_ip, proxy_port, proxy_user, proxy_pass)
            is_working = self.test_proxy(proxies, self.timeout)
        else:
            for protocol in self.supported_proxy_protocols:
                proxies = self.get_proxies(protocol, proxy_ip, proxy_port, proxy_user, proxy_pass)
                if self.test_proxy(proxies, self.timeout):
                    proxy_type = protocol
                    is_working = True
                    break
            else:
                is_working = False

        timezone = None
        if is_working and self.check_timezone:
            timezone = self.get_timezone(proxy_ip, proxies)

        return is_working, proxy_type, proxy_ip, proxy_port, proxy_user, proxy_pass, timezone

    def get_timezone(self, proxy_ip, proxies):
        api_key_param = f'?token={self.ipinfo_api_key}' if self.ipinfo_api_key else ''
        req_url = f'http://ipinfo.io/{proxy_ip}/json{api_key_param}' if self.ip_address_is_valid(proxy_ip) else f'http://ipinfo.io/json{api_key_param}'
        response = httpc.get(req_url, proxies=proxies if not self.ip_address_is_valid(proxy_ip) else None)
        return response.json().get("timezone")

    def ip_address_is_valid(self, ip_string):
        try:
            ipaddress.ip_address(ip_string)
            return True
        except ValueError:
            return False
