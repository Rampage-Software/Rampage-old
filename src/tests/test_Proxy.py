# pylint: disable = missing-function-docstring
import os
import unittest
from tools.ProxyChecker import ProxyChecker
from App import App

class TestProxy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = App()
        cls.tool = ProxyChecker(cls.app)
        cls.test_file_path = os.path.join(cls.app.cache_directory, "test_file_format")

    def test_check_proxies_file_format(self):
        # make sure file doesn't exist
        try:
            os.remove(self.test_file_path)
        except Exception:
            pass

        with self.assertRaises(FileNotFoundError, msg="Should returns error when file doesn't exist"):
            self.tool.check_proxies_file_format(self.test_file_path)

        # should return true when file is good
        file = open(self.test_file_path, "w")
        file.write("http:10.10.10.10:10:admin:1234\n6.6.6.6:80:user:pass")
        file.close()

        is_good = self.tool.check_proxies_file_format(self.test_file_path)
        self.assertEqual(is_good, True, "Should return true when file is good")

        # should return error when file is empty
        file = open(self.test_file_path, "w")
        file.truncate()
        file.close()

        with self.assertRaises(Exception, msg="Should return error when file is empty"):
            self.tool.check_proxies_file_format(self.test_file_path)

        # should return error for empty line
        file = open(self.test_file_path, "w")
        file.write("\n\n")
        file.close()

        with self.assertRaises(Exception, msg="Should return error for empty line"):
            self.tool.check_proxies_file_format(self.test_file_path)

        # should return error for unsupported proxy type
        file = open(self.test_file_path, "w")
        file.write("css:8.8.8.8:10:admin:1234\n")
        file.close()

        with self.assertRaises(Exception, msg="Should return error for unsupported proxy type"):
            self.tool.check_proxies_file_format(self.test_file_path)

        # should return error for invalid proxy port
        # because port is out of range
        file = open(self.test_file_path, "w")
        file.write("http:8.8.8.8:65537:admin:1234\n")
        file.close()

        with self.assertRaises(Exception, msg="Should return error for invalid proxy port (out of range)"):
            self.tool.check_proxies_file_format(self.test_file_path)

        # because port is not a number
        file = open(self.test_file_path, "w")
        file.write("http:8.8.8.8:lol:admin:1234\n")
        file.close()

        with self.assertRaises(Exception, msg="Should return error for invalid proxy port (not a number)"):
            self.tool.check_proxies_file_format(self.test_file_path)

    def test_get_proxies_values(self):
        line = "102.237.17.4:80"
        proxy_type_provided, proxy_type, proxy_ip, proxy_port, proxy_user, proxy_pass = self.tool.get_proxy_values(line)
        self.assertEqual(proxy_type_provided, False)
        self.assertEqual(proxy_type, "http")
        self.assertEqual(proxy_ip, "102.237.17.4")
        self.assertEqual(proxy_port, 80)
        self.assertEqual(proxy_user, None)
        self.assertEqual(proxy_pass, None)

        line = "http:8.8.8.8:1000"
        proxy_type_provided, proxy_type, proxy_ip, proxy_port, proxy_user, proxy_pass = self.tool.get_proxy_values(line)
        self.assertEqual(proxy_type_provided, True)
        self.assertEqual(proxy_type, "http")
        self.assertEqual(proxy_ip, "8.8.8.8")
        self.assertEqual(proxy_port, 1000)
        self.assertEqual(proxy_user, None)
        self.assertEqual(proxy_pass, None)

        line = "123.456.789.0:1000:admin:1234"
        proxy_type_provided, proxy_type, proxy_ip, proxy_port, proxy_user, proxy_pass = self.tool.get_proxy_values(line)
        self.assertEqual(proxy_type_provided, False)
        self.assertEqual(proxy_type, "http")
        self.assertEqual(proxy_ip, "123.456.789.0")
        self.assertEqual(proxy_port, 1000)
        self.assertEqual(proxy_user, "admin")
        self.assertEqual(proxy_pass, "1234")

        line = "socks5:1.1.1.1:2000:user:pass"
        proxy_type_provided, proxy_type, proxy_ip, proxy_port, proxy_user, proxy_pass = self.tool.get_proxy_values(line)
        self.assertEqual(proxy_type_provided, True)
        self.assertEqual(proxy_type, "socks5")
        self.assertEqual(proxy_ip, "1.1.1.1")
        self.assertEqual(proxy_port, 2000)
        self.assertEqual(proxy_user, "user")
        self.assertEqual(proxy_pass, "pass")

        with self.assertRaises(ValueError):
            line = "socks6"
            proxy_type_provided, proxy_type, proxy_ip, proxy_port, proxy_user, proxy_pass = self.tool.get_proxy_values(line)

    def test_get_proxies(self):
        proxies = self.tool.get_proxies("http", "8.8.8.8", 80, "admin", "1234")
        self.assertEqual(proxies, {
            "http": "http://admin:1234@8.8.8.8:80/",
            "https": "http://admin:1234@8.8.8.8:80/",
        })

        proxies = self.tool.get_proxies("socks4", "8.8.8.8", 80)
        self.assertEqual(proxies, {
            "http": "socks4://8.8.8.8:80/",
            "https": "socks4://8.8.8.8:80/"
        })

        with self.assertRaises(Exception):
            self.tool.get_proxies("http", "8.8.8.8", 80, "username", None)

    def test_test_proxy(self):
        is_working = self.tool.test_proxy({
            "all://": "http://10.8.8.8@admin:1234/"
        }, 1)

        self.assertEqual(is_working, False)

    def test_write_proxy_line(self):
        line = self.tool.write_proxy_line("socks4", "8.8.8.8", 80, "admin", "1234")
        self.assertEqual(line, "socks4:8.8.8.8:80:admin:1234")

        line = self.tool.write_proxy_line("http", "8.8.8.8", 80)
        self.assertEqual(line, "8.8.8.8:80")

        line = self.tool.write_proxy_line(None, "8.8.8.8", 80, "admin", "1234")
        self.assertEqual(line, "8.8.8.8:80:admin:1234")

        line = self.tool.write_proxy_line("socks5", "8.8.8.8", 80, "admin", "1234")
        self.assertEqual(line, "socks5:8.8.8.8:80:admin:1234")

        line = self.tool.write_proxy_line(None, "8.8.8.8", 80)
        self.assertEqual(line, "8.8.8.8:80")

        with self.assertRaises(ValueError, msg="Should raise error when username is provided but password is not"):
            self.tool.write_proxy_line("http", "8.8.8.8", 80, "admin", None)
