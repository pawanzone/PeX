import React, { useState } from "react";
import { initiatePayment } from "../../services/api";
import { PlusCircle, CheckCircle2, Shield, ArrowRight, Zap, RefreshCw } from "lucide-react";

interface Props {
  onSuccess: (caseId: string) => void;
}

export const PaymentIntake: React.FC<Props> = ({ onSuccess }) => {
  const [clientRef, setClientRef] = useState("CLIENT-REF-2026-001");
  const [rail, setRail] = useState("SWIFT / CBPR+");
  const [profile, setProfile] = useState("INVALID_IBAN");
  const [debtorName, setDebtorName] = useState("Acme Global Holdings");
  const [creditorName, setCreditorName] = useState("Nordhavn Components A/S");
  const [amount, setAmount] = useState(250000);
  const [currency, setCurrency] = useState("USD");
  const [country, setCountry] = useState("DK");
  const [reason, setReason] = useState("Beneficiary account identifier failed validation against the receiving bank profile.");
  const [correctedIban, setCorrectedIban] = useState("GB82 WEST 1234 5698 7654 32");
  
  const [loading, setLoading] = useState(false);
  const [submittedCaseId, setSubmittedCaseId] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await initiatePayment({
        client_reference: clientRef,
        payment_rail: rail,
        exception_profile: profile,
        debtor_name: debtorName,
        creditor_name: creditorName,
        amount: Number(amount),
        currency,
        beneficiary_country: country,
        exception_reason: reason,
        corrected_beneficiary_iban: correctedIban,
      });
      if (res.success) {
        setSubmittedCaseId(res.case_id);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Payment Intake &amp; Origination Simulator</h1>
        <p className="text-xs text-slate-500 mt-1">Submit synthetic payment exceptions through the canonical PeX intake contract</p>
      </div>

      {submittedCaseId ? (
        <div className="bg-white p-8 rounded-2xl border border-emerald-200 shadow-sm text-center space-y-4 max-w-xl mx-auto">
          <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-7 h-7" />
          </div>
          <h2 className="text-lg font-bold text-slate-900">Payment Accepted Into PeX Lifecycle</h2>
          <p className="text-xs text-slate-600">
            Case <span className="font-mono font-bold text-sky-700">{submittedCaseId}</span> has passed intake schema validation, PII tokenization, and initial AI evidence planning.
          </p>
          <div className="pt-2 flex justify-center space-x-3">
            <button
              onClick={() => onSuccess(submittedCaseId)}
              className="px-5 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all"
            >
              <span>View Case in Approvals</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => setSubmittedCaseId(null)}
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition-all"
            >
              Submit Another
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <form onSubmit={handleSubmit} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm lg:col-span-2 space-y-5">
            <h3 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-3">Payment Instruction Envelope</h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">CLIENT PAYMENT REFERENCE</label>
                <input
                  type="text"
                  value={clientRef}
                  onChange={(e) => setClientRef(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg font-mono"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">PAYMENT RAIL</label>
                <select
                  value={rail}
                  onChange={(e) => setRail(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg"
                >
                  <option value="SWIFT / CBPR+">SWIFT / CBPR+</option>
                  <option value="ISO 20022 pacs.008">ISO 20022 pacs.008</option>
                  <option value="Fedwire MQ">Fedwire MQ</option>
                  <option value="SEPA Credit Transfer">SEPA Credit Transfer</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">EXCEPTION PROFILE</label>
                <select
                  value={profile}
                  onChange={(e) => setProfile(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg font-semibold text-sky-700"
                >
                  <option value="INVALID_IBAN">Invalid IBAN</option>
                  <option value="INVALID_BIC">Invalid BIC / Routing</option>
                  <option value="DUPLICATE_PAYMENT">Duplicate Payment Suspected</option>
                  <option value="SANCTIONS_SUSPECTED">Sanctions Screening Match</option>
                  <option value="KYC_EXPIRED">KYC Periodic Review Expired</option>
                  <option value="RETURNED_PAYMENT">Returned Payment (pacs.004)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">DEBTOR / ORIGINATING PARTY</label>
                <input
                  type="text"
                  value={debtorName}
                  onChange={(e) => setDebtorName(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">BENEFICIARY / RECEIVING PARTY</label>
                <input
                  type="text"
                  value={creditorName}
                  onChange={(e) => setCreditorName(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">AMOUNT</label>
                  <input
                    type="number"
                    value={amount}
                    onChange={(e) => setAmount(Number(e.target.value))}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg font-mono font-bold"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">CURRENCY</label>
                  <input
                    type="text"
                    value={currency}
                    onChange={(e) => setCurrency(e.target.value)}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg font-mono uppercase"
                    required
                  />
                </div>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">EXCEPTION REASON / ERROR NARRATIVE</label>
              <textarea
                rows={2}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg"
              />
            </div>

            <div className="bg-sky-50/70 border border-sky-200 rounded-xl p-4 space-y-2">
              <span className="text-[11px] font-bold text-sky-800 uppercase font-mono">PROFILE EVIDENCE GATE</span>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">CORRECTED BENEFICIARY IBAN (LOCAL VALIDATION)</label>
                <input
                  type="text"
                  value={correctedIban}
                  onChange={(e) => setCorrectedIban(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-white border border-sky-300 rounded-lg font-mono font-semibold text-slate-800"
                />
                <p className="text-[10px] text-slate-500 mt-1">Validated locally using ISO 7064 MOD-97 check; only tokenized value is persisted to AI reasoning context.</p>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-between">
              <span className="text-xs text-slate-500 flex items-center space-x-1.5">
                <Shield className="w-4 h-4 text-emerald-500" />
                <span>No payment-changing action occurs at intake.</span>
              </span>
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-2.5 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-bold flex items-center space-x-2 transition-all shadow-sm"
              >
                {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                <span>Accept into PeX &rarr;</span>
              </button>
            </div>
          </form>

          {/* Stepper Cards */}
          <div className="space-y-4">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
              <div className="flex items-center space-x-2 text-sky-600 font-bold text-xs font-mono">
                <span className="w-5 h-5 rounded-full bg-sky-100 flex items-center justify-center text-sky-700">1</span>
                <span>VALIDATE</span>
              </div>
              <p className="text-xs text-slate-600">Schema, mandatory fields, and duplicate payment reference checks are computed instantly at the ingestion gateway.</p>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
              <div className="flex items-center space-x-2 text-sky-600 font-bold text-xs font-mono">
                <span className="w-5 h-5 rounded-full bg-sky-100 flex items-center justify-center text-sky-700">2</span>
                <span>CLASSIFY</span>
              </div>
              <p className="text-xs text-slate-600">Exception profile, triage queue, SLA due timestamp, and dynamic evidence collection plan are assigned.</p>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
              <div className="flex items-center space-x-2 text-sky-600 font-bold text-xs font-mono">
                <span className="w-5 h-5 rounded-full bg-sky-100 flex items-center justify-center text-sky-700">3</span>
                <span>GOVERN</span>
              </div>
              <p className="text-xs text-slate-600">Case enters tokenized investigation before any human repair authorization. External rails remain locked.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
