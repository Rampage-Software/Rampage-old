import random
import string
import concurrent.futures
import httpc
import click
from Tool import Tool
from CaptchaSolver import CaptchaSolver
from utils import Utils
from data.adjectives import adjectives
from data.nouns import nouns

class CookieGenerator(Tool):
    def __init__(self, app):
        super().__init__("Cookie Generator", "Generates Roblox Cookies.", app)

    def run(self):
        click.secho("Warning: Cookies generated using our tool are region locked.", fg='yellow')

        # open cookies.txt for writing in it
        f = open(self.cookies_file_path, 'a')

        worked_gen = 0
        failed_gen = 0
        total_gen = self.config["max_generations"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config["max_workers"]) as self.executor:
            self.results = [self.executor.submit(self.generate_cookie, self.config["vanity"], self.config["custom_password"], self.config["captcha_solver"], self.config["use_proxy"]) for gen in range(self.config["max_generations"])]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    has_generated, response_text = future.result()
                except Exception as e:
                    has_generated, response_text = False, str(e)

                if has_generated:
                    worked_gen += 1
                    f.write(response_text+"\n")
                    f.flush()
                else:
                    failed_gen += 1

                self.print_status(worked_gen, failed_gen, total_gen, response_text, has_generated, "Generated")
        f.close()

    @Utils.handle_exception(2, False)
    def verify_username(self, user_agent:str, csrf_token:str, username:str, birthday: str, client):
        """
        Verifies if a username is valid
        """
        req_url = "https://auth.roblox.com/v1/usernames/validate"
        req_headers = httpc.get_roblox_headers(user_agent, csrf_token)
        req_json={"birthday": birthday, "context": "Signup", "username": username}

        response = client.post(req_url, headers=req_headers, json=req_json)

        if response.status_code != 200:
            raise Exception(Utils.return_res(response))

        try:
            message = response.json()["message"]
        except KeyError:
            message = Utils.return_res(response)

        return "Username is valid" in message, message

    def generate_username(self, vanity):
        """
        Generates a random username
        """
        if vanity is None:
            word1 = random.choice(adjectives)
            word2 = random.choice(nouns)
            word1 = word1.title()
            word2 = word2.title()
            generated_username = f"{word1}{word2}{random.randint(1, 9999)}"
        else:
            characters = string.ascii_uppercase + string.digits
            random_chars = ''.join(random.choice(characters) for _ in range(6))

            generated_username = f"{vanity}_{random_chars}"

        return generated_username

    def generate_password(self):
        """
        Generates a random and complex password
        """
        length = 10
        password = ''.join(random.choices(string.ascii_uppercase + string.digits + string.punctuation, k=length))
        password = password.replace(":", "v")

        return password

    def generate_birthday(self):
        """
        Generates a random birthday
        """
        return str(random.randint(2006, 2010)).zfill(2) + "-" + str(random.randint(1, 12)).zfill(2) + "-" + str(random.randint(1, 27)).zfill(2) + "T05:00:00.000Z"

    @Utils.handle_exception(3, False)
    def send_signup_request(self, user_agent:str, csrf_token:str, username:str, password:str, birthday:str, is_girl:bool, client):
        """
        Sends a signup request to the auth.roblox.com endpoint
        """
        req_url = "https://auth.roblox.com/v2/signup"
        req_headers = httpc.get_roblox_headers(user_agent, csrf_token)
        req_json = {
            "username": username,
            "password": password,
            "birthday": birthday,
            "gender": 1 if is_girl else 2,

            # some values here are hardcoded but it helps to avoid flagging
            "isTosAgreementBoxChecked": True,
            "agreementIds": [
                "3f341564-2a8b-4d10-8b1b-fd6e20d0a88a",
                "c52851e3-faeb-4853-a597-12e374f8aa98"
            ],
            "secureAuthenticationIntent": {
                "clientPublicKey": "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEHk3GEjQ+8PCsdhvnX7w3FzVk7iB2Z4BfAzfzLoNdKrkfZ/VMd5NfSMSZ/KqZKrRDerSGxbaZMojn59mvMrOfWg==",
                "clientEpochTimestamp": 1714165961,
                "serverNonce": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6IlFSSzJIVlFKM0JHMkpNS1kiLCJuYmYiOjE3MTQxNjU5NTksImV4cCI6MTcxNDE2NjI1OSwiaWF0IjoxNzE0MTY1OTU5LCJpc3MiOiJoYmEtc2VydmljZSJ9.IncRfxheutZCJBH9DZjKHeuUljqqFg50ansSfPxzthE",
                "saiSignature":"NKCRkOrVb97PY2eO/f7Y+5Kkx9e1AVLo3/WWdFVSpmvBsDarfH8WgydYi20G6RM+24mhvb89HktMO9DBmIZuYA=="
            }
        }
        result = client.post(req_url, headers=req_headers, json=req_json)

        return result

    @Utils.handle_exception()
    def generate_cookie(self, vanity:str, custom_password:str, captcha_service:str, use_proxy:bool) -> tuple:
        """
        Generates a ROBLOSECURITY cookie
        Returns a tuple with the error and the cookie
        """
        proxies, proxy_line = self.get_random_proxy(line=True) if use_proxy else (None, None)

        with httpc.Session(proxies=proxies, spoof_tls=True) as client:
            captcha_solver = CaptchaSolver(captcha_service, self.captcha_tokens.get(captcha_service))
            user_agent = httpc.get_random_user_agent()
            csrf_token = self.get_csrf_token(None, client)

            birthday = self.generate_birthday()

            retry_count = 0
            while retry_count < 5:
                username = self.generate_username(vanity)
                is_username_valid, response_text = self.verify_username(user_agent, csrf_token, username, birthday, client)

                if is_username_valid:
                    break

                retry_count += 1

            if not is_username_valid:
                raise Exception(f"Failed to generate a valid username after {retry_count} tries. ({response_text})")

            password = custom_password or self.generate_password()
            is_girl = random.choice([True, False])

            sign_up_req = self.send_signup_request(user_agent, csrf_token, username, password, birthday, is_girl, client)
            sign_up_res = captcha_solver.solve_captcha(sign_up_req, "ACTION_TYPE_WEB_SIGNUP", proxy_line, client)

        try:
            cookie = httpc.extract_cookie(sign_up_res, ".ROBLOSECURITY")
        except Exception:
            raise Exception(Utils.return_res(sign_up_res))

        return True, f"{username}:{password}:{cookie}"
