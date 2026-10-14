# Specialist layer outlines

Status: Proposed definitions for review; not yet accepted model specifications.

Revised: September 28, 2026.

Original source/access notes reviewed September 26, 2026; biotech source additions reviewed September 27, 2026. These are proposed collection routes, not claims of verified coverage. See [Specialist data collection plan](specialist_data_collection_plan.md) for dataset IDs, priorities, access constraints, and implementation steps.

## For ALL

**Decision question:** Does this product address an underserved application, or compete in an already crowded market—and how does that differ by geography?

**Assess:**

- How is the sector performing relative to the S&P 500, Dow Jones Industrial Average, Nasdaq and relevant local-market benchmarks? Use suitable unleveraged sector ETFs as proxies, with dated holdings and explicit geographic exposure.
- How crowded is the application in each market? Compare supplier counts, deployments, procurement activity and installed capacity against a customer-demand denominator. Separate company headquarters from production and deployment locations.

**Programmatic data sources and thoughts — C01–C03, C12:** Use [EODHD APIs](https://eodhd.com/financial-apis/quick-start-with-our-financial-data-apis) for licensed daily prices, corporate actions and available fundamentals; issuer websites for ETF holdings; and [SEC submissions/XBRL](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) for financial evidence. Compute relative returns, drawdowns and valuation comparisons with dated inputs. For regional crowding, combine procurement records, disclosed sites and [IFR statistics](https://ifr.org/worldrobotics?id=about-ifr) or [SEMI market intelligence](https://www.semi.org/en/products-services/market-intelligence), subject to report licenses. Supplier counts and news counts are proxies, not market share; country coverage will be uneven.

## Biotech

Evaluate at product × indication × treatment line × geography × as-of date, with explicit trial, comparator, institution and person identities. Aggregate to the company using dated ownership and economic rights; do not transfer evidence between unrelated assets. The five layers below use the same assessment format as the other sectors. Their two predictive models follow the shared model contract below.

### 1. Comparator Credibility

**Decision question:** How credible and decision-relevant is the benchmark used to support claims about a product's clinical, scientific or commercial performance?

**Assess:**

- **Relevance and standard-of-care alignment:** Compare with the treatment, technology or care pathway a clinician, regulator or buyer would actually select for the stated population and market. Use dated guidelines, regulatory precedents, payer policies, pivotal trials, treatment-line and biomarker standards, and credible utilization evidence.
- **Design strength:** Randomization, prospective concurrent controls, prespecification, feasible blinding, allocation concealment, stratification, central review and regulator-agreed designs. Distinguish head-to-head evidence from adjusted external controls and unadjusted cross-trial comparisons.
- **Population, information size and statistical integrity:** Match disease stage, treatment line, biomarkers, prior therapy, prognosis, severity, demographics, eligibility and baseline risk. Inspect covariate balance, common support after matching/weighting, event counts, effect precision, confidence intervals, multiplicity, sensitivity analyses, missing-data handling and robust standard errors where applicable.
- **Endpoint alignment:** Common definitions, estimands, assessment schedules, censoring, adjudication, response criteria, follow-up windows and clinically important differences. Compare absolute and relative effects; inspect endpoint switching, repeated looks, underpowered subgroups and outcome-selected model specifications.
- **Data maturity and follow-up:** Event fraction, median follow-up, numbers at risk, survival/durability curves, proportional-hazards assessment, late toxicity, informative censoring and consistency across data cuts. Align the company's data cut with the comparator's maturity.
- **Past and future reproducibility:** Treatment era, geography, diagnostic capability, subsequent therapy, crossover, supportive care, access and community/academic setting. Prefer transparent protocols, regulatory reviews, peer-reviewed reports, independent datasets and disclosed methods/code; preserve conflicts, duplicate cohorts, practice changes and pandemic effects.
- **Clinical and commercial materiality:** Absolute benefit, number needed to treat/harm when estimable, quality of life, safety, convenience, discontinuation, resource use, total cost and prespecified superiority/noninferiority margins. Test whether the difference can affect use, filing, reimbursement or adoption.

**Collect:** Versioned trial registrations, protocols, statistical analysis plans, results and data cuts; comparator cohorts and eligibility; regulatory reviews/labels; dated guidelines and payer policies; full publications/supplements; utilization and cost evidence where accessible. Preserve population, endpoint, comparator and analysis versions.

**Negative-Short:** Obsolete, weak, geographically irrelevant or cherry-picked benchmarks; supportive care where an active standard exists; single-arm evidence presented as comparative proof; incompatible populations/endpoints; immature tails or hidden uncertainty; statistical significance without material benefit; investor decks without reproducible support.

**Positive-Long:** A rigorous, mature and independently corroborated comparison shows clinically meaningful benefit against the relevant standard, with tolerability and delivered cost supporting adoption before market expectations adjust.

**Programmatic data sources and thoughts — B01–B03, C01, C04, C11:** Reuse ClinicalTrials.gov and existing regulatory/disclosure collectors after field and history checks. Add [PubMed](https://pubmed.ncbi.nlm.nih.gov/download/) and [Europe PMC](https://europepmc.org/RestfulWebService) metadata and permitted full text; retrieve original FDA review packages, EMA assessment reports, guideline editions and payer documents through A27–A30. [NICE syndication](https://www.nice.org.uk/reusing-our-content/nice-syndication-api) requires access/licensing review. Trial registries alone do not establish full comparator quality; individual-patient data and utilization feeds are optional licensed inputs, not assumed holdings.

### 2. Western Validation

**Decision question:** To what extent has a product or platform been independently validated by credible Western institutions with real scientific, regulatory, clinical or commercial commitment?

**Assess:**

- **Counterparty quality and independence:** Named institution, domain and indication expertise, regulatory standing, financial ties and independence. Evaluate regulators, academic centers, biopharma partners, journals, payers and health systems by relevant actions rather than logos or general prestige.
- **Strength of commitment:** Selectivity, cost and reversibility of executed licenses/options, equity investment, co-development, trial sponsorship, procurement, named grants, accepted filings, site activation and independently funded replication. Separate each stage and its conditions.
- **Evidence independence and replication:** Who owns the protocol, funds and controls the data, performs the analysis and reproduces results. Identify reused company datasets, circular citations, sponsored content and agreement across independent institutions.
- **Clinical and regulatory relevance:** Exact asset, indication, population, development stage and target market supported by FDA, EMA, MHRA or Health Canada actions, trial authorization, designation, protocol agreement or ethics approval. These actions have different evidentiary strength and do not all imply approval or efficacy.

**Collect:** Executed agreements and amendments, disclosed financial commitments, institutional confirmations, trial sponsorship/site changes, grant awards, regulatory decisions and independent replication. Record jurisdiction, institution role, relationship, conflicts, conditions, expiry and cancellation.

**Negative-Short:** Affiliates or paid advisers portrayed as independent validators; distributor-only relationships; unverifiable logos; nonbinding MOUs, exploratory meetings and conference attendance; company-funded endorsements; platform praise applied to a different asset or indication.

**Positive-Long:** Independent institutions make substantial, asset-specific commitments and replicate evidence relevant to the intended market before that validation is reflected in expectations.

**Programmatic data sources and thoughts — B01, B03, B04, C01, C03, C05, C11:** Reuse SEC/HKEX disclosures, licensing/strategic-transaction candidates and trial/regulatory records; corroborate with the partner, university, hospital or funder. A28 covers public FDA/EMA/MHRA/Health Canada evidence; [NIH RePORTER](https://api.reporter.nih.gov/) supplies a candidate grant route under A33. Private regulator correspondence is unavailable unless publicly disclosed. Define the working geography as US, Canada, UK and EU/EEA and retain countries explicitly; geographic membership is a scope filter, not proof of scientific quality.

### 3. Key Opinion Leaders (KOL)

**Decision question:** How strong, independent, relevant and behaviorally engaged is the network of key opinion leaders surrounding the asset?

**Assess:**

- **KOL definition and influence:** An identifiable expert with dated, indication-specific evidence of guideline authorship, trial leadership, relevant publications, society leadership, advisory participation or referral-center expertise. Record the qualifying evidence and role; social followers, generic fame and employer prestige alone do not qualify an expert. Citation features must reflect information available at the time.
- **Breadth and depth:** Independent experts across institutions, relevant specialties, regions and community/academic practice. Measure unique people and institutions, with affiliation and coauthor dependence retained rather than counting one lab as many independent validators.
- **Commitment and information engagement:** PI/steering roles, protocol authorship, investigator-initiated trials, guideline work, invited scientific presentations, repeat collaboration and adoption research. Extract specific discussion of mechanism, selection, endpoints, comparative value, limitations and evidence thresholds, including reactions after adverse data.
- **Motivation and conflicts:** Consulting, research funding, equity and professional ties; disclosure completeness, independent funding, balanced commentary and activity predating engagement. Separate institutional research funding from personal compensation and avoid treating payment alone as proof of bias.
- **History and trajectory:** Dated independent-node growth, bridges across institutions, new investigators, repeat engagement, concentration and retention after negative events. Track departures, retractions and identity changes without using future network information in past assessments.

**Collect:** Person–institution–asset–trial relationships, role start/end dates, guideline and publication authorship, scientific presentations, dated substantive statements, funding/payment disclosures, retractions and corrections. Preserve the exact supporting action and whether engagement is paid, independent or unknown.

**Negative-Short:** Generic fame, weak indication fit, title inflation, predatory publications, company-created panels without substantive work, one-center/celebrity dependence, passive quotes or paid webinars, undisclosed conflicts, coordinated promotion, duplicate identities and sudden promotional bursts. Silence is not disapproval.

**Positive-Long:** A growing, diverse set of relevant experts makes sustained and substantive commitments, with transparent conflicts and engagement that remains credible after difficult data updates.

**Programmatic data sources and thoughts — B01, B03, B05, C07, C11:** Reuse trial investigators, Crossref proceedings and personnel records as discovery inputs. Add PubMed/Europe PMC author and affiliation evidence (A30), society/guideline and institutional biographies (A29/A34), and [CMS Open Payments](https://www.cms.gov/priorities/key-initiatives/open-payments) files (A31). Match person, institution and sponsor carefully; US payment reporting is not a global conflict register, and absence of a payment match is not independence. Conference metadata rarely establishes the content or stance of a talk; original programs and disclosures remain needed.

### 4. Talent Migration

**Decision question:** Does the pattern of people joining, leaving or concentrating around the company reveal informed confidence or execution risk?

**Assess:**

- **Role criticality and timing:** Clinical development, regulatory, CMC, translational science, biostatistics, quality, launch and business-development capabilities relative to the next milestone. Establish the milestone from a dated registry, filing or company plan, keeping planned, revised and observed dates separate; unknown schedules remain unknown.
- **Track record in role:** Attributable prior approvals, trial delivery, scale-up, launches, publications/patents, recency and growing responsibility. Verify biographies and distinguish individual contribution from a former employer's success.
- **Origin and destination:** Domain-relevant peers, regulators, labs and biopharma; classify retirement, academia and unrelated-sector moves separately. Include disclosed layoffs, acquisitions and relocations; do not invent personal motives or presume every hire/departure is favorable/adverse.
- **Cluster formation and coherence:** Complementary hires across functions, prior-team ties, geographic hubs and sequencing consistent with program plans. Separate backfills, recruiter noise, duplicate vacancies and acquisition transfers from expansion.
- **Retention, churn and succession:** Tenure-adjusted retention, handoffs, internal promotions, interim roles, critical vacancies and retention after data events. Compare flow acceleration with the company's own history and matched peers; missing headcount prevents a reliable churn rate.

**Collect:** Confirmed appointments, departures, prior roles, employment dates, leadership biographies, succession, disclosed organizational changes and separate vacancy snapshots; dated milestone baselines and revisions.

**Negative-Short:** Prestige without relevant delivery, unverifiable biographies, generic hiring treated as milestone readiness, unexplained critical-function churn, simultaneous program-team departures, repeated interim appointments and persistent vacancies. A removed job advertisement is not proof of a hire.

**Positive-Long:** Complementary, experienced clinical, regulatory and manufacturing teams assemble and remain in place ahead of documented milestones, with orderly succession and resources appropriate to execution.

**Programmatic data sources and thoughts — B06, C01, C03, C07, C11:** Reuse BioSpace/Fierce Biotech personnel feeds, personnel archives, filings and company/institutional announcements; add Greenhouse/Lever jobs where employers use them. Join confirmed people events to B01 trial history, A28 regulatory actions and original milestone guidance. Existing keyword matches remain candidates until reviewed; milestone histories and attributable prior outcomes require new normalization and evidence checks.

### 5. Trial Quality

**Decision question:** Are the selected and activated institutions likely to recruit the right patients, execute the protocol reliably and produce credible, regulator-ready data?

**Unit of analysis:** `trial_id × site_id × as_of_date`, aggregated to `product_id × indication` and `company_id`. Keep selected, listed, activated, recruiting and enrolling sites distinct; record aggregation weights and unknown enrollment shares.

**Assess:**

- **Investigator and team quality:** Similar-trial experience, enrollment history, publication quality, stability, coordinator training, workload and public compliance history. Distinguish honorary from operational PI roles and unresolved from resolved findings.
- **Patient access and recruitment realism:** Referral networks, eligible population, demographic fit, competing-trial load, prescreening and historical screening/enrollment rates. Avoid double-counted catchments and recruitment forecasts constructed after outcomes.
- **Execution and data quality:** Startup time, query rates, missing data, visit adherence, protocol deviations, sample integrity, central-review concordance, retention and database-lock timeliness where disclosed. Check selective reporting, outcome-dependent closure, delayed entry and audit findings.
- **Infrastructure and specialist ecosystem:** Demonstrated similar-trial delivery, accredited labs, imaging, pathology, surgery/ICU, cold chain, chain of identity/custody, genomic testing, pharmacy and multidisciplinary care. Verify outsourced handoffs and distinguish documented capability from marketing assertions.
- **Geographic and regulatory representativeness:** Intended filing/label population, care standards, diversity, public evidence of GCP/ethics readiness, central/local review and regional interruption risks. Country or prestige alone cannot establish regulatory acceptability.
- **Portfolio concentration and resilience:** Enrollment distribution, backup sites, activation pipeline, redundancy and correlated geographic exposure. Separate qualified expansion from low-productivity over-expansion and late rescue additions masking slippage.

**Collect:** Versioned registry site lists/statuses, investigator identities, activation/recruitment milestones, site-specific prior trial experience, public inspection/enforcement records, documented capabilities and disclosed operational measurements with denominators.

**Negative-Short:** Overstretched investigators, unresolved material compliance findings, unsupported enrollment forecasts, excessive deviations, missing verification, marketing-only infrastructure, non-comparable care settings, one-site dependence and unexplained late site additions. Missing private site metrics indicate uncertainty, not misconduct.

**Positive-Long:** Qualified sites demonstrate realistic recruitment, protocol-relevant capability, reliable execution and diversified enrollment ahead of a credible filing or data milestone.

**Programmatic data sources and thoughts — B01, B03, B07, C11:** Reuse trial registry snapshots and regulatory sources; add [FDA inspection/compliance data](https://www.fda.gov/about-fda/performance-data/fda-data-dashboard) (A32), original publications and institutional capability evidence (A34). Registry listing does not prove activation or site-level enrollment. Screening logs, query rates, deviations and source verification generally require authorized sponsor/CRO/site exports (A35); public models must retain explicit missingness and use labeled proxies.

## Robotics

### 1. Task Advantage and Comparator Credibility

**Decision question:** Does the robot perform an economically useful task better than the human or robotic alternatives available to its intended customer?

**Assess:**

- Performance against human work, conventional automation and competing robots under comparable conditions.
- Task completion, throughput, precision, payload, operating environment and human intervention.
- Whether advantages survive unfamiliar objects, changing layouts and other realistic variations.
- Fully installed cost per successful task, including supervision, integration and maintenance including the initial setup cost

**Collect:** Events covering benchmark releases, independent evaluations, customer trials and product revisions. Preserve the test conditions, comparator and robot/software version.

**Negative-Short:** Edited demonstrations, undisclosed teleoperation, favorable task selection and laboratory results presented as production performance.

**Positive-Long:** A company becomes economically competitive in a narrow, repeatable task before attracting attention as a general robotics platform.

Task-specific measurement is consistent with [NIST’s robotics performance framework](https://www.nist.gov/programs-projects/performance-assessment-framework-robotic-systems).

**Programmatic data sources and thoughts — R01, C01, C04:** Ingest manufacturer/customer technical reports and independent lab pages through RSS, sitemaps and permitted HTML/PDF downloads. Use [NIST robotics performance work](https://www.nist.gov/programs-projects/performance-assessment-framework-robotic-systems) to define test-condition fields, not as a universal robot-results API. Join wages from the [BLS API](https://www.bls.gov/developers/api_FAQs.htm) to task duration, integration cost and successful-task counts where disclosed. Label manufacturer claims separately from independent tests; teleoperation and intervention denominators are often missing.

### 2. Customer Commitment and Deployment Expansion

**Decision question:** Are customers moving from experimentation to meaningful, repeated use? What is the ease and cost of implementation?

**Assess:**

- Progression from demonstration to paid pilot, production deployment and repeat purchase.
- Customer confirmation, deployment size and operational importance. 
- What are the dated market caps/valuations and locations of companies deploying product?
- Expansion across sites or applications.
- Renewal, cancellation, customer concentration and dependence on related parties.

**Collect:** Contract awards, customer announcements, procurement records, deployment milestones, renewals and cancellations. Distinguish orders, shipments, installations and active deployments. RFPs

**Negative-Short:** Unpaid pilots described as commercial adoption, nonbinding agreements and repeated announcements of the same deployment.

**Positive-Long:** Modest initial deployments expand within customers before that expansion becomes visible in company revenue.

**Programmatic data sources and thoughts — C01, C03, C05, R02:** Monitor both supplier and customer announcements, [SAM.gov public opportunities](https://open.gsa.gov/api/get-opportunities-public-api/), [TED Search API](https://docs.ted.europa.eu/api/latest/search.html) and [USAspending API](https://api.usaspending.gov/docs/). Link notices to awards and later deployment evidence; a tender is not an order. Join public customer valuations from EODHD and disclosed private funding from company announcements or a licensed [Crunchbase API](https://support.crunchbase.com/hc/en-us/articles/32319290128019-Crunchbase-API-FAQ). Store valuation dates, customer sites, installed units, setup time and cost; unknown contract values remain unknown.

### 3. Workflow Integration and Distribution

**Decision question:** Can the company enter existing workflows and distribute its product without rebuilding every deployment from scratch? What is the stage of the company and what's the plan to execution from prototype to scale?

**Assess:**

- Compatibility with customers’ equipment and operational software.
- Installation time, customization burden and time to productive use.
- Integrator commitment, service coverage and channel productivity.
- Reusable software, accessories and application packages.
- Whether a component supplier benefits across multiple robot manufacturers.

**Collect:** Integration releases, supported-platform changes, integrator agreements, partner-led installations and application launches.

**Negative-Short:** Partner-logo lists without activity, bespoke engineering disguised as scalable software and dependence on one distribution partner.

**Positive-Long:** An uncelebrated component, software or integration company becomes a recurring requirement across several robotics platforms.

**Programmatic data sources and thoughts — R03, C06:** Snapshot vendor compatibility matrices, integration documentation, integrator case studies and [GitHub release APIs](https://docs.github.com/en/rest/releases/releases). Extract supported hardware/software versions, installation steps and named deployed customers. Build dated supplier–integrator–customer relationships. An SDK release or directory listing establishes technical availability, not a productive sales channel; customization hours require case-study disclosure or customer access.

### 4. Talent Migration and Execution Readiness

**Decision question:** Is the company assembling and retaining the capabilities needed for its next commercial milestone?

**Assess:**

- Relevant experience in controls, perception, hardware, safety, manufacturing and field service.
- Movement from research-heavy staffing toward deployment and production capability.
- Complementary hiring clusters and leadership continuity.
- Whether hiring plans, financing and demonstrated execution fit the announced timetable.

**Collect:** Personnel appointments, departures, organizational changes, financing and milestone announcements. Treat vacancies as hiring intentions, not completed hires.

**Negative-Short:** Prestige without role relevance, persistent critical vacancies and repeated milestone slippage.

**Positive-Long:** Experienced manufacturing and customer-service teams assemble around a company still perceived primarily as a research project.

**Programmatic data sources and thoughts — C07, C03:** Poll public jobs via [Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html) and [Lever Postings API](https://github.com/lever/postings-api); collect named appointments/departures from filings and employer announcements. Classify roles and work locations against the next milestone, then reconcile funding announcements to filed cash balances where available. A removed vacancy does not prove a hire, and staff biographies are not verified headcount histories.

### 5. Fleet Reliability and Production Scalability and Warranty/service liabilities

**Decision question:** Can the company deliver and support dependable robots at growing volumes while handling the requisite customer service?

**Assess:**

- Uptime, intervention frequency, failures, repair time and safety incidents.
- Reliability across customers, environments and hardware generations.
- Manufacturing consistency, supplier dependencies and service capacity.
- Warranty burden and economics as deployments grow.

**Collect:** Fleet-performance disclosures, recalls, service changes, production milestones, supplier agreements and customer operating reports.

**Negative-Short:** Shipped units presented as active fleets, capacity announcements presented as output and reliability claims without operating hours or fleet size.

**Positive-Long:** Improving reliability reduces support costs and unlocks deployments that previously failed the customer’s economic threshold.

**Programmatic data sources and thoughts — R04, C01, C08:** Collect fleet operating disclosures, service bulletins and customer operating reports; extract warranty provisions and expenses from filing notes. Use the [CPSC recall service](https://www.cpsc.gov/s3fs-public/RecallRetrievalWebServicesProgrammersGuide20180917.pdf) for relevant consumer products and official industrial-safety records for industrial deployments. CPSC is not a complete industrial robot incident register. Preserve fleet size, operating hours, hardware version and failure definitions; do not infer failure rates from raw incident counts.

## Semiconductors

These specialists need different measurement templates for chip designers, manufacturers, equipment suppliers, materials companies and packaging providers.

### 1. Application Advantage and Benchmark Credibility

**Decision question:** Does the product offer a meaningful advantage in the workload or manufacturing process customers actually care about?

**Assess:**

- Application-specific performance, energy use, cost and reliability.
- Comparable software, precision, system configurations and operating conditions.
- For equipment and materials: throughput, defect reduction, process compatibility and cost per acceptable output.
- Reproducibility and performance at commercially relevant scale.

**Collect:** Benchmark results, independent evaluations, product releases and process demonstrations.

**Negative-Short:** Peak specifications without application results, selective comparisons and component advantages erased by system-level costs.

**Positive-Long:** A company solves a commercially important niche problem that broad headline benchmarks miss.

For AI chips, [MLPerf’s rules](https://github.com/mlcommons/inference_policies/blob/master/inference_rules.adoc) provide a useful example of controlling workload, quality and latency; they are not a universal benchmark for every semiconductor business.

**Programmatic data sources and thoughts — S01, C04:** Collect [MLCommons benchmark results](https://docs.mlcommons.org/inference_results_v5.1/), linked submission repositories and independent technical publications, keyed by benchmark version and system configuration. Vendor datasheets and equipment acceptance reports supply other workloads. Preserve precision, latency, power boundary, software stack and availability. AI inference scores cannot rank fabrication equipment, analog chips or materials; those need throughput, defect and qualified-output templates.

### 2. Qualification and Design-Win Conversion

**Decision question:** Are customers committing to the product, and how likely is that commitment to become sustained production revenue?

**Assess:**

- Movement through sampling, evaluation, qualification, design selection and production.
- Customer confirmation and the importance of the relevant product program.
- Expected product lifetime, production timing and replacement risk.
- Repeat wins across customers and product generations.

**Collect:** Qualification announcements, customer product launches, credible teardowns, production orders, shipment disclosures and program cancellations.

**Negative-Short:** Unnamed design wins, evaluation samples counted as adoption and announced lifetime revenue treated as contracted backlog.

**Positive-Long:** A small supplier qualifies for a long-lived customer platform before production ramps.

**Programmatic data sources and thoughts — S02, C01:** Monitor supplier/customer filings, product launches, qualification notices and permitted teardown publications. A licensed teardown provider can add component identification; do not assume a public teardown API. Extract customer program, qualification stage, production start and disclosed order value. Link the same design win across announcements and keep lifetime-sales estimates separate from enforceable backlog.

### 3. Ecosystem Position and Value Capture

**Decision question:** Does the company control a difficult-to-replace part of the semiconductor ecosystem—and can it earn attractive economics from that position?

**Assess:**

- Dependence on its IP, software, process knowledge, materials or packaging capability.
- Compatibility with design tools, manufacturing processes and customer workflows.
- Substitution difficulty, switching costs and competing solutions.
- Pricing power, licensing economics and customer bargaining power.
- Exposure to standards changes and access restrictions, specifically geopolitical

**Collect:** Toolchain integrations, IP licenses, process qualifications, standards adoption, sourcing changes and product discontinuations.

**Negative-Short:** Patent counts without commercial relevance, nominal partnerships and technical importance without a viable revenue model.

**Positive-Long:** An overlooked supplier becomes a constraint on a growing market and gains commercial leverage. Have there been changes in geopolitics that allow openings in new markets?

**Programmatic data sources and thoughts — S03, C06, C09, C12:** Combine dated software/toolchain releases, foundry qualification directories, IP-license disclosures and patent records from the [USPTO Open Data Portal](https://data.uspto.gov/). Track official policy through the [Federal Register API](https://www.federalregister.gov/developers/documentation/api/v1) and [ITA Consolidated Screening List](https://www.trade.gov/consolidated-screening-list), plus relevant local authorities. Record territorial scope and effective dates; list membership alone does not establish a product-specific prohibition or a newly addressable market. Switching costs and pricing power remain evidence-based estimates.

### 4. Talent Migration and Development Execution

**Decision question:** Can the team deliver the next design or process milestone reliably?

**Assess:**

- Relevant experience in architecture, verification, physical design, process engineering, packaging and software.
- What is the execution/scaling plan and is there an execution/scale team in place?
- Tape-out, first-silicon, qualification and customer-launch execution.
- Leadership retention, development funding and dependence on a few individuals.

**Collect:** Hiring and departure events, tape-outs, silicon demonstrations, revisions, delays and financing.

**Negative-Short:** Impressive affiliations without demonstrated delivery, repeated unexplained delays and development schedules unsupported by resources.

**Positive-Long:** A technically credible team is paired with a good execution team--the company is moving from R&D to production/scale.

**Programmatic data sources and thoughts — C07, S02:** Use employer hiring APIs and named leadership announcements, then join them to dated tape-out, first-silicon, revision and qualification events from company/customer disclosures. Classify architecture, verification, physical-design, manufacturing and program-management roles separately. Track planned versus observed milestone dates; job advertisements and conference presentations cannot establish that production silicon shipped.

### 5. Manufacturing and Supply Scalability

**Decision question:** Can the company supply qualified products at viable cost and volume?

**Assess:**

- Yield, quality, process maturity and cost per acceptable unit.
- Foundry, packaging, testing and material dependencies.
- Capacity access, utilization and supply concentration.
- Working-capital requirements, inventory and production economics.
- For equipment suppliers: installation, customer acceptance and service support.

**Collect:** Production ramps, capacity agreements, facility milestones, quality incidents, supply disruptions and relevant financial disclosures. Find drop in cost of production/manufacturing.

**Negative-Short:** Nameplate capacity treated as usable output, unverified yield claims and growth that requires persistently uneconomic production.

**Positive-Long:** Manufacturing improvements convert a previously marginal technology into an economically viable product.

**Programmatic data sources and thoughts — S04, C01, C12:** Extract capacity, utilization, inventory, capital spending and production-cost disclosures from company filings and facility updates. [SEMI reports](https://www.semi.org/en/products-services/market-intelligence) are candidate licensed supply-chain context, not assumed API access. Link plants to foundry, packaging and material counterparties. Yield and unit-cost data are frequently private; use disclosed gross-margin/inventory trends as labeled proxies and retain product-mix and accounting changes rather than interpreting every margin increase as a manufacturing improvement.

## Energy storage

Evaluate companies by application: vehicle, stationary grid, industrial, backup power or another defined use. Batteries, thermal storage and mechanical storage should not share an undifferentiated technology ranking. Compare systems using usable energy capacity (kWh), discharge power (kW), duration (hours), and discounted cost per delivered kWh under the same duty cycle. A solar cell generates electricity and is not a standardized unit of storage. Keep electrical and thermal output separate unless conversion losses and the end use are specified. 

Working hypothesis to test: mature storage segments face commodity-like pricing pressure, making production cost and material access central. Do not assume all storage is commoditized: duration, safety, degradation, integration and financing can differentiate products. Measure whether innovation improves delivered economics rather than relying on novelty claims. 

### 1. Application Value and Comparator Credibility

**Decision question:** Does the technology offer a material advantage for a specific storage application?

**Assess:**

- Warranty and service costs.
- Required duration, power, response time, usable capacity and duty cycle.
- Installed and lifetime costs, including efficiency losses, maintenance and replacement.
- Space, weight, temperature and siting constraints.
- Comparison with realistic storage alternatives and other ways of meeting the customer’s need.

**Collect:** Independently tested performance, product specifications, customer evaluations and project-cost disclosures.

**Negative-Short:** Cell-level figures presented as system performance and cost comparisons using inconsistent operating assumptions.

**Positive-Long:** A technology considered inferior in general becomes compelling for a particular duration, environment or operating pattern.

The [DOE storage cost and performance assessment](https://www.energy.gov/cmei/2022-grid-energy-storage-technology-cost-and-performance-assessment) illustrates why duration, replacement, cycle life and calendar life belong in these comparisons.

**Programmatic data sources and thoughts — E01, C01:** Collect datasheets, independent test reports, warranty documents and actual project disclosures. Use the [DOE cost/performance assessment](https://www.energy.gov/cmei/2022-grid-energy-storage-technology-cost-and-performance-assessment) as a published comparison framework and historical baseline, not current vendor pricing. Calculate scenario-based installed $/kW, $/usable-kWh and discounted cost per delivered kWh, retaining duration, cycles, temperature, efficiency boundary, financing and replacement assumptions.

### 2. Geopolitics, Material Access and Supply Resilience

**Decision question:** Can the company obtain qualified materials and components at a competitive delivered cost, and can it continue selling into its target markets when trade rules or supply conditions change?

**Assess:**

- Chemistry-specific material intensity and bill of materials: lithium, nickel, cobalt, graphite, manganese, iron/phosphate, sodium inputs, copper and other relevant materials. Distinguish critical minerals from rare earths; they are not interchangeable categories.
- Exposure at each supply-chain stage: extraction, refining, active materials, cells, modules and recycling. Record operating sites and supplier ownership separately.
- Dependence on single suppliers, countries, transport routes and scarce processing capacity; distinguish announced capacity from qualified operating supply.
- Binding supply/offtake terms, pricing formulas, qualification lead times, substitution options and inventory buffers.
- Tariffs, export controls, sanctions, rules of origin and procurement eligibility, with announcement and effective dates kept separate.
- Whether alternative chemistries, recycling or redesigned components reduce a verified bottleneck without worsening performance or lifetime cost.
- Pass-through ability: who absorbs a material-price shock under the actual customer contract?

**Collect:** Dated material and component specifications; disclosed supplier/offtake agreements; mine, refinery and factory operating milestones; commodity price series; country/product trade flows; official trade-rule changes; supplier qualification and substitution announcements. Link each exposure to a company, product/chemistry, material, geography, source and effective period.

**Negative-Short:** Resource ownership presented as battery-grade supply, announced refineries treated as operating capacity, unqualified substitutes, and policy benefits assumed before eligibility is demonstrated.

**Positive-Long:** A company secures qualified diversified supply, lowers material intensity or qualifies an alternative chemistry before competitors can respond to a supply or trade-policy change.

**Programmatic data sources and thoughts — E02, C09:** Combine [USGS mineral summaries](https://www.usgs.gov/centers/national-minerals-information-center/mineral-commodity-summaries), [UN Comtrade](https://comtrade.un.org/), supplier/offtake disclosures and licensed commodity price feeds. USGS offers published reports/data; Comtrade provides trade statistics with product-code and access constraints, not a company-level bill of materials. Add dated rules from the Federal Register and affected-country authorities. Map HS codes to material/form carefully: customs unit values are not battery-grade spot prices, and mine production is not refining capacity.

### 3. Customer Commitment and Project Bankability

**Decision question:** Will credible customers and financing partners commit resources to deploying the technology?

**Assess:**

- Paid demonstration, binding order, financing, construction, commissioning and repeat deployment.
- Counterparty independence and financial capacity.
- Contract conditions, cancellation rights, guarantees and warranty support.
- Whether announced projects reach operational acceptance.
- Financing

**Collect:** Tenders, awards, contracts, financing decisions, construction milestones, commissioning and cancellations.

**Negative-Short:** Memoranda of understanding, speculative project pipelines and financing announcements confused with completed financing.

**Positive-Long:** A first independently financed project or repeat customer materially reduces commercialization uncertainty.

**Programmatic data sources and thoughts — E03, C05, C03:** Join SAM.gov/TED tender and award records with utility procurement sites, customer filings and lender/developer announcements. Use [EIA generator inventory files](https://www.eia.gov/electricity/data/detail-data.php) to corroborate US plant status where applicable. Model each project as a sequence from proposal to financing close, construction, commissioning and acceptance; capture sponsor, lender, customer and guarantor separately. Announced financing and interconnection-queue entry do not prove financial close or operation.

### 4. Material Substitution, Market Access and Revenue Durability

**Decision question:** Can the company’s products earn durable economic returns in the markets they are targeting? 

**Assess:**

- Are they linked to other established products?
- Is there new availability to raw materials or the ability to circumvent the use of one in scarcity?
- Interconnection, permitting, procurement eligibility and route to market.
- Customer tariffs, contracted payments and merchant-price exposure.
- Compatibility of proposed revenue streams with actual operating constraints.
- Dependence on subsidies, local-content rules or temporary shortages.
- Whether project value translates into value for the manufacturer, developer or operator being assessed.

**Collect:** Product compatibility and co-location announcements; qualified material-substitution milestones and updated cost/performance evidence; interconnection applications and status changes; permits; tenders and award notices; executed offtake, capacity and service contracts; financing-close and commissioning evidence; market-rule and tariff revisions; interval energy and ancillary-service prices; disclosed dispatch, degradation, warranty and replacement obligations. Record project ownership, manufacturer/developer/operator roles, contract duration, conditions precedent, currency, capacity in MW/MWh, expected versus realized revenue and the dates each fact became public. Separate merchant scenarios from contracted cash flows and avoid counting the same available capacity in incompatible services.

**Negative-Short:** Theoretical revenue stacking, double-counted markets and treating a policy announcement as realized demand.

**Positive-Long:** A change in market access or procurement requirements makes a previously niche product commercially relevant.

**Programmatic data sources and thoughts — E02–E04, C09:** Collect interconnection/permit records from the relevant utility or system operator, official tariffs and market rules, contract disclosures and substitution evidence. Use the [CAISO OASIS download API specification](https://www.caiso.com/documents/oasisapispecification.pdf) for a US market pilot and [EIA Open Data](https://www.eia.gov/opendata/) for electricity context; other markets require their own adapters. Preserve node, interval, timezone and price component. Simulated arbitrage or service stacking must respect power/energy and state-of-charge constraints and must not be labeled realized revenue.

### 5. Financing Runway and Talent Migration

**Decision question:** Does the company have the talent needed to execute? Are they acquiring it?

**Assess:**

- Hiring and retention in process engineering, quality, commissioning and service.
- Capital requirements, funding and milestone delivery.
- Warranty obligations and end-of-life responsibilities.

**Collect:** Production disclosures, supply agreements, relevant personnel movements, financing and commissioning performance.

**Negative-Short:** Announced factory capacity treated as production, laboratory teams without industrial capability and scale-up economics based only on projected costs.

**Positive-Long:** Acquisition of C-level executives with clear milestones and proven market need.

**Programmatic data sources and thoughts — C03, C07, E05:** Combine Greenhouse/Lever vacancy snapshots, leadership disclosures, financing-close announcements and filing cash-flow/debt notes with factory and commissioning milestones. Collect disclosed grants, guarantees and warranty/recycling obligations separately. Compute runway scenarios using unrestricted cash and operating cash burn, labeling undrawn facilities and contingent funding. A successful raise or executive appointment is an event, not proof of manufacturing readiness.

## Two predictive models for every specialist layer

**Scope:** Five layers per sector across biotech, robotics, semiconductors and energy storage: 20 layers and 40 model artifacts. Shared market context and recognition are inputs to each pair, not additional layers. These are research model specifications. The sole developer owns collection, evidence review and modeling. The companion plan runs October 5, 2026–January 15, 2027, with Monday–Friday work, weekends off and holiday buffer in late December. It prioritizes early collection and historical backfills for all layers, then delivers verified training/validation/test files from EC2 to S3 by Friday, January 15, 2027. Automated collection may continue unattended over weekends. Training, tuning, backtests and saved models will follow on the developer's local Windows PC; no model training runs on EC2. Price forecasting applies to listed securities with verified histories. Private-company assessments remain available, but private valuations are not fabricated daily price labels.

**Storage and preparation cadence:** All collected and prepared data is stored durably in S3. Build training/validation/test files from direct S3 reads or Athena in at most one consolidated run per day across all layers and both model families. Provider collection and backfills retain their source-specific cadences. Publish versioned export bundles to S3, then download a selected bundle to Windows and reuse it locally for training and backtests. Manual work remains Monday–Friday.

**Correlational model:** For each layer, relate dated historical events, measurements and changes to subsequent security returns using event studies and regularized panel regression with prespecified lags. Control for sector/market returns, prior volatility, size and other observed confounders. Train only on earlier observations, quantify uncertainty with time/company-aware resampling, and compare similar past patterns out of sample. Associations and coefficients do not establish causation.

**ML time-series model:** For each layer, train a pooled-across-companies Temporal Fusion Transformer (TFT) using that layer's features and the same shared controls and targets. Use static identifiers, historically observed features and genuinely known future calendar inputs as separate groups, following the [TFT architecture](https://arxiv.org/abs/1912.09363). Actual future trial results, prices, completed milestones and later revisions are never known-future inputs. Start with a proposed 252-session lookback and 5/20/60-session horizons, subject to validation and available history; output return quantiles (10th/50th/90th percentiles).

**Common target and comparison:** Interpret price changes as corporate-action-aware total returns, reporting raw returns alongside local-market/sector-benchmark excess returns. Use the same companies, cutoffs, horizons and evaluation windows for both models. Generate features after the local session close, forecast from the next tradable session close, and define each horizon from that anchor; this conservative daily convention must be fixed before training. Keep market, FX and benchmark conventions explicit. Report each model separately rather than assuming agreement or averaging them without validation.

**Feature and validation contract:** Use C13–C15 in the collection plan. Join by verified availability time, retain source age/missingness, fit transformations on training data only, and construct chronological walk-forward folds with purging of overlapping outcome windows. Reserve a final untouched holdout. Compare to zero-excess-return and market/history-only baselines; report prediction error, rank correlation, directional accuracy, TFT quantile loss/coverage and results by period/sector. If performance is translated into trading results, include turnover, costs and realistic execution. Test the incremental value of each layer through ablation. Sparse events and short history can make a trained TFT unsuitable for use; keep an explicit insufficient-evidence status rather than claiming validation.

**Outputs:** Keep the existing current assessment, change, confidence/coverage and next milestone. Add separate correlational and TFT predictions, horizon, uncertainty, model/data version, evidence cutoff, validation status and missing-data flags. Preserve traceability from every modeled feature to source records; feature importance is not causal proof.

## Identifying underrecognized potential

Each specialist should produce four separate outputs:

| Output | Meaning |
|---|---|
| Current assessment | How strong the product or business position is today |
| Change | What has materially improved or deteriorated |
| Confidence and coverage | How independently supported and complete the assessment is |
| Next milestone | Which observable event would strengthen or weaken the assessment |

Apply a **shared market-recognition assessment**, rather than adding a sixth specialist. Compare operational progress with analyst coverage, market expectations, relevant news, Reddit discussion and search interest. For listed companies, include valuation and financial expectations; for private companies, keep commercial opportunity separate from uncertain private valuations.

**Low attention alone is not an opportunity signal.** A stronger candidate combines material progress, a plausible path to capturing economic value and indications that prevailing expectations have not incorporated that progress.

**Programmatic data sources and thoughts — C02, C10, C16:** Align operational events with dated prices, news and estimates from licensed providers. Collect Reddit only through [permitted API access](https://www.reddit.com/dev/api/) and applicable commercial terms; use the [Google Trends API alpha](https://developers.google.com/search/apis/trends) only if access is granted, otherwise approved exports. Keep missing attention data separate from low attention. Analyst coverage and historical consensus usually require a licensed point-in-time dataset. Deduplicate syndicated articles and distinguish publication counts from independent corroboration.

**DataForSEO enrichment — A36, C10, C16:** The existing account reported by the user is a candidate source for [historical keyword metrics](https://docs.dataforseo.com/v3/dataforseo_labs-google-historical_keyword_data-live/) and [search-result snapshots](https://docs.dataforseo.com/v3/serp/google/organic/live/advanced/). Test company/product/application attention against operational progress across all layers. Search can also discover original guideline, partner, KOL, hiring, trial-site and customer evidence; retrieve and verify the original documents before using them in a specialist assessment. Search visibility is not expert credibility, trial quality, product adoption or market share. Preserve query/geography definitions and actual availability dates; retrospectively retrieved or revised histories are not automatically eligible for point-in-time backtests. The collection plan specifies the bounded pilot and remaining verification.

## Event and source-record requirements

Each event should retain:

- Company and product identities.
- Application.
- Event date.
- First-public date.
- First-observed date.
- Underlying source records.
- Counterparties.
- Relevant measurements and their conditions.
- Revisions.

A deployment announced through a press release, filing and customer statement should become **one linked event with three source records**, routed to the relevant specialists. Multiple reports of one action must not be mistaken for multiple independent actions.

Daily collection and historical collection should preserve the source records required to reconstruct these events. Historical assessments must use information available as of the assessment date, with publication and observation timestamps kept distinct from the date the underlying action occurred.

**Programmatic data sources and thoughts — C11:** Preserve source-native IDs (filing accession, tender/award ID, DOI, patent/publication ID, job ID, project ID), canonical URLs, retrieval time and content hashes. Use existing collection manifests as lineage inputs. Entity matching should use the reviewed company registry plus aliases and explicit product/site/counterparty tables; fuzzy names produce candidates for review. Store extraction locations and page-skip metadata. Timestamp uncertainty and retrospective corrections must remain explicit so later disclosures do not leak into historical assessments.

## Data availability and collection planning

Some desirable inputs—robot intervention rates, semiconductor yields and storage warranty claims—will often be private. Before expanding collection, distinguish:

- **Required public inputs:** Publicly accessible source records necessary for the intended assessment.
- **Useful public proxies:** Indirect observations with their limitations explicitly recorded.
- **Optional private inputs:** Metrics usable if legitimate access becomes available, without assuming such access exists.

Missing operational data should lower confidence rather than automatically lower the company’s quality assessment.

The companion plan maps layer definitions to candidate sources; implementation must verify historical availability, daily freshness, entity coverage and event fields. A proposed input is not verified collection coverage.

**Programmatic data sources and thoughts — all collection-plan rows:** Start with existing filings, news, market, patent and personnel collectors after checking their manifests and coverage. Add procurement, employer jobs, benchmark evidence and storage/material datasets in phases. For each API, prove authentication, pagination, sample fields, historical reach, licensing and entity joins before calling it covered. Site-only or private metrics require a separate access decision. See the companion plan for the source catalog and acceptance checklist.

