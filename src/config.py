import click

class ConfigType:
    @staticmethod
    def validate_type(config, key, expected_type):
        value = config.get(key)

        if type(value) != expected_type and value is not None:
            raise ValueError(f"Invalid config type for key: {key}. Expected {expected_type.__name__}, not {type(value).__name__}")
        return value

    @staticmethod
    def string(config, key):
        return ConfigType.validate_type(config, key, str)

    @staticmethod
    def integer(config, key):
        return ConfigType.validate_type(config, key, int)

    @staticmethod
    def boolean(config, key):
        return ConfigType.validate_type(config, key, bool)

    @staticmethod
    def list(config, key):
        return ConfigType.validate_type(config, key, list)

class Config:
    @staticmethod
    def input_max_generations():
        while True:
            output = input(click.style(" ► Enter max generations: ", fg='yellow'))

            try:
                number = int(output)
            except ValueError:
                click.secho("Invalid input. Please enter a number.", fg='red')
                continue

            if number < 1:
                click.secho("Invalid input. Please enter a number greater than 0.", fg='red')
                continue

            return number