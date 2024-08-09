import sys
import os
import functools
import sys
from datetime import datetime, timezone
import difflib
import subprocess
import threading
import time
import humanize
import re
from threading import Lock
import click

s_echo_lock = Lock()

class Utils():
    """
    Utility functions
    """
    @staticmethod
    def ensure_directories_exist(directories):
        """
        Creates directories if they don't exist
        """
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)

    @staticmethod
    def ensure_files_exist(files):
        """
        Creates files if they don't exist
        """
        for file in files:
            if not os.path.exists(file):
                with open(file, 'w'):
                    pass

    @staticmethod
    def clear_line(line: str) -> str:
        """
        Clears a line from spaces, tabs and newlines
        """
        return line.replace("\n", "").replace(" ", "").replace("\t", "")

    @staticmethod
    def return_res(response) -> str:
        """
        Returns a string with the response text and status code
        """
        return response.text + " HTTPStatus: " + str(response.status_code)

    @staticmethod
    def handle_exception(retries = 1, decorate_exception = True):
        """
        Decorator to retry executing a function x times until there's no exception
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                """
                Retry executing function x times until there's no exception
                """
                err = None
                err_line = None
                for _ in range(retries):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        err = str(e)
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        err_line = exc_tb.tb_next.tb_lineno
                else:
                    if decorate_exception:
                        err_msg = f"Error {err} on line {err_line}. Tried running {func.__name__}"

                        if retries == 1:
                            raise Exception(err_msg + " once")
                        else:
                            raise Exception(err_msg + f" {retries} times")
                    else:
                        raise Exception(err)
            return wrapper
        return decorator

    @staticmethod
    def utc_sec():
        """
        Returns the current UTC time in seconds
        """
        utc_time = datetime.utcnow()
        utc_seconds = round((utc_time - datetime(1970, 1, 1)).total_seconds())
        return utc_seconds

    @staticmethod
    def get_closest_match(str, str_list):
        """
        Returns the closest match from a list of string
        """
        closest_match = difflib.get_close_matches(str, str_list, n=1)

        # if there's a match, return it
        if len(closest_match) > 0:
            return closest_match[0]
        else:
            return None

    @staticmethod
    def get_hwid():
        cmd = 'wmic csproduct get uuid'
        uuid = str(subprocess.check_output(cmd))
        pos1 = uuid.find("\\n")+2
        uuid = uuid[pos1:-15]

        return uuid

    @staticmethod
    def get_time_elapsed(date_string):
        """
        Returns the time elapsed since a date
        Format: 2023-09-10T04:47:57.407Z
        """
        date_string = date_string[:19]
        date_object = datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
        current_time = datetime.now(timezone.utc)
        time_difference = current_time - date_object

        return humanize.naturaltime(time_difference)

    @staticmethod
    def extract_cookie(text):
        """
        Extracts cookie from text
        """
        pattern = re.compile(r'_\|WARNING:-DO-NOT-SHARE-THIS\.-.*')
        cookies = [match.group(0) for match in pattern.finditer(text)]
        return cookies[0]

    @staticmethod
    def s_print(*a, **b):
        """
        Thread safe print function
        """
        with s_echo_lock:
            click.secho(*a, **b)

    @staticmethod
    def escape_ansi(line):
        ansi_escape =re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
        return ansi_escape.sub('', line)

class Infinite:
    def __init__(self, thread_function, max_threads=30):
        self.thread_function = thread_function
        self.max_threads = max_threads if max_threads else 30

        self.exit_event = threading.Event()

    def shutdown(self, **kwargs):
        self.exit_event.set()

    def while_function(self):
        while not self.exit_event.is_set():
            self.thread_function()

    def start(self):
        threads = []
        for _ in range(self.max_threads):
            thread = threading.Thread(target=self.while_function)
            thread.start()
            threads.append(thread)

        try:
            while not self.exit_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            for thread in threads:
                thread.join()
            print("All threads stopped.")