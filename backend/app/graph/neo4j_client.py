"""
TRINETRA Neo4j Client
=====================

Centralized Neo4j database client.

Responsibilities
----------------
- Create and manage the Neo4j driver
- Verify database connectivity
- Execute Cypher queries
- Execute write transactions
- Execute read queries
- Provide clean shutdown

This module does NOT:
- Build investigation-specific graph structures
- Extract entities
- Detect relationships
- Perform analytics
"""

from __future__ import annotations

from typing import Any, Iterable

from neo4j import (
    Driver,
    GraphDatabase,
    Record,
)


class Neo4jClient:
    """
    Thin wrapper around the official Neo4j Python driver.
    """

    def __init__(
        self,
        uri: str,
        username: str,
        password: str,
        database: str = "neo4j",
    ) -> None:

        if not uri:
            raise ValueError(
                "Neo4j URI is required."
            )

        if not username:
            raise ValueError(
                "Neo4j username is required."
            )

        if not password:
            raise ValueError(
                "Neo4j password is required."
            )

        self.uri = uri
        self.username = username
        self.database = database

        self._driver: Driver = (
            GraphDatabase.driver(
                uri,
                auth=(
                    username,
                    password,
                ),
            )
        )

    # ========================================================
    # CONNECTION
    # ========================================================

    def verify_connection(self) -> bool:
        """
        Verify that Neo4j is reachable.

        Returns:
            True when the connection succeeds.

        Raises:
            Exception when Neo4j cannot be reached.
        """

        self._driver.verify_connectivity()

        return True

    # ========================================================
    # READ
    # ========================================================

    def execute_read(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[Record]:
        """
        Execute a Cypher read query.
        """

        parameters = parameters or {}

        with self._driver.session(
            database=self.database
        ) as session:

            return session.execute_read(
                self._read_transaction,
                query,
                parameters,
            )

    @staticmethod
    def _read_transaction(
        tx,
        query: str,
        parameters: dict[str, Any],
    ) -> list[Record]:
        """
        Transaction callback for read queries.
        """

        result = tx.run(
            query,
            parameters,
        )

        return list(result)

    # ========================================================
    # WRITE
    # ========================================================

    def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[Record]:
        """
        Execute a Cypher write query.
        """

        parameters = parameters or {}

        with self._driver.session(
            database=self.database
        ) as session:

            return session.execute_write(
                self._write_transaction,
                query,
                parameters,
            )

    @staticmethod
    def _write_transaction(
        tx,
        query: str,
        parameters: dict[str, Any],
    ) -> list[Record]:
        """
        Transaction callback for write queries.
        """

        result = tx.run(
            query,
            parameters,
        )

        return list(result)

    # ========================================================
    # GENERIC QUERY
    # ========================================================

    def execute(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[Record]:
        """
        Execute a Cypher query.

        Use this only when the caller does not need to
        distinguish between read and write operations.
        """

        parameters = parameters or {}

        with self._driver.session(
            database=self.database
        ) as session:

            result = session.run(
                query,
                parameters,
            )

            return list(result)

    # ========================================================
    # SINGLE VALUE
    # ========================================================

    def execute_scalar(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> Any:
        """
        Execute a query and return the first field of the
        first record.

        Returns None when no record is returned.
        """

        records = self.execute(
            query,
            parameters,
        )

        if not records:
            return None

        record = records[0]

        if len(record) == 0:
            return None

        return record[0]

    # ========================================================
    # DATABASE CHECK
    # ========================================================

    def ping(self) -> bool:
        """
        Simple database health check.
        """

        try:
            result = self.execute_scalar(
                "RETURN 1 AS health"
            )
            return result == 1
        except Exception:
            return False

    def health_check(self) -> bool:
        """
        Backward-compatible health check used by the API layer.

        Delegates to the client's ping method.
        """
        return self.ping()

    # ========================================================
    # CLOSE
    # ========================================================

    def close(self) -> None:
        """
        Close the Neo4j driver.
        """

        self._driver.close()

    # ========================================================
    # CONTEXT MANAGER
    # ========================================================

    def __enter__(
        self,
    ) -> "Neo4jClient":
        """
        Support:

            with Neo4jClient(...) as client:
                ...
        """

        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        """
        Close driver when leaving context.
        """

        self.close()


# ============================================================
# FACTORY
# ============================================================


def create_neo4j_client(
    uri: str,
    username: str,
    password: str,
    database: str = "neo4j",
) -> Neo4jClient:
    """
    Create a configured Neo4j client.
    """

    return Neo4jClient(
        uri=uri,
        username=username,
        password=password,
        database=database,
    )