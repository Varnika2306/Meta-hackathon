"""
Synthetic Legal Contracts
- Task 1 (Easy): NDA with 5 key issues
- Task 2 (Medium): SLA with 8 issues  
- Task 3 (Hard): M&A Agreement with 10 complex issues
"""

from typing import List, Dict, Any


# ============================================================================
# TASK 1: NDA CLAUSE IDENTIFICATION (EASY)
# ============================================================================

NDA_CONTRACT = """
MUTUAL NON-DISCLOSURE AGREEMENT

This Mutual Non-Disclosure Agreement ("Agreement") is entered into as of March 1, 2026,
between TechCorp Inc., a Delaware corporation ("Discloser"), and InnovateLabs LLC, a 
California limited liability company ("Recipient").

WHEREAS, the parties wish to discuss potential business opportunities and desire to 
protect confidential information shared during such discussions.

1. CONFIDENTIAL INFORMATION
"Confidential Information" means any non-public technical, business, or financial information 
disclosed by Discloser to Recipient, including but not limited to source code, algorithms, 
customer lists, pricing information, and product roadmaps.

2. NON-COMPETE OBLIGATION
For a period of FIVE (5) YEARS from the date of disclosure, Recipient agrees to refrain from 
engaging, directly or indirectly, in any business that competes with Discloser's business 
activities ANYWHERE IN THE WORLD. This includes developing competing products, services, or 
technologies, or working for any competitor entity.

3. INTELLECTUAL PROPERTY ASSIGNMENT
Recipient hereby assigns ALL RIGHT, TITLE, AND INTEREST in any intellectual property, inventions, 
discoveries, or works derived from or relating to Confidential Information to Discloser, IN PERPETUITY, 
including any improvements, modifications, or derivative works created by Recipient or its employees.

4. JURISDICTION AND GOVERNING LAW
This Agreement shall be governed by the laws of the Cayman Islands and shall be subject to the 
exclusive jurisdiction of Cayman Islands courts. Any disputes shall be resolved exclusively in 
Cayman Islands courts of competent jurisdiction.

5. TERM AND TERMINATION
This Agreement shall continue indefinitely unless terminated by mutual written consent. The 
obligations under this Agreement shall continue IN PERPETUITY, even after termination, and 
shall bind all successors and assigns.

6. REMEDIES
Recipient acknowledges that breach of this Agreement will cause irreparable harm for which 
monetary damages are an insufficient remedy. Accordingly, Discloser shall be entitled to seek 
equitable relief, including specific performance and injunctive relief, in addition to any 
other remedies available at law or in equity.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first written above.

Discloser: TechCorp Inc.
By: _______________________
Title: _____________________

Recipient: InnovateLabs LLC
By: _______________________
Title: _____________________
"""

NDA_GROUND_TRUTH = [
    {
        "id": 1,
        "title": "Overbroad Non-Compete Scope",
        "severity": "critical",
        "keywords": ["five (5) years", "anywhere in the world", "non-compete", "refrain from engaging"],
        "description": "5-year worldwide non-compete is extremely overbroad. Market standard is 1-2 years, limited geography.",
        "clause_reference": "Section 2",
        "weight": 0.25
    },
    {
        "id": 2,
        "title": "Blanket Perpetual IP Assignment",
        "severity": "critical",
        "keywords": ["all right, title, and interest", "in perpetuity", "intellectual property", "assignment"],
        "description": "Assignment of ALL IP in perpetuity is dangerous. Should be limited to derivative works only.",
        "clause_reference": "Section 3",
        "weight": 0.25
    },
    {
        "id": 3,
        "title": "Perpetual Term and Obligations",
        "severity": "high",
        "keywords": ["continue indefinitely", "in perpetuity", "continue in perpetuity"],
        "description": "Indefinite term with perpetual obligations. Should have reasonable sunset clause (2-3 years).",
        "clause_reference": "Section 5",
        "weight": 0.15
    },
    {
        "id": 4,
        "title": "Unfavorable Jurisdiction",
        "severity": "high",
        "keywords": ["cayman islands", "governing law", "exclusive jurisdiction"],
        "description": "Cayman Islands jurisdiction is unusual and unfavorable. Negotiate for neutral jurisdiction or home state.",
        "clause_reference": "Section 4",
        "weight": 0.20
    },
    {
        "id": 5,
        "title": "Unbalanced Remedies Clause",
        "severity": "medium",
        "keywords": ["irreparable harm", "equitable relief", "injunctive relief"],
        "description": "Acknowledges irreparable harm too readily. Should add mutual consent requirement for injunctions.",
        "clause_reference": "Section 6",
        "weight": 0.15
    }
]


# ============================================================================
# TASK 2: SLA CONTRACT REVIEW (MEDIUM)
# ============================================================================

SLA_CONTRACT = """
SERVICE LEVEL AGREEMENT (SLA)
Between CloudServe Inc. ("Provider") and EnterpriseClient Corp. ("Customer")

Effective Date: April 1, 2026
Term: 3 years

1. SERVICE DESCRIPTION
Provider agrees to provide cloud infrastructure services including compute, storage, and 
networking resources as specified in the attached Schedule A.

2. SERVICE LEVEL OBJECTIVES
Provider shall maintain the following service levels:
- Availability: The services shall be available during normal business hours (9 AM - 5 PM EST)
- Response Time: Provider will respond to support tickets within 2 business days
- Uptime: Services are maintained to the best of Provider's ability

3. CREDITS AND LIABILITY CAPS
If Provider fails to meet service level objectives, Customer may be eligible for service 
credits not to exceed $500 per month. Provider's total liability under this agreement shall 
not exceed $500 in aggregate.

4. INCIDENT RESPONSE
Upon detection of an incident, Provider shall notify Customer within "a reasonable timeframe" 
and work toward resolution. No specific timelines are established.

5. TERMINATION
Customer may terminate this agreement with 12 months written notice. Provider may terminate 
with 30 days written notice. Upon termination, all data will be deleted after 30 days.

6. SERVICE UPDATES AND MAINTENANCE
Provider may perform maintenance at any time without advance notice. Provider shall not be 
liable for service disruptions due to maintenance activities.

7. AUDIT AND COMPLIANCE
Provider does not commit to any specific audit frequency or compliance certifications. 
Audit requests will be honored at Provider's discretion.

8. BREACH NOTIFICATION
Provider shall notify Customer of data breaches "when discovered." No specific notification 
timeline is guaranteed.

IN WITNESS WHEREOF:
Provider: CloudServe Inc. _______  Customer: EnterpriseClient Corp. _______
"""

SLA_GROUND_TRUTH = [
    {
        "id": 1,
        "title": "No Numeric Uptime SLA",
        "severity": "critical",
        "keywords": ["uptime", "best of ability", "no specific", "objectives"],
        "description": "Vague uptime commitment ('best of ability'). Need 99.5% uptime + clear measurement.",
        "clause_reference": "Section 2",
        "weight": 0.15
    },
    {
        "id": 2,
        "title": "Liability Cap Too Low",
        "severity": "critical",
        "keywords": ["$500", "liability", "caps", "not exceed"],
        "description": "$500 liability cap is inadequate for enterprise services. Should be tied to monthly fees.",
        "clause_reference": "Section 3",
        "weight": 0.15
    },
    {
        "id": 3,
        "title": "Undefined Incident Timelines",
        "severity": "high",
        "keywords": ["reasonable timeframe", "no specific timelines", "incident"],
        "description": "'Reasonable timeframe' is vague. Need 1-hour response, 4-hour mitigation SLAs.",
        "clause_reference": "Section 4",
        "weight": 0.12
    },
    {
        "id": 4,
        "title": "Asymmetric Termination Rights",
        "severity": "high",
        "keywords": ["12 months", "30 days", "termination", "asymmetric"],
        "description": "Customer needs 12 months to exit; Provider only 30 days. Should be symmetric or include early exit clause.",
        "clause_reference": "Section 5",
        "weight": 0.12
    },
    {
        "id": 5,
        "title": "Unilateral Maintenance Right",
        "severity": "medium",
        "keywords": ["maintenance", "any time", "without advance notice"],
        "description": "Provider can perform maintenance without notice. Need 48-hour advance notice.",
        "clause_reference": "Section 6",
        "weight": 0.10
    },
    {
        "id": 6,
        "title": "No Audit Commitments",
        "severity": "medium",
        "keywords": ["audit", "discretion", "no commit", "compliance"],
        "description": "No audit frequency or compliance certs guaranteed. Need SOC 2 Type II annual audit minimum.",
        "clause_reference": "Section 7",
        "weight": 0.10
    },
    {
        "id": 7,
        "title": "Vague Breach Notification",
        "severity": "high",
        "keywords": ["breach", "when discovered", "no specific", "notification"],
        "description": "'When discovered' is too vague. Requires 48-72 hour legal notification.",
        "clause_reference": "Section 8",
        "weight": 0.14
    },
    {
        "id": 8,
        "title": "Data Deletion Clause Issue",
        "severity": "medium",
        "keywords": ["data", "deleted", "30 days", "termination"],
        "description": "30-day data retention post-termination may not comply with GDPR/regulations. Need clear policy.",
        "clause_reference": "Section 5",
        "weight": 0.12
    }
]


# ============================================================================
# TASK 3: M&A DUE DILIGENCE ASSESSMENT (HARD)
# ============================================================================

MA_AGREEMENT = """
MERGER AND ACQUISITION AGREEMENT
Between AcquirerCorp Holdings Inc. ("Buyer") and TargetTech Solutions Ltd. ("Seller")

Date: March 15, 2026
Purchase Price: $50,000,000 USD

1. REPRESENTATIONS AND WARRANTIES
Seller represents and warrants:
(a) Seller has disclosed all pending litigation and regulatory matters known to management
(b) All tax filings have been made and Seller has no knowledge of audit issues
(c) All material contracts are disclosed; no undisclosed side agreements exist
(d) Seller has not received any notice of lien or claim against assets

2. MATERIAL ADVERSE EFFECT (MAE) CARVE-OUTS
Buyer's obligation to close shall not be conditioned on the absence of a Material Adverse 
Effect, except for effects arising from:
- Acts of God or natural disasters
- General economic conditions affecting the industry generally
- Changes in law that affect the industry generally
- Epidemics or pandemics

3. INDEMNIFICATION CAP
Seller's indemnification obligations shall be capped at 5% of the purchase price ($2,500,000).
This cap applies to all claims, including fraud, breach of warranty, and tax matters.

4. ESCROW PROVISIONS
$10 million shall be held in escrow for 12 months to cover potential indemnification claims.
After 12 months, any remaining escrow shall be released to Seller without requirement of 
final audit or settlement of disputed claims.

5. NON-COMPETE AND EXCLUSIVITY
For 18 months post-closing, Seller shall not engage in any business activities that compete
with Buyer's operations. Additionally, Seller grants Buyer exclusive rights to use Seller's
brand and customer relationships for 18 months. No reverse termination fee applies if Buyer
terminates the transaction pre-closing.

6. TAX MATTERS
Seller shall indemnify Buyer for any tax liabilities arising from periods prior to closing.
Seller represents no tax audits are pending or anticipated. Seller has not disclosed recent
correspondence with the IRS regarding a $2.3 million assessment related to 2022 transfer pricing.

7. EMPLOYEE AND BENEFITS MATTERS
Seller represents all employee matters are in order. Seller has not disclosed that a class
action lawsuit by 47 former employees regarding wage-and-hour violations is pending in 
California Superior Court, alleging $3.2 million in damages.

8. INTELLECTUAL PROPERTY
Seller represents that it owns or has valid licenses for all IP used in the business. Seller
has not disclosed that three patent infringement claims are pending against TargetTech by
competing entities, each alleging $5 million in damages.

9. REGULATORY AND COMPLIANCE
Seller represents full compliance with all applicable regulations. Recent DOJ inquiry 
regarding potential antitrust violations related to data sharing practices has not been 
disclosed to Buyer.

10. REVERSE TERMINATION FEE
If Buyer terminates this agreement for any reason (including discovery of material 
information), there is no reverse termination fee or expense reimbursement obligation.

IN WITNESS WHEREOF:
Buyer: AcquirerCorp Holdings Inc. _______   Seller: TargetTech Solutions Ltd. _______
"""

MA_GROUND_TRUTH = [
    {
        "id": 1,
        "title": "Undisclosed Tax Assessment",
        "severity": "critical",
        "keywords": ["irs", "$2.3 million", "assessment", "transfer pricing", "not disclosed"],
        "description": "Seller omitted $2.3M IRS assessment from tax reps. Material adverse change.",
        "clause_reference": "Section 6",
        "weight": 0.12
    },
    {
        "id": 2,
        "title": "Hidden Employee Litigation",
        "severity": "critical",
        "keywords": ["class action", "wage-and-hour", "47 former employees", "$3.2 million", "not disclosed"],
        "description": "Seller concealed pending class action by 47 employees for $3.2M wage claims.",
        "clause_reference": "Section 7",
        "weight": 0.11
    },
    {
        "id": 3,
        "title": "Undisclosed Patent Infringement Claims",
        "severity": "high",
        "keywords": ["patent", "infringement", "three", "$5 million", "competing entities"],
        "description": "Three pending patent claims ($5M each) not disclosed. Major IP liability.",
        "clause_reference": "Section 8",
        "weight": 0.10
    },
    {
        "id": 4,
        "title": "Overbroad MAE Carve-Outs",
        "severity": "high",
        "keywords": ["material adverse effect", "carve-out", "general economic", "industry generally"],
        "description": "MAE carve-outs for 'general economic conditions' and 'changes in law' are too broad.",
        "clause_reference": "Section 2",
        "weight": 0.10
    },
    {
        "id": 5,
        "title": "Low Indemnification Cap",
        "severity": "high",
        "keywords": ["indemnification", "cap", "5%", "$2,500,000", "fraud"],
        "description": "5% cap applies even to fraud. Cap should exclude fraud and fundamental reps.",
        "clause_reference": "Section 3",
        "weight": 0.10
    },
    {
        "id": 6,
        "title": "Asymmetric Exclusivity and Non-Compete",
        "severity": "medium",
        "keywords": ["18 months", "non-compete", "exclusivity", "brand", "customer relationships"],
        "description": "18-month non-compete + exclusive brand/customer use is very restrictive; imbalanced.",
        "clause_reference": "Section 5",
        "weight": 0.09
    },
    {
        "id": 7,
        "title": "No Reverse Termination Fee",
        "severity": "medium",
        "keywords": ["reverse termination", "fee", "buyer terminates", "pre-closing", "no"],
        "description": "Buyer can terminate for discovered issues without paying Seller's costs. Imbalanced.",
        "clause_reference": "Section 10",
        "weight": 0.09
    },
    {
        "id": 8,
        "title": "Short Escrow Release Timeline",
        "severity": "medium",
        "keywords": ["escrow", "12 months", "release", "without requirement"],
        "description": "Escrow released after 12 months without audit completion. Standard is 18-24 months.",
        "clause_reference": "Section 4",
        "weight": 0.09
    },
    {
        "id": 9,
        "title": "Undisclosed DOJ Antitrust Inquiry",
        "severity": "high",
        "keywords": ["doj", "antitrust", "inquiry", "data sharing", "not disclosed"],
        "description": "Ongoing DOJ antitrust inquiry about data sharing practices not mentioned.",
        "clause_reference": "Section 9",
        "weight": 0.10
    },
    {
        "id": 10,
        "title": "Broad Seller Indemnity for Pre-Close Taxes",
        "severity": "medium",
        "keywords": ["tax liabilities", "periods prior", "indemnify", "unlimited"],
        "description": "Seller indemnifies ALL pre-close tax matters without cap or survival limit.",
        "clause_reference": "Section 6",
        "weight": 0.09
    }
]


# ============================================================================
# TASK REGISTRY
# ============================================================================

TASK_DATA = {
    "clause_id": {
        "name": "NDA Clause Identification",
        "difficulty": 1,
        "contract": NDA_CONTRACT,
        "ground_truth": NDA_GROUND_TRUTH,
        "instruction": "You are a legal analyst reviewing a Mutual Non-Disclosure Agreement (NDA). "
                      "Carefully read the contract and identify any risky, overbroad, or unfavorable clauses "
                      "that a company should negotiate. Look for overly broad non-compete scope, perpetual "
                      "obligations, unfavorable jurisdiction, and unbalanced terms. Provide a detailed analysis "
                      "with specific clause references and remediation suggestions.",
        "max_steps": 3,
        "expected_issues": 5
    },
    "sla_review": {
        "name": "SLA Contract Review",
        "difficulty": 2,
        "contract": SLA_CONTRACT,
        "ground_truth": SLA_GROUND_TRUTH,
        "instruction": "You are an enterprise procurement specialist reviewing a Service Level Agreement (SLA). "
                      "This contract has multiple defects that could expose the company to risk. Carefully analyze "
                      "each section and identify: missing or vague SLAs, inadequate liability caps, undefined incident "
                      "response timelines, asymmetric termination rights, and compliance gaps. Each issue should be "
                      "clearly documented with the section reference and recommended changes.",
        "max_steps": 4,
        "expected_issues": 8
    },
    "ma_assessment": {
        "name": "M&A Due Diligence Risk Assessment",
        "difficulty": 3,
        "contract": MA_AGREEMENT,
        "ground_truth": MA_GROUND_TRUTH,
        "instruction": "You are a senior deal lawyer conducting M&A due diligence on a $50M acquisition. "
                      "This purchase agreement contains multiple hidden risks and undisclosed liabilities that could "
                      "derail the deal or expose the buyer to significant losses. Conduct a comprehensive risk assessment "
                      "covering: representations and warranties gaps, hidden litigation and regulatory matters, intellectual "
                      "property risks, tax exposure, employee/labor issues, and deal structure vulnerabilities. Rate overall "
                      "risk level (low/medium/high/critical) and provide specific, actionable recommendations.",
        "max_steps": 5,
        "expected_issues": 10
    }
}


def get_task_data(task_id: str) -> Dict[str, Any]:
    """Retrieve task configuration by ID"""
    return TASK_DATA.get(task_id)


def list_tasks() -> Dict[str, Dict[str, Any]]:
    """List all available tasks"""
    return {
        task_id: {
            "name": data["name"],
            "difficulty": data["difficulty"],
            "expected_issues": data["expected_issues"],
            "max_steps": data["max_steps"]
        }
        for task_id, data in TASK_DATA.items()
    }
