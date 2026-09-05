# Legal

This page contains the legal notices, disclaimers, and policies that govern the use of Citeable.

---

## 1. Disclaimer & Limitation of Liability

Citeable is provided on an **"AS IS"** and **"AS AVAILABLE"** basis, without warranties of any kind, either express or implied, including but not limited to implied warranties of merchantability, fitness for a particular purpose, non-infringement, or accuracy.

**No Commercial or Ranking Guarantee.** Audit scores and remediation narratives measure diagnostic site readiness based on empirical heuristics and observed data. Citeable does **not** guarantee website indexing, search engine rankings, AI search citations, web traffic, or any commercial outcomes. Scores represent a point-in-time technical evaluation, not a prediction of future AI engine behavior.

**No Professional Advice.** Audit outputs, qualitative reviewer notes, knowledge base guidance, and AI-generated synthesis do not constitute legal, financial, SEO consulting, cybersecurity, or any other form of professional advice. Users are solely responsible for verifying and testing any technical remediations before deployment to production environments.

**Limitation of Liability.** In no event shall the authors, maintainers, or contributors of Citeable be liable for any direct, indirect, incidental, special, consequential, or punitive damages arising out of or in connection with the use of, or inability to use, this software, third-party API services, or audit findings, even if advised of the possibility of such damages.

---

## 2. Acceptable Use Policy

By initiating an audit via the Citeable UI or API, you represent and warrant that:

1. **Domain Authorization.** You are the owner of the target domain, or you have obtained explicit written authorization from the domain owner to perform automated diagnostic scanning and content analysis.
2. **Lawful Use.** You will not use Citeable to conduct denial-of-service attacks, bypass access controls, scan domains you are not authorized to audit, or violate the target domain's published Terms of Service or Robots Exclusion Protocol (RFC 9309).
3. **No Misrepresentation.** You will not present automated diagnostic findings as legal determinations, regulatory compliance certifications, or professional consulting opinions.
4. **Liability.** Citeable disclaims all liability for unauthorized scans, network requests, or audit actions executed by third parties using this software.

---

## 3. Privacy & Data Notice

### What Data is Collected

| Data Category | Source | Retention |
|---|---|---|
| Target domain URL | User input | Stored in audit run history (SQLite) |
| Crawled webpage content | Automated fetch from target domain | Stored in audit findings for the duration of the run record |
| Analyst ID | Optional header (`X-Analyst-Id`) | Stored in audit trail for attribution |
| BYOK API keys | User-provided per-request | Held in memory only during request processing; never written to disk, database, logs, or telemetry |
| Audit scores and findings | Computed by the scoring engine | Stored in audit run history |

### Data Retention Model

Citeable uses an append-only audit trail architecture. Modification operations maintain historical records through status transitions (e.g., `active` to `deprecated`) rather than physical deletion. This design prioritizes audit integrity and provenance tracking.

### GDPR & CCPA Compliance

Operators deploying Citeable in jurisdictions subject to the EU General Data Protection Regulation (GDPR), the California Consumer Privacy Act (CCPA), or equivalent privacy regulations are responsible for:

- Implementing administrative procedures to handle data subject access requests (DSARs)
- Configuring data redaction, tombstoning, or cryptographic erasure mechanisms for personal data upon valid erasure requests
- Ensuring that crawled webpage content containing third-party personal data is processed under a lawful basis (e.g., legitimate interest for diagnostic evaluation of publicly accessible information)

### Third-Party API Usage

When BYOK keys are configured, Citeable transmits audit-related content to third-party LLM providers (e.g., Google Gemini, OpenAI, Anthropic, Groq, Mistral, DeepSeek) for synthesis. Users bear sole financial and legal responsibility for their third-party API accounts, usage costs, and compliance with each provider's Acceptable Use Policy.

---

## 4. Diagnostic Opinion Disclaimer

All diagnostic findings produced by Citeable, including but not limited to:

- **Cloaking detection** (`CLOAKING_DETECTED`): This is a technical heuristic that compares content served to different user agents. It is an algorithmic observation of content disparity, not a legal determination of intentional deception, fraud, or search engine manipulation.
- **Schema honesty analysis**: Evaluations of JSON-LD structured data alignment with visible page content are automated consistency checks, not accusations of dishonesty or regulatory non-compliance.
- **Authority scoring**: Domain authority metrics are derived from third-party data sources and heuristic models. They do not represent endorsements, rankings, or official assessments by any search engine or AI platform.
- **Competitor analysis**: Comparative observations regarding competitor domains are based on publicly accessible data and do not constitute competitive intelligence services, market analysis, or disparagement of any business.

Human reviewer notes recorded during the Guided Review process reflect subjective qualitative opinions of the reviewing analyst, not legal, technical, or regulatory rulings.

---

## 5. Crawler & Robots.txt Analysis Disclaimer

Citeable's analysis of robots.txt directives, AI crawler tokens (e.g., `Google-Extended`, `GPTBot`, `OAI-SearchBot`), and `llms.txt` files is provided for technical diagnostic purposes only.

This analysis **does not constitute legal advice** regarding:

- Statutory copyright opt-outs under Article 4 of EU Directive 2019/790 (Digital Single Market Copyright Directive)
- Text and data mining (TDM) reservation rights
- Intellectual property protection strategies
- Compliance with any jurisdiction's copyright, data protection, or computer access laws

Users should consult qualified legal counsel before modifying crawler access policies based on Citeable's diagnostic findings.

---

## 6. Third-Party Trademarks & Attribution

All trademarks, service marks, trade names, and company names referenced within Citeable's documentation and software — including but not limited to **Google**, **Googlebot**, **Google AI Overviews**, **Gemini**, **OpenAI**, **ChatGPT**, **GPTBot**, **OAI-SearchBot**, **Anthropic**, **Claude**, **Perplexity**, **Microsoft Bing**, **Moz**, **Ahrefs**, **BrightEdge**, **Schema.org**, **Wikidata**, **Wikipedia**, **Groq**, **Mistral**, **DeepSeek**, and **xAI** — are the property of their respective owners.

Their mention in Citeable does not imply any affiliation with, endorsement by, or sponsorship from those respective trademark holders.

---

## 7. Open-Source License

Citeable is licensed under the **Apache License, Version 2.0**. You may obtain a copy of the License at:

> [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

Third-party vendor libraries bundled with Citeable (e.g., `marked.js`, `mermaid.js`) retain their original MIT license headers.

---

*Last updated: 2026-09-04*
