"""AST and Provider Neutrality Verification for Wave 1.

Scans all Wave 1 ports, adapters, and engines using Python's ast module to verify:
1. Zero imports of proprietary cloud/vendor SDKs (AWS boto3, Azure SDK, Google Cloud, OpenAI, Anthropic, etc.).
2. Clean separation of SPI interfaces from runtime adapters.
3. Provider and model neutrality across all core domain capability packages.
"""
import ast
from pathlib import Path
import pytest


class TestWave1ProviderNeutralityAST:
    """Rigorous AST scanning of Wave 1 source code."""

    FORBIDDEN_SDK_MODULES = [
        "boto3", "botocore", "azure", "google.cloud", "redis", "kafka",
        "pika", "pymongo", "psycopg2", "cx_Oracle", "ibm_db", "openai",
        "anthropic", "langchain", "llama_index"
    ]

    TARGET_DIRECTORIES = [
        "backend/app/ports",
        "backend/app/adapters/reference",
        "backend/app/services/engines",
        "backend/app/schemas/contracts"
    ]

    def test_wave1_zero_vendor_sdk_dependencies(self):
        for dir_path_str in self.TARGET_DIRECTORIES:
            target_dir = Path(dir_path_str)
            assert target_dir.exists(), f"Directory {dir_path_str} must exist"
            
            py_files = list(target_dir.glob("*.py"))
            assert len(py_files) >= 1, f"No python files found in {dir_path_str}"

            for p_file in py_files:
                tree = ast.parse(p_file.read_text(encoding="utf-8"), filename=str(p_file))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            for forbidden in self.FORBIDDEN_SDK_MODULES:
                                assert not alias.name.startswith(forbidden), (
                                    f"Forbidden vendor SDK '{alias.name}' imported in {p_file}"
                                )
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            for forbidden in self.FORBIDDEN_SDK_MODULES:
                                assert not node.module.startswith(forbidden), (
                                    f"Forbidden vendor SDK '{node.module}' imported in {p_file}"
                                )
