"""In-Memory Reference Configuration Adapter.

TEST / DEMO / REFERENCE ONLY.
Implements ConfigurationSchemaPort for system parameters and dynamic Bank Evidence Required configurations.
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone

from app.ports.configuration_port import ConfigurationSchemaPort
from app.schemas.contracts.configuration_schemas import (
    ValidatedSystemConfig,
    RailCutoffSchedule,
)
from app.schemas.contracts.evidence_config_schemas import (
    BankEvidenceRequiredConfig,
    EvidenceRuleDefinition,
    EvidenceAcquisitionMode,
    HitlWorkflowConfig,
    HitlFieldDefinition,
    HitlFieldType,
)
from app.schemas.contracts.evidence_schemas import TrustTier


class InMemoryConfigurationAdapter(ConfigurationSchemaPort):
    """Hermetic reference implementation of ConfigurationSchemaPort."""

    def __init__(
        self,
        config: Optional[ValidatedSystemConfig] = None,
        evidence_configs: Optional[List[BankEvidenceRequiredConfig]] = None
    ):
        self._config = config or ValidatedSystemConfig(
            environment="TEST_ONLY",
            service_name="pex_resolution_platform",
            version="0.2.0",
            rail_schedules=[
                RailCutoffSchedule(rail_code="FEDWIRE", currency="USD", operating_start_utc="00:00", cutoff_utc="22:00"),
                RailCutoffSchedule(rail_code="CHAPS", currency="GBP", operating_start_utc="06:00", cutoff_utc="17:00"),
                RailCutoffSchedule(rail_code="TARGET2", currency="EUR", operating_start_utc="07:00", cutoff_utc="18:00"),
                RailCutoffSchedule(rail_code="SWIFT_CBPR+", currency="USD", operating_start_utc="00:00", cutoff_utc="23:59")
            ],
            default_currency="USD",
            max_idempotency_lease_seconds=300,
            token_vault_key_id="REFERENCE_DEV_KEY_01",
            audit_chain_initial_seed="PEX_GENESIS_SEED_20261008",
            is_valid=True,
            validated_at=datetime.now(timezone.utc)
        )
        self._evidence_configs: Dict[Tuple[str, str], BankEvidenceRequiredConfig] = {}
        self._initialize_default_evidence_configs()

        if evidence_configs:
            for ec in evidence_configs:
                self.publish_evidence_config(ec)

    def _initialize_default_evidence_configs(self) -> None:
        """Populates canonical standard published configurations for DEFAULT_BANK."""
        defaults = [
            # DQ-01: Invalid IBAN
            BankEvidenceRequiredConfig(
                tenant_id="DEFAULT_BANK",
                profile_id="DQ-01",
                config_version="1.0.0",
                rules=[
                    EvidenceRuleDefinition(
                        rule_id="R-DQ01-01",
                        evidence_type="CORE_DDA_ACCOUNT",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_1_CORE_RECORD,
                        condition_expression=None,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR, EvidenceAcquisitionMode.MODE_3_BANK_PUSH]
                    ),
                    EvidenceRuleDefinition(
                        rule_id="R-DQ01-02",
                        evidence_type="ROUTING_DIRECTORY",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_2_REGULATORY_SCHEME,
                        condition_expression=None,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR]
                    )
                ],
                hitl_config=HitlWorkflowConfig(
                    enabled=True,
                    target_role="PAYMENT_OPERATOR",
                    fields=[
                        HitlFieldDefinition(field_id="verified_iban", label="Verified Creditor IBAN", field_type=HitlFieldType.IBAN, required=True),
                        HitlFieldDefinition(field_id="repair_notes", label="Operator Notes", field_type=HitlFieldType.TEXT, required=False)
                    ]
                )
            ),
            # DQ-08: Routing Code Discrepancy
            BankEvidenceRequiredConfig(
                tenant_id="DEFAULT_BANK",
                profile_id="DQ-08",
                config_version="1.0.0",
                rules=[
                    EvidenceRuleDefinition(
                        rule_id="R-DQ08-01",
                        evidence_type="FEDLINE_ROUTING_DIRECTORY",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_2_REGULATORY_SCHEME,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR]
                    ),
                    EvidenceRuleDefinition(
                        rule_id="R-DQ08-02",
                        evidence_type="ROUTING_SYNTAX_MASTER",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_2_REGULATORY_SCHEME,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR]
                    )
                ]
            ),
            # PR-01: Duplicate Payment
            BankEvidenceRequiredConfig(
                tenant_id="DEFAULT_BANK",
                profile_id="PR-01",
                config_version="1.0.0",
                rules=[
                    EvidenceRuleDefinition(
                        rule_id="R-PR01-01",
                        evidence_type="HISTORICAL_PAYMENT_JOURNAL",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_1_CORE_RECORD,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR]
                    ),
                    EvidenceRuleDefinition(
                        rule_id="R-PR01-02",
                        evidence_type="SETTLEMENT_LEDGER",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_1_CORE_RECORD,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR]
                    )
                ]
            ),
            # PR-08: Queue Processing Failure
            BankEvidenceRequiredConfig(
                tenant_id="DEFAULT_BANK",
                profile_id="PR-08",
                config_version="1.0.0",
                rules=[
                    EvidenceRuleDefinition(
                        rule_id="R-PR08-01",
                        evidence_type="STREAMING_BROKER_JOURNAL",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_1_CORE_RECORD,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_3_BANK_PUSH]
                    ),
                    EvidenceRuleDefinition(
                        rule_id="R-PR08-02",
                        evidence_type="DLQ_RECORD",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_1_CORE_RECORD,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_3_BANK_PUSH]
                    )
                ]
            ),
            # ST-01: Returned Payment
            BankEvidenceRequiredConfig(
                tenant_id="DEFAULT_BANK",
                profile_id="ST-01",
                config_version="1.0.0",
                rules=[
                    EvidenceRuleDefinition(
                        rule_id="R-ST01-01",
                        evidence_type="INWARD_PACS004_RETURN",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_1_CORE_RECORD,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_3_BANK_PUSH]
                    ),
                    EvidenceRuleDefinition(
                        rule_id="R-ST01-02",
                        evidence_type="ORIGINAL_DEBIT_RECORD",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_1_CORE_RECORD,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR]
                    )
                ]
            ),
            # CO-04: Restricted Corridor / Sanctions
            BankEvidenceRequiredConfig(
                tenant_id="DEFAULT_BANK",
                profile_id="CO-04",
                config_version="1.0.0",
                rules=[
                    EvidenceRuleDefinition(
                        rule_id="R-CO04-01",
                        evidence_type="SANCTIONS_WATCHLIST",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_2_REGULATORY_SCHEME,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR]
                    ),
                    EvidenceRuleDefinition(
                        rule_id="R-CO04-02",
                        evidence_type="CORRIDOR_POLICY_MATRIX",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_2_REGULATORY_SCHEME,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD]
                    )
                ]
            ),
            # === WAVE 1 PROFILES (9 PROFILES) ===
            # DQ-03: Missing Beneficiary Data
            BankEvidenceRequiredConfig(
                tenant_id="DEFAULT_BANK",
                profile_id="DQ-03",
                config_version="1.0.0",
                rules=[
                    EvidenceRuleDefinition(
                        rule_id="R-DQ03-01",
                        evidence_type="CLIENT_MASTER_RECORD",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_1_CORE_RECORD,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR, EvidenceAcquisitionMode.MODE_3_BANK_PUSH, EvidenceAcquisitionMode.MODE_4_HITL_OPERATOR]
                    ),
                    EvidenceRuleDefinition(
                        rule_id="R-DQ03-02",
                        evidence_type="ACCOUNT_STATEMENT",
                        mandatory=False,
                        min_trust_tier=TrustTier.TIER_1_CORE_RECORD,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_3_BANK_PUSH, EvidenceAcquisitionMode.MODE_4_HITL_OPERATOR]
                    )
                ],
                hitl_config=HitlWorkflowConfig(
                    enabled=True,
                    target_role="PAYMENT_OPERATOR",
                    fields=[
                        HitlFieldDefinition(field_id="verified_creditor_name", label="Verified Creditor Legal Name", field_type=HitlFieldType.TEXT, required=True),
                        HitlFieldDefinition(field_id="verified_postal_address", label="Verified Postal Address", field_type=HitlFieldType.TEXT, required=False)
                    ]
                )
            ),
            # DQ-04: Missing Remittance Info
            BankEvidenceRequiredConfig(
                tenant_id="DEFAULT_BANK",
                profile_id="DQ-04",
                config_version="1.0.0",
                rules=[
                    EvidenceRuleDefinition(
                        rule_id="R-DQ04-01",
                        evidence_type="INVOICE_BILLING_RECORD",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_1_CORE_RECORD,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR, EvidenceAcquisitionMode.MODE_3_BANK_PUSH, EvidenceAcquisitionMode.MODE_4_HITL_OPERATOR]
                    ),
                    EvidenceRuleDefinition(
                        rule_id="R-DQ04-02",
                        evidence_type="PURCHASE_ORDER_DOC",
                        mandatory=False,
                        min_trust_tier=TrustTier.TIER_2_REGULATORY_SCHEME,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_3_BANK_PUSH]
                    )
                ],
                hitl_config=HitlWorkflowConfig(
                    enabled=True,
                    target_role="PAYMENT_OPERATOR",
                    fields=[
                        HitlFieldDefinition(field_id="invoice_reference_number", label="Invoice Reference Number", field_type=HitlFieldType.TEXT, required=True)
                    ]
                )
            ),
            # DQ-07: Invalid Account Number
            BankEvidenceRequiredConfig(
                tenant_id="DEFAULT_BANK",
                profile_id="DQ-07",
                config_version="1.0.0",
                rules=[
                    EvidenceRuleDefinition(
                        rule_id="R-DQ07-01",
                        evidence_type="CORE_DDA_MASTER",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_1_CORE_RECORD,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR, EvidenceAcquisitionMode.MODE_3_BANK_PUSH, EvidenceAcquisitionMode.MODE_4_HITL_OPERATOR]
                    ),
                    EvidenceRuleDefinition(
                        rule_id="R-DQ07-02",
                        evidence_type="ACCOUNT_STRUCTURE_RULES",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_2_REGULATORY_SCHEME,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR]
                    )
                ],
                hitl_config=HitlWorkflowConfig(
                    enabled=True,
                    target_role="PAYMENT_OPERATOR",
                    fields=[
                        HitlFieldDefinition(field_id="verified_account_number", label="Verified Account Number", field_type=HitlFieldType.TEXT, required=True)
                    ]
                )
            ),
            # DQ-09: Beneficiary Name Mismatch (Confirmation of Payee)
            BankEvidenceRequiredConfig(
                tenant_id="DEFAULT_BANK",
                profile_id="DQ-09",
                config_version="1.0.0",
                rules=[
                    EvidenceRuleDefinition(
                        rule_id="R-DQ09-01",
                        evidence_type="CORE_ACCOUNT_TITLE",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_1_CORE_RECORD,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR, EvidenceAcquisitionMode.MODE_3_BANK_PUSH]
                    ),
                    EvidenceRuleDefinition(
                        rule_id="R-DQ09-02",
                        evidence_type="VERIFICATION_OF_PAYEE_CONFIRMATION",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_2_REGULATORY_SCHEME,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR]
                    )
                ],
                hitl_config=HitlWorkflowConfig(
                    enabled=True,
                    target_role="PAYMENT_OPERATOR",
                    fields=[
                        HitlFieldDefinition(field_id="confirmed_payee_name", label="Confirmed Payee Legal Name", field_type=HitlFieldType.TEXT, required=True)
                    ]
                )
            ),
            # PR-02: Routing Failure
            BankEvidenceRequiredConfig(
                tenant_id="DEFAULT_BANK",
                profile_id="PR-02",
                config_version="1.0.0",
                rules=[
                    EvidenceRuleDefinition(
                        rule_id="R-PR02-01",
                        evidence_type="ROUTING_DIRECTORY_AUTHORITY",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_2_REGULATORY_SCHEME,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR]
                    ),
                    EvidenceRuleDefinition(
                        rule_id="R-PR02-02",
                        evidence_type="BANK_DESIGNATED_SSI",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_1_CORE_RECORD,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR, EvidenceAcquisitionMode.MODE_3_BANK_PUSH]
                    )
                ]
            ),
            # PR-04: Cutoff Missed
            BankEvidenceRequiredConfig(
                tenant_id="DEFAULT_BANK",
                profile_id="PR-04",
                config_version="1.0.0",
                rules=[
                    EvidenceRuleDefinition(
                        rule_id="R-PR04-01",
                        evidence_type="RAIL_OPERATING_CALENDAR",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_2_REGULATORY_SCHEME,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR]
                    ),
                    EvidenceRuleDefinition(
                        rule_id="R-PR04-02",
                        evidence_type="RAIL_CUTOFF_SCHEDULE",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_2_REGULATORY_SCHEME,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR]
                    ),
                    EvidenceRuleDefinition(
                        rule_id="R-PR04-03",
                        evidence_type="BANK_CUTOFF_POLICY",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_2_REGULATORY_SCHEME,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR]
                    )
                ]
            ),
            # PR-07: Network Timeout
            BankEvidenceRequiredConfig(
                tenant_id="DEFAULT_BANK",
                profile_id="PR-07",
                config_version="1.0.0",
                rules=[
                    EvidenceRuleDefinition(
                        rule_id="R-PR07-01",
                        evidence_type="GATEWAY_SOCKET_STATE",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_1_CORE_RECORD,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR, EvidenceAcquisitionMode.MODE_3_BANK_PUSH]
                    ),
                    EvidenceRuleDefinition(
                        rule_id="R-PR07-02",
                        evidence_type="IDEMPOTENCY_LEDGER_LOCK",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_1_CORE_RECORD,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR]
                    ),
                    EvidenceRuleDefinition(
                        rule_id="R-PR07-03",
                        evidence_type="RETRY_BUDGET_RECORD",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_2_REGULATORY_SCHEME,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR]
                    )
                ]
            ),
            # PR-09: Payment Held for Repair
            BankEvidenceRequiredConfig(
                tenant_id="DEFAULT_BANK",
                profile_id="PR-09",
                config_version="1.0.0",
                rules=[
                    EvidenceRuleDefinition(
                        rule_id="R-PR09-01",
                        evidence_type="PAYMENT_HUB_REPAIR_QUEUE",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_1_CORE_RECORD,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR, EvidenceAcquisitionMode.MODE_3_BANK_PUSH]
                    ),
                    EvidenceRuleDefinition(
                        rule_id="R-PR09-02",
                        evidence_type="SYNTAX_ERROR_SPECIFICATION",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_2_REGULATORY_SCHEME,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR]
                    )
                ]
            ),
            # CO-07: Regulatory Reporting Required
            BankEvidenceRequiredConfig(
                tenant_id="DEFAULT_BANK",
                profile_id="CO-07",
                config_version="1.0.0",
                rules=[
                    EvidenceRuleDefinition(
                        rule_id="R-CO07-01",
                        evidence_type="REGULATORY_PURPOSE_DIRECTORY",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_2_REGULATORY_SCHEME,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR]
                    ),
                    EvidenceRuleDefinition(
                        rule_id="R-CO07-02",
                        evidence_type="CENTRAL_BANK_BOP_CODES",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_2_REGULATORY_SCHEME,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR]
                    ),
                    EvidenceRuleDefinition(
                        rule_id="R-CO07-03",
                        evidence_type="STATUTORY_REPORTING_RULE",
                        mandatory=True,
                        min_trust_tier=TrustTier.TIER_2_REGULATORY_SCHEME,
                        acquisition_modes=[EvidenceAcquisitionMode.MODE_1_INBOUND_PAYLOAD, EvidenceAcquisitionMode.MODE_2_API_CONNECTOR]
                    )
                ]
            )
        ]
        for cfg in defaults:
            key = (cfg.tenant_id.upper(), cfg.profile_id.upper())
            self._evidence_configs[key] = cfg

    def load_configuration(
        self,
        config_dict: Optional[Dict[str, Any]] = None
    ) -> ValidatedSystemConfig:
        if config_dict:
            # Parse and validate
            schedules = [RailCutoffSchedule(**s) for s in config_dict.get("rail_schedules", [])]
            self._config = ValidatedSystemConfig(
                environment=config_dict.get("environment", "TEST_ONLY"),
                service_name=config_dict.get("service_name", "pex_resolution_platform"),
                version=config_dict.get("version", "0.2.0"),
                rail_schedules=schedules,
                default_currency=config_dict.get("default_currency", "USD"),
                is_valid=True,
                validated_at=datetime.now(timezone.utc)
            )
        return self._config

    def get_rail_schedule(
        self,
        rail_code: str
    ) -> Optional[Dict[str, Any]]:
        for s in self._config.rail_schedules:
            if s.rail_code == rail_code:
                return s.model_dump()
        return None

    def get_evidence_config(
        self,
        tenant_id: str,
        profile_id: str
    ) -> Optional[BankEvidenceRequiredConfig]:
        key = ((tenant_id or "DEFAULT_BANK").upper(), (profile_id or "UNKNOWN").upper())
        return self._evidence_configs.get(key)

    def publish_evidence_config(
        self,
        config: BankEvidenceRequiredConfig
    ) -> bool:
        key = (config.tenant_id.upper(), config.profile_id.upper())
        self._evidence_configs[key] = config
        return True

    def list_evidence_configs(
        self,
        tenant_id: Optional[str] = None
    ) -> List[BankEvidenceRequiredConfig]:
        if tenant_id:
            tid = tenant_id.upper()
            return [cfg for (t, p), cfg in self._evidence_configs.items() if t == tid]
        return list(self._evidence_configs.values())
