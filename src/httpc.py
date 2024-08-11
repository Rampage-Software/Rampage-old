import tls_client
import httpx
import random
from data.user_agents import user_agents

def get_random_user_agent() -> str:
    """
    Generates a random user agent
    """
    return random.choice(user_agents)

def get_roblox_headers(user_agent = None, csrf_token = None, content_type = None):
    """
    Returns a dict of headers for Roblox requests
    """
    req_headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-GB,en;q=0.9,en-US;q=0.8',
    'content-type': 'application/json',
    'origin': 'https://www.roblox.com',
    'priority': 'u=1, i',
    'referer': 'https://www.roblox.com/',
    'sec-ch-ua': '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0',
    }

    if user_agent is not None:
        req_headers["User-Agent"] = user_agent

    if content_type is not None:
        req_headers["Content-Type"] = content_type

    if csrf_token is not None:
        req_headers["X-Csrf-Token"] = csrf_token

    return req_headers

def extract_cookie(response, cookie_name):
    cookie = ''.join(response.headers.get("Set-Cookie")).split(f"{cookie_name}=")[1].split(";")[0]

    return cookie

def format_response(response, method, url, **kwargs):
    # append original request to response
    response.request = kwargs
    response.request["method"] = method
    response.request["url"] = url

    # format headers
    formatted_headers = {}

    for key, value in response.headers.items():
        formatted_key = "-".join(word.capitalize() for word in key.split("-"))
        formatted_headers[formatted_key] = value

    response.headers = formatted_headers

    return response

# Requests without session

def get(url, **kwargs):
    proxies = kwargs.get("proxies")

    with Session(proxies=proxies) as client:
        return client.get(url, **kwargs)

def post(url, **kwargs):
    proxies = kwargs.get("proxies")

    with Session(proxies=proxies) as client:
        return client.post(url, **kwargs)

class Session():
    def __init__(self, **kwargs):
        self.spoof_tls = kwargs.get("spoof_tls")
        self.proxies = kwargs.get("proxies")

        if self.spoof_tls:
            self.session = tls_client.Session(
                client_identifier="chrome112",
                random_tls_extension_order=True,
            )
            self.session.proxies = self.proxies
        else:
            if self.proxies:
                self.proxies = {
                    "all://": self.proxies["http"]
                }
            self.session = httpx.Client(proxies=self.proxies)

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        if not self.spoof_tls:
            self.session.close()

    def get(self, url, **kwargs):
        return self._make_request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self._make_request("POST", url, **kwargs)

    def patch(self, url, **kwargs):
        return self._make_request("PATCH", url, **kwargs)

    def _make_request(self, method, url, **kwargs):
        args = {
            "headers": kwargs.get("headers"),
            "cookies": kwargs.get("cookies"),
            "json": kwargs.get("json"),
            "data": kwargs.get("data"),
            "params": kwargs.get("params"),
            "files": kwargs.get("files")
        }

        # remove all args that are nulls
        args = {k: v for k, v in args.items() if v is not None}

        timeout = kwargs.get("timeout")

        if not self.spoof_tls:
            args["timeout"] = timeout
        else:
            self.session.timeout_seconds = timeout or 10

        if method == "GET":
            response = self.session.get(url, **args)
        elif method == "POST":
            response = self.session.post(url, **args)
        elif method == "PATCH":
            response = self.session.patch(url, **args)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        format_response(response, method, url, **kwargs)

        return response
