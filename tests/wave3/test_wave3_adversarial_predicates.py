"""Adversarial & Fault Injection Tests for Wave 3 across the Canonical 8 Predicates.

Remediates Finding W3-FOR-01 in accordance with Remediation Gate v0.1.4:
- Minimum 24 qualifying Category A single-predicate isolated mutation scenarios.
- Strict Category A isolation: Baseline has all 8 predicates True; exactly 1 predicate mutated to False;
  other 7 predicates remain strictly True; STP_ELIGIBLE evaluates to False.
- Category B compound adversarial tests including TR-08 zero-autonomous-STP invariant.
"""
import pytest
from app.services.e2e_runner import E2EExecutionHarness
from app.schemas.contracts.e2e_schemas import CanonicalE2EInput, E2EPaymentInfo


@pytest.fixture
def harness():
    return E2EExecutionHarness()


# ==============================================================================
# BASELINE BUILDERS (ALL 8 PREDICATES EVALUATE TO TRUE)
# ==============================================================================

def make_tr02_baseline(exception_id: str = "BASE-TR02") -> CanonicalE2EInput:
    """Builds a pristine TR-02 input where all 8 predicates evaluate to True."""
    return CanonicalE2EInput(
        exception_id=exception_id,
        profile_id="TR-02",
        domain="CLIENT_TREASURY",
        error_code="ERR_INSUFFICIENT_FUNDS",
        error_message="Intraday liquidity check required",
        payment_info=E2EPaymentInfo(
            payment_id="PMT-TR02-BASE",
            uetr="UETR-TR02-BASE",
            amount=5000.0,  # <= $10k auto STP threshold
            currency="USD",
            clearing_rail="FEDWIRE",
            debtor_name="Apex Corp",
            debtor_account="ACCT-CORP-USD-001",  # Has $450,000 available
            debtor_agent_bic="CHASUS33XXX",
        ),
        bank_supplied_evidence={
            "debtor_account": "ACCT-CORP-USD-001",
            "core_dda_balance_record": {"account_number": "ACCT-CORP-USD-001"},
            "intraday_reservation_schedule": {"reservation_id": "RES-01"},
        },
    )


def make_tr03_baseline(exception_id: str = "BASE-TR03") -> CanonicalE2EInput:
    """Builds a pristine TR-03 input where all 8 predicates evaluate to True."""
    return CanonicalE2EInput(
        exception_id=exception_id,
        profile_id="TR-03",
        domain="CLIENT_TREASURY",
        error_code="ERR_NOSTRO_SHORTFALL",
        error_message="Correspondent Nostro balance verification",
        payment_info=E2EPaymentInfo(
            payment_id="PMT-TR03-BASE",
            uetr="UETR-TR03-BASE",
            amount=8000.0,  # <= $10k auto STP threshold
            currency="EUR",
            clearing_rail="TARGET2",
            debtor_name="Apex Global",
            debtor_account="ACCT-CORP-EUR-001",
            debtor_agent_bic="BNPAFRPPXXX",
            creditor_agent_bic="BNPAFRPPXXX",
        ),
        bank_supplied_evidence={
            "nostro_bic": "BNPAFRPPXXX",
            "nostro_position_statement": {"nostro_bic": "BNPAFRPPXXX"},
            "pending_correspondent_credits": {"has_credits": True},
        },
    )


def make_tr04_baseline(exception_id: str = "BASE-TR04") -> CanonicalE2EInput:
    """Builds a pristine TR-04 input where all 8 predicates evaluate to True."""
    return CanonicalE2EInput(
        exception_id=exception_id,
        profile_id="TR-04",
        domain="CLIENT_TREASURY",
        error_code="ERR_FX_RATE_UNAVAILABLE",
        error_message="Live FX rate quote required",
        payment_info=E2EPaymentInfo(
            payment_id="PMT-TR04-BASE",
            uetr="UETR-TR04-BASE",
            amount=5000.0,
            currency="EUR",
            clearing_rail="SWIFT_CBPR+",
            debtor_name="Apex Europe",
            debtor_account="ACCT-CORP-EUR-001",
            debtor_agent_bic="BNPAFRPPXXX",
        ),
        bank_supplied_evidence={
            "currency_pair": "EUR/USD",
            "settlement_currency": "USD",
            "official_fx_rate_feed": {
                "currency_pair": "EUR/USD",
                "mid_rate": 1.0850,
                "is_live": True,
                "is_authoritative": True,
            },
            "fx_spread_policy_matrix": {
                "currency_pair": "EUR/USD",
                "max_rate_age_seconds": 60.0,
                "max_spread_tolerance_bps": 50.0,
                "allow_auto_booking": True,
            },
            "inward_payment_record": {
                "payment_id": "PMT-TR04-BASE",
                "amount": 5000.0,
                "currency": "EUR",
            },
        },
    )


def make_tr06_baseline(exception_id: str = "BASE-TR06") -> CanonicalE2EInput:
    """Builds a pristine TR-06 input where all 8 predicates evaluate to True."""
    return CanonicalE2EInput(
        exception_id=exception_id,
        profile_id="TR-06",
        domain="CLIENT_TREASURY",
        error_code="ERR_LIMIT_BREACH",
        error_message="Operational limit evaluation",
        payment_info=E2EPaymentInfo(
            payment_id="PMT-TR06-BASE",
            uetr="UETR-TR06-BASE",
            amount=5000.0,
            currency="USD",
            clearing_rail="FEDWIRE",
            debtor_name="CLI-CORP-001",
            debtor_account="ACCT-CORP-USD-001",
            debtor_agent_bic="CHASUS33XXX",
        ),
        bank_supplied_evidence={
            "limit_id": "LIM-DAILY-CORP-01",
            "client_id": "CLI-CORP-001",
            "limit_utilization_record": {"limit_id": "LIM-DAILY-CORP-01"},
            "client_limit_agreement": {"client_id": "CLI-CORP-001"},
        },
    )


def make_tr07_baseline(exception_id: str = "BASE-TR07") -> CanonicalE2EInput:
    """Builds a pristine TR-07 input where all 8 predicates evaluate to True."""
    return CanonicalE2EInput(
        exception_id=exception_id,
        profile_id="TR-07",
        domain="CLIENT_TREASURY",
        error_code="ERR_LIQUIDITY_CONSTRAINT",
        error_message="Clearing reserve headroom verification",
        payment_info=E2EPaymentInfo(
            payment_id="PMT-TR07-BASE",
            uetr="UETR-TR07-BASE",
            amount=5000.0,
            currency="USD",
            clearing_rail="FEDWIRE",
            debtor_name="Apex Corp",
            debtor_account="ACCT-CORP-USD-001",
            debtor_agent_bic="CHASUS33XXX",
        ),
        bank_supplied_evidence={
            "clearing_context": "FEDWIRE",
            "clearing_liquidity_reserve": {"clearing_context": "FEDWIRE"},
            "settlement_queue_status": {"clearing_context": "FEDWIRE"},
        },
    )


def assert_isolated_predicate_failure(out, target_predicate: str):
    """Normative assertion helper proving single-predicate isolation:

    1. target predicate evaluates to False
    2. the other 7 predicates remain strictly True
    3. stp_eligible evaluates to False
    """
    pb = out.predicate_breakdown
    assert out.stp_eligible is False, "STP_ELIGIBLE must be False when any predicate fails"

    predicates = {
        "e_suff": pb.e_suff,
        "r_det": pb.r_det,
        "r_uniq": pb.r_uniq,
        "v_det": pb.v_det,
        "v_auth": pb.v_auth,
        "p_bank": pb.p_bank,
        "c_comp": pb.c_comp,
        "x_pre": pb.x_pre,
    }

    assert predicates[target_predicate] is False, f"Target predicate {target_predicate} must evaluate to False"

    for name, val in predicates.items():
        if name != target_predicate:
            assert val is True, f"Non-target predicate {name} must remain True (failed single-predicate isolation)"


# ==============================================================================
# WORKSTREAM B: 24 QUALIFYING CATEGORY A ISOLATED PREDICATE MUTATION SCENARIOS
# ==============================================================================

# --- GROUP 1: E_suff (Evidence Sufficiency) Isolated Tests ---

def test_cat_a_01_e_suff_tr02_missing_reservation_schedule(harness):
    """Category A #1: TR-02 E_suff == False (missing mandatory reservation schedule)."""
    inp = make_tr02_baseline("CAT-A-01")
    # Mutation: Omit mandatory INTRADAY_RESERVATION_SCHEDULE
    inp.bank_supplied_evidence = {
        "debtor_account": "ACCT-CORP-USD-001",
        "core_dda_balance_record": {"account_number": "ACCT-CORP-USD-001"},
    }
    out = harness.process_input(inp)
    assert_isolated_predicate_failure(out, "e_suff")


def test_cat_a_02_e_suff_tr03_missing_pending_credits(harness):
    """Category A #2: TR-03 E_suff == False (missing mandatory pending correspondent credits)."""
    inp = make_tr03_baseline("CAT-A-02")
    # Mutation: Omit mandatory PENDING_CORRESPONDENT_CREDITS
    inp.bank_supplied_evidence = {
        "nostro_bic": "BNPAFRPPXXX",
        "nostro_position_statement": {"nostro_bic": "BNPAFRPPXXX"},
    }
    out = harness.process_input(inp)
    assert_isolated_predicate_failure(out, "e_suff")


def test_cat_a_03_e_suff_tr04_missing_spread_policy(harness):
    """Category A #3: TR-04 E_suff == False (missing mandatory spread policy matrix)."""
    inp = make_tr04_baseline("CAT-A-03")
    # Mutation: Omit mandatory FX_SPREAD_POLICY_MATRIX
    inp.bank_supplied_evidence = {
        "currency_pair": "EUR/USD",
        "official_fx_rate_feed": {
            "currency_pair": "EUR/USD",
            "mid_rate": 1.0850,
            "is_live": True,
            "is_authoritative": True,
        },
        "inward_payment_record": {
            "payment_id": "PMT-TR04-BASE",
            "amount": 5000.0,
            "currency": "EUR",
        },
    }
    out = harness.process_input(inp)
    assert_isolated_predicate_failure(out, "e_suff")


# --- GROUP 2: R_det (Deterministic Candidate Exists) Isolated Tests ---

def test_cat_a_04_r_det_tr02_persistent_deficit(harness):
    """Category A #4: TR-02 R_det == False (persistent deficit without pending credits)."""
    inp = make_tr02_baseline("CAT-A-04")
    # Mutation: Account has hard deficit ($500 avail vs $5000 required, 0 pending)
    inp.payment_info.debtor_account = "ACCT-DEFICIT-USD-002"
    inp.bank_supplied_evidence["debtor_account"] = "ACCT-DEFICIT-USD-002"
    inp.bank_supplied_evidence["core_dda_balance_record"] = {"account_number": "ACCT-DEFICIT-USD-002"}
    out = harness.process_input(inp)
    assert_isolated_predicate_failure(out, "r_det")


def test_cat_a_05_r_det_tr03_nostro_deficit_unfunded(harness):
    """Category A #5: TR-03 R_det == False (Nostro deficit exceeding auto-sweep threshold)."""
    inp = make_tr03_baseline("CAT-A-05")
    # Mutation: Amount within policy ($8k), mandatory evidence supplied, but unregistered Nostro BIC has no position
    inp.payment_info.amount = 8000.0
    inp.payment_info.creditor_agent_bic = "UNKNOWNBICXX"
    inp.bank_supplied_evidence = {
        "nostro_bic": "UNKNOWNBICXX",
        "nostro_position_statement": {"nostro_bic": "UNKNOWNBICXX"},
        "pending_correspondent_credits": {"has_credits": False},
    }
    out = harness.process_input(inp)
    assert_isolated_predicate_failure(out, "r_det")


def test_cat_a_06_r_det_tr04_stale_market_quote(harness):
    """Category A #6: TR-04 R_det == False (market quote marked inactive / stale)."""
    inp = make_tr04_baseline("CAT-A-06")
    # Mutation: Inactive / stale quote feed causes resolve_tr04 to fail closed to HITL
    inp.bank_supplied_evidence["official_fx_rate_feed"]["is_live"] = False
    out = harness.process_input(inp)
    assert_isolated_predicate_failure(out, "r_det")


# --- GROUP 3: R_uniq (Single Candidate Determinism) Isolated Tests ---

def test_cat_a_07_r_uniq_tr02_ambiguous_funding_candidates(harness):
    """Category A #7: TR-02 R_uniq == False (multiple candidate funding options without precedence)."""
    inp = make_tr02_baseline("CAT-A-07")
    # Mutation: Flag ambiguous candidates
    inp.bank_supplied_evidence["ambiguous_candidates"] = True
    out = harness.process_input(inp)
    assert_isolated_predicate_failure(out, "r_uniq")


def test_cat_a_08_r_uniq_tr03_ambiguous_nostro_sweep_routes(harness):
    """Category A #8: TR-03 R_uniq == False (ambiguous rebalancing sweep route)."""
    inp = make_tr03_baseline("CAT-A-08")
    # Mutation: Flag ambiguous sweep routes
    inp.bank_supplied_evidence["ambiguous_candidates"] = True
    out = harness.process_input(inp)
    assert_isolated_predicate_failure(out, "r_uniq")


def test_cat_a_09_r_uniq_tr04_ambiguous_market_rate_quotes(harness):
    """Category A #9: TR-04 R_uniq == False (multiple conflicting rate quotes)."""
    inp = make_tr04_baseline("CAT-A-09")
    # Mutation: Flag ambiguous FX rate candidates
    inp.bank_supplied_evidence["ambiguous_candidates"] = True
    out = harness.process_input(inp)
    assert_isolated_predicate_failure(out, "r_uniq")


# --- GROUP 4: V_det (Deterministic Syntax & Format Validation) Isolated Tests ---

def test_cat_a_10_v_det_tr02_syntax_validation_failure(harness):
    """Category A #10: TR-02 V_det == False (formatting/syntax validation failure)."""
    inp = make_tr02_baseline("CAT-A-10")
    # Mutation: Flag deterministic syntax validation failure
    inp.bank_supplied_evidence["syntax_validation_failed"] = True
    out = harness.process_input(inp)
    assert_isolated_predicate_failure(out, "v_det")


def test_cat_a_11_v_det_tr04_formatting_failure(harness):
    """Category A #11: TR-04 V_det == False (mathematical / syntax formatting failure)."""
    inp = make_tr04_baseline("CAT-A-11")
    # Mutation: Flag deterministic validation failure
    inp.bank_supplied_evidence["deterministic_validation_failed"] = True
    out = harness.process_input(inp)
    assert_isolated_predicate_failure(out, "v_det")


def test_cat_a_12_v_det_tr06_limit_id_syntax_failure(harness):
    """Category A #12: TR-06 V_det == False (limit identifier syntax corrupted)."""
    inp = make_tr06_baseline("CAT-A-12")
    # Mutation: Flag syntax validation failure
    inp.bank_supplied_evidence["syntax_validation_failed"] = True
    out = harness.process_input(inp)
    assert_isolated_predicate_failure(out, "v_det")


# --- GROUP 5: V_auth (Authoritative Evidence Verification) Isolated Tests ---

def test_cat_a_13_v_auth_tr02_non_authoritative_source(harness):
    """Category A #13: TR-02 V_auth == False (unverified/non-authoritative DDA feed)."""
    inp = make_tr02_baseline("CAT-A-13")
    # Mutation: Flag simulated authority unavailable / non-authoritative source
    inp.bank_supplied_evidence["simulate_authority_unavailable"] = True
    out = harness.process_input(inp)
    assert_isolated_predicate_failure(out, "v_auth")


def test_cat_a_14_v_auth_tr04_unverified_fx_source(harness):
    """Category A #14: TR-04 V_auth == False (unverified FX pricing authority)."""
    inp = make_tr04_baseline("CAT-A-14")
    # Mutation: Flag simulated authority unavailable
    inp.bank_supplied_evidence["simulate_authority_unavailable"] = True
    out = harness.process_input(inp)
    assert_isolated_predicate_failure(out, "v_auth")


def test_cat_a_15_v_auth_tr06_unverified_limit_authority(harness):
    """Category A #15: TR-06 V_auth == False (unverified limit authority feed)."""
    inp = make_tr06_baseline("CAT-A-15")
    # Mutation: Flag simulated authority unavailable
    inp.bank_supplied_evidence["simulate_authority_unavailable"] = True
    out = harness.process_input(inp)
    assert_isolated_predicate_failure(out, "v_auth")


# --- GROUP 6: P_bank (Bank Policy Thresholds) Isolated Tests ---

def test_cat_a_16_p_bank_tr02_amount_exceeds_threshold(harness):
    """Category A #16: TR-02 P_bank == False (amount exceeds autonomous/fast-lane ceiling)."""
    inp = make_tr02_baseline("CAT-A-16")
    # Mutation: Amount $50k exceeds $25k auto/fast-lane ceiling, but easily covered by $450k balance
    inp.payment_info.amount = 50000.0
    out = harness.process_input(inp)
    assert_isolated_predicate_failure(out, "p_bank")


def test_cat_a_17_p_bank_tr03_amount_exceeds_threshold(harness):
    """Category A #17: TR-03 P_bank == False (amount exceeds fast-lane ceiling)."""
    inp = make_tr03_baseline("CAT-A-17")
    # Mutation: Amount $50k exceeds $25k auto/fast-lane ceiling, but covered by Nostro position
    inp.payment_info.amount = 50000.0
    out = harness.process_input(inp)
    assert_isolated_predicate_failure(out, "p_bank")


def test_cat_a_18_p_bank_tr04_amount_exceeds_threshold(harness):
    """Category A #18: TR-04 P_bank == False (amount exceeds fast-lane ceiling)."""
    inp = make_tr04_baseline("CAT-A-18")
    # Mutation: Amount $50k exceeds $25k auto/fast-lane ceiling
    inp.payment_info.amount = 50000.0
    out = harness.process_input(inp)
    assert_isolated_predicate_failure(out, "p_bank")


# --- GROUP 7: C_comp (Compliance Screening Clearance) Isolated Tests ---

def test_cat_a_19_c_comp_tr02_sanctions_match(harness):
    """Category A #19: TR-02 C_comp == False (sanctions match on debtor/creditor)."""
    inp = make_tr02_baseline("CAT-A-19")
    # Mutation: Flag OFAC sanctions hit
    inp.bank_supplied_evidence["ofac_sanctions_hit"] = True
    out = harness.process_input(inp)
    assert_isolated_predicate_failure(out, "c_comp")


def test_cat_a_20_c_comp_tr06_prohibited_corridor(harness):
    """Category A #20: TR-06 C_comp == False (prohibited corridor flagged)."""
    inp = make_tr06_baseline("CAT-A-20")
    # Mutation: Flag prohibited corridor
    inp.bank_supplied_evidence["corridor_prohibited"] = True
    out = harness.process_input(inp)
    assert_isolated_predicate_failure(out, "c_comp")


def test_cat_a_21_c_comp_tr07_sanctions_match(harness):
    """Category A #21: TR-07 C_comp == False (OFAC watchlist hit)."""
    inp = make_tr07_baseline("CAT-A-21")
    # Mutation: Flag OFAC sanctions hit
    inp.bank_supplied_evidence["ofac_sanctions_hit"] = True
    out = harness.process_input(inp)
    assert_isolated_predicate_failure(out, "c_comp")


# --- GROUP 8: X_pre (Pre-Execution Locks & Rail Status) Isolated Tests ---

def test_cat_a_22_x_pre_tr02_idempotency_collision(harness):
    """Category A #22: TR-02 X_pre == False (idempotency lock collision)."""
    inp = make_tr02_baseline("CAT-A-22")
    # Mutation: Flag idempotency locked
    inp.bank_supplied_evidence["idempotency_locked"] = True
    out = harness.process_input(inp)
    assert_isolated_predicate_failure(out, "x_pre")


def test_cat_a_23_x_pre_tr06_idempotency_collision(harness):
    """Category A #23: TR-06 X_pre == False (idempotency lock collision)."""
    inp = make_tr06_baseline("CAT-A-23")
    # Mutation: Flag idempotency locked
    inp.bank_supplied_evidence["idempotency_locked"] = True
    out = harness.process_input(inp)
    assert_isolated_predicate_failure(out, "x_pre")


def test_cat_a_24_x_pre_tr07_idempotency_collision(harness):
    """Category A #24: TR-07 X_pre == False (idempotency lock collision)."""
    inp = make_tr07_baseline("CAT-A-24")
    # Mutation: Flag idempotency locked
    inp.bank_supplied_evidence["idempotency_locked"] = True
    out = harness.process_input(inp)
    assert_isolated_predicate_failure(out, "x_pre")


# ==============================================================================
# CATEGORY B: COMPOUND ADVERSARIAL & INVARIANT TESTS
# ==============================================================================

def test_cat_b_01_tr08_zero_auto_stp_invariant(harness):
    """Category B #1 (MANDATORY INVARIANT): TR-08 Credit Exposure Breach MUST NEVER achieve autonomous STP."""
    inp = CanonicalE2EInput(
        exception_id="CAT-B-01-TR08",
        profile_id="TR-08",
        domain="CLIENT_TREASURY",
        error_code="ERR_CREDIT_EXPOSURE_BREACH",
        error_message="Credit exposure breach must require dual-auth",
        payment_info=E2EPaymentInfo(
            payment_id="PMT-TR08-INV",
            uetr="UETR-TR08-INV",
            amount=5000.0,  # Below standard $10k autonomous ceiling
            currency="USD",
            clearing_rail="FEDWIRE",
            debtor_name="CPTY-CORP-ALPHA",
            debtor_account="ACCT-CORP-USD-001",
            debtor_agent_bic="ALPHUS33XXX",
        ),
        bank_supplied_evidence={
            "counterparty_id": "CPTY-CORP-ALPHA",
            "counterparty_exposure_record": {
                "counterparty_id": "CPTY-CORP-ALPHA",
                "total_facility_limit": 10000000.0,
                "current_drawn_exposure": 9500000.0,
                "currency": "USD",
                "is_breached": False,
                "is_authoritative": True,
            },
            "credit_facility_agreement": {
                "facility_id": "FAC-ALPHA-01",
                "borrower_entity": "CPTY-CORP-ALPHA",
            },
            "enterprise_risk_rating": {
                "counterparty_id": "CPTY-CORP-ALPHA",
                "rating": "AA",
            },
        },
    )
    out = harness.process_input(inp)
    assert out.stp_eligible is False
    assert out.predicate_breakdown.p_bank is False  # Policy blocks auto STP for TR-08
    assert out.hitl_required is True
    assert out.approval_requirement == "MAKER_CHECKER_DUAL_AUTH"
    assert out.execution_owner == "BANK"


def test_cat_b_02_compound_missing_evidence_and_deficit(harness):
    """Category B #2: Compound failure of E_suff and R_det concurrently."""
    inp = CanonicalE2EInput(
        exception_id="CAT-B-02-COMPOUND",
        profile_id="TR-02",
        domain="CLIENT_TREASURY",
        error_code="ERR_INSUFFICIENT_FUNDS",
        error_message="Compound missing evidence and deficit",
        payment_info=E2EPaymentInfo(
            payment_id="PMT-COMPOUND-01",
            uetr="UETR-COMPOUND-01",
            amount=5000.0,
            currency="USD",
            clearing_rail="FEDWIRE",
            debtor_name="Apex Corp",
            debtor_account="ACCT-DEFICIT-USD-002",
            debtor_agent_bic="CHASUS33XXX",
        ),
        bank_supplied_evidence={},  # Missing all mandatory evidence
    )
    out = harness.process_input(inp)
    assert out.stp_eligible is False
    assert out.predicate_breakdown.e_suff is False
    assert out.predicate_breakdown.r_det is False  # Both co-failed


def test_cat_b_03_compound_policy_and_unverified_authority(harness):
    """Category B #3: Compound failure of P_bank and V_auth concurrently."""
    inp = make_tr02_baseline("CAT-B-03")
    # Compound mutations: High value ($50k > $25k) AND unverified authority
    inp.payment_info.amount = 50000.0
    inp.bank_supplied_evidence["simulate_authority_unavailable"] = True
    out = harness.process_input(inp)
    assert out.stp_eligible is False
    assert out.predicate_breakdown.p_bank is False
    assert out.predicate_breakdown.v_auth is False
