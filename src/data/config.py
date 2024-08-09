config = {
    "License": {
        "key": "your_key_here"
    },
    "GlobalSettings": {
        "//theme_colors": "black, red, green, yellow, blue, magenta, cyan, white, bright_black, bright_red, bright_green, bright_yellow, bright_blue, bright_magenta, bright_cyan, bright_white",
        "color": "red",
        "discord_webhook": None,
        "auto_files_launch": True
    },
    "FunCaptchaSolvers": {
        "//solvers_name": [
            "anti-captcha",
            "2captcha",
            "capsolver",
            "capbypass",
            "capbuster"
        ],
        "anti-captcha_token": "xx",
        "2captcha_token": "xx",
        "capsolver_token": "xx",
        "capbypass": "xx",
        "capbuster_token": "xx"
    },
    "AdsScraper": {
        "ad_format": "random",
        "use_proxy": False,
        "max_threads": None
    },
    "AutoDiscordRPC": {
        "active": True,
        "client_id": "1215805121724813467",
        "state": None,
        "details": "Botting Roblox",
        "small_text": None,
        "small_image": None,
        "large_text": "Privatools",
        "large_image": "privatools"
    },
    "ChatSpammer": {
        "message": "Hello, I'm a bot :D",
        "recipient_id": 1,
        "use_proxy": True,
        "max_threads": None,
    },
    "CommentBot": {
        "//comment": "set message to null to use the comment pool",
        "message": None,
        "asset_id": 0,
        "captcha_solver": "capbypass",
        "use_proxy": True,
        "max_threads": 50
    },
    "CookieChecker": {
        "check_pending": False,
        "check_age": False,
        "check_premium": False,
        "delete_invalid_cookies": False,
        "use_proxy": True,
        "max_threads": None
    },
    "CookieFlagChecker": {
        "use_proxy": True,
        "delete_flagged_cookies": False,
        "max_threads": None
    },
    "CookieGenerator": {
        "vanity": None,
        "custom_password": None,
        "gender": None,
        "unflag": False,
        "captcha_solver": "capbypass",
        "use_proxy": True,
        "max_threads": 50
    },
    "CookieRefresher": {
        "use_proxy": True,
        "max_threads": None
    },
    "CookieRegionUnlocker": {
        "timeout": 30,
        "use_proxy": True,
        "max_threads": None
    },
    "CookieVerifier": {
        "use_proxy": True,
        "max_threads": None
    },
    "DisplayNameChanger": {
        "new_display_names": ["PrivatoolsBEST"],
        "use_proxy": True,
        "max_threads": None
    },
    "EmailChecker": {
        "captcha_solver": "capsolver",
        "use_proxy": True,
        "max_threads": None
    },
    "FavoriteBot": {
        "asset_id": 0,
        "unfavorite": False,
        "use_proxy": True,
        "max_threads": 50,
        "timeout": 0
    },
    "FollowBot": {
        "user_id": 1,
        "timeout": 3,
        "debug_mode": False,
        "solve_pow": False,
        "captcha_solver": "capbypass",
        "use_proxy": True,
        "max_threads": 50
    },
    "FriendRequestBot": {
        "user_id": 1,
        "use_proxy": True,
        "max_threads": None
    },
    "GamepassCreator": {
        "prices": [
            10,
            20,
            50,
            100,
            1000
        ],
        "names": [
            "Donation 10",
            "Donation 20",
            "Donation 50",
            "Donation 100",
            "Donation 1000",
        ],
        "use_one_image": True,
        "use_proxy": False,
        "max_threads": None,
    },
    "GameVisits": {
        "timeout": 10,
        "place_id": 0,
        "max_threads": 5
    },
    "GameVote": {
        "game_id": 0,
        "timeout": 10,
        "dislike": False,
        "use_proxy": True,
        "max_threads": None
    },
    "Gen2018Acc": {
        "use_proxy": False
    },
    "GroupAllyBot": {
        "start_group_id": 9999999,
        "your_group_id": 0,
        "use_proxy": True,
        "max_threads": None
    },
    "GroupClothesStealer": {
        "group_id": 1,
        "remove_trademark": True,
        "use_proxy": False,
        "max_threads": None,
        "timeout": 10
    },
    "GroupJoinBot": {
        "group_id": 0,
        "captcha_solver": "capbypass",
        "use_proxy": True,
        "max_threads": 50
    },
    "GroupScraper": {
        "cookie_claimer": "_|WARNING:",
        "start_group_id": 10000000,
        "end_group_id": 30000000,
        "use_proxy": True,
        "max_threads": None,
    },
    "GroupWallSpammer": {
        "message": "Hello, I'm a bot :D",
        "start_group_id": 10000000,
        "captcha_solver": "capbypass",
        "use_proxy": True,
        "max_threads": None
    },
    "ItemBuyer": {
        "item_id": 0,
        "use_proxy": True,
        "max_threads": None
    },
    "MassClothesDownloader": {
        "remove_trademark": True,
        "//sorts": ["relevance", "favouritedalltime", "favouritedallweek", "favouritedallday", "bestsellingalltime", "bestsellingweek", "bestsellingday", "recentlycreated", "pricehightolow", "pricelowtohigh"],
        "sort": "relevance",
        "keyword": "red",
        "asset_type": "shirt",
        "use_proxy": False,
        "max_threads": None
    },
    "MassClothesUploader": {
        "cookie": "_|WARNING:",
        "robux_price": 5,
        "description": "Made by a goat (me)",
        "group_id": 0,
        "use_proxy": False,
        "max_threads": None,
        "timeout": 45
    },
    "MessageBot": {
        "//comment": "If you want to message a group of users, use MessageUsersScraper tool, then enable use_scraped_users option",
        "use_scraped_users": False,
        "recipient_id": 1,
        "subject": "Hello",
        "body": "Hey there! I'm a bot :D\n\nCan you please follow me?",
        "use_proxy": True,
        "max_threads": None
    },
    "MessageUsersScraper": {
        "group_id": 0,
        "use_proxy": True,
        "max_threads": None
    },
    "ModelFavorite": {
        "model_id": 0,
        "delete_favorite": False,
        "use_proxy": True,
        "max_threads": None,
    },
    "ModelSales": {
        "asset_id": 0,
        "use_proxy": True,
        "max_threads": None
    },
    "ModelVote": {
        "model_id": 0,
        "dislike": False,
        "use_proxy": True,
        "max_threads": None
    },
    "PasswordChanger": {
        "new_password": "1234newpass",
        "use_proxy": True,
        "max_threads": None
    },
    "ProxyChecker": {
        "check_timezone": False,
        "filter_timezone": None,
        "ipinfo_api_key": None,
        "//ipinfo_api_url": "https://ipinfo.io/",
        "delete_failed_proxies": True,
        "timeout": 2,
        "max_threads": None
    },
    "ProxyScraper": {
        "max_sites": None,
        "custom_sites": None,
        "max_threads": None
    },
    "RbxSpaceAutoLister": {
        "rbxspace_authorization": "xx",
        "queue_id": 1,
        "use_proxy": True,
        "max_threads": None
    },
    "RbxTransfer": {
        "main_cookie": "_|WARNING:",
        "use_proxy_for_main_cookie": False,
        "use_proxy": True,
        "max_threads": None
    },
    "ReportBot": {
        "report_type": "user",
        "thing_id": 1,
        "comment": "Roblox scammed me! Please ban him!",
        "use_proxy": True,
        "max_threads": None
    },
    "StatusChanger": {
        "new_status": "Hello I'm a bot :D",
        "use_proxy": True,
        "max_threads": None
    },
    "T-ShirtGenerator": {
        "query": "elon musk",
        "//image_search_api_url": "https://rapidapi.com/emailmatteoutile/api/image-search-api2",
        "image_search_api_key": "xx"
    },
    "UPConverter": {
        "delete_converted_up": True,
        "ignore_captchas": False,
        "captcha_solver": "capbypass",
        "use_proxy": True,
        "max_threads": None
    },
    "UsernameSniper": {
        "username_length": 3,
        "use_proxy": False,
        "max_threads": None,
    },
    "VipServerScraper": {
        "use_proxy": False,
        "max_threads": None
    }
}
