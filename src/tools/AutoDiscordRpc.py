from Tool import Tool
import discordRpc
import time
from time import mktime
import click
from config import ConfigType

class AutoDiscordRpc(Tool):
    def __init__(self, app):
        super().__init__("Auto Discord RPC", "Change your discord status!",app)

    def run(self, is_allowed=False):
        active = ConfigType.boolean(self.config, "active")
        client_id = ConfigType.string(self.config, "client_id")
        state = ConfigType.string(self.config, "state")
        details = ConfigType.string(self.config, "details")
        small_text = ConfigType.string(self.config, "small_text")
        small_image = ConfigType.string(self.config, "small_image")
        large_text = ConfigType.string(self.config, "large_text")
        large_image = ConfigType.string(self.config, "large_image")

        if not is_allowed:
            click.secho("You cannot run this tool. It runs automatically when Privatools is launched.\nRelaunch Privatools to update config", fg="red")
            return

        if not active:
            return

        try:
            rpc_obj = discordRpc.DiscordIpcClient.for_platform(client_id)
        except Exception:
            return

        time.sleep(5)
        start_time = mktime(time.localtime())
        while True:
            activity = {
                    "state": state,
                    "details": details,
                    "timestamps": {
                        "start": start_time
                    },
                    "assets": {
                        "small_text": small_text,
                        "small_image": small_image,
                        "large_text": large_text,
                        "large_image": large_image
                    }
                }

            # idk why
            if not small_image:
                del activity["assets"]["small_image"]
                del activity["assets"]["small_text"]

            if not state:
                del activity["state"]

            rpc_obj.set_activity(activity)
            time.sleep(900)