"""Folio: a web library where people read, upload and share books."""
from dotenv import load_dotenv
from flask import Flask

load_dotenv()  # must run before config reads the environment


def create_app(config_object=None) -> Flask:
    from .cli import register_commands
    from .config import Config
    from .extensions import csrf, db, limiter, login_manager
    from .hooks import register_hooks

    app = Flask(__name__)
    app.config.from_object(config_object or Config)
    if not app.config["SECRET_KEY"]:
        raise RuntimeError(
            "SECRET_KEY is not set. Copy .env.example to .env and generate one with: "
            'python -c "import secrets; print(secrets.token_hex(32))"'
        )

    db.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.session_protection = "strong"

    _register_blueprints(app)
    register_hooks(app)
    register_commands(app)
    return app


def _register_blueprints(app: Flask) -> None:
    from .blueprints import (
        account, assistant, auth, books, library, notifications, reader, speech,
    )

    for module in (auth, library, books, reader, notifications, assistant, speech, account):
        app.register_blueprint(module.bp)
