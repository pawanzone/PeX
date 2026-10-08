"""Tests for Deterministic Sandboxed ConditionalExpressionEngine."""
import pytest
from app.services.conditional_expression_engine import ConditionalExpressionEngine, SecurityError



def test_empty_or_none_expression():
    assert ConditionalExpressionEngine.evaluate(None, {}) is True
    assert ConditionalExpressionEngine.evaluate("", {}) is True
    assert ConditionalExpressionEngine.evaluate("   ", {"amount": 50}) is True


def test_simple_comparison():
    context = {"amount": 150000, "currency": "USD", "clearing_rail": "FEDWIRE"}
    assert ConditionalExpressionEngine.evaluate("amount > 100000", context) is True
    assert ConditionalExpressionEngine.evaluate("amount <= 100000", context) is False
    assert ConditionalExpressionEngine.evaluate("currency == 'USD'", context) is True
    assert ConditionalExpressionEngine.evaluate("currency != 'EUR'", context) is True


def test_boolean_conjunctions():
    context = {"amount": 250000, "currency": "EUR", "corridor": "EUR_BRL"}
    assert ConditionalExpressionEngine.evaluate("amount > 100000 and currency == 'EUR'", context) is True
    assert ConditionalExpressionEngine.evaluate("amount > 500000 or corridor == 'EUR_BRL'", context) is True
    assert ConditionalExpressionEngine.evaluate("not (amount < 100000)", context) is True


def test_membership_operations():
    context = {"currency": "USD", "clearing_rail": "FEDWIRE"}
    assert ConditionalExpressionEngine.evaluate("currency in ['USD', 'EUR', 'GBP']", context) is True
    assert ConditionalExpressionEngine.evaluate("currency not in ['JPY', 'CHF']", context) is True


def test_missing_context_variable_safe_handling():
    context = {"currency": "USD"}
    # Missing variable evaluates to None, condition evaluates to False
    assert ConditionalExpressionEngine.evaluate("amount > 100000", context) is False


def test_security_sandbox_rejection_of_arbitrary_code():
    # Attempt function execution or import
    with pytest.raises(SecurityError):
        ConditionalExpressionEngine.evaluate("__import__('os').system('ls')", {})

    with pytest.raises(SecurityError):
        ConditionalExpressionEngine.evaluate("eval('1+1')", {})

    with pytest.raises(SecurityError):
        ConditionalExpressionEngine.evaluate("print('hello')", {})


def test_extract_variables():
    vars_found = ConditionalExpressionEngine.extract_variables("amount > 100000 and (currency == 'USD' or corridor == 'US_CA')")
    assert vars_found == {"amount", "currency", "corridor"}
