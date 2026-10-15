# Product Requirements Document (PRD)

## 1. Document Overview
- **Product / Feature Name**: Agentic AI Travel Assistant – PDF Generation Engine
- **Document Owner**: Hamed Yazdani (Lead Engineer)
- **Stakeholders**: Product Management, UI/UX Design, Engineering, QA, Marketing
- **Version**: 1.0
- **Status**: Draft (ready for review)
- **Last Updated**: 2026-10-15
- **Related Links**:
  - Repository: https://github.com/Hamed18/Agentic-AI-Travel-Assistant
  - Design Mockups: `docs/designs/`
  - PDF Engine Documentation: `pdf_generator.py`
  - SOLVED_PROBLEMS_DOCUMENTATION.md

---

## 2. Problem Statement and Opportunity
**Problem**
- The previous PDF generation module failed to render tables, omitted day‑wise plans, and produced PDFs lacking budget visualisation.
- Users received a UI preview that was complete, but the downloadable PDF was missing critical details, leading to confusion and extra manual editing.

**Opportunity**
- Provide a reliable “one‑click” PDF export that mirrors the UI exactly, enabling travel agents and end‑users to share professional itineraries with partners and clients.
- Differentiates the product from generic travel planners by delivering publish‑ready, brandable documents (logo, motto, colour‑coded sections, pie‑chart budget).

---

## 3. Goals and Success Metrics
| Goal | Success Metric |
|------|----------------|
| Accurate rendering | 100 % of tables (flights, hotels, weather, budget) appear in the PDF across 100 regression test cases |
| Performance | PDF generation time ≤ 2 seconds for a 7‑day itinerary |
| Visual completeness | All UI sections (day‑wise plan, budget chart, logo) present in >95 % of generated PDFs |
| Reliability | PDF generation error rate < 1 % in production |
| User satisfaction | ≥ 4.5/5 rating on post‑download survey |

---

## 4. Target Users and Use Cases
- **Travel planners** creating itineraries for clients.
- **Tour operators** needing printable PDFs for brochures.
- **End‑users** of the Streamlit app who want a shareable itinerary.

**Key Use Cases**
1. Planner inputs destination and preferences → UI shows day‑wise plan → clicks *Download PDF* → receives a fully‑formatted document.
2. Tour operator customises branding (logo, motto) → generates PDF for client hand‑out.
3. QA validates that the PDF matches UI for a given markdown input.

---

## 5. Scope and Priorities
### In‑Scope (MVP)
- Day‑wise plan rendered as colour‑coded headings/sub‑headings.
- Tables for flights, hotels, weather, overall budget.
- Budget allocation visualised as a donut (pie) chart.
- SAGATRAVELLER logo, name, and motto on the cover page.
- Streamlit download button for final PDF.

### Out of Scope
- Multi‑language PDF localisation.
- Export to Word or HTML formats.
- Advanced interactive charts (e.g., drill‑down).

### Prioritisation (MoSCoW)
- **Must**: Table rendering, day‑wise text layout, budget donut chart, branding.
- **Should**: PDF metadata (title, author), error handling/retry.
- **Could**: Optional cover page templates, custom colour themes.
- **Won’t**: Real‑time collaborative editing of PDF.

---

## 6. Functional Requirements
| ID | Requirement | Description | Acceptance Criteria |
|----|-------------|-------------|---------------------|
| FR‑1 | Table Rendering | Render markdown tables for flights, hotels, weather, and budget using `fpdf2.table` context manager. | All tables appear with correct column alignment and no missing rows in the generated PDF. |
| FR‑2 | Day‑wise Card Layout | For each itinerary day, generate a heading with the date, sub‑heading for location, and bullet‑point activities with colour coding. | PDF contains a separate section per day, headings styled consistently, and no overlapping text. |
| FR‑3 | Budget Donut Chart | Produce a donut chart image from budget data and embed it on the *Budget Summary* page. | Chart matches the numeric breakdown, legend is legible, and image scales correctly on A4 page. |
| FR‑4 | Branding | Add SAGATRAVELLER logo, name, and motto on the cover page. | Cover page displays logo image, product name “SAGATRAVELLER”, and motto “Your Journey, Our Story”. |
| FR‑5 | PDF Generation API | Expose a function `generate_itinerary_pdf(markdown: str) -> bytes` that returns the PDF binary. | Unit test asserts the function returns non‑empty bytes and the file opens in a PDF viewer. |
| FR‑6 | Download Button | Streamlit UI includes a *Download PDF* button that streams the generated PDF to the browser. | Clicking the button triggers a file download named `SAGATRAVELLER_Itinerary.pdf`. |
| FR‑7 | Error Handling | If PDF generation fails, UI shows a friendly error message and logs details. | Simulated failure returns error toast; logs contain stack trace. |

---

## 7. User Experience and Design
### User Flow
```mermaid
flowchart TD
    A[User opens Streamlit UI] --> B[Enter itinerary parameters]
    B --> C[Agents generate markdown itinerary]
    C --> D[Preview rendered markdown]
    D --> E[Click "Download PDF"]
    E --> F[PDF Engine (pdf_generator.py)]
    F --> G[PDF file returned]
    G --> H[Browser download prompt]
```

### Wireframe (placeholder)
![UI Mockup](file:///C:/Users/WALTON/.gemini/antigravity/brain/bf37c4dd-7c8c-4057-a181-2b053bdef338/media_1791130652803.png)

### PDF Sample Visuals
- **Budget Donut Chart**: ![Budget Chart](file:///C:/Users/WALTON/.gemini/antigravity/brain/bf37c4dd-7c8c-4057-a181-2b053bdef338/scratch/page_3.png)
- **Cover Page Branding** (illustrative placeholder) – the actual logo will be placed in `assets/logo.png`.

---

## 8. Non‑Functional Requirements
- **Performance**: PDF generation ≤ 2 s for up to 10‑day itineraries on typical dev machine (Intel i5, 8 GB RAM).
- **Scalability**: Stateless generation; can be horizontal‑scaled behind a load balancer.
- **Security**: No external network calls during PDF rendering; input sanitised to prevent injection.
- **Reliability**: Automatic retry (up to 2 attempts) on transient failures; logs emitted to `logs/pdf_generation.log`.
- **Accessibility**: PDF includes tagged text for screen readers; colour contrast ≥ 4.5:1.
- **Compatibility**: Generates A4 PDF, viewable in Adobe Reader, Chrome, and mobile PDF viewers.

---

## 9. Data, Integrations, and Analytics
- **Data Flow**: Markdown itinerary (produced by agents) → `pdf_generator` parses sections → renders PDF components → returns binary.
- **Integrations**:
  - `fpdf2` for PDF creation.
  - `Pillow` for chart image handling.
  - Streamlit for UI download.
- **Analytics**: Increment a counter `pdf_downloads_total` in `analytics.py`; expose via Prometheus endpoint.
- **Retention**: Generated PDFs are not persisted on server; only streamed to client.

---

## 10. Delivery Plan and Dependencies
| Milestone | Target Date | Dependencies |
|-----------|-------------|--------------|
| Development complete (MVP) | 2026‑10‑22 | fpdf2 ≥ 2.5, Pillow ≥ 9.0 |
| Unit & integration testing | 2026‑10‑24 | pytest, pytest‑mock |
| QA sign‑off | 2026‑10‑27 | Test matrix, PDF visual diff tool |
| Beta release (internal) | 2026‑10‑29 | CI pipeline, feature flag |
| Public release | 2026‑11‑02 | Documentation, marketing assets |

---

## 11. Testing and Launch Readiness
- **Unit Tests**: `tests/test_pdf_generator.py` validates table rendering, chart embedding, and cover page.
- **End‑to‑End Tests**: Simulate UI flow with Selenium (or Playwright) to click download and verify PDF size > 0.
- **Acceptance Criteria**: All FRs pass; visual diff shows no regression compared to baseline PDFs.
- **Rollback Plan**: Revert to previous PDF engine commit (`5f2c3a1`) via Git; redirect download button to legacy version.
- **Support Readiness**: Update support FAQ with “PDF download fails” troubleshooting steps.

---

## 12. Open Questions and Approvals
- **Logo assets**: Final high‑resolution SVG for SAGATRAVELLER logo – pending design team sign‑off.
- **Motto wording**: Confirm final copy (“Your Journey, Our Story”).
- **Budget categories**: Verify that all expense categories (flight, hotel, activities, food, transport) are exhaustive.
- **Stakeholder approvals**: Product Manager, Engineering Lead, QA Lead.

---

*Prepared by the Antigravity AI coding assistant.*
