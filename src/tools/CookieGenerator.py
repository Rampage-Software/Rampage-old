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
from config import ConfigType, Config
from BoundAuthToken import BATGenerator

class CookieGenerator(Tool):
    def __init__(self, app):
        super().__init__("Cookie Generator", "Generates Roblox Cookies.", app)

    def run(self):
        self.vanity = ConfigType.string(self.config, "vanity")
        self.is_vanity_random = ConfigType.boolean(self.config, "is_vanity_random")
        self.custom_password = ConfigType.string(self.config, "custom_password")
        self.gender = ConfigType.string(self.config, "gender")
        self.unflag = ConfigType.boolean(self.config, "unflag")
        self.captcha_solver = ConfigType.string(self.config, "captcha_solver")
        self.use_proxy = ConfigType.boolean(self.config, "use_proxy")
        self.max_threads = ConfigType.integer(self.config, "max_threads")
        self.max_generations = Config.input_max_generations()
        self.use_pow = ConfigType.boolean(self.config, "use_pow")

        if not self.max_generations or not self.captcha_solver:
            raise Exception("max_generations and captcha_solver must not be null.")

        if self.gender not in ["male", "female", None]:
            raise Exception("Gender must be either \"male\" \"female\" or null")

        proxies_lines = self.get_proxies_lines() if self.use_proxy else [None]

        click.secho("Warning: Cookies generated using our tool are region locked.", fg='yellow')

        # open cookies.txt for writing in it
        f = open(self.cookies_file_path, 'a')

        worked_gen = 0
        failed_gen = 0
        total_gen = self.max_generations

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as self.executor:
            self.results = [self.executor.submit(self.generate_cookie, random.choice(proxies_lines)) for gen in range(self.max_generations)]

            for future in concurrent.futures.as_completed(self.results):
                try:
                    has_generated, upc = future.result()
                except Exception as e:
                    has_generated, response_text = False, str(e)

                if has_generated:
                    worked_gen += 1
                    f.write(upc+"\n")
                    f.flush()

                    up_split = upc.split(":")
                    response_text = f"Account {up_split[0]} generated successfully."
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
        last_vanity = 0

        response = client.post(req_url, headers=req_headers, json=req_json)

        if response.status_code != 200:
            raise Exception(Utils.return_res(response))

        try:
            message = response.json()["message"]
        except KeyError:
            message = Utils.return_res(response)

        return "Username is valid" in message, message

    def generate_username(self):
        """
        Generates a random username
        """
        if self.vanity is None:
            word1 = random.choice(adjectives)
            word2 = random.choice(nouns)
            word1 = word1.title()
            word2 = word2.title()
            generated_username = f"{word1}{word2}{random.randint(1, 9999)}"
        elif not self.is_vanity_random:
            # if not self.is_vanity_random, we will try to generate a username until we find a valid one
            generated_username = self.vanity
            last_vanity = 0
            while True:
                if last_vanity == 0:
                    last_vanity = 1
                else:
                    last_vanity += 1
                    generated_username = f"{self.vanity}{last_vanity}"

                if self.verify_username(httpc.get_random_user_agent(), self.get_csrf_token(None, None), generated_username, self.generate_birthday(), httpc.Session())[0]:
                    break
        else:
            characters = string.ascii_uppercase + string.digits
            random_chars = ''.join(random.choice(characters) for _ in range(6))

            generated_username = f"{self.vanity}_{random_chars}"

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
        req_headers["X-Retry-Attempt"] = "1"
        req_cookies = self.get_session_cookies(None, user_agent, client) if self.unflag else None

        req_json={
            "username": username,
            "password": password,
            "birthday": birthday,
            "gender": 1 if is_girl else 2,
            "isTosAgreementBoxChecked": True,
            "agreementIds": ["3f341564-2a8b-4d10-8b1b-fd6e20d0a88a", "c52851e3-faeb-4853-a597-12e374f8aa98"],
        }

        if self.unflag:
            bat_gen = BATGenerator()
            authIntent = bat_gen.generate_secure_auth_intent(user_agent, csrf_token, client)
            req_json["securityAuthIntent"] = authIntent

        response = client.post(req_url, headers=req_headers, json=req_json, cookies=req_cookies)

        return response

    @Utils.handle_exception()
    def generate_cookie(self, proxies_line):
        """
        Generates a ROBLOSECURITY cookie
        Returns a tuple with the error and the cookie
        """
        proxies = self.convert_line_to_proxy(proxies_line) if proxies_line else None

        with httpc.Session(proxies=proxies, spoof_tls=True) as client:
            captcha_solver = CaptchaSolver(self.captcha_solver, self.captcha_tokens.get(self.captcha_solver))
            user_agent = httpc.get_random_user_agent()
            csrf_token = self.get_csrf_token(None, client)

            birthday = self.generate_birthday()

            retry_count = 0
            while retry_count < 5:
                username = self.generate_username()
                is_username_valid, response_text = self.verify_username(user_agent, csrf_token, username, birthday, client)

                if is_username_valid:
                    break

                retry_count += 1

            if not is_username_valid:
                raise Exception(f"Failed to generate a valid username after {retry_count} tries. ({response_text})")

            password = self.custom_password or self.generate_password()

            if self.gender == 'female':
                is_girl = True
            elif self.gender == 'male':
                is_girl = False
            else:
                is_girl = random.choice([True, False])

            sign_up_req = self.send_signup_request(user_agent, csrf_token, username, password, birthday, is_girl, client)
            sign_up_res = captcha_solver.solve_captcha(sign_up_req, "ACTION_TYPE_WEB_SIGNUP", proxies_line, client, self.use_pow)

            try:
                cookie = httpc.extract_cookie(sign_up_res, ".ROBLOSECURITY")
            except Exception:
                raise Exception(Utils.return_res(sign_up_res))

        return True, f"{username}:{password}:{cookie}"
