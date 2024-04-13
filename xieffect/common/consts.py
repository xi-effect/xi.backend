from __future__ import annotations

from os import getenv

# None of these are secret
TEST_EMAIL: str = "test@test.test"
TEST_MOD_NAME: str = "test"

TEST_PASS: str = "q"
BASIC_PASS: str = "0a989ebc4a77b56a6e2bb7b19d995d185ce44090c13e2984b7ecc6d446d4b61ea9991b76a4c2f04b1b4d244841449454"

TEST_INVITE_ID: int = 0

# From environment
DISABLE_WEBHOOKS: bool = getenv("ENABLE_WEBHOOKS", "0") != "1"
PRODUCTION_MODE: bool = getenv("PRODUCTION", "0") == "1"
DATABASE_RESET: bool = getenv("DATABASE_RESET", "0") == "1"

# File limit for the embed tables
FILES_LIMIT: int = 10
