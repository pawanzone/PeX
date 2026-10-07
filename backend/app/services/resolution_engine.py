"""Deterministic Resolution Engine for PeX Evidence-Driven STP Architecture.

Implements lossless, deterministic resolution contracts. For PR-03 (ISO20022_ERROR),
performs schema-compliant tag re-sequencing, namespace normalization, and envelope repair
without modifying or inventing business payload data.
"""
import re
import uuid
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone

from app.schemas.evidence_contract import EvidenceDossier
from app.schemas.resolution_contract import (
    ResolutionStatus,
    ResolutionUniqueness,
    ResolutionCandidate,
    ResolutionResult,
)


# Register default ISO 20022 namespace to serialize with clean default xmlns
ET.register_namespace("", "urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08")

# Canonical ISO 20022 pacs.008 tag sequencing definition
PACS008_ROOT_SEQUENCE = ["GrpHdr", "CdtTrfTxInf"]
PACS008_TX_SEQUENCE = [
    "PmtId",
    "PmtTpInf",
    "IntrBkSttlmAmt",
    "IntrBkSttlmDt",
    "SttlmPrty",
    "ChrgBr",
    "Dbtr",
    "DbtrAcct",
    "DbtrAgt",
    "CdtrAgt",
    "Cdtr",
    "CdtrAcct",
    "Purp",
    "RmtInf",
]
PACS008_PMTID_SEQUENCE = ["EndToEndId", "TxId", "UETR", "ClrSysRef"]
PACS008_PARTY_SEQUENCE = ["Nm", "PstlAdr", "Id", "CtryOfRes"]


def _strip_ns(tag: str) -> str:
    """Helper to remove XML namespace prefix for clean tag matching."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _reorder_elements(element: ET.Element, sequence: List[str], diff_log: List[str], reordered_fields: List[str]):
    """Deterministically reorders child elements matching the authoritative sequence without altering values."""
    children = list(element)
    if not children:
        return

    child_tags = [_strip_ns(c.tag) for c in children]
    
    # Sort children according to authoritative sequence
    def sort_key(child):
        tag = _strip_ns(child.tag)
        try:
            return (0, sequence.index(tag))
        except ValueError:
            return (1, tag)

    sorted_children = sorted(children, key=sort_key)
    sorted_tags = [_strip_ns(c.tag) for c in sorted_children]

    if child_tags != sorted_tags:
        diff_log.append(f"Re-sequenced children of <{_strip_ns(element.tag)}>: {child_tags} -> {sorted_tags}")
        reordered_fields.extend([f"{_strip_ns(element.tag)}/{t}" for t in sorted_tags])
        # Remove and re-append in canonical order to preserve element attributes & text
        for c in children:
            element.remove(c)
        for sc in sorted_children:
            element.append(sc)

    # Recursively reorder known nested elements
    for child in list(element):
        ctag = _strip_ns(child.tag)
        if ctag in ["FIToFICstmrCdtTrf", "pacs.008.001.08", "CstmrCdtTrfInitn"]:
            _reorder_elements(child, PACS008_ROOT_SEQUENCE, diff_log, reordered_fields)
        elif ctag == "CdtTrfTxInf":
            _reorder_elements(child, PACS008_TX_SEQUENCE, diff_log, reordered_fields)
        elif ctag == "PmtId":
            _reorder_elements(child, PACS008_PMTID_SEQUENCE, diff_log, reordered_fields)
        elif ctag in ["Dbtr", "Cdtr"]:
            _reorder_elements(child, PACS008_PARTY_SEQUENCE, diff_log, reordered_fields)


class PR03Resolver:
    """Deterministic, lossless structural resolver for PR-03 (ISO20022_ERROR)."""

    def resolve(self, raw_xml_or_json: str) -> Tuple[ResolutionStatus, ResolutionUniqueness, Optional[ResolutionCandidate], List[str], Optional[str]]:
        diff_log: List[str] = []
        namespaces_normalized: List[str] = []
        reordered_fields: List[str] = []
        default_envelope_applied = False

        # Check for empty or unparseable input
        if not raw_xml_or_json or not raw_xml_or_json.strip():
            return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, ["Input is empty."], "Cannot repair empty payload."

        text = raw_xml_or_json.strip()

        # Check for non-XML structured JSON format and extract XML payload if embedded
        if text.startswith("{") and "raw_xml" in text:
            import json
            try:
                data = json.loads(text)
                text = data.get("raw_xml", text)
            except Exception:
                pass

        # 1. Structural Repair: Envelope Normalization
        if not text.startswith("<?xml") and not text.startswith("<Document") and not text.startswith("<FIToFICstmrCdtTrf"):
            # Check if root is missing
            if "<GrpHdr>" in text or "<CdtTrfTxInf>" in text:
                text = f'<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08"><FIToFICstmrCdtTrf>{text}</FIToFICstmrCdtTrf></Document>'
                default_envelope_applied = True
                diff_log.append("Wrapped raw transaction fragment in standard pacs.008 Document envelope.")
        elif text.startswith("<FIToFICstmrCdtTrf") and not text.startswith("<Document"):
            text = f'<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">{text}</Document>'
            default_envelope_applied = True
            diff_log.append("Added outer <Document> namespace envelope.")

        # 2. Namespace Normalization: Clean up malformed or duplicated xmlns
        if 'xmlns=""' in text or 'xmlns="null"' in text:
            text = text.replace('xmlns=""', 'xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08"')
            text = text.replace('xmlns="null"', 'xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08"')
            namespaces_normalized.append("Replaced null/empty namespace with canonical pacs.008 urn.")
            diff_log.append("Normalized xmlns attribute.")

        # 3. XML Parsing & Deterministic Element Re-Sequencing
        try:
            root = ET.fromstring(text)
        except ET.ParseError as pe:
            # Handle common non-structural syntax errors like unclosed tags or trailing junk
            cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
            try:
                root = ET.fromstring(cleaned)
                diff_log.append("Stripped invalid non-printable control characters during parse.")
            except ET.ParseError as pe2:
                return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, f"Unrepairable XML syntax error: {str(pe2)}"

        # Find target payment document node
        doc_root = root
        if _strip_ns(root.tag) == "Document":
            fi_element = None
            for child in root:
                if _strip_ns(child.tag) in ["FIToFICstmrCdtTrf", "pacs.008.001.08", "CstmrCdtTrfInitn"]:
                    fi_element = child
                    break
            if fi_element is not None:
                doc_root = fi_element

        # Re-sequence root level elements (GrpHdr before CdtTrfTxInf)
        _reorder_elements(doc_root, PACS008_ROOT_SEQUENCE, diff_log, reordered_fields)

        # Re-serialize normalized XML
        repaired_xml = ET.tostring(root, encoding="utf-8").decode("utf-8")
        if not repaired_xml.startswith("<?xml"):
            repaired_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + repaired_xml

        # Check that mandatory business payload elements were not erased
        for mandatory_tag in ["IntrBkSttlmAmt", "Dbtr", "Cdtr"]:
            if mandatory_tag not in repaired_xml and mandatory_tag in raw_xml_or_json:
                return ResolutionStatus.RESOLUTION_NOT_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, None, diff_log, f"Lossless check failed: {mandatory_tag} was lost."

        candidate = ResolutionCandidate(
            candidate_id=f"CAND-PR03-{uuid.uuid4().hex[:8]}",
            repaired_payload=repaired_xml,
            diff_summary="; ".join(diff_log) if diff_log else "XML structure already valid or normalized.",
            derivation_method="DETERMINISTIC_ISO20022_XSD_RESEQUENCER",
            is_lossless=True,
            fields_reordered=reordered_fields,
            namespaces_normalized=namespaces_normalized,
            default_envelope_applied=default_envelope_applied
        )

        return ResolutionStatus.RESOLUTION_DETERMINED, ResolutionUniqueness.RESOLUTION_UNIQUE, candidate, diff_log, None


from app.services.pr05_transformer import pr05_transformer, GovernedCharacterEncodingTransformer


class PR05Resolver:
    """Deterministic, lossless character and encoding resolver for PR-05 (CORRUPTED_MESSAGE_FORMAT)."""

    def __init__(self, transformer: Optional[GovernedCharacterEncodingTransformer] = None):
        self.transformer = transformer or pr05_transformer

    def resolve(
        self,
        raw_bytes_or_str: Any,
        target_scheme: str = "ISO20022_UTF8",
        bank_transliteration_authorized: bool = True
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, Optional[ResolutionCandidate], List[str], Optional[str], bool]:
        """Resolves corrupted character encodings through the 9-stage governed pipeline."""
        res = self.transformer.transform(
            raw_input=raw_bytes_or_str,
            target_scheme=target_scheme,
            bank_transliteration_authorized=bank_transliteration_authorized,
            enforce_semantic_invariance=True
        )

        trail = res.audit_trail
        if not res.success:
            return (
                ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                ResolutionUniqueness.RESOLUTION_UNIQUE,
                None,
                trail,
                res.error_message or "PR-05 transformation failed.",
                res.is_lossless
            )

        candidate = ResolutionCandidate(
            candidate_id=f"CAND-PR05-{uuid.uuid4().hex[:8]}",
            repaired_payload=res.transformed_payload,
            diff_summary=res.diff_summary,
            derivation_method="GOVERNED_9STAGE_ENCODING_TRANSFORMER",
            is_lossless=res.is_lossless,
            fields_reordered=[],
            namespaces_normalized=[],
            default_envelope_applied=False
        )

        return (
            ResolutionStatus.RESOLUTION_DETERMINED,
            ResolutionUniqueness.RESOLUTION_UNIQUE,
            candidate,
            trail,
            None,
            res.is_lossless
        )


class PR08Resolver:
    """Deterministic, lossless special character transformer and state validator for PR-08."""

    def __init__(self):
        from app.services.pr08_transformer import pr08_transformer, ProcessingStateRecord
        self.transformer = pr08_transformer

    def resolve(
        self,
        raw_payload: str,
        target_rail: str = "SWIFT_CBPR_XSET",
        bank_policy_authorized: bool = True,
        bank_substitution_map: Optional[Dict[str, str]] = None,
        processing_state: Optional[Any] = None
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, Optional[ResolutionCandidate], List[str], Optional[str], bool, bool]:
        """Resolves unsupported special characters under target rail and bank policy."""
        res = self.transformer.transform(
            raw_payload=raw_payload,
            target_rail=target_rail,
            bank_policy_authorized=bank_policy_authorized,
            bank_substitution_map=bank_substitution_map,
            processing_state=processing_state,
            enforce_semantic_invariance=True
        )
        trail = res.audit_trail
        if not res.success:
            return (
                ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                ResolutionUniqueness.RESOLUTION_UNIQUE,
                None,
                trail,
                res.error_message or "PR-08 character substitution failed or blocked by state.",
                res.is_lossless,
                res.is_re_enqueue_eligible
            )

        candidate = ResolutionCandidate(
            candidate_id=f"CAND-PR08-{uuid.uuid4().hex[:8]}",
            repaired_payload=res.transformed_payload,
            diff_summary=res.diff_summary,
            derivation_method="GOVERNED_PR08_CHARACTER_SUBSTITUTION_ENGINE",
            is_lossless=res.is_lossless
        )

        return (
            ResolutionStatus.RESOLUTION_DETERMINED,
            ResolutionUniqueness.RESOLUTION_UNIQUE,
            candidate,
            trail,
            None,
            res.is_lossless,
            res.is_re_enqueue_eligible
        )


class DQ05Resolver:
    """Deterministic, lossless beneficiary postal address structurer and validator for DQ-05."""

    def __init__(self):
        from app.services.dq05_address_resolver import dq05_transformer
        self.transformer = dq05_transformer

    def resolve(
        self,
        raw_payload: str,
        bank_policy_authorized: bool = True,
        beneficiary_master: Optional[Dict[str, Any]] = None,
        force_ambiguity: bool = False
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, List[ResolutionCandidate], Optional[ResolutionCandidate], List[str], Optional[str], bool]:
        """Resolves invalid beneficiary postal address into ISO 20022 structured address."""
        res = self.transformer.parse_and_resolve(
            raw_payload=raw_payload,
            bank_policy_authorized=bank_policy_authorized,
            beneficiary_master_data=beneficiary_master,
            force_ambiguity=force_ambiguity
        )
        trail = res.audit_trail
        if not res.success:
            return (
                ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                res.uniqueness,
                [],
                None,
                trail,
                res.error_message or "DQ-05 address parsing failed.",
                res.is_lossless
            )

        primary_cand = res.candidates[0] if res.candidates else None
        return (
            ResolutionStatus.RESOLUTION_DETERMINED,
            res.uniqueness,
            res.candidates,
            primary_cand,
            trail,
            None,
            res.is_lossless
        )


class PR01Resolver:
    """Deterministic duplicate payment detector and identity resolver for PR-01."""

    def __init__(self):
        from app.services.pr01_duplicate_detector import pr01_detector
        self.detector = pr01_detector

    def resolve(
        self,
        raw_payload: str,
        identity: Optional[Any] = None,
        settlement_state: Optional[Any] = None,
        bank_policy: Optional[Dict[str, Any]] = None,
        historical_index: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, List[ResolutionCandidate], Optional[ResolutionCandidate], List[str], Optional[str], bool]:
        """Resolves duplicate payment candidates under ledger state and bank policy."""
        res = self.detector.detect_and_resolve(
            raw_payload=raw_payload,
            identity=identity,
            settlement_state=settlement_state,
            bank_policy=bank_policy,
            historical_index=historical_index
        )
        trail = res.audit_trail
        if not res.success:
            return (
                ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                res.uniqueness,
                [],
                None,
                trail,
                res.error_message or "PR-01 duplicate detection failed.",
                res.is_lossless
            )

        primary_cand = res.candidates[0] if res.candidates else None
        return (
            ResolutionStatus.RESOLUTION_DETERMINED,
            res.uniqueness,
            res.candidates,
            primary_cand,
            trail,
            None,
            res.is_lossless
        )


class DQ08Resolver:
    """Deterministic, lossless BIC / SWIFT reference data resolver for DQ-08."""

    def __init__(self):
        from app.services.dq08_bic_resolver import dq08_resolver
        self.resolver = dq08_resolver

    def resolve(
        self,
        raw_payload: str,
        original_bic: Optional[str] = None,
        reference_entry: Optional[Any] = None,
        bank_ssi: Optional[Any] = None,
        target_rail_spec: Optional[Any] = None
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, List[ResolutionCandidate], Optional[ResolutionCandidate], List[str], Optional[str], bool]:
        """Resolves BIC reference directory status, successor mapping, and reachability."""
        res = self.resolver.resolve_bic(
            raw_payload=raw_payload,
            original_bic=original_bic,
            reference_entry=reference_entry,
            bank_ssi=bank_ssi,
            target_rail_spec=target_rail_spec
        )
        trail = res.audit_trail
        if not res.success:
            return (
                ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                res.uniqueness,
                [],
                None,
                trail,
                res.error_message or "DQ-08 BIC resolution failed.",
                res.is_lossless
            )

        primary_cand = res.candidates[0] if res.candidates else None
        return (
            ResolutionStatus.RESOLUTION_DETERMINED,
            res.uniqueness,
            res.candidates,
            primary_cand,
            trail,
            None,
            res.is_lossless
        )


class DQ02Resolver:
    """Deterministic, lossless BIC / SWIFT reference data resolver for DQ-02."""

    def __init__(self):
        from app.services.dq02_bic_resolver import dq02_resolver
        self.resolver = dq02_resolver

    def resolve(
        self,
        raw_payload: str,
        original_bic: Optional[str] = None,
        reference_entry: Optional[Any] = None,
        bank_ssi: Optional[Any] = None,
        target_rail_spec: Optional[Any] = None,
        allow_bic8_normalization: bool = True
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, List[ResolutionCandidate], Optional[ResolutionCandidate], List[str], Optional[str], bool]:
        """Resolves BIC reference directory status, successor mapping, rail reachability, and SSI corroboration."""
        res = self.resolver.resolve_bic(
            raw_payload=raw_payload,
            original_bic=original_bic,
            reference_entry=reference_entry,
            bank_ssi=bank_ssi,
            target_rail_spec=target_rail_spec,
            allow_bic8_normalization=allow_bic8_normalization
        )
        trail = res.audit_trail
        if not res.success:
            return (
                ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                res.uniqueness,
                [],
                None,
                trail,
                res.error_message or "DQ-02 BIC resolution failed.",
                res.is_lossless
            )

        primary_cand = res.candidates[0] if res.candidates else None
        return (
            ResolutionStatus.RESOLUTION_DETERMINED,
            res.uniqueness,
            res.candidates,
            primary_cand,
            trail,
            None,
            res.is_lossless
        )


class DQ01Resolver:
    """Deterministic, lossless IBAN & Bank System-of-Record resolver for DQ-01."""

    def __init__(self):
        from app.services.dq01_iban_resolver import dq01_resolver
        self.resolver = dq01_resolver

    def resolve(
        self,
        raw_payload: str,
        original_iban: Optional[str] = None,
        beneficiary_name: Optional[str] = None,
        ssi_record: Optional[Any] = None,
        dda_record: Optional[Any] = None,
        cop_response: Optional[Any] = None,
        allow_stale_evidence: bool = False,
        require_cop: bool = False
    ) -> Tuple[ResolutionStatus, ResolutionUniqueness, List[ResolutionCandidate], Optional[ResolutionCandidate], List[str], Optional[str], bool]:
        """Resolves IBAN ISO 13616 structure, MOD-97-10 checksum, permutations, and Bank SoR corroboration."""
        res = self.resolver.resolve_iban(
            raw_payload=raw_payload,
            original_iban=original_iban,
            beneficiary_name=beneficiary_name,
            ssi_record=ssi_record,
            dda_record=dda_record,
            cop_response=cop_response,
            allow_stale_evidence=allow_stale_evidence,
            require_cop=require_cop
        )
        trail = res.audit_trail
        if not res.success and not res.candidates:
            return (
                ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                res.uniqueness,
                res.candidates,
                None,
                trail,
                res.error_message or "DQ-01 IBAN resolution failed.",
                res.is_lossless
            )

        primary_cand = res.candidates[0] if res.candidates else None
        status = ResolutionStatus.RESOLUTION_DETERMINED if primary_cand is not None else ResolutionStatus.RESOLUTION_NOT_DETERMINED
        return (
            status,
            res.uniqueness,
            res.candidates,
            primary_cand,
            trail,
            res.error_message,
            res.is_lossless
        )


class ResolutionEngine:
    """Master Resolution Engine dispatching to profile-specific deterministic resolvers."""

    def __init__(self):
        self._pr03_resolver = PR03Resolver()
        self._pr05_resolver = PR05Resolver()
        self._pr08_resolver = PR08Resolver()
        self._dq05_resolver = DQ05Resolver()
        self._pr01_resolver = PR01Resolver()
        self._dq08_resolver = DQ08Resolver()
        self._dq02_resolver = DQ02Resolver()
        self._dq01_resolver = DQ01Resolver()

    def derive_resolution(self, dossier: EvidenceDossier) -> ResolutionResult:
        """Derives a deterministic candidate resolution from an Evidence Dossier."""
        profile_id = dossier.profile_id
        trail: List[str] = [f"Initiating deterministic resolution for profile: {profile_id}"]


        if profile_id == "PR-03":
            raw_item = dossier.get_item("RAW_PAYLOAD")
            if not raw_item:
                trail.append("Missing RAW_PAYLOAD item in evidence dossier.")
                return ResolutionResult(
                    profile_id=profile_id,
                    status=ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                    uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                    is_lossless=True,
                    audit_trail=trail,
                    error_message="Missing RAW_PAYLOAD in evidence dossier."
                )

            raw_text = str(raw_item.payload.get("raw_text") or raw_item.payload.get("raw_xml") or "")
            status, uniqueness, candidate, diff_log, err = self._pr03_resolver.resolve(raw_text)
            trail.extend(diff_log)

            candidates = [candidate] if candidate else []
            return ResolutionResult(
                profile_id=profile_id,
                status=status,
                uniqueness=uniqueness,
                candidates=candidates,
                primary_candidate=candidate,
                is_lossless=True,
                audit_trail=trail,
                error_message=err
            )

        elif profile_id == "PR-05":
            raw_item = dossier.get_item("RAW_PAYLOAD_BYTES") or dossier.get_item("RAW_PAYLOAD")
            if not raw_item:
                trail.append("Missing RAW_PAYLOAD_BYTES item in evidence dossier for PR-05.")
                return ResolutionResult(
                    profile_id=profile_id,
                    status=ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                    uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                    is_lossless=True,
                    audit_trail=trail,
                    error_message="Missing RAW_PAYLOAD_BYTES in evidence dossier."
                )

            raw_content = raw_item.payload.get("raw_bytes") or raw_item.payload.get("raw_text") or ""
            scheme_item = dossier.get_item("TARGET_SCHEME_CHARSET_SPEC")
            target_scheme = scheme_item.payload.get("target_scheme", "ISO20022_UTF8") if scheme_item else "ISO20022_UTF8"

            policy_item = dossier.get_item("BANK_TRANSLITERATION_POLICY")
            bank_translit_auth = policy_item.payload.get("is_authorized", True) if policy_item else False

            status, uniqueness, candidate, diff_log, err, is_lossless = self._pr05_resolver.resolve(
                raw_bytes_or_str=raw_content,
                target_scheme=target_scheme,
                bank_transliteration_authorized=bank_translit_auth
            )
            trail.extend(diff_log)

            candidates = [candidate] if candidate else []
            return ResolutionResult(
                profile_id=profile_id,
                status=status,
                uniqueness=uniqueness,
                candidates=candidates,
                primary_candidate=candidate,
                is_lossless=is_lossless,
                audit_trail=trail,
                error_message=err
            )

        elif profile_id == "PR-08":
            raw_item = dossier.get_item("RAW_PAYLOAD") or dossier.get_item("RAW_PAYLOAD_BYTES")
            if not raw_item:
                trail.append("Missing RAW_PAYLOAD item in evidence dossier for PR-08.")
                return ResolutionResult(
                    profile_id=profile_id,
                    status=ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                    uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                    is_lossless=True,
                    audit_trail=trail,
                    error_message="Missing RAW_PAYLOAD in evidence dossier."
                )

            raw_text = str(raw_item.payload.get("raw_text") or "")
            rail_item = dossier.get_item("TARGET_RAIL_CHARSET_SPEC")
            target_rail = rail_item.payload.get("target_rail", "SWIFT_CBPR_XSET") if rail_item else "SWIFT_CBPR_XSET"

            policy_item = dossier.get_item("BANK_CHARACTER_SUBSTITUTION_POLICY")
            bank_policy_auth = policy_item.payload.get("is_authorized", True) if policy_item else False
            bank_subs_map = policy_item.payload.get("custom_substitutions") if policy_item else None

            state_item = dossier.get_item("PROCESSING_STATE_RECORD")
            proc_state = None
            if state_item and isinstance(state_item.payload, dict):
                from app.services.pr08_transformer import ProcessingStateRecord
                try:
                    proc_state = ProcessingStateRecord(**state_item.payload)
                except Exception:
                    pass

            status, uniqueness, candidate, diff_log, err, is_lossless, is_re_enq = self._pr08_resolver.resolve(
                raw_payload=raw_text,
                target_rail=target_rail,
                bank_policy_authorized=bank_policy_auth,
                bank_substitution_map=bank_subs_map,
                processing_state=proc_state
            )
            trail.extend(diff_log)

            candidates = [candidate] if candidate else []
            return ResolutionResult(
                profile_id=profile_id,
                status=status,
                uniqueness=uniqueness,
                candidates=candidates,
                primary_candidate=candidate,
                is_lossless=is_lossless,
                audit_trail=trail,
                error_message=err
            )

        elif profile_id == "DQ-05":
            raw_item = dossier.get_item("RAW_PAYLOAD") or dossier.get_item("RAW_PAYLOAD_BYTES")
            if not raw_item:
                trail.append("Missing RAW_PAYLOAD item in evidence dossier for DQ-05.")
                return ResolutionResult(
                    profile_id=profile_id,
                    status=ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                    uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                    is_lossless=True,
                    audit_trail=trail,
                    error_message="Missing RAW_PAYLOAD in evidence dossier."
                )

            raw_text = str(raw_item.payload.get("raw_text") or "")
            policy_item = dossier.get_item("BANK_ADDRESS_POLICY")
            bank_policy_auth = policy_item.payload.get("is_authorized", True) if policy_item else False

            master_item = dossier.get_item("BENEFICIARY_MASTER_RECORD")
            master_data = master_item.payload if (master_item and master_item.is_valid) else None

            force_ambig = dossier.metadata.get("force_ambiguity", False)

            status, uniqueness, candidates, primary_cand, diff_log, err, is_lossless = self._dq05_resolver.resolve(
                raw_payload=raw_text,
                bank_policy_authorized=bank_policy_auth,
                beneficiary_master=master_data,
                force_ambiguity=force_ambig
            )
            trail.extend(diff_log)

            return ResolutionResult(
                profile_id=profile_id,
                status=status,
                uniqueness=uniqueness,
                candidates=candidates,
                primary_candidate=primary_cand,
                is_lossless=is_lossless,
                audit_trail=trail,
                error_message=err
            )

        elif profile_id == "PR-01":
            raw_item = dossier.get_item("RAW_PAYLOAD") or dossier.get_item("RAW_PAYLOAD_BYTES")
            if not raw_item:
                trail.append("Missing RAW_PAYLOAD item in evidence dossier for PR-01.")
                return ResolutionResult(
                    profile_id=profile_id,
                    status=ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                    uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                    is_lossless=True,
                    audit_trail=trail,
                    error_message="Missing RAW_PAYLOAD in evidence dossier."
                )

            raw_text = str(raw_item.payload.get("raw_text") or "")

            ident_item = dossier.get_item("PAYMENT_IDENTITY_RECORD")
            ident_data = None
            if ident_item and isinstance(ident_item.payload, dict):
                from app.services.pr01_duplicate_detector import PaymentIdentityRecord
                try:
                    ident_data = PaymentIdentityRecord(**ident_item.payload)
                except Exception:
                    pass

            settle_item = dossier.get_item("CURRENT_SETTLEMENT_STATE")
            settle_data = None
            if settle_item and isinstance(settle_item.payload, dict):
                from app.services.pr01_duplicate_detector import CurrentSettlementState
                try:
                    settle_data = CurrentSettlementState(**settle_item.payload)
                except Exception:
                    pass

            policy_item = dossier.get_item("BANK_DUPLICATE_POLICY")
            policy_data = policy_item.payload if (policy_item and policy_item.is_valid) else None

            hist_item = dossier.get_item("HISTORICAL_PAYMENT_INDEX")
            hist_index = hist_item.payload.get("historical_payments") if (hist_item and isinstance(hist_item.payload, dict)) else None

            status, uniqueness, candidates, primary_cand, diff_log, err, is_lossless = self._pr01_resolver.resolve(
                raw_payload=raw_text,
                identity=ident_data,
                settlement_state=settle_data,
                bank_policy=policy_data,
                historical_index=hist_index
            )
            trail.extend(diff_log)

            return ResolutionResult(
                profile_id=profile_id,
                status=status,
                uniqueness=uniqueness,
                candidates=candidates,
                primary_candidate=primary_cand,
                is_lossless=is_lossless,
                audit_trail=trail,
                error_message=err
            )

        elif profile_id == "DQ-08":
            raw_item = dossier.get_item("RAW_PAYLOAD") or dossier.get_item("RAW_PAYLOAD_BYTES")
            if not raw_item:
                trail.append("Missing RAW_PAYLOAD item in evidence dossier for DQ-08.")
                return ResolutionResult(
                    profile_id=profile_id,
                    status=ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                    uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                    is_lossless=True,
                    audit_trail=trail,
                    error_message="Missing RAW_PAYLOAD in evidence dossier."
                )

            raw_text = str(raw_item.payload.get("raw_text") or "")

            orig_item = dossier.get_item("ORIGINAL_BIC_RECORD")
            orig_bic = orig_item.payload.get("bic_code") if (orig_item and isinstance(orig_item.payload, dict)) else None

            ref_item = dossier.get_item("BIC_REFERENCE_DIRECTORY")
            ref_entry = None
            if ref_item and isinstance(ref_item.payload, dict):
                from app.services.dq08_bic_resolver import BICReferenceEntry
                try:
                    ref_entry = BICReferenceEntry(**ref_item.payload)
                except Exception:
                    pass

            ssi_item = dossier.get_item("BANK_COUNTERPARTY_SSI")
            ssi_data = None
            if ssi_item and isinstance(ssi_item.payload, dict):
                from app.services.dq08_bic_resolver import BankCounterpartySSI
                try:
                    ssi_data = BankCounterpartySSI(**ssi_item.payload)
                except Exception:
                    pass

            rail_item = dossier.get_item("TARGET_RAIL_ROUTING_SPEC")
            rail_spec = None
            if rail_item and isinstance(rail_item.payload, dict):
                from app.services.dq08_bic_resolver import TargetRailRoutingSpec
                try:
                    rail_spec = TargetRailRoutingSpec(**rail_item.payload)
                except Exception:
                    pass

            status, uniqueness, candidates, primary_cand, diff_log, err, is_lossless = self._dq08_resolver.resolve(
                raw_payload=raw_text,
                original_bic=orig_bic,
                reference_entry=ref_entry,
                bank_ssi=ssi_data,
                target_rail_spec=rail_spec
            )
            trail.extend(diff_log)

            return ResolutionResult(
                profile_id=profile_id,
                status=status,
                uniqueness=uniqueness,
                candidates=candidates,
                primary_candidate=primary_cand,
                is_lossless=is_lossless,
                audit_trail=trail,
                error_message=err
            )

        elif profile_id == "DQ-02":
            raw_item = dossier.get_item("RAW_PAYLOAD") or dossier.get_item("RAW_PAYLOAD_BYTES")
            if not raw_item:
                trail.append("Missing RAW_PAYLOAD item in evidence dossier for DQ-02.")
                return ResolutionResult(
                    profile_id=profile_id,
                    status=ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                    uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                    is_lossless=True,
                    audit_trail=trail,
                    error_message="Missing RAW_PAYLOAD in evidence dossier."
                )

            raw_text = str(raw_item.payload.get("raw_text") or "")

            orig_item = dossier.get_item("ORIGINAL_BIC_RECORD")
            orig_bic = orig_item.payload.get("bic_code") if (orig_item and isinstance(orig_item.payload, dict)) else None

            ref_item = dossier.get_item("BIC_REFERENCE_DIRECTORY")
            ref_entry = None
            if ref_item and isinstance(ref_item.payload, dict):
                from app.services.dq02_bic_resolver import BICReferenceEntry
                try:
                    ref_entry = BICReferenceEntry(**ref_item.payload)
                except Exception:
                    pass

            ssi_item = dossier.get_item("BANK_COUNTERPARTY_SSI")
            ssi_data = None
            if ssi_item and isinstance(ssi_item.payload, dict):
                from app.services.dq02_bic_resolver import BankCounterpartySSI
                try:
                    ssi_data = BankCounterpartySSI(**ssi_item.payload)
                except Exception:
                    pass

            rail_item = dossier.get_item("TARGET_RAIL_ROUTING_SPEC")
            rail_spec = None
            if rail_item and isinstance(rail_item.payload, dict):
                from app.services.dq02_bic_resolver import TargetRailRoutingSpec
                try:
                    rail_spec = TargetRailRoutingSpec(**rail_item.payload)
                except Exception:
                    pass

            allow_bic8_norm = dossier.metadata.get("allow_bic8_normalization", True)

            status, uniqueness, candidates, primary_cand, diff_log, err, is_lossless = self._dq02_resolver.resolve(
                raw_payload=raw_text,
                original_bic=orig_bic,
                reference_entry=ref_entry,
                bank_ssi=ssi_data,
                target_rail_spec=rail_spec,
                allow_bic8_normalization=allow_bic8_norm
            )
            trail.extend(diff_log)

            return ResolutionResult(
                profile_id=profile_id,
                status=status,
                uniqueness=uniqueness,
                candidates=candidates,
                primary_candidate=primary_cand,
                is_lossless=is_lossless,
                audit_trail=trail,
                error_message=err
            )

        elif profile_id == "DQ-01":
            raw_item = dossier.get_item("RAW_PAYLOAD") or dossier.get_item("RAW_PAYLOAD_BYTES")
            if not raw_item:
                trail.append("Missing RAW_PAYLOAD item in evidence dossier for DQ-01.")
                return ResolutionResult(
                    profile_id=profile_id,
                    status=ResolutionStatus.RESOLUTION_NOT_DETERMINED,
                    uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
                    is_lossless=True,
                    audit_trail=trail,
                    error_message="Missing RAW_PAYLOAD in evidence dossier."
                )

            raw_text = str(raw_item.payload.get("raw_text") or "")

            orig_iban = dossier.metadata.get("original_iban")
            bene_name = dossier.metadata.get("beneficiary_name")

            # Extract SSI Record
            ssi_item = dossier.get_item("BANK_SSI_MASTER_RECORD")
            ssi_data = None
            if ssi_item and isinstance(ssi_item.payload, dict):
                from app.services.dq01_iban_resolver import BankSSIMasterEntry
                try:
                    ssi_data = BankSSIMasterEntry(**ssi_item.payload)
                except Exception:
                    pass

            # Extract DDA Record
            dda_item = dossier.get_item("CORE_DDA_ACCOUNT_STATUS")
            dda_data = None
            if dda_item and isinstance(dda_item.payload, dict):
                from app.services.dq01_iban_resolver import CoreDDAAccountRecord
                try:
                    dda_data = CoreDDAAccountRecord(**dda_item.payload)
                except Exception:
                    pass

            # Extract CoP Response
            cop_item = dossier.get_item("COP_VOP_RESPONSE")
            cop_data = None
            if cop_item and isinstance(cop_item.payload, dict):
                from app.services.dq01_iban_resolver import CoPResponse
                try:
                    cop_data = CoPResponse(**cop_item.payload)
                except Exception:
                    pass

            allow_stale = dossier.metadata.get("allow_stale_evidence", False)
            require_cop = dossier.metadata.get("require_cop", False)

            status, uniqueness, candidates, primary_cand, diff_log, err, is_lossless = self._dq01_resolver.resolve(
                raw_payload=raw_text,
                original_iban=orig_iban,
                beneficiary_name=bene_name,
                ssi_record=ssi_data,
                dda_record=dda_data,
                cop_response=cop_data,
                allow_stale_evidence=allow_stale,
                require_cop=require_cop
            )
            trail.extend(diff_log)

            return ResolutionResult(
                profile_id=profile_id,
                status=status,
                uniqueness=uniqueness,
                candidates=candidates,
                primary_candidate=primary_cand,
                is_lossless=is_lossless,
                audit_trail=trail,
                error_message=err
            )

        # Fallback for unregistered profiles
        trail.append(f"No deterministic resolver registered for profile {profile_id}.")
        return ResolutionResult(
            profile_id=profile_id,
            status=ResolutionStatus.RESOLUTION_NOT_DETERMINED,
            uniqueness=ResolutionUniqueness.RESOLUTION_UNIQUE,
            is_lossless=True,
            audit_trail=trail,
            error_message=f"Resolver for profile {profile_id} not implemented."
        )


# Global singleton resolution engine
resolution_engine = ResolutionEngine()


