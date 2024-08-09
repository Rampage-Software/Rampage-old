from prompt_toolkit import prompt
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style
from pygments.lexers import JsonLexer
import click

class JsonEditor():
    def __init__(self):
        self.lexer = PygmentsLexer(JsonLexer)

        self.style = Style.from_dict({
            'prompt_toolkit-toolbar': 'bg:#ffffff #333333',
            'prompt_toolkit-primary': 'bg:#ffffff #333333',
            'prompt_toolkit-secondary': 'bg:#ffffff #333333',
            'pygments.comment': '#888888',
            'pygments.keyword': '#007700',
            'pygments.operator': '#333333',
            'pygments.string': '#ee7700',
            'pygments.number': '#009999',
        })

    def edit(self, title:str, initial_content: str) -> str:
        result = prompt(title+"\n", lexer=self.lexer, style=self.style, default=initial_content)

        # clear lines
        lines_config = len(result.split("\n"))+1
        click.echo("\033[1A\033[K" * lines_config)

        return result