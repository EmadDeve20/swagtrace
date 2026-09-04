from tomllib import load

from swagtrace.schemas.config_schema import Config

_CONFIG: Config | None = None


def load_config(config: str):
    global _CONFIG

    with open(config, "rb") as f:
        _CONFIG = Config(**load(f))


def get_config() -> Config:
    if _CONFIG is None:
        raise RuntimeError("Config has not been loaded.")

    return _CONFIG
