"""PostgreSQL URL/TLS policy, the bounded connection pool and transaction advisory locks."""

import hashlib
import ipaddress
from urllib.parse import parse_qsl, urlsplit

from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import URL, Connection, Engine, make_url
from sqlalchemy.exc import SQLAlchemyError

APPLICATION_ID = "humanizar-lumen-v1"


def connection_options(value: str) -> tuple[URL, dict[str, str | int]]:
    """Only loopback permits cleartext; remote TLS always verifies CA and hostname."""
    try:
        fields = parse_qsl(
            urlsplit(value).query,
            keep_blank_values=True,
            max_num_fields=2,
            strict_parsing=True,
        )
        query = dict(fields)
        if len(query) != len(fields) or any(
            key not in {"sslmode", "sslrootcert"} or not parameter for key, parameter in fields
        ):
            raise ValueError
        url = make_url(value)
        if url.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}:
            raise ValueError
        if not url.host or not url.database:
            raise ValueError
        if url.port is not None and not 1 <= url.port <= 65535:
            raise ValueError
        if any(not isinstance(item, str) for item in url.query.values()):
            raise ValueError
        if set(url.query) - {"sslmode", "sslrootcert"}:
            raise ValueError
        host = url.host.casefold()
        try:
            loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = host == "localhost"
        requested = query.get("sslmode", "verify-full")
        if not loopback and requested != "verify-full":
            raise ValueError
        if requested not in {"disable", "verify-full"}:
            raise ValueError
        options: dict[str, str | int] = {
            "connect_timeout": 5,
            "sslmode": str(requested),
            "options": (
                "-c statement_timeout=10000 -c lock_timeout=5000 "
                "-c idle_in_transaction_session_timeout=15000"
            ),
        }
        if requested == "verify-full":
            options["sslrootcert"] = query.get("sslrootcert", "system")
        elif "sslrootcert" in query:
            raise ValueError
        return url.set(drivername="postgresql+psycopg", query={}), options
    except (ValueError, TypeError, SQLAlchemyError):
        raise ValueError(
            "DATABASE_URL debe ser PostgreSQL con TLS verify-full fuera de loopback."
        ) from None


def bounded_engine(url: URL, options: dict[str, str | int]) -> Engine:
    return create_engine(
        url,
        connect_args=options,
        pool_size=5,
        max_overflow=2,
        pool_timeout=5,
        pool_recycle=300,
        pool_pre_ping=True,
        echo=False,
        hide_parameters=True,
    )


def advisory_lock(connection: Connection, schema: str, resource: str) -> None:
    """Transaction-scoped lock keyed by application, schema and resource."""
    digest = hashlib.sha256(f"{APPLICATION_ID}:{schema}:{resource}".encode()).digest()
    key = int.from_bytes(digest[:8], "big", signed=True)
    connection.execute(select(func.pg_advisory_xact_lock(key)))
