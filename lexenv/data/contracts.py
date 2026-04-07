"""
Synthetic legal contracts and ground-truth issues for LexEnv.

Contains three contracts of increasing difficulty:
  1. NDA (Easy)       — 5 issues, max 3 steps
  2. SLA (Medium)     — 8 issues, max 4 steps
  3. M&A (Hard)       — 10 issues, max 5 steps

Each contract has realistic legal language with deliberately
planted risky/problematic clauses for the agent to identify.
"""

from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Issue definition helper
# ---------------------------------------------------------------------------

def _issue(
    issue_id: str,
    keywords: List[str],
    weight: float,
    description: str,
    expected_risk: str = "high",
) -> Dict[str, Any]:
    """Create a ground-truth issue dict."""
    return {
        "id": issue_id,
        "keywords": keywords,
        "weight": weight,
        "description": description,
        "expected_risk": expected_risk,
    }


# ═══════════════════════════════════════════════════════════════════════════
# TASK 1 — NDA (Non-Disclosure Agreement)  ·  Easy  ·  5 issues
# ═══════════════════════════════════════════════════════════════════════════

NDA_CONTRACT = """
MUTUAL NON-DISCLOSURE AGREEMENT

This Mutual Non-Disclosure Agreement ("Agreement") is entered into as of
January 15, 2025, by and between TechVenture Corp., a Delaware corporation
("Discloser"), and InnoStart LLC, a California limited liability company
("Recipient").

1. DEFINITION OF CONFIDENTIAL INFORMATION
"Confidential Information" shall mean any and all information, whether
written, oral, electronic, or visual, disclosed by either party to the
other, including but not limited to trade secrets, business plans, financial
data, customer lists, technical specifications, source code, algorithms,
marketing strategies, employee records, and any information marked or
reasonably understood to be confidential. This definition extends to all
derivatives, analyses, compilations, studies, or other documents prepared
by the Recipient that contain, reflect, or are based upon Confidential
Information.

2. NON-COMPETE OBLIGATION
The Recipient agrees that for a period of five (5) years following the
termination of this Agreement, the Recipient shall not, directly or
indirectly, engage in, own, manage, operate, consult for, or participate
in any business that competes with the Discloser's business anywhere in
the world. This non-compete applies to all industries, sectors, and
markets in which the Discloser currently operates or plans to operate.
The Recipient acknowledges that this worldwide scope and five-year duration
are reasonable given the nature of the Confidential Information disclosed.

3. INTELLECTUAL PROPERTY ASSIGNMENT
All inventions, discoveries, improvements, works of authorship, designs,
formulas, and ideas, whether or not patentable, copyrightable, or
protectable as trade secrets, that are conceived, developed, or reduced
to practice by the Recipient during or as a result of access to
Confidential Information, shall be the sole and exclusive property of the
Discloser. The Recipient hereby irrevocably assigns, transfers, and
conveys to the Discloser all right, title, and interest in and to such
intellectual property, including all patent rights, copyrights, trade
secret rights, and any other intellectual property rights therein, without
limitation or additional compensation. This assignment extends to all work
performed by the Recipient, regardless of whether it was developed using
Confidential Information.

4. TERM AND DURATION
This Agreement shall remain in effect in perpetuity from the Effective
Date. The confidentiality obligations contained herein shall survive
indefinitely and shall not expire. Neither party may terminate the
confidentiality obligations under any circumstances, including mutual
agreement, material breach, or change of control. The obligations shall
bind the parties, their successors, heirs, and assigns forever.

5. DISPUTE RESOLUTION AND GOVERNING LAW
This Agreement shall be governed by and construed in accordance with the
laws of the Cayman Islands, without regard to its conflict of laws
principles. Any disputes arising under or in connection with this Agreement
shall be resolved exclusively in the courts of the Cayman Islands. The
Recipient irrevocably waives any right to challenge jurisdiction or venue.
The Recipient further agrees to bear all costs of litigation, including
the Discloser's reasonable attorney's fees, regardless of the outcome.

6. UNILATERAL AMENDMENT
The Discloser reserves the right to modify, amend, or supplement any
provision of this Agreement at any time, at its sole discretion, by
providing written notice to the Recipient. Such modifications shall take
effect immediately upon delivery of notice. The Recipient's continued
access to or use of Confidential Information after such notice shall
constitute acceptance of the amended terms. The Recipient waives any
right to object to or negotiate such modifications.

7. GENERAL PROVISIONS
This Agreement constitutes the entire agreement between the parties with
respect to the subject matter hereof. All notices shall be in writing.
If any provision is found unenforceable, the remaining provisions shall
continue in full force and effect.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the
date first written above.
""".strip()

NDA_ISSUES = [
    _issue(
        "overbroad_non_compete",
        [
            "non-compete", "non compete", "five years", "5 years", "5-year",
            "worldwide", "anywhere in the world", "all industries",
            "overbroad", "unreasonable scope", "anticompetitive",
        ],
        0.25,
        "The non-compete clause is overbroad: 5-year duration with worldwide "
        "scope across all industries. Most jurisdictions would find this "
        "unenforceable due to excessive geographic and temporal scope.",
        "high",
    ),
    _issue(
        "blanket_ip_assignment",
        [
            "ip assignment", "intellectual property assignment",
            "blanket assignment", "all inventions", "irrevocably assigns",
            "sole and exclusive property", "without limitation",
            "regardless of whether", "all work performed",
        ],
        0.25,
        "Blanket IP assignment clause transfers ALL inventions to the "
        "Discloser, even those not developed using Confidential Information. "
        "This is overly broad and may capture pre-existing IP.",
        "high",
    ),
    _issue(
        "perpetual_term",
        [
            "perpetuity", "perpetual", "indefinitely", "survive indefinitely",
            "never expire", "forever", "no termination",
            "shall not expire", "cannot terminate",
        ],
        0.20,
        "The agreement has a perpetual term with no termination mechanism. "
        "Confidentiality obligations lasting forever are unusual and "
        "potentially unenforceable. Standard NDAs have 2-5 year terms.",
        "high",
    ),
    _issue(
        "cayman_islands_jurisdiction",
        [
            "cayman islands", "cayman", "offshore jurisdiction",
            "waives any right to challenge jurisdiction",
            "bear all costs", "attorney's fees regardless",
        ],
        0.15,
        "Governing law is set to the Cayman Islands — an offshore jurisdiction "
        "with limited legal protections. The Recipient also waives the right "
        "to challenge jurisdiction and must pay all legal costs regardless of outcome.",
        "critical",
    ),
    _issue(
        "unilateral_amendment",
        [
            "unilateral amendment", "unilateral modification",
            "sole discretion", "modify at any time",
            "immediately upon delivery", "waives any right to object",
            "continued access constitutes acceptance",
        ],
        0.15,
        "The Discloser can unilaterally modify the agreement at any time "
        "without the Recipient's consent. Combined with the perpetual term, "
        "this creates an extremely one-sided arrangement.",
        "high",
    ),
]

NDA_DATA = {
    "task_id": "clause_id",
    "title": "NDA Clause Identification",
    "difficulty": "easy",
    "text": NDA_CONTRACT,
    "issues": NDA_ISSUES,
    "max_steps": 3,
    "expected_risk_level": "high",
    "instruction": (
        "You are a legal analyst reviewing a Non-Disclosure Agreement (NDA). "
        "Carefully read the contract and identify ALL risky, problematic, or "
        "unusual clauses. For each issue found, explain why it is problematic "
        "and what risks it poses to the Recipient. Flag each issue by its "
        "identifier and provide an overall risk assessment."
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# TASK 2 — SLA (Service Level Agreement)  ·  Medium  ·  8 issues
# ═══════════════════════════════════════════════════════════════════════════

SLA_CONTRACT = """
SERVICE LEVEL AGREEMENT

This Service Level Agreement ("SLA") is entered into effective March 1, 2025,
by and between CloudBase Systems Inc. ("Provider") and MedTech Solutions Corp.
("Customer"), governing the provision of cloud infrastructure and managed
services under Master Services Agreement No. MSA-2025-0447.

1. SERVICE DESCRIPTION
Provider shall deliver enterprise cloud hosting, data storage, application
deployment, and managed database services (collectively, the "Services") to
Customer. Services include 24/7 system monitoring, automated backups, and
disaster recovery capabilities as described in Schedule A.

2. SERVICE AVAILABILITY
Provider shall use commercially reasonable efforts to maintain high
availability of the Services. Provider targets a generally reliable service
and will endeavor to minimize downtime. In the event of service
interruptions, Provider will work diligently to restore Services in a
timely manner. No specific uptime percentage or availability metric is
guaranteed. Provider's internal monitoring systems shall be the sole
determinant of any service unavailability.

3. INCIDENT RESPONSE AND SUPPORT
Provider shall maintain a support desk accessible via email during standard
business hours (9:00 AM - 5:00 PM EST, Monday through Friday, excluding
holidays). Upon receiving an incident report, Provider will acknowledge
the incident and begin investigation. Response times and resolution
targets will be determined on a case-by-case basis depending on Provider's
assessment of severity and available resources. Provider reserves the right
to reclassify incident severity at any time.

4. LIABILITY AND INDEMNIFICATION
Provider's total aggregate liability under this Agreement, whether in
contract, tort, negligence, strict liability, or otherwise, shall not
exceed Five Hundred U.S. Dollars ($500.00) in any twelve (12) month
period. This limitation applies to all claims, losses, damages,
liabilities, costs, and expenses of any kind whatsoever, including but
not limited to direct damages, indirect damages, consequential damages,
loss of data, loss of revenue, loss of profits, and business interruption.
Customer acknowledges that this liability cap reflects the allocation of
risk between the parties and the fees paid under this Agreement.

5. TERMINATION
This Agreement shall continue for an initial term of thirty-six (36)
months from the Effective Date and shall automatically renew for successive
twelve (12) month terms unless terminated. Customer may terminate this
Agreement by providing twelve (12) months' prior written notice before the
end of the then-current term. Provider may terminate this Agreement by
providing thirty (30) days' prior written notice at any time, for any
reason or no reason. Upon termination by Provider, Customer shall have
fourteen (14) calendar days to retrieve its data, after which Provider
may delete all Customer data without further notice or liability.

6. DATA HANDLING AND SECURITY
Provider shall implement reasonable security measures to protect Customer
data. Provider does not warrant that its security measures will prevent
all unauthorized access. Provider shall not be liable for any data
breaches, unauthorized access, data loss, or corruption regardless of
cause. In the event of a security incident involving Customer data,
Provider has no obligation to notify Customer of such incident within any
specific timeframe. Provider may disclose information about security
incidents at its sole discretion.

7. SERVICE CREDITS
This Agreement does not include any service credit program. Customer
shall not be entitled to any refunds, credits, discounts, or other
financial remedies in the event of service downtime, degradation,
outages, or failure to meet any performance targets. The monthly service
fee is payable in full regardless of actual service availability or
performance.

8. FORCE MAJEURE
Neither party shall be liable for any failure or delay in performance
due to circumstances beyond its reasonable control. Force majeure events
shall include, without limitation: acts of God, natural disasters,
pandemics, government actions, internet outages, power failures, hardware
failures, software bugs, third-party service failures, cyberattacks,
employee absences, management decisions, budget constraints, resource
reallocation, changes in business priorities, or any other event that
Provider determines, in its sole discretion, to be beyond its reasonable
control.

9. DATA PORTABILITY AND MIGRATION
Upon termination or expiration of this Agreement, Provider shall have no
obligation to assist Customer with data migration or transfer. Customer
data shall be stored in Provider's proprietary format. Provider does not
guarantee data export in any standard or interoperable format. Any data
migration assistance requested by Customer shall be subject to Provider's
then-current professional services rates and availability.

10. GENERAL PROVISIONS
This Agreement constitutes the entire agreement between the parties.
Any amendments must be in writing and signed by both parties. This
Agreement shall be governed by the laws of the State of Delaware.
""".strip()

SLA_ISSUES = [
    _issue(
        "no_uptime_sla",
        [
            "no specific uptime", "no uptime guarantee", "no availability metric",
            "commercially reasonable efforts", "generally reliable",
            "no guaranteed uptime", "no sla percentage", "no 99",
            "no uptime percentage",
        ],
        0.20,
        "The SLA provides no numeric uptime guarantee (e.g., 99.9%). It only "
        "promises 'commercially reasonable efforts' and 'generally reliable' "
        "service. For enterprise/medical applications, this is unacceptable.",
        "critical",
    ),
    _issue(
        "low_liability_cap",
        [
            "$500", "five hundred", "500 dollars", "liability cap",
            "aggregate liability", "total liability", "absurdly low",
            "inadequate liability", "liability shall not exceed",
        ],
        0.15,
        "Liability is capped at $500 total per year — absurdly low for "
        "enterprise cloud services. This doesn't cover even minor data loss "
        "scenarios, let alone business interruption.",
        "critical",
    ),
    _issue(
        "undefined_incident_timelines",
        [
            "case-by-case", "no defined response time", "no resolution target",
            "undefined timeline", "no sla on response", "determined on a case",
            "depending on provider's assessment", "reclassify severity",
            "no incident sla",
        ],
        0.15,
        "Incident response and resolution timelines are completely undefined. "
        "Provider determines severity and timeline 'on a case-by-case basis' "
        "and can reclassify severity at will.",
        "high",
    ),
    _issue(
        "asymmetric_termination",
        [
            "asymmetric termination", "12 months notice", "twelve months",
            "30 days", "thirty days", "unequal termination",
            "customer 12 months", "provider 30 days",
            "for any reason or no reason",
        ],
        0.15,
        "Termination is highly asymmetric: Customer must give 12 months' "
        "notice, while Provider can terminate with only 30 days' notice "
        "for any reason. Customer gets only 14 days to retrieve data.",
        "high",
    ),
    _issue(
        "no_breach_notification",
        [
            "no obligation to notify", "no notification",
            "no breach notification", "no security notification",
            "sole discretion", "no specific timeframe",
            "not liable for data breach", "not liable for unauthorized access",
        ],
        0.10,
        "Provider has NO obligation to notify Customer of data breaches or "
        "security incidents. This likely violates HIPAA, GDPR, and other "
        "data protection regulations for a medical technology company.",
        "critical",
    ),
    _issue(
        "no_service_credits",
        [
            "no service credit", "no refund", "no credits", "no discount",
            "no financial remedy", "payable in full regardless",
            "no remedies", "no credit program",
        ],
        0.10,
        "No service credit program exists. Customer pays full price regardless "
        "of actual uptime or performance. Standard SLAs include credits for "
        "downtime exceeding the guaranteed uptime.",
        "high",
    ),
    _issue(
        "vague_force_majeure",
        [
            "vague force majeure", "overbroad force majeure",
            "budget constraints", "resource reallocation",
            "management decisions", "changes in business priorities",
            "employee absences", "sole discretion",
            "software bugs", "any other event",
        ],
        0.10,
        "Force majeure clause is absurdly broad — includes 'budget constraints', "
        "'management decisions', 'employee absences', and 'software bugs'. "
        "These are normal business operations, not force majeure events.",
        "high",
    ),
    _issue(
        "no_data_portability",
        [
            "no data portability", "proprietary format", "no data migration",
            "no export", "no standard format", "no interoperable format",
            "no obligation to assist", "professional services rates",
            "no data transfer",
        ],
        0.05,
        "No data portability or migration support. Data stored in proprietary "
        "format with no guarantee of standard export. Creates vendor lock-in.",
        "medium",
    ),
]

SLA_DATA = {
    "task_id": "sla_review",
    "title": "SLA Contract Review",
    "difficulty": "medium",
    "text": SLA_CONTRACT,
    "issues": SLA_ISSUES,
    "max_steps": 4,
    "expected_risk_level": "critical",
    "instruction": (
        "You are a legal analyst reviewing a Service Level Agreement (SLA) "
        "for a medical technology company. This is a critical contract for "
        "enterprise cloud services. Identify ALL deficiencies, risks, and "
        "problematic clauses. Pay special attention to uptime guarantees, "
        "liability limits, incident response, termination asymmetry, data "
        "breach notification, service credits, and data portability. "
        "Flag each issue and provide a comprehensive risk assessment."
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# TASK 3 — M&A Due Diligence  ·  Hard  ·  10 issues
# ═══════════════════════════════════════════════════════════════════════════

MA_CONTRACT = """
AGREEMENT AND PLAN OF MERGER

This Agreement and Plan of Merger ("Agreement") is entered into as of
February 10, 2025, by and between Apex Global Holdings Inc., a Delaware
corporation ("Acquirer"), and NovaTech Innovations Ltd., a Nevada
corporation ("Target"), and, solely for purposes of certain sections
herein, Marcus Chen, CEO and majority shareholder of Target ("Founder").

RECITALS
WHEREAS, the Board of Directors of each of the Acquirer and the Target
has approved and declared advisable the merger of Target with and into
a wholly-owned subsidiary of Acquirer (the "Merger"), upon the terms and
subject to the conditions set forth in this Agreement;

WHEREAS, the aggregate Merger Consideration shall be One Hundred Fifty
Million U.S. Dollars ($150,000,000), payable as set forth in Article III;

ARTICLE I — THE MERGER
1.1 Effective Time. The Merger shall become effective upon the filing of
a Certificate of Merger with the Secretary of State of Delaware (the
"Effective Time").

1.2 Effects of the Merger. At the Effective Time, Target shall be merged
with and into Merger Sub, with Merger Sub continuing as the surviving
entity and a wholly-owned subsidiary of Acquirer.

ARTICLE II — REPRESENTATIONS AND WARRANTIES OF TARGET
2.1 Financial Statements. Target represents that its financial statements
for the fiscal years ended December 31, 2022, 2023, and 2024, fairly
present in all material respects the financial condition, results of
operations, and cash flows of Target. Notwithstanding the foregoing,
Target acknowledges that certain adjustments may be required related to
ongoing tax audit proceedings by the Internal Revenue Service for fiscal
years 2021-2023, the results of which are currently unknown and have not
been reflected in the financial statements. Target has not disclosed the
existence of these audits to the Acquirer prior to the execution of
this Agreement.

2.2 Undisclosed Liabilities. Except as set forth in Schedule 2.2, Target
has no liabilities of any nature required to be reflected on a balance
sheet prepared in accordance with GAAP, except liabilities incurred in
the ordinary course of business. Schedule 2.2 reflects a contingent
litigation liability in the amount of approximately Two Million Three
Hundred Thousand U.S. Dollars ($2,300,000) arising from a pending
patent infringement lawsuit filed by CyberShield Technologies Inc.
This liability was classified as "remote" in prior financial statements
but has since been reclassified to "probable" by Target's outside counsel
as of January 2025.

2.3 Material Adverse Effect. "Material Adverse Effect" shall mean any
event, occurrence, or change that has had or would reasonably be expected
to have a material adverse effect on the business, financial condition,
or results of operations of Target, excluding any event arising from:
(a) changes in general economic or market conditions; (b) changes in
applicable law or accounting standards; (c) changes in the industry
in which Target operates; (d) the announcement or pendency of the
Merger; (e) any action taken by Acquirer or its affiliates; (f) changes
in geopolitical conditions, including acts of war or terrorism;
(g) pandemics or public health emergencies; (h) changes in interest
rates or currency exchange rates; (i) any failure to meet internal
projections or forecasts; or (j) any adverse change in the competitive
landscape, including the entry of new competitors or loss of market share.

ARTICLE III — MERGER CONSIDERATION AND PAYMENT
3.1 Merger Consideration. Each share of Target Common Stock issued and
outstanding immediately prior to the Effective Time shall be converted
into the right to receive a pro rata portion of the aggregate Merger
Consideration of $150,000,000. Payment shall be made 60% in cash and
40% in Acquirer common stock. The stock component shall be subject to a
24-month lock-up period during which Founder and other Target shareholders
may not sell, transfer, or otherwise dispose of Acquirer shares received.

3.2 No Reverse Termination Fee. In the event that Acquirer fails to
consummate the Merger or breaches its obligations under this Agreement,
Target shall not be entitled to any reverse termination fee, break-up
fee, or other monetary remedy. Target's sole remedy shall be specific
performance, subject to the limitations set forth in Section 8.3.

ARTICLE IV — COVENANTS
4.1 Exclusivity. From the date of this Agreement until the earlier of
(a) eighteen (18) months following the date hereof, or (b) the Effective
Time, Target and Founder shall not, and shall cause their respective
representatives not to, directly or indirectly: (i) solicit, initiate,
or encourage any Acquisition Proposal from any third party; (ii) furnish
any non-public information to any third party in connection with any
Acquisition Proposal; or (iii) enter into any agreement with respect to
any Acquisition Proposal. Acquirer shall have no corresponding exclusivity
obligation and may pursue other acquisition targets during this period.

4.2 Conduct of Business. Between the date of this Agreement and the
Effective Time, Target shall operate in the ordinary course, consistent
with past practice. Target shall not, without Acquirer's prior written
consent: issue new equity, incur indebtedness exceeding $50,000, enter
into material contracts, or make capital expenditures exceeding $25,000.

ARTICLE V — INDEMNIFICATION
5.1 Indemnification by Founder. Founder shall indemnify and hold harmless
Acquirer and its affiliates against all losses arising from any breach of
representations, warranties, or covenants by Target or Founder under this
Agreement. The indemnification cap shall be limited to 5% of the aggregate
Merger Consideration (i.e., $7,500,000).

5.2 Basket and Deductible. Acquirer shall not be entitled to indemnification
unless aggregate losses exceed $3,000,000 (the "Basket"), and the Basket
shall serve as a true deductible, meaning Acquirer may only recover losses
in excess of the Basket. However, the indemnification cap of $7,500,000
includes the Basket amount, resulting in maximum net recovery of $4,500,000.

5.3 No Representation and Warranty Insurance. The parties acknowledge that
no representation and warranty insurance ("RWI") policy has been obtained
in connection with this transaction. Founder bears full exposure for all
indemnification obligations.

ARTICLE VI — CONDITIONS TO CLOSING
6.1 Conditions to Acquirer's Obligation. The obligations of Acquirer to
consummate the Merger are subject to the satisfaction of the following
conditions: (a) the representations and warranties of Target shall be
true in all respects as of the Closing Date; and (b) Target shall have
performed all covenants in all respects. No materiality qualifiers or
"bring-down" standards apply. Minor or immaterial breaches shall entitle
Acquirer to refuse to close.

ARTICLE VII — FOUNDER RESTRICTIONS
7.1 Accelerated Vesting. In the event of a Change of Control of Acquirer
within 36 months following the Effective Time, all restricted stock units
and unvested equity awards held by Founder shall immediately vest. However,
the exercise or settlement of such awards shall be subject to Acquirer's
Board approval, which may be withheld in Acquirer's sole discretion.

ARTICLE VIII — TERMINATION
8.1 Termination Rights. This Agreement may be terminated prior to the
Effective Time by mutual written consent of the parties, or by either
party if the Merger has not been consummated by the Outside Date
(September 30, 2025).

8.2 Effect of Termination. In the event of termination, this Agreement
shall become void and of no effect, except that the confidentiality,
exclusivity (Section 4.1), and indemnification provisions shall survive
termination.

8.3 Limitation on Remedies. Target's remedies for breach by Acquirer
shall be limited to specific performance. Target explicitly waives any
right to recover monetary damages of any kind from Acquirer, including
expectation damages, reliance damages, or consequential damages.

ARTICLE IX — MISCELLANEOUS
9.1 This Agreement constitutes the entire agreement between the parties.
9.2 Governing law: State of Delaware.
9.3 Amendment requires written consent of both parties.
""".strip()

MA_ISSUES = [
    _issue(
        "undisclosed_tax_audits",
        [
            "tax audit", "irs audit", "internal revenue service",
            "not disclosed", "undisclosed", "not reflected",
            "currently unknown", "ongoing tax",
            "fiscal years 2021", "has not disclosed",
        ],
        0.12,
        "Target has undisclosed IRS tax audits for fiscal years 2021-2023 "
        "that have not been reflected in the financial statements. This is a "
        "material omission that could significantly impact valuation.",
        "critical",
    ),
    _issue(
        "hidden_liability",
        [
            "2.3 million", "$2,300,000", "2300000", "hidden liability",
            "contingent liability", "patent infringement",
            "reclassified to probable", "cybershield",
            "previously classified as remote",
        ],
        0.12,
        "A $2.3M patent infringement liability was recently reclassified from "
        "'remote' to 'probable'. This hidden liability was buried in a "
        "schedule and represents a significant undisclosed risk.",
        "critical",
    ),
    _issue(
        "overbroad_mae_carveouts",
        [
            "material adverse effect", "mae carve-out", "mae exclusion",
            "overbroad carve-out", "excluding any event",
            "changes in general economic", "loss of market share",
            "failure to meet projections", "competitive landscape",
            "ten carve-outs", "10 exclusions",
        ],
        0.10,
        "The MAE definition has 10 sweeping carve-outs including 'failure to "
        "meet internal projections' and 'adverse changes in competitive "
        "landscape'. This makes it nearly impossible for Acquirer to invoke MAE.",
        "high",
    ),
    _issue(
        "no_reverse_termination_fee",
        [
            "no reverse termination fee", "no break-up fee",
            "no breakup fee", "no monetary remedy",
            "sole remedy shall be specific performance",
            "no reverse break", "no rtf",
        ],
        0.10,
        "No reverse termination fee protects Target if Acquirer walks away. "
        "Target's only remedy is specific performance, which is difficult to "
        "enforce and provides no compensation for opportunity cost.",
        "high",
    ),
    _issue(
        "asymmetric_exclusivity",
        [
            "asymmetric exclusivity", "18 months", "eighteen months",
            "no corresponding exclusivity", "one-sided exclusivity",
            "unilateral exclusivity", "acquirer may pursue",
            "target shall not solicit",
        ],
        0.10,
        "18-month exclusivity binds only Target — Acquirer has no "
        "corresponding obligation and may pursue other acquisitions. "
        "This is unusually long and completely one-sided.",
        "high",
    ),
    _issue(
        "low_indemnification_cap",
        [
            "5% indemnification", "5 percent", "$7,500,000",
            "7.5 million", "indemnification cap", "low cap",
            "limited to 5%",
        ],
        0.10,
        "Indemnification cap of 5% ($7.5M) on a $150M deal is very low. "
        "Standard M&A deals typically have 10-15% caps. Combined with the "
        "hidden liabilities, this leaves Acquirer significantly exposed.",
        "high",
    ),
    _issue(
        "no_rwi_insurance",
        [
            "no representation and warranty insurance", "no rwi",
            "no reps and warranties insurance", "no insurance policy",
            "founder bears full exposure", "no r&w insurance",
        ],
        0.09,
        "No Representation and Warranty Insurance (RWI) policy obtained. "
        "Founder bears full indemnification exposure personally, and the "
        "low cap means Acquirer has limited recourse.",
        "high",
    ),
    _issue(
        "basket_deductible_mismatch",
        [
            "basket", "deductible", "$3,000,000", "3 million",
            "true deductible", "includes the basket",
            "net recovery", "$4,500,000", "4.5 million",
            "basket deductible mismatch",
        ],
        0.09,
        "The $3M basket is a true deductible (not a tipping basket), and the "
        "$7.5M cap includes the basket. Maximum net recovery is only $4.5M "
        "— just 3% of deal value for all breaches combined.",
        "high",
    ),
    _issue(
        "no_closing_conditions_materiality",
        [
            "no materiality qualifier", "true in all respects",
            "all respects", "no bring-down", "minor breaches",
            "immaterial breaches", "refuse to close",
            "no closing condition materiality",
        ],
        0.09,
        "Closing conditions require reps to be 'true in all respects' with "
        "no materiality qualifiers. Any minor or immaterial breach gives "
        "Acquirer the right to refuse to close — a hidden walk-away right.",
        "critical",
    ),
    _issue(
        "accelerated_vesting_illusory",
        [
            "accelerated vesting", "change of control",
            "board approval", "sole discretion",
            "withheld in acquirer's sole discretion",
            "illusory vesting", "restricted stock units",
        ],
        0.09,
        "Accelerated vesting on Change of Control is illusory — exercise "
        "requires Acquirer Board approval which 'may be withheld in sole "
        "discretion'. This effectively negates the vesting protection.",
        "high",
    ),
]

MA_DATA = {
    "task_id": "ma_due_diligence",
    "title": "M&A Due Diligence",
    "difficulty": "hard",
    "text": MA_CONTRACT,
    "issues": MA_ISSUES,
    "max_steps": 5,
    "expected_risk_level": "critical",
    "instruction": (
        "You are a senior legal analyst performing due diligence on a $150M "
        "merger agreement. This is a high-stakes transaction. Analyze the "
        "agreement thoroughly for ALL risks, hidden liabilities, asymmetric "
        "terms, inadequate protections, and problematic provisions. Pay "
        "special attention to: financial representations, undisclosed "
        "liabilities, MAE carve-outs, termination rights, exclusivity terms, "
        "indemnification structure, and closing conditions. Flag every issue "
        "with specific references to the contract language."
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# Registry — all contracts keyed by task_id
# ═══════════════════════════════════════════════════════════════════════════

CONTRACTS = {
    "clause_id": NDA_DATA,
    "sla_review": SLA_DATA,
    "ma_due_diligence": MA_DATA,
}

TASK_IDS = list(CONTRACTS.keys())


def get_contract(task_id: str) -> Dict[str, Any]:
    """Retrieve contract data by task ID.

    Args:
        task_id: One of 'clause_id', 'sla_review', 'ma_due_diligence'.

    Returns:
        Dict with keys: task_id, title, difficulty, text, issues, max_steps,
        expected_risk_level, instruction.

    Raises:
        ValueError: If task_id is not recognised.
    """
    if task_id not in CONTRACTS:
        raise ValueError(
            f"Unknown task_id '{task_id}'. Must be one of {TASK_IDS}"
        )
    return CONTRACTS[task_id]
