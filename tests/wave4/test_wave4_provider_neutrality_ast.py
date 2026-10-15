"""AST Verification of Zero Third-Party Cloud/Vendor SDK Dependencies in Wave 4 Source Files."""
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

WAVE4_SOURCE_PATHS = [
    "backend/app/schemas/contracts/wave4_schemas.py",
    "backend/app/ports/kyc_master_port.py",
    "backend/app/ports/corporate_mandate_port.py",
    "backend/app/ports/transit_tracker_port.py",
    "backend/app/adapters/reference/reference_kyc_master_adapter.py",
    "backend/app/adapters/reference/reference_corporate_mandate_adapter.py",
    "backend/app/adapters/reference/reference_transit_tracker_adapter.py",
    "backend/app/services/engines/wave4_resolution_engine.py",
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


@pytest.mark.parametrize("file_path", WAVE4_SOURCE_PATHS)
def test_wave4_file_has_zero_banned_imports(file_path):
    if not os.path.exists(file_path):
        pytest.skip(f"File {file_path} not found.")

    with open(file_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=file_path)

    visitor = ImportVisitor()
    visitor.visit(tree)

    for imp in visitor.imports:
        top_pkg = imp.split(".")[0]
        assert top_pkg not in BANNED_IMPORTS, f"Banned vendor SDK import '{imp}' in {file_path}"
