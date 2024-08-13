
from multiprocessing import freeze_support
import click
from App import App
import json
import signal
import traceback
from os import system, name
import webbrowser
import threading as Threading
from JsonEditor import JsonEditor
import time
import sys

BUY_LICENSE_URL = "https://rampagee.mysellix.io/"
DISCORD_INVITE = "https://discord.gg/bmbbNJ99xQ"

app = App()

global tool
tool = None

def ensure_updates():
    click.echo("Checking for updates...")
    server_version = app.check_auto_update()

    if server_version is None:
        click.secho("Failed to check for updates. Please check your internet connection.", fg='red')
        raise KeyboardInterrupt()
    if server_version == False:
        click.secho("Launching...", fg='green')
    else:
        if app.get_version() != server_version:
            click.secho(f"New version available: {server_version}", fg='yellow')
            click.echo("Updating...")

            try:
                app.update()
            except Exception as e:
                click.secho(str(e), fg='red')
                raise KeyboardInterrupt()
            else:
                click.secho("Update successful. Please restart the program.", fg='green')
                raise KeyboardInterrupt()

def verify_license():
    click.echo("\nChecking license... If it takes too long, please check your internet connection.")

    try:
        return app.verify_license()
    except Exception as e:
        click.secho(str(e), fg='red')
        raise KeyboardInterrupt()

def ask_license():
    clear_terminal()
    click.secho("License not found or invalid. Please buy it here: "+BUY_LICENSE_URL, fg='red')
    click.echo("\n    1 - Buy license key")
    click.echo("    2 - Enter license key")
    click.echo("    3 - Exit")

    while True:
        choice = input(click.style("\n ► Select an option: ", fg=app.color))

        if choice == "1":
            webbrowser.open(BUY_LICENSE_URL)
            click.echo("Browser has been opened. Please buy Privatools")
        elif choice == "2":
            license_key = input(click.style("\n ► Enter your license key: ", fg='blue'))
            app.set_license_key(license_key)
            return
        elif choice == "3":
            raise KeyboardInterrupt()
        else:
            click.secho("Invalid option. Please try again.", fg='red')

def edit_config(config_name, config_getter, config_setter):
    config_data = config_getter()
    config_json = json.dumps(config_data, indent=2)

    json_editor = JsonEditor()
    edited_config = json_editor.edit(f"Editing {config_name} config", config_json)

    try:
        updated_config = json.loads(edited_config)
    except json.JSONDecodeError:
        click.secho("Invalid JSON format. Please try again.", fg='red')
        return

    config_setter(updated_config)
    click.secho(f"Configuration for {config_name} updated.", fg='green')

def config_tool(tool_name):
    tool = app.get_tool_from(tool_name)
    config_getter = lambda: tool.config
    config_setter = lambda config: app.set_tool_config(tool, config)
    edit_config(tool.name, config_getter, config_setter)

def setup_solver_keys():
    config_getter = app.get_solver_config
    config_setter = app.set_solver_config
    edit_config("captcha tokens", config_getter, config_setter)

def edit_global_settings():
    config_getter = app.get_global_settings
    config_setter = app.set_global_settings
    edit_config("global settings", config_getter, config_setter)

def open_files():
    click.secho("Cookies and proxies must be put in their respective files, one per line.", fg='bright_black')
    click.secho("Proxies are in the format: ip:port:username:password", fg='bright_black')

    app.start_files_dir()

def clear_terminal():
    if name == 'nt':
        _ = system('cls')
    else:
        _ = system('clear')

def display_logo():
    logo = f"""

                                                                                    
                                                                                
                                                                                
                                                                                
                                                                                
                                              @@                                
                                          #@@@@                                 
                                    @@@@@@@@#         @                         
                                  @@@@@@             @@                         
                                  @@@@@   @@@@@@@@@@@@                          
                                   @@@@@  ,@@@@@@*                              
                             ,,,,,         ,,,,,@@@                             
                         ,,  ,,    ,,,    ,,,,,,,,,@@%                          
                       ,,,,,   ,,,               ,,,,@@                         
                     ,,,,,,,            ,,,,,,,    .,,,@@@                      
                    ,,,,,,   ,....    .,,,,,,,,,,,,,,,,,,,,@@@                  
                   ,,  .,,  ,,...     .,,,,,,,,,,,,,,,,,,,,, ,,,                
                  .,,  ,,.  ,,....     ..,,,,,,,,,,,,,,,,,,, ,,                 
                  ,,,   ,,   ,,,...      .........    ...,,,.                   
                  ,,,   ,,,   ,,,...               .,     .                     
                   ,,,   ,,,    ,,,,,..         ,,.                             
                   ,,,,    ,,,     ,,,,,,..    .,,                              
                    ,,,,     ,,,,.      ,,,,,,  ,,,                             
                      ,,,,      ,,,,,,      ,,,,, ,,                            
                        ,,,,,       ,,,,,,     .,,,,,,                          
                          ,,,,,,.       ,,,,,     ,,,,,                         
                              ,,,,,,,      ,,,,    ,,,                          
                                    ,,,,     ,,,                                                
                                                                                
                                                                                
                                                                                
      /$$$$$$  /$$$$$$  /$$$$$$/$$$$   /$$$$$$   /$$$$$$   /$$$$$$   /$$$$$$ 
     /$$__  $$|____  $$| $$_  $$_  $$ /$$__  $$ |____  $$ /$$__  $$ /$$__  $$
    | $$  \__/ /$$$$$$$| $$ \ $$ \ $$| $$  \ $$  /$$$$$$$| $$  \ $$| $$$$$$$$
    | $$      /$$__  $$| $$ | $$ | $$| $$  | $$ /$$__  $$| $$  | $$| $$_____/
    | $$     |  $$$$$$$| $$ | $$ | $$| $$$$$$$/|  $$$$$$$|  $$$$$$$|  $$$$$$$
    |__/      \_______/|__/ |__/ |__/| $$____/  \_______/ \____  $$ \_______/
                                     | $$                 /$$  \ $$          
                                     | $$                |  $$$$$$/          
                                     |__/                 \______/           

    Version {app.get_version()} | {DISCORD_INVITE} | Made by RAMPAGE TEAM | Color {app.color}
"""
    click.secho(logo, fg=app.color)

def show_menu():
    tools = app.tools
    tools.sort(key=lambda x: x.name)

    for i, tool in enumerate(tools):
        tool_name_str = click.style(f"   {(' ' if i<9 else '') + str(i+1)} - ", fg=app.color) + tool.name
        space = " " * (26 - len(tool.name))
        tool_desc_str = click.style(tool.description, fg='bright_black')

        click.secho(tool_name_str + space + tool_desc_str)

    click.echo(click.style("\n   a - ", fg='yellow') +"Open files (proxies/cookies/...)")
    click.echo(click.style("   b - ", fg='blue') +"Setup captcha solver keys")
    click.echo(click.style("   c - ", fg='bright_magenta') +"Edit global settings")
    click.echo(click.style("   0 - ", fg='red') +"Exit")

    tool_name = None
    selected = False

    while not selected:
        choice = input(click.style("\n ► Select an option: ", fg=app.color))

        if choice == "a":
            open_files()
        elif choice == "b":
            setup_solver_keys()
        elif choice == "c":
            edit_global_settings()
        elif choice == "0":
            raise KeyboardInterrupt()
        elif choice.isdigit() and int(choice) > 0 and int(choice) <= len(tools):
            tool_name = tools[int(choice) - 1].name
            selected = True
        else:
            click.secho("Invalid option. Please try again.", fg='red')

    click.secho(f" ✓ Selected tool: {tool_name}", fg='green')
    return tool_name

def sigint_handle(signum, frame):
    progress = 0
    click.secho("\n ✖ Stopping tool please wait...", fg=app.color)

    if tool is not None:
        while progress <= 100:
            sys.stdout.write(f"\r█{'█' * (progress // 10)}{'▒' * (10 - progress // 10)} {progress}%")
            sys.stdout.flush()
            time.sleep(0.1)  
            progress += 10
        
        tool.signal_handler()
        raise KeyboardInterrupt()

def reset_signal_handler():
    signal.signal(signal.SIGINT, signal.SIG_IGN)

def launch_tool(tool_name):
    global tool

    signal.signal(signal.SIGINT, sigint_handle)

    try:
        tool = app.get_tool_from(tool_name)
        tool.load_config()
        tool.run()

        reset_signal_handler()
    except (KeyboardInterrupt, EOFError):
        reset_signal_handler()

        click.secho("\n ✖ Tool stopped by user ██████████ 100%", fg='red')
    except Exception as err:
        reset_signal_handler()

        traceback_str = traceback.format_exc()
        click.echo(traceback_str)
        click.secho(str(err), fg='red')

def last_step(tool_name):
    click.secho("\n    1 - Run", fg='green')
    click.secho("    2 - Config tool", fg='yellow')
    click.secho("    3 - Return to menu", fg='cyan')

    wait_option = True
    option = None

    while wait_option:
        option = input(click.style("\n ► Select an option: ", fg=app.color))

        if option == "1":
            wait_option = False
            launch_tool(tool_name)
            input("\nPress Enter to come back to the menu...")
        elif option == "2":
            config_tool(tool_name)
        elif option == "3":
            break
        else:
            click.secho("Invalid option. Please try again.", fg='red')
            wait_option = True

def run_program():
    if app.auto_files_launch:
        app.start_files_dir()

    Threading.Thread(target=app.start_rpc_thread, daemon=True).start()

    while True:
        clear_terminal()
        display_logo()
        last_step(show_menu())

def last_input():
    try:
        input("Press Enter to exit...")
    except (KeyboardInterrupt, EOFError):
        pass

if __name__ == "__main__":
    freeze_support()

    # start a detect reverse engineering thread
    Threading.Thread(target=app.watch_re_in_tasklist, daemon=True).start()

    try:
        ensure_updates()

        time.sleep(5)

        valid_license = False
        while valid_license == False:
            valid_license = verify_license()

            if valid_license:
                break

            ask_license()

        run_program()
    except (KeyboardInterrupt, EOFError):
        click.secho("\n 〜 See you next time :)", fg='blue')
        last_input()
