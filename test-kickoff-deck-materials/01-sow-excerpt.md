# STATEMENT OF WORK — EXCERPT

**Client:** Helio Medical Systems GmbH
**Engagement:** Global Commercial Experience Program — Discovery Phase
**SOW Reference:** HMS-2026-0417
**Effective:** 7 September 2026
**Duration:** 8 weeks

*(Extract only — Sections 1.1, 1.2, 1.3, 1.4 and 1.6. Commercial terms, rate
card and Section 1.5 (Change Control) omitted from this copy.)*

---

## 1.1 Background

Helio Medical Systems ("Helio") designs and manufactures minimally invasive
surgical visualization systems, with direct commercial operations in the United
States, Germany, the United Kingdom, and Japan, and a distributor network
across a further eleven markets.

Helio's commercial systems estate has grown organically over approximately
fourteen years. The core CRM is a heavily customized deployment of a legacy
platform that is no longer supported by the original vendor's current release
line. Quoting, contract administration, service dispatch and installed-base
tracking are handled across four further systems with limited integration
between them, and a material volume of commercial process is executed in
spreadsheets maintained locally by regional teams.

Helio's Executive Committee has approved a multi-year program to consolidate
the commercial estate onto a single platform. This Statement of Work covers the
Discovery phase only. Design, build and deployment phases are subject to a
separate Statement of Work to be agreed following the Discovery closeout gate.

## 1.2 Scope

### 1.2.1 In-scope business processes

The following commercial process areas ("Journeys") are in scope for Discovery.
One Journey Lead is to be nominated by Helio for each.

1. Account Management
2. Corporate Agreements
3. Standard Sales Cycle
4. Large Deals
5. Repurchase
6. Configure, Price, Quote
7. Service Contracts
8. Demonstrations & Evaluations
9. Product Support
10. Commercial Support

The following are explicitly **out of scope** for Discovery and for the MVP
release contemplated by this SOW:

- Manufacturing execution and shop-floor systems
- Regulatory submission management
- Clinical affairs and post-market surveillance
- Distributor portal for the eleven indirect markets (deferred to a later phase;
  see Assumption A-07)
- Human capital and finance systems other than the integration points named in
  1.2.2

### 1.2.2 In-scope systems and integration points

| System | Role | Integration expectation |
|---|---|---|
| SAP ERP | System of record for orders, billing, inventory | Bi-directional, near real time |
| SAP MDG | Master data governance — customer and material master | Inbound to CRM, batch |
| SAP Vistex | Rebates, chargebacks, pricing agreements | Inbound to CRM, batch |
| Analytics platform | Commercial reporting | Outbound from CRM |
| Content management | Marketing and product collateral | Outbound reference only |
| Quality management system | Complaint intake linkage | Outbound event, one way |

Middleware selection is not settled. Helio IT has an existing MuleSoft footprint
and a preference to reuse it; this is to be validated during Discovery and is
recorded as Open Question OQ-04.

## 1.3 Deliverables

| # | Deliverable | Description | Slalom responsibility | Helio responsibility | Responsibility area |
|---|---|---|---|---|---|
| 1 | Project Schedule | Develop the project plan outlining the entire program, including workstreams, phases and key milestones. *Format: presentation* | Draft; Update/Revise | Provide input | Project Management |
| 2 | Project Charter | Presentation outlining the vision statement, mission and desired outcomes for the project, roles, responsibilities, timelines and success criteria. *Format: presentation* | Jointly develop | Jointly develop; Review and sign-off | Project Management |
| 3 | Program Governance | Establish program governance committees, processes, change control plan, operational procedures and team cadences. *Format: scheduled meetings, status reports, project templates* | Jointly develop | Jointly develop; Review and sign-off | Project Management |
| 4 | Future State Process Flows | Description of all future state business processes and actors/groups to be implemented within the application. One process flow per MVP business process identified in 1.2.1. *Format: diagram document* | Develop | Provide input; Review and sign-off | Business |
| 5 | Product Backlog and Business Requirements | Defines user expectations in a format mutually understandable by the business and at a level of detail the delivery team can build toward. *Format: PMO toolkit* | Draft; Update/Revise | Provide input | Business + IT |
| 6 | Implementation Roadmap & Release Plan | Sequence of implementation phases, proposed future state architecture, and prioritized user stories required for a first MVP release. Includes updated release plan and timelines, solution delivery by country, sprint plan and structure, known risks and gap analysis. *Format: presentation* | Develop | Provide input; Review and sign-off | Business + IT |
| 7 | High-Level Technical Design | Description of high-level system components and business processes required to implement requirements, including object model, key integrations, data management, recommended technologies and other design considerations. *Format: presentation* | Develop | Review and sign-off | Business + IT |
| 8 | Data Migration Strategy | Approach and sequence of steps for data to be migrated from current systems. *Format: document* | Develop | Provide input; Review and sign-off | IT |
| 9 | Data Integration Strategy | Strategy for exchange of data between the platform and Helio's commercial enterprise systems per 1.2.2. Includes data mapping, approach/method/tools, frequency, triggering events and transformations required. *Format: document* | Develop | Provide input; Review and sign-off | IT |
| 10 | User Experience Prototype | Visual depiction of key user flows and experiences targeted for the application, usable to elicit business and technical requirements. Up to eight high-fidelity screen mock-ups. *Format: presentation* | Develop | Provide input; Review and sign-off | Business |
| 11 | Stakeholder Personas | Visual representation of the types of people within key stakeholder groups to target during implementation, based on the use cases. Up to six personas. *Format: presentation* | Develop | Provide input; Review and sign-off | Business + IT |
| 12 | High Level Impact Assessment and Change Management Strategy | Summary of anticipated impacts to people, process, technology and data, with key activities required to enable readiness, adoption and performance. Includes approach to engagement and communication, ongoing impact and readiness tracking, and capability/behavior change. *Format: presentation or document* | Jointly develop | Jointly develop; Review and sign-off | Business + IT |

## 1.4 Assumptions

- **A-01** — Helio will nominate one Journey Lead per in-scope process area
  (1.2.1) prior to the commencement of Business Alignment Workshops, and those
  individuals will be available for the full duration of their Journey's
  workshop sessions.
- **A-02** — Discovery is conducted remotely. Two on-site weeks may be
  substituted at Helio's request subject to change control and travel cost
  recovery.
- **A-03** — All workshops are conducted in English. Translation services, if
  required for regional participants, are provided by Helio.
- **A-04** — Helio provides read access to current-state systems, including a
  representative data extract, no later than the end of Week 1. Delay to this
  access is a schedule risk borne by Helio.
- **A-05** — The MVP market scope is the United States and the United Kingdom.
  Germany and Japan are addressed in the Implementation Roadmap but are not
  detailed to requirement level within this phase.
- **A-06** — Platform licensing is procured by Helio directly. Slalom makes
  recommendations but does not transact licences.
- **A-07** — The distributor portal is out of scope for Discovery. The
  Implementation Roadmap will note it as a candidate for a later release but
  will not size it.
- **A-08** — Helio's existing middleware may be reused. If Discovery concludes a
  different integration approach is required, the resulting effort change is
  handled under change control.

## 1.6 Client responsibilities

Helio will:

- Provide a single point of accountability for scope decisions (the Executive
  Sponsor, Business).
- Convene the Steering Committee monthly for the duration of the engagement.
- Make subject-matter experts available for scheduled workshop sessions, with a
  minimum of five working days' notice of any substitution.
- Review and provide consolidated feedback on each deliverable within five
  working days of receipt. Deliverables not returned within ten working days are
  deemed accepted.
- Own internal communications to affected commercial and service populations.
