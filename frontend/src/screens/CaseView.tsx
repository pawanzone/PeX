import React from "react";
import { CasePage } from "./case/CasePage";

/** Case page (worklist context). Variant-driven: see screens/case/CasePage.tsx. Designs 04-07, 12. */
export const CaseView: React.FC<{ id?: string }> = ({ id }) => (id ? <CasePage id={id} context="worklist" /> : null);
