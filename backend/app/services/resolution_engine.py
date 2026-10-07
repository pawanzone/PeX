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


class ResolutionEngine:
    """Master Resolution Engine dispatching to profile-specific deterministic resolvers."""

    def __init__(self):
        self._pr03_resolver = PR03Resolver()
        self._pr05_resolver = PR05Resolver()
        self._pr08_resolver = PR08Resolver()
        self._dq05_resolver = DQ05Resolver()

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

