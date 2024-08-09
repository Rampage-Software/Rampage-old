from Tool import Tool
import click

class UP2UPC(Tool):
    def __init__(self, app):
        super().__init__("UPC to C Converter", "Convert your UPC to only cookies", app)

    def run(self):
        cookies = self.get_cookies(None)

        with open(self.cookies_file_path, 'w') as f:
            f.write("\n".join(cookies))

        click.secho(f"Converted {len(cookies)} UPC to C", fg="green")