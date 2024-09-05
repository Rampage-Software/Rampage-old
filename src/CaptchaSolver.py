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
    def __init__(self, captcha_service: str, api_key: str, debug_mode: bool = False, should_solve_pow: bool = False):
        super().__init__()
        self.captcha_service = captcha_service.lower()
        self.api_key = api_key
        self.debug_mode = debug_mode
        self.should_solve_pow = should_solve_pow

        self.supported_services = {"anti-captcha", "2captcha", "capsolver", "capbypass", "capbuster"}

        if self.captcha_service not in self.supported_services:
            raise Exception(f"Captcha service not supported. Supported: {', '.join(self.supported_services)}")

        if not self.api_key:
            raise Exception(f"API Key for {self.captcha_service} must be set.")

    def solve_captcha(self, response, action_type: str, proxy_line: str, client, solve_pow: bool = False):
        """
        Resolves a Roblox "Challenge is required..." request using the specified captcha service.
        Returns the captcha bypassed response from the request.
        """
        if response.status_code == 423:  # rate limited
            raise Exception(Utils.return_res(response))
        elif response.status_code != 403:  # no captcha
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

        token = self.send_to_solver(website_url, website_subdomain, public_key, blob, user_agent, proxy_line)

        metadata, metadata_base64 = self.build_fc_metadata(captcha_id, token, meta_action_type)

        # challenge_continue
        self.challenge_continue(user_agent, csrf_token, cookies, captcha_id, "captcha", metadata, client)

        # send request again but with captcha token
        req_url, req_headers, req_json, req_data = self.build_captcha_res(response.request, captcha_id, metadata_base64, meta_action_type)

        return client.post(req_url, headers=req_headers, json=req_json, data=req_data)

    def get_captcha_data(self, metadata_base64):
        metadata = json.loads(base64.b64decode(metadata_base64))
        return metadata["dataExchangeBlob"], metadata["unifiedCaptchaId"], metadata["actionType"]

    def solve_cap(self, domain, website_url, public_key, website_subdomain, blob, proxy):
        captcha_response = httpc.post(f'https://{domain}/api/createTask', json={
            "clientKey": self.api_key,
            "task": {
                "type": "FunCaptchaTask",
                "websiteURL": website_url,
                "websitePublicKey": public_key,
                "websiteSubdomain": website_subdomain,
                "data": f'{{"blob": "{blob}"}}',
                "proxy": proxy
            }
        })

        result = captcha_response.json()
        taskId = result.get("taskId")
        errorId = result.get("errorId")

        if not taskId or errorId != 0:
            raise Exception(Utils.return_res(captcha_response))

        # polling
        for _ in range(50):
            captcha_response = httpc.post(f'https://{domain}/api/getTaskResult', json={
                "clientKey": self.api_key,
                "taskId": taskId
            })

            result = captcha_response.json()
            solution = result.get("solution")
            errorId = result.get("errorId")

            if solution:
                return solution

            if errorId != 0:
                raise Exception(Utils.return_res(captcha_response))

            time.sleep(1)

        raise Exception(Utils.return_res(captcha_response))

    def send_to_solver(self, website_url, website_subdomain, public_key, blob, user_agent, proxy_line):
        if self.captcha_service == "anti-captcha":
            solver = funcaptchaProxyless()
            solver.set_key(self.api_key)
            solver.set_website_url(website_url)
            solver.set_website_key(public_key)
            solver.set_data_blob(f'{{"blob":"{blob}"}}')
            token = solver.solve_and_return_solution()

            if not token:
                raise Exception(f"task finished with error {solver.error_code}")

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
                "data": f'{{"blob":"{blob}"}}',
                "proxy": proxy_line
            })
            token = solution["token"]

        elif self.captcha_service in {"capbypass", "capbuster"}:
            token = self.solve_cap(
                "capbypass.com" if self.captcha_service == "capbypass" else "captchabusters.com",
                website_url, public_key, website_subdomain, blob, proxy_line
            )

        else:
            raise Exception("Captcha service not found")

        return token

    def build_fc_metadata(self, unified_captcha_id, token, action_type):
        metadata = f'{{"unifiedCaptchaId":"{unified_captcha_id}","captchaToken":"{token}","actionType":"{action_type}"}}'
        return metadata, base64.b64encode(metadata.encode()).decode()

    def build_pow_metadata(self, sessionId, redemptionToken):
        return f'{{"redemptionToken":"{redemptionToken}","sessionId":"{sessionId}"}}'

    def challenge_continue(self, user_agent, csrf_token, cookies, captcha_id, challengeType, metadata, client, should_continue=True):
        req_url = "https://apis.roblox.com/challenge/v1/continue"

        continue_headers = httpc.get_roblox_headers(user_agent, csrf_token)
        req_json = {"challengeId": captcha_id, "challengeMetadata": metadata, "challengeType": challengeType}

        result = client.post(req_url, headers=continue_headers, json=req_json, cookies=cookies)
        response = result.json()

        challengeType = response.get("challengeType")
        if challengeType == "proofofwork" and should_continue and self.should_solve_pow:
            if self.debug_mode:
                Utils.s_print("Proof of work detected, attempting solving it.", fg="yellow")

            self.solve_pow(user_agent, cookies, csrf_token, response, client)

        if challengeType and not should_continue:
            raise Exception("Challenge loop detected. " + Utils.return_res(result))

        if result.status_code != 200 or challengeType:
            raise Exception(Utils.return_res(result))

        return {
            "challengeId": response.get("challengeId"),
            "challengeType": challengeType,
            "challengeMetadata": response.get("challengeMetadata")
        }

    def solve_pow(self, user_agent, cookies, csrf_token, response, client):
        challengeId = response.get("challengeId")
        challengeType = response.get("challengeType")
        challengeMetadata = json.loads(response.get("challengeMetadata"))

        if challengeType != "proofofwork":
            raise Exception("Not a PoW challenge")

        sessionId = challengeMetadata.get("sessionId")

        # get puzzle
        req_url = "https://apis.roblox.com/proof-of-work-service/v1/pow-puzzle"
        req_headers = httpc.get_roblox_headers(user_agent, csrf_token)
        response = client.get(req_url, params={"sessionID": sessionId}, headers=req_headers, cookies=cookies)

        if response.status_code != 200:
            raise Exception("Failed to get puzzle " + response.text)

        artifacts = json.loads(response.json()["artifacts"])
        solver = TimeLockPuzzleSolver({
            "N": int(artifacts["N"]),
            "A": int(artifacts["A"]),
            "T": int(artifacts["T"])
        })
        solution = solver.run()

        # submit solution
        result = client.post(req_url, json={"sessionID": sessionId, "solution": solution})
        response = result.json()

        if result.status_code != 200 or not response.get("answerCorrect"):
            raise Exception("PoW solution was incorrect " + Utils.return_res(result))

        if self.debug_mode:
            Utils.s_print("PoW solved " + Utils.return_res(result), fg="yellow")

        pow_continue = self.challenge_continue(
            user_agent, csrf_token, cookies, challengeId, "proofofwork",
            self.build_pow_metadata(sessionId, response.get("redemptionToken")), client, False
        )

        if self.debug_mode:
            Utils.s_print("PoW continue result: " + str(pow_continue), fg="yellow")

    def build_captcha_res(self, req, captcha_id, metadata_base64, action_type):
        req_url = req["url"]
        req_headers = req["headers"]
        req_headers["X-Roblox-Challenge-Id"] = captcha_id
        req_headers["X-Roblox-Challenge-Metadata"] = metadata_base64

        if action_type == "verifyPhone" and req["json"]:
            req_json = req["json"]
            req_json["captchaId"] = captcha_id
            req_json["captchaToken"] = metadata_base64
            return req_url, req_headers, req_json, None

        elif req["data"]:
            req_data = req["data"]
            req_data["captchaId"] = captcha_id
            req_data["captchaToken"] = metadata_base64
            return req_url, req_headers, None, req_data

        return req_url, req_headers, None, None
