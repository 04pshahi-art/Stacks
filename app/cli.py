"""Command-line tasks: `flask --app run init-db` and `flask --app run seed-demo`."""
import re

import click
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url

from .extensions import db

_DATABASE_NAME_RE = re.compile(r"^[A-Za-z0-9_]{1,64}$")


def _create_mysql_database(uri: str) -> None:
    """Create the database (utf8mb4) if it doesn't exist yet. XAMPP doesn't do this for you."""
    url = make_url(uri)
    if url.get_backend_name() != "mysql":
        return
    if not _DATABASE_NAME_RE.match(url.database or ""):
        raise click.ClickException("DATABASE_URL has an invalid database name.")

    # URL.set(database=None) would keep the old database, so build the URL afresh.
    server_url = URL.create(
        url.drivername,
        username=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        query=url.query,
    )
    engine = create_engine(server_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS `{url.database}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )
    engine.dispose()


def register_commands(app) -> None:
    @app.cli.command("init-db")
    def init_db():
        """Create the database and all tables."""
        _create_mysql_database(app.config["SQLALCHEMY_DATABASE_URI"])
        db.create_all()
        click.echo("Database ready.")

    @app.cli.command("seed-demo")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def seed_demo(password):
        """Add a demo publisher ("inkwell") with three sample books."""
        from .seed import create_demo_library

        created = create_demo_library(password)
        click.echo(f"Added {created} sample books. Sign in as inkwell@example.com.")
