<h4 align="center">RAMPAGE - Private Multitool | Bot followers, group joins & more </h4>
<p align="center">
	Private Roblox botting tools written in Python.
</p>

<p align="center">
	<a href="#installation">Installation</a> •
	<a href="#file-templates">File templates</a> •
  <a href="https://3rr0r.lol">Website</a> •
	<a href="https://discord.gg/sV359yYZHY">Discord server</a>
</p>
<br/>

## Running from source

First clone this repository:

```bash
git clone
```

Then install the requirements:

```bash
pip install -r requirements.txt
```

Finally, run the program:

```bash
python src/main.py
```

To convert the program to an executable, run:

```bash
pyinstaller --onefile --add-data '.venv/Lib/site-packages/tls_client/dependencies/tls-client-64.dll;tls_client/dependencies' --icon=icon.ico --name=Privatools src/main.py
```

Then to obsfucate the program, run:

```bash
pyarmor gen --enable-jit --enable-themida --pack dist/Privatools.exe -r src/main.py
```

To run unit tests:

```bash
python -m unittest discover src
```

### files/config.json

All attributes are mandatory. Removing them will break the program.

### files/cookies.txt

Add your cookies in this file. You can generate them using our Cookie Generator tool.
Privatools understands both UPC and C format for cookies.

### files/proxies.txt

You can use this template to add your proxies. We currently only support HTTP proxies.
Here are some examples of valid proxies lines:

```
8.8.8.8:5001
http:8.8.8.8:5001
8.8.8.8:5003:username:password
```
