import json
import time
import base64
from anticaptchaofficial.funcaptchaproxyless import funcaptchaProxyless
from twocaptcha import TwoCaptcha
import capsolver
from utils import Utils
import httpc
from Proxy import Proxy
from data.public_keys import public_keys
from PowSolver import TimeLockPuzzleSolver

class CaptchaSolver(Proxy):
    def __init__(self, captcha_service:str, api_key:str, debug_mode:bool=False, should_solve_pow:bool = False):
        super().__init__()

        self.captcha_service = captcha_service.lower()
        self.api_key = api_key
        self.debug_mode = debug_mode
        self.should_solve_pow = should_solve_pow

        self.supported_services = ["anti-captcha", "2captcha", "capsolver", "capbypass", "capbuster"]

        if self.captcha_service not in self.supported_services:
            raise Exception(f"Captcha service not supported. Supported: {', '.join(self.supported_services)}")

        if not self.api_key:
            raise Exception(f"API Key for {self.captcha_service} must be set.")

    def solve_captcha(self, response, action_type:str, proxy_line:str, client):
        """
        Resolves a Roblox "Challenge is required..." request using the specified captcha service.
        Returns the captcha bypassed response from the request.
        """
        if response.status_code == 423: # rate limited
            raise Exception(Utils.return_res(response))
        elif response.status_code != 403: # no captcha
            return response

        user_agent = response.request["headers"]["User-Agent"]
        csrf_token = response.request["headers"]["X-Csrf-Token"]
        cookies = response.request.get("cookies")

        try:
            metadata = response.headers["Rblx-Challenge-Metadata"]
            blob, captcha_id, meta_action_type = self.get_captcha_data(metadata)
        except KeyError:
            raise Exception(f"No metadata found. {Utils.return_res(response)}")

        public_key = public_keys[action_type]
        website_url = "https://www.roblox.com"
        website_subdomain = "roblox-api.arkoselabs.com"

        # solve captcha using specified service
        token = self.send_to_solver(website_url, website_subdomain, public_key, blob, user_agent, proxy_line)

        metadata, metadata_base64 = self.build_fc_metadata(captcha_id, token, meta_action_type)

        # challenge_continue
        self.challenge_continue(user_agent, csrf_token, cookies, captcha_id, "captcha", metadata, client)

        # send request again but with captcha token
        req_url, req_headers, req_json, req_data = self.build_captcha_res(response.request, captcha_id, metadata_base64, meta_action_type)

        final_response = client.post(req_url, headers=req_headers, json=req_json, data=req_data)

        return final_response

    def get_captcha_data(self, metadata_base64):
        metadata = json.loads(base64.b64decode(metadata_base64))
        blob = metadata["dataExchangeBlob"]
        unified_captcha_id = metadata["unifiedCaptchaId"]
        action_type = metadata["actionType"]

        return blob, unified_captcha_id, action_type

    def solve_cap(self, domain, website_url, public_key, website_subdomain, blob, proxy):
        captcha_response = httpc.post(f'https://{domain}/api/createTask', json={
            "clientKey": self.api_key,
            "task": {
                "type": "FunCaptchaTask",
                "websiteURL": website_url,
                "websitePublicKey": public_key,
                "websiteSubdomain": website_subdomain,
                "data": "{\"blob\": \""+blob+"\"}",
                "proxy": proxy
            }
        })

        try:
            result = captcha_response.json()

            taskId = result["taskId"]
            errorId = result["errorId"]
        except Exception:
            raise Exception("create task error. " + Utils.return_res(captcha_response))

        if errorId != 0:
            raise Exception(Utils.return_res(captcha_response))

        # polling
        # wait for captcha to be solved
        tries = 50
        solution = None

        while not solution and tries > 0:
            captcha_response = httpc.post(f'https://{domain}/api/getTaskResult', json={
                "clientKey": self.api_key,
                "taskId": taskId
            })

            try:
                result = captcha_response.json()

                solution = result.get("solution")
                errorId = result["errorId"]
            except KeyError:
                raise Exception("get task error. " + Utils.return_res(captcha_response))

            if errorId != 0:
                raise Exception(Utils.return_res(captcha_response))

            tries -= 1
            time.sleep(1)

        try:
            return solution
        except KeyError:
            raise Exception(Utils.return_res(captcha_response))

    def send_to_solver(self, website_url, website_subdomain, public_key, blob, user_agent, proxy_line):
        if self.captcha_service == "anti-captcha":
            solver = funcaptchaProxyless()
            solver.set_verbose(0)
            solver.set_key(self.api_key)
            solver.set_website_url(website_url)
            solver.set_website_key(public_key)
            solver.set_data_blob('{"blob":"' + blob + '"}')
            solver.set_soft_id(0)

            token = solver.solve_and_return_solution()

            if token == 0:
                raise Exception("task finished with error " + solver.error_code)
        elif self.captcha_service == "2captcha":
            solver = TwoCaptcha(self.api_key)

            result = solver.funcaptcha(
                sitekey=public_key,
                url=website_url,
                userAgent=user_agent,
                **{"data[blob]": blob}
            )

            token = result["code"]
        elif self.captcha_service == "capsolver":
            capsolver.api_key = self.api_key
            solution = capsolver.solve({
                "type": "FunCaptchaTask",
                "websitePublicKey": public_key,
                "websiteURL": website_url,
                "data": f"{{\"blob\":\"{blob}\"}}",
                "proxy": proxy_line
            })

            token = solution["token"]
        elif self.captcha_service == "capbypass":
            token = self.solve_cap("capbypass.com", website_url, public_key, website_subdomain, blob, proxy_line)
        elif self.captcha_service == "capbuster":
            token = self.solve_cap("captchabusters.com", website_url, public_key, website_subdomain, blob, proxy_line)
        else:
            raise Exception("Captcha service not found")

        return token

    def build_fc_metadata(self, unified_captcha_id, token, action_type):
        metadata = f"{{\"unifiedCaptchaId\":\"{unified_captcha_id}\",\"captchaToken\":\"{token}\",\"actionType\":\"{action_type}\"}}"
        metadata_base64 = base64.b64encode(metadata.encode()).decode()

        return metadata, metadata_base64

    def build_pow_metadata(self, sessionId, redemptionToken):
        metadata = f"{{\"redemptionToken\":\"{redemptionToken}\",\"sessionId\":\"{sessionId}\"}}"

        return metadata

    def challenge_continue(self, user_agent, csrf_token, cookies, captcha_id, challengeType, metadata, client, should_continue=True):
        req_url = "https://apis.roblox.com/challenge/v1/continue"

        continue_headers = httpc.get_roblox_headers(user_agent, csrf_token)
        req_json = {"challengeId": captcha_id, "challengeMetadata": metadata, "challengeType": challengeType}

        result = client.post(req_url, headers=continue_headers, json=req_json, cookies=cookies)

        response = result.json()

        challengeId = response.get("challengeId")
        challengeType = response.get("challengeType")
        challengeMetadata = response.get("challengeMetadata")

        if challengeType == "proofofwork" and should_continue and self.should_solve_pow:
            if self.debug_mode:
                Utils.s_print("Proof of work detected, attempting solving it. ", fg="yellow")

            self.solve_pow(user_agent, cookies, csrf_token, response, client)

        if challengeType != "" and not should_continue:
            raise Exception("Challenge loop detected. " + Utils.return_res(result))

        if result.status_code != 200 or challengeType != "":
            raise Exception(Utils.return_res(result))

        return {
            "challengeId": challengeId,
            "challengeType": challengeType,
            "challengeMetadata": challengeMetadata
        }

    def solve_pow(self, user_agent, cookies, csrf_token, response, client):
        # we gotta solve PoW :D
        # get params
        challengeId = response.get("challengeId")
        challengeType = response.get("challengeType")
        challengeMetadata = response.get("challengeMetadata")

        if challengeType != "proofofwork":
            raise Exception("Not a PoW challenge")

        # decode json
        challengeMetadata = json.loads(challengeMetadata)

        sessionId = challengeMetadata.get("sessionId")
        requestPath = challengeMetadata.get("requestPath")
        requestMethod = challengeMetadata.get("requestMethod")
        sharedParameters = challengeMetadata.get("sharedParameters")

        # get parameters
        req_url = "https://apis.roblox.com/proof-of-work-service/v1/pow-puzzle"
        req_params = {"sessionID": sessionId}
        req_headers = httpc.get_roblox_headers(user_agent, csrf_token)

        response = client.get(req_url, params=req_params, headers=req_headers, cookies=cookies)

        if response.status_code != 200:
            raise Exception("Failed to get puzzle " + response.text)

        result = response.json()

        artifacts = result["artifacts"]

        # decode json string
        artifacts = json.loads(artifacts)
        artifacts = {
            "N": int(artifacts["N"]),
            "A": int(artifacts["A"]),
            "T": int(artifacts["T"]),
        }

        solver = TimeLockPuzzleSolver(artifacts)
        solution = solver.run()

        req_url = "https://apis.roblox.com/proof-of-work-service/v1/pow-puzzle"
        req_json = {
            "sessionID": sessionId,
            "solution": solution,
        }

        result = client.post(req_url, json=req_json)
        response = result.json()
        answerCorrect = response.get("answerCorrect")
        redemptionToken = response.get("redemptionToken")

        if result.status_code != 200:
            raise Exception("Failed to solve PoW " + Utils.return_res(result))

        if not answerCorrect:
            raise Exception("PoW solution was incorrect " + Utils.return_res(result))

        if self.debug_mode:
            Utils.s_print("PoW solved " +Utils.return_res(result), fg="yellow")

        metadata = self.build_pow_metadata(sessionId, redemptionToken)

        pow_continue = self.challenge_continue(user_agent, csrf_token, cookies, challengeId, "proofofwork", metadata, client, False)

        if self.debug_mode:
            Utils.s_print(f"PoW continue response {str(pow_continue)}", fg="yellow")

    def build_captcha_res(self, init_req, captcha_id, metadata_base64, meta_action_type):
        req_url = init_req["url"]
        req_headers = init_req["headers"]

        req_headers['rblx-challenge-id'] = captcha_id
        req_headers["rblx-challenge-type"] = "captcha"
        req_headers["rblx-challenge-metadata"] = metadata_base64

        req_json = init_req.get("json")
        req_data = init_req.get("data")

        return req_url, req_headers, req_json, req_data

    def get_balance(self):
        """
        Gets the balance of the captcha service
        """
        if self.captcha_service == "anti-captcha":
            solver = funcaptchaProxyless() # or any other class
            solver.set_verbose(0)
            solver.set_key(self.api_key)
            balance = solver.get_balance()
        elif self.captcha_service == "2captcha":
            solver = TwoCaptcha(self.api_key)
            balance = solver.balance()
        elif self.captcha_service == "capsolver":
            capsolver.api_key = self.api_key
            balance = capsolver.balance()["balance"]
        elif self.captcha_service == "capbypass":
            req_url = 'https://capbypass.com/api/getBalance'
            req_data = {
                'clientKey': self.api_key,
            }

            response = httpc.post(req_url, json=req_data)
            try:
                balance = response.json()["credits"]
            except KeyError:
                raise Exception(Utils.return_res(response))
            return balance
        elif self.captcha_service == "capbuster":
            req_url = 'https://captchabusters.com/api/getBalance'
            req_json = {
                "clientKey": self.api_key
            }
            response = httpc.post(req_url, json=req_json)

            try:
                balance = response.json()["balance"]
            except KeyError:
                raise Exception(Utils.return_res(response))
            return balance
        else:
            raise Exception("Captcha service not found")

        return balance

    def __str__(self):
        return "A funcaptcha Solver using " + self.captcha_service + " as the captcha service."