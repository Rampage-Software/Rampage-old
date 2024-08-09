from Tool import Tool
from CaptchaSolver import CaptchaSolver
import click

class SolverBalanceChecker(Tool):
    def __init__(self, app):
        super().__init__("Solver Balance Checker", "Check balance of your solvers", app)

    def run(self):
        solvers = ["capbypass", "capbuster", "capsolver", "anti-captcha", "2captcha"]

        for solver_name in solvers:
            if self.exit_flag is False:
                captcha_solver = CaptchaSolver(solver_name, self.captcha_tokens.get(solver_name))
                try:
                    balance = captcha_solver.get_balance()
                    click.secho(f"{solver_name.title()}: {balance}$", fg="green")
                except Exception as e:
                    click.secho(f"{solver_name.title()}: ERROR {e}", fg="red")