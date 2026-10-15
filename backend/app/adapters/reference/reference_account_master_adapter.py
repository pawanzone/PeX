"""In-Memory Reference Account Master & Verification of Payee Adapter.

TEST / REFERENCE ONLY.
Implements AccountMasterPort with deterministic lookup and fuzzy/Levenshtein matching.
Zero vendor SDK dependencies.
"""
import difflib
from typing import Dict, List, Any, Optional
from app.ports.account_master_port import AccountMasterPort
from app.schemas.contracts.wave1_schemas import (
    AccountMasterRecord,
    BeneficiaryProfileRecord,
    PayeeVerificationResult,
    PayeeMatchStatus,
)


class InMemoryAccountMasterAdapter(AccountMasterPort):
    """Hermetic reference implementation of AccountMasterPort."""

    def __init__(
        self,
        accounts: Optional[Dict[str, AccountMasterRecord]] = None,
        beneficiaries: Optional[Dict[str, BeneficiaryProfileRecord]] = None
    ):
        self._accounts: Dict[str, AccountMasterRecord] = accounts or {
            "12345678": AccountMasterRecord(
                account_number="12345678",
                account_title="ACME INDUSTRIAL SUPPLIES LTD",
                account_status="ACTIVE",
                currency="GBP",
                bank_id_or_bic="MIDLGB22XXX",
                country="GB",
                entity_legal_name="ACME INDUSTRIAL SUPPLIES LTD",
                postal_address={"street": "10 Commercial Rd", "city": "London", "postal_code": "EC1A 1BB", "country": "GB"},
                tax_identifier="GB123456789"
            ),
            "87654321": AccountMasterRecord(
                account_number="87654321",
                account_title="GLOBAL LOGISTICS GMBH",
                account_status="ACTIVE",
                currency="EUR",
                bank_id_or_bic="DEUTDEDDXXX",
                country="DE",
                entity_legal_name="GLOBAL LOGISTICS GMBH",
                postal_address={"street": "Hauptstrasse 45", "city": "Frankfurt", "postal_code": "60311", "country": "DE"},
                tax_identifier="DE987654321"
            ),
            "99887766": AccountMasterRecord(
                account_number="99887766",
                account_title="PACIFIC RIM TRADING CORP",
                account_status="ACTIVE",
                currency="USD",
                bank_id_or_bic="CHASUS33XXX",
                country="US",
                entity_legal_name="PACIFIC RIM TRADING CORP",
                postal_address={"street": "500 Howard St", "city": "San Francisco", "postal_code": "94105", "country": "US"},
                tax_identifier="US-94-1234567"
            ),
            "11223344": AccountMasterRecord(
                account_number="11223344",
                account_title="SIEMENS AG INDUSTRIAL POWER",
                account_status="ACTIVE",
                currency="EUR",
                bank_id_or_bic="DBEUDEDDXXX",
                country="DE",
                entity_legal_name="SIEMENS AG",
                postal_address={"street": "Werner-von-Siemens-Strasse 1", "city": "Munich", "postal_code": "80333", "country": "DE"},
                tax_identifier="DE112233445"
            ),
            "99887700": AccountMasterRecord(
                account_number="99887700",
                account_title="PACIFIC RIM TRADING CORP",
                account_status="CLOSED",
                currency="USD",
                bank_id_or_bic="CHASUS33XXX",
                country="US",
                entity_legal_name="PACIFIC RIM TRADING CORP",
                postal_address={"street": "500 Howard St", "city": "San Francisco", "postal_code": "94105", "country": "US"},
                tax_identifier="US-94-1234567"
            ),
            "33445566": AccountMasterRecord(
                account_number="33445566",
                account_title="METRO PROPERTIES HOLDING LLC",
                account_status="FROZEN",
                is_frozen=True,
                currency="USD",
                bank_id_or_bic="CHASUS33XXX",
                country="US",
                entity_legal_name="METRO PROPERTIES HOLDING LLC",
                postal_address={"street": "200 Park Ave", "city": "New York", "postal_code": "10166", "country": "US"},
                tax_identifier="US-13-1122334"
            ),
        }

        self._beneficiaries: Dict[str, BeneficiaryProfileRecord] = beneficiaries or {
            "DEBTOR-001:ACME": BeneficiaryProfileRecord(
                debtor_id="DEBTOR-001",
                creditor_id="CRED-ACME-01",
                creditor_name="ACME INDUSTRIAL SUPPLIES LTD",
                creditor_account="12345678",
                creditor_agent_bic="MIDLGB22XXX",
                postal_address={"street": "10 Commercial Rd", "city": "London", "postal_code": "EC1A 1BB", "country": "GB"},
                tax_identifier="GB123456789"
            ),
            "DEBTOR-002:SIEMENS": BeneficiaryProfileRecord(
                debtor_id="DEBTOR-002",
                creditor_id="CRED-SIEMENS-01",
                creditor_name="SIEMENS AG INDUSTRIAL POWER",
                creditor_account="11223344",
                creditor_agent_bic="DBEUDEDDXXX",
                postal_address={"street": "Werner-von-Siemens-Strasse 1", "city": "Munich", "postal_code": "80333", "country": "DE"},
                tax_identifier="DE112233445"
            )
        }

    def get_account_master(self, account_number: str) -> Optional[AccountMasterRecord]:
        return self._accounts.get(account_number.strip())

    def register_account(self, account: AccountMasterRecord) -> None:
        self._accounts[account.account_number.strip()] = account

    def verify_payee(
        self,
        account_number: str,
        payee_name: str,
        account_type: Optional[str] = None
    ) -> PayeeVerificationResult:
        acct = self.get_account_master(account_number)
        if not acct:
            return PayeeVerificationResult(
                account_number=account_number,
                queried_name=payee_name,
                authoritative_name="",
                match_status=PayeeMatchStatus.ACCOUNT_NOT_FOUND,
                match_score=0.0,
                reason=f"Account {account_number} not found in Core DDA."
            )

        auth_name_norm = acct.account_title.strip().upper()
        query_name_norm = payee_name.strip().upper()

        if auth_name_norm == query_name_norm:
            return PayeeVerificationResult(
                account_number=account_number,
                queried_name=payee_name,
                authoritative_name=acct.account_title,
                match_status=PayeeMatchStatus.EXACT_MATCH,
                match_score=1.0,
                matched_entity_id=acct.entity_legal_name,
                reason="Exact string match against Core DDA account title."
            )

        # Calculate similarity score using standard library difflib SequenceMatcher
        ratio = difflib.SequenceMatcher(None, auth_name_norm, query_name_norm).ratio()
        
        # Token-based set matching for word reordering (e.g. "SIEMENS AG" vs "SIEMENS AKTIENGESELLSCHAFT")
        auth_tokens = set(auth_name_norm.split())
        query_tokens = set(query_name_norm.split())
        overlap = len(auth_tokens.intersection(query_tokens)) / max(len(auth_tokens), len(query_tokens))
        composite_score = round(max(ratio, overlap), 4)

        if composite_score >= 0.85:
            status = PayeeMatchStatus.CLOSE_MATCH
            reason = f"Close fuzzy match ({composite_score:.2f}) within policy threshold band."
        else:
            status = PayeeMatchStatus.NO_MATCH
            reason = f"Name mismatch ({composite_score:.2f}) below acceptable threshold."

        return PayeeVerificationResult(
            account_number=account_number,
            queried_name=payee_name,
            authoritative_name=acct.account_title,
            match_status=status,
            match_score=composite_score,
            matched_entity_id=acct.entity_legal_name,
            reason=reason
        )

    def lookup_beneficiary_profile(
        self,
        debtor_id: str,
        creditor_hint: str
    ) -> Optional[BeneficiaryProfileRecord]:
        key = f"{debtor_id}:{creditor_hint.upper()}"
        if key in self._beneficiaries:
            return self._beneficiaries[key]
        for b_key, rec in self._beneficiaries.items():
            if rec.debtor_id == debtor_id and (creditor_hint.upper() in rec.creditor_name.upper() or creditor_hint == rec.creditor_account):
                return rec
        return None
