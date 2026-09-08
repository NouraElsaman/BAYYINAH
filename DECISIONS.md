# Engineering Decisions Log (DECISIONS.md)

All architectural and engineering design decisions are logged here permanently.

---

## [ED-005] Three-Column Contract Analysis SaaS Dashboard Layout

* **Date:** 2026-07-04
* **Sprint Reference:** Sprint 2.5
* **Context:** Redesigning the Contract Analysis workspace into a premium, SaaS-like dashboard.
* **Problem:** Displaying rich file upload widgets, full clause lists, executive summary metadata, risk gauges, recommendations, and export options on a single screen without layout shifts, overflow, or cognitive overload.
* **Alternatives Considered:**
  1. Multi-tab dashboard layout (separating uploader, summary, clauses, and widgets).
  2. Single vertical column feed layout (original approach).
  3. Structured 3-column desktop layout (`Upload | Workspace | AI Insights`) collapsing to a 2-column tablet grid and accordion stacked panels on mobile.
* **Chosen Solution:** Alternative 3 (Three-Column Responsive Grid).
* **Why Selected:** Satisfies executive overview demands at a single glance. Provides clear visual hierarchy: upload widgets act as metadata sidebar, middle workspace contains core text clauses, and left sidebar holds quick action tools (gauges, exports, filters).
* **Impact on Project:** Clean responsive mapping via Tailwind breakpoint rules (`hidden lg:grid grid-cols-12` vs `md:grid lg:hidden` vs `block md:hidden`).
* **Related Files:** `frontend/src/app/contract-analysis/page.tsx`

---

## [ED-003] Framer Motion for Landing Page Animations

* **Date:** 2026-07-04
* **Sprint Reference:** Sprint 2.3
* **Context:** The landing page hero section requires subtle entrance animations to communicate quality and professionalism.
* **Problem:** Next.js 14 App Router requires `"use client"` for interactive components. Animation libraries must not block SSR or cause hydration mismatches.
* **Alternatives Considered:**
  1. Pure CSS `@keyframes` animations (no JS overhead, no hydration risk).
  2. Framer Motion with `motion` components (industry-standard, declarative, performant).
  3. GSAP (powerful but heavyweight, 67KB gzip vs Framer Motion's 43KB).
* **Chosen Solution:** Alternative 2 — Framer Motion.
* **Why Selected:** Declarative `variants` API integrates cleanly with React state, stagger children animations are trivial, and the bundle overhead is acceptable at 43KB.
* **Trade-offs:** Adds ~43KB to the `/` route bundle (48.8KB total page chunk), which is acceptable for a marketing page.
* **Impact on Project:** `/` First Load JS increased from 138B to 48.8KB, all other routes unaffected.
* **Future Considerations:** If Lighthouse LCP regresses, animations can be deferred with `AnimatePresence` and `lazy`.
* **Related Files:** `frontend/src/app/page.tsx`, `frontend/package.json`

---

## [ED-004] Animated Counter via useEffect + setInterval (No Library)

* **Date:** 2026-07-04
* **Sprint Reference:** Sprint 2.3
* **Context:** Statistics section requires animated number counters that count up on page load.
* **Problem:** Adding another library (e.g. `react-countup`) for a single component is wasteful.
* **Chosen Solution:** Custom `AnimatedCounter` component using `useEffect` + `setInterval` with a fixed step size.
* **Why Selected:** Zero dependency cost, fewer than 20 lines of code, fully controllable behavior.
* **Trade-offs:** Does not pause/restart on viewport entry — counts immediately on mount. Future improvement: add IntersectionObserver to trigger only when visible.
* **Related Files:** `frontend/src/app/page.tsx`



---

## [ED-001] Design System Derived from Official Logo Asset

* **Date:** 2026-07-04
* **Sprint Reference:** Sprint 2.1
* **Context:** A rebranding milestone was approved to rename the platform from DigitLaw to BAYYINAH. An official logo already exists.
* **Problem:** Defining a design system palette that conflicts with the logo colors would result in branding inconsistencies.
* **Alternatives Considered:**
  1. Define a generic slate/gold palette based on Tailwind defaults.
  2. Extract exact hex codes from the `bayyinah-logo.png` image asset.
* **Chosen Solution:** Alternative 2. Hex values `#0b3c5d` (Navy) and `#bda054` (Gold) were extracted from the logo.
* **Why Selected:** It maintains exact visual alignment with the official brand asset, which is the single source of truth.
* **Trade-offs:** We must configure HSL color mappings for dark mode ourselves, since the logo has high contrast navy/gold designed for light backgrounds.
* **Impact on Project:** Ensures visual continuity on page load.
* **Future Considerations:** The logo uses white backings internally; a transparent SVG variant would improve visual blending in dark mode headers.
* **Related Files:** `globals.css`, `app-shell.tsx`

---

## [ED-002] Multi-page Layout Structure & Sitemap REST

* **Date:** 2026-07-04
* **Sprint Reference:** Sprint 2.2
* **Context:** The original MVP redirected the root `/` page directly to the `/chat` route.
* **Problem:** Marketing the application, showcasing feature vectors, and providing an AI legal disclaimer requires a clear home page landing.
* **Alternatives Considered:**
  1. Keep redirecting `/` to `/chat` and create a sub-route for the landing page (e.g. `/home`).
  2. Map `/` directly to the new SaaS Landing Page and host the interactive assistant workspace at `/chat`.
* **Chosen Solution:** Alternative 2.
* **Why Selected:** standard SaaS architecture conventions. It allows search engines to index the landing page first, while reserving `/chat` for verified tools.
* **Trade-offs:** Link references inside navbar and buttons had to be updated to map to anchors (`/#services`, `/#blog`) on `/`.
* **Impact on Project:** Changed default entry route.
* **Related Files:** `app-shell.tsx`, `page.tsx`
