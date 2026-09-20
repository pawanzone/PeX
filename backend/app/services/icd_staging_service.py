"""ICD Staging Service: Interfaces with external banking systems on demand."""
import os
import json
from typing import Dict, Any, Optional, Tuple, List

STAGING_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'icd_staging_store.json')

def load_staging_store() -> Dict[str, Any]:
    if os.path.exists(STAGING_FILE_PATH):
        with open(STAGING_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

class ICDStagingService:
    def __init__(self):
        self._cache = None

    @property
    def store(self) -> Dict[str, Any]:
        if self._cache is None:
            self._cache = load_staging_store()
        return self._cache

    def reload(self):
        self._cache = load_staging_store()

    def query_fedwire_aba(self, aba: str) -> Optional[Dict[str, Any]]:
        fed_dir = self.store.get('federal_reserve_directory', {}).get('fedwire_aba_routing', {})
        return fed_dir.get(aba)

    def query_fedwire_cutoff_status(self) -> Dict[str, Any]:
        return self.store.get('federal_reserve_directory', {}).get('fedwire_cutoffs', {})

    def query_swift_bic(self, bic: str) -> Optional[Dict[str, Any]]:
        bic_dir = self.store.get('swift_reference_master', {}).get('bic_directory', {})
        b8 = bic[:8] if bic else ''
        for k, v in bic_dir.items():
            if k == bic or k == b8:
                return v
        return None

    def query_ssi_counterparty(self, party_name: str) -> Optional[Dict[str, Any]]:
        cp_master = self.store.get('core_banking_ssi', {}).get('counterparty_master', {})
        p_lower = party_name.lower()
        for name, data in cp_master.items():
            if p_lower in name.lower() or name.lower() in p_lower:
                return {'matched_name': name, **data}
        return None

    def query_successor_account(self, old_iban: str) -> Optional[Dict[str, Any]]:
        mappings = self.store.get('core_banking_ssi', {}).get('successor_account_registry', {}).get('CLOSED_ACCOUNT_MAPPING', {})
        return mappings.get(old_iban)

    def query_ofac_watchlist(self, party_name: str) -> Optional[Dict[str, Any]]:
        homonyms = self.store.get('sanctions_and_compliance', {}).get('ofac_sdn_watchlist', {}).get('false_positive_homonyms', {})
        p_lower = party_name.lower()
        for name, data in homonyms.items():
            if p_lower in name.lower() or name.lower() in p_lower:
                return {'matched_name': name, **data}
        return None

    def query_nostro_liquidity(self, currency: str) -> Dict[str, Any]:
        balances = self.store.get('treasury_and_liquidity', {}).get('nostro_corridor_balances', {})
        return balances.get(currency, {'intraday_balance': '$50,000,000.00', 'liquidity_status': 'SURPLUS'})

icd_staging_service = ICDStagingService()
