import os
import subprocess
import click
import httpx

# Paths
base_dir = os.path.dirname(__file__)
version_file_path = os.path.join(base_dir, "./src/data/version.py")
exe_file_path = os.path.join(base_dir, "./dist/Privatools.exe")
# Updated path for tls-client-64.dll
tls_dll_path = os.path.join(base_dir, "tls_client/dependencies/tls-client-64.dll")

# URL for version info
req_url = "https://raw.githubusercontent.com/Its3rr0rsWRLD/RAMPAGE/main/version.txt"

# Fetch current version
response = httpx.get(req_url)
click.secho("Current version: " + response.text.strip(), fg='green')

# Automatically set the new version
new_version = response.text.strip().split(".")
new_version[-1] = str(int(new_version[-1]) + 1)
new_version = ".".join(new_version)
click.secho("New version: " + new_version, fg='green')
with open(version_file_path, 'w') as file:
    file.write(f'version = "{new_version}"')

# Build the executable
build_command = f"pyinstaller --onefile --add-data {tls_dll_path};tls_client/dependencies --icon=icon.ico --name=Privatools src/main.py"
try:
    subprocess.check_call(build_command, shell=True)
except subprocess.CalledProcessError as e:
    click.secho(f"Build failed: {e}", fg='red')
    sys.exit(1)

# Obfuscate the build
obfuscate_command = "pyarmor gen --enable-jit --enable-themida --pack dist/Privatools.exe -r src/main.py"
try:
    subprocess.check_call(obfuscate_command, shell=True)
except subprocess.CalledProcessError as e:
    click.secho(f"Obfuscation failed: {e}", fg='red')
    sys.exit(1)

click.secho("Packaging and Obfuscation done.", fg='green')