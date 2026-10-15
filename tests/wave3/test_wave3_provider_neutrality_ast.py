"""AST Verification of Zero Third-Party Cloud/Vendor SDK Dependencies in Wave 3 Source Files."""
import ast
import os
import pytest

BANNED_IMPORTS = {
    "boto3",
    "botocore",
    "azure",
    "google.cloud",
    "langchain",
    "openai",
    "anthropic",
    "confluent_kafka",
    "pika",
    "celery",
    "redis",
    "sqlalchemy",
    "psycopg2",
    "pymongo",
}

WAVE3_SOURCE_PATHS = [
    "backend/app/schemas/contracts/wave3_schemas.py",
    "backend/app/ports/treasury_position_port.py",
    "backend/app/ports/nostro_position_port.py",
    "backend/app/ports/fx_pricing_port.py",
    "backend/app/ports/limit_management_port.py",
    "backend/app/ports/credit_risk_port.py",
    "backend/app/ports/liquidity_reserve_port.py",
    "backend/app/adapters/reference/reference_treasury_position_adapter.py",
    "backend/app/adapters/reference/reference_nostro_position_adapter.py",
    "backend/app/adapters/reference/reference_fx_pricing_adapter.py",
    "backend/app/adapters/reference/reference_limit_management_adapter.py",
    "backend/app/adapters/reference/reference_credit_risk_adapter.py",
    "backend/app/adapters/reference/reference_liquidity_reserve_adapter.py",
    "backend/app/services/engines/treasury_exposure_engine.py",
]


class ImportVisitor(ast.NodeVisitor):
    def __init__(self):
        self.imports = []

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.append(node.module)
        self.generic_visit(node)


@pytest.mark.parametrize("file_path", WAVE3_SOURCE_PATHS)
def test_wave3_file_has_zero_banned_imports(file_path):
    if not os.path.exists(file_path):
        pytest.skip(f"File {file_path} not found.")

    with open(file_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=file_path)

    visitor = ImportVisitor()
    visitor.visit(tree)

    for imp in visitor.imports:
        top_pkg = imp.split(".")[0]
        assert top_pkg not in BANNED_IMPORTS, f"Banned vendor SDK import '{imp}' in {file_path}"
