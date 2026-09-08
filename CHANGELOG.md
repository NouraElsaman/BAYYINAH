# Changelog

All notable changes to the **بينة | BAYYINAH** Egyptian Legal AI platform will be documented in this file.

## [Sprint 2.5] — Professional Contract Analysis Workspace — 2026-07-04

### Summary
Completely transformed `/contract-analysis` into a premium Legal AI workspace similar to Harvey AI or Copilot. Added robust file drag-and-drop mechanics, animated step timeline loaders, responsive multi-column layouts, visual risk score gauges, filtering of clauses by threat levels, recommendation prioritizers, and interactive export stubs. No backend changes.

### Features Completed
* **Redesigned Page Workspace Layout:**
  * **Desktop Layout:** Structured 3-column configuration: `[Upload Info Panel] [Analysis Workspace] [AI Insights Tools]`.
  * **Tablet Layout:** Balanced 2-column configuration: a left-side workspace list and a right-side general metadata card.
  * **Mobile Layout:** Stacked accordion controls preventing scroll overload on 320px screens.
* **Professional File Upload Center:**
  * Support for PDF, DOCX, and TXT files.
  * Drag & Drop, simulated upload progress bar, and validations (< 15MB size, extensions matching).
  * Preview details, size formatters, and easy clear/replace controls.
* **Animated AI Pipeline Loader:**
  * Timeline checking through 8 sequential checkpoints (Uploading document -> Reading -> Chunks -> Detecting clauses -> Searching references -> Risk assessment -> Summary -> Finalizing).
* **Executive Summary Dashboard:**
  * Key fields: Contract type, parties involved, duration tags, number of clauses, overall risk, and completion states.
* **Interactive Risk Gauge:**
  * SVG visual progress circle displaying overall risk percentage and matching risk threat bands (Low, Medium, High, Critical).
* **Clause Analysis Cards:**
  * Expandable card block representing Clause Type, Risk Badge, Simple Explanation, extracted text segments, and matched Egyptian legal context.
* **Filters Bar:**
  * Dynamic toggles to filter clauses list by Risk Level (Low/Medium/High/Critical) and category triggers (Financial, Employment, Commercial, Government).
* **AI Recommendations Panel:**
  * Lists modification advice with Priority Badges (Crucial, Medium, Low) and suggested contract edits.
* **Export Widgets:**
  * Clean UI buttons to prepare PDF, DOCX, and JSON exports.

### Files Modified
* `frontend/src/app/contract-analysis/page.tsx` — Complete redesign
* `ROADMAP.md` — Updated status
* `CHANGELOG.md` — Prepend current release
* `PROJECT_STATUS.md` — Prepend current release
* `TEST_REPORT.md` — Updated verification details

---

## [Sprint 2.4] — Enhanced Chat Experience — 2026-07-04

### Summary
Completely redesigned `/chat` page into a premium legal AI assistant. Fully responsive, accessible, with collapsible conversation logs, thinking state animations, actions, collapsible sources, and client-side aborting controls. No backend changes.

### Features Completed
* **Conversation Layout Sidebar:**
  * Interactive right-sided (RTL-first) sidebar listing past saved conversations.
  * Search bar for filtering past logs by text.
  * "محادثة جديدة" (New Conversation) action button.
  * Collapsible sidebar with slide animations.
* **Redesigned Messages UI:**
  * Styled user (primary dark theme Navy) and assistant bubbles (neutral grey card).
  * Custom markdown parser (`markdown.tsx`) for tables, headers, lists, bold/italic, and inline code.
  * Framer Motion animations for messages entrance.
  * Timestamps formatted in Arabic (e.g. `12:30 م`).
* **Enhanced Chat Input:**
  * Auto-resizing textarea up to 180px height.
  * Client-side "إيقاف" (Stop Generation) stream button.
  * Character counter displaying `0 / 1000`.
  * Keyboard triggers: `Enter` to send, `Shift + Enter` for new lines.
  * Paperclip (Attachment) and Microphone (Audio Input) UI placeholder triggers.
* **Animated Stepper Thinking State:**
  * Displays sequential steps before assistant response stream:
    1. Searching legal database...
    2. Analyzing question/statutes...
    3. Verifying citations...
    4. Generating final text...
* **Collapsible Sources Card:**
  * Bottom of each message contains a details disclosure with the list of matches, matched score percentages, law names, and matched text segments.
* **Suggested Follow-up Questions:**
  * Dynamically populates 3 follow-up bubbles based on domain (e.g., labor/tenancy/general) that send on click.
* **Interactive Message Actions:**
  * Buttons for Copy text, Like/Dislike feedback, Regenerate response, Share link, and PDF/DOCX export placeholders.
* **Accessibility (A11y) & Responsiveness:**
  * Fully WCAG compliant with custom focus outlines, appropriate `role="log"`, and `aria-live`.
  * Breakpoints verified from 320px to 1440px.

### Files Modified / Created
* `frontend/src/components/chat-interface.tsx` — Full redesign
* `frontend/src/lib/markdown.tsx` — **[NEW]** Custom markdown parser
* `ROADMAP.md` — Updated status
* `CHANGELOG.md` — Prepend current release
* `PROJECT_STATUS.md` — Prepend current release
* `TEST_REPORT.md` — Updated verification details

---

## [Sprint 2.3.2] — UI/UX Polish — 2026-07-04

### Summary
Production-ready polish pass across all frontend pages. Zero backend changes.

### Visual Improvements
* **globals.css:** Added `prefers-reduced-motion` support, `overflow-y: scroll` (prevents CLS from scrollbar), `overflow-x: hidden`, font anti-aliasing, `focus-visible` gold ring, `h-screen-dvh` utility, named shadow variables, `section-py` utility.
* **button.tsx:** Active press `scale(0.97)` feedback, accent variant added, `icon-sm` size, consistent `ring-offset-background` on all focus rings, `transition-all`.
* **card.tsx:** `flex flex-col` base — grids achieve equal card heights automatically. `CardFooter` added. Shadow transition on theme toggle.
* **input.tsx / textarea.tsx:** Unified focus ring using `accent` token with border color change on focus. Disabled background state added.
* **chat-interface.tsx:** `100dvh` height for correct mobile browser chrome handling. `role="log"` + `aria-live="polite"` on messages region. `aria-label` on send button and textarea.
* **app-shell.tsx:** Upgraded to `z-50`. IntersectionObserver refactored with `visibleSet` to prevent flickering between sections. `aria-current="page"` on active nav link.
* **page.tsx (Landing):** `prefers-reduced-motion` check in Framer Motion variants. All section paddings responsive (`py-14 sm:py-20 md:py-24`). Hero buttons full-width on mobile. All sections have `aria-label`. Decorative elements have `aria-hidden="true"`. CTA buttons full-width on mobile.
* **blog/page.tsx:** Equal-height cards via `flex + flex-1`, `<time>` element with `dateTime`, `<article>` wrapper, tag icon in badge, pinned "read more" footer.
* **history/page.tsx:** Semantic `<main>`, improved empty state with icon, responsive padding, `shrink-0` on clear button.
* **settings/page.tsx:** Semantic `<main>`, `<dl>/<dt>/<dd>` for health info, `aria-label` on all buttons, icon `aria-hidden`.
* **contract-analysis/page.tsx:** Semantic `<main>`, responsive heading sizes and padding, `aria-label`.

### Responsive QA — Breakpoints Verified
| Breakpoint | Width | Status |
|---|---|---|
| Extra small | 320px | ✅ No overflow, buttons stack vertically |
| Small | 375px | ✅ Full content visible |
| Tablet | 768px | ✅ 2-column grids, proper spacing |
| Large | 1024px | ✅ Desktop nav appears |
| Wide | 1440px | ✅ Max-width containers |

### Accessibility
* `aria-current="page"` on active nav item
* `role="log"` + `aria-live="polite"` on chat message region
* `aria-label` on all icon-only buttons
* `aria-hidden="true"` on all decorative icons and background elements
* `focus-visible` ring using gold accent token on all interactive elements
* `prefers-reduced-motion` — animations disabled or reduced globally

### Bugs Fixed
* Chat height incorrect on mobile Safari (fixed with `100dvh`)
* Navbar flicker between sections during fast scroll (fixed with `visibleSet` priority system)
* Card heights unequal in grids (fixed with `flex flex-col` on Card base)
* CTA buttons too narrow on mobile (now `w-full sm:w-auto`)
* Background glow decorations caused overflow on 320px (added `overflow-hidden` to containers)

### Files Modified
* `frontend/src/app/globals.css`
* `frontend/src/components/ui/button.tsx`
* `frontend/src/components/ui/card.tsx`
* `frontend/src/components/ui/input.tsx`
* `frontend/src/components/ui/textarea.tsx`
* `frontend/src/components/chat-interface.tsx`
* `frontend/src/components/app-shell.tsx`
* `frontend/src/app/page.tsx`
* `frontend/src/app/blog/page.tsx`
* `frontend/src/app/history/page.tsx`
* `frontend/src/app/settings/page.tsx`
* `frontend/src/app/contract-analysis/page.tsx`

---

## [Sprint 2.3.1] — Bug Fix Release — 2026-07-04

### Bugs Fixed
* Navbar active state flicker — IntersectionObserver implemented
* CTA secondary button broken — Fixed with theme-proof `bg-[#0b3c5d]` Navy
* Created dedicated `/blog` page
* Fixed `المدونة` nav link from `/#blog` to `/blog`
* Added `id="hero"` to hero section
* Added full Contact section with form
* Theme persistence via `localStorage`
* `scroll-behavior: smooth` in globals.css
* Mobile drawer closes on navigation

---

## [Sprint 2.3] - 2026-07-04

### Features Completed
* **Complete SaaS Landing Page (`/`):** Implemented all 9 required sections:
  1. **Hero Section** – Logo, Arabic headline, subtitle, dual CTA buttons, animated glows, Framer Motion entrance animations.
  2. **Services Section** – 6 cards: المساعد القانوني، تحليل العقود، الاستشارات، البحث في القوانين، استخراج المعلومات، promo CTA card.
  3. **Why BAYYINAH** – 6-item feature grid with icons and Arabic descriptions.
  4. **How It Works** – 4-step horizontal timeline (اسأل → استرجاع → تحقق → إجابة).
  5. **Statistics Section** – 4 animated counters (25,000+ articles, 98% accuracy, 1,200+ contracts, 4,500+ sessions).
  6. **Testimonials** – 3 professional customer quote cards with names and roles.
  7. **FAQ** – 4 collapsible accordion items using the reusable `Accordion` component.
  8. **CTA Banner** – Full-width gradient call-to-action section.
  9. **Footer** – Reused from AppShell (no duplication).
* **Framer Motion installed** and integrated for Hero entrance animations.

### Files Modified
* `frontend/src/app/page.tsx` — Complete SaaS landing page (new)
* `frontend/package.json` — Added `framer-motion` dependency

### Tests Executed
* TypeScript: `npx tsc --noEmit` — ✅ 0 errors
* ESLint: `npm run lint` — ✅ 0 warnings/errors (fixed unescaped entity errors)
* Production Build: `npm run build` — ✅ 8/8 pages compiled

### Bugs Fixed
* Fixed 6 ESLint `react/no-unescaped-entities` errors in testimonial paragraphs (replaced `"` with `&ldquo;`/`&rdquo;`).
* Fixed intermittent `.next` cache ENOENT by killing all node processes and rebuilding cleanly.

### Breaking Changes
* Root route `/` no longer redirects to `/chat`. It now serves the full landing page.

### Migration Notes
* Users who bookmarked `/` will see the landing page; the chat remains at `/chat`.

---

## [Sprint 2.2] - 2026-07-04

### Features Completed
* **Reusable Application Shell (`AppShell`):** Implemented the global sticky responsive header, mobile toggle navigation menu, Light/Dark mode switcher, browser back/forward history navigation buttons, and a comprehensive legal-resources footer with an AI Disclaimer.

### Files Modified
* `frontend/src/components/app-shell.tsx`

### Tests Executed
* TypeScript Compilation Check (`npx tsc --noEmit`)
* ESLint Linter Check (`npm run lint`)
* Production Build (`npm run build`)

### Bugs Fixed
* Fixed responsiveness layout shifting on mobile headers by wrapping action groups in container flex boxes.

### Breaking Changes
* None.

### Migration Notes
* None.

---

## [Sprint 2.1] - 2026-07-04

### Features Completed
* **Design System & Reusable Foundation UI:** Set up the tailwind color variables matching the official `bayyinah-logo.png` assets, customized fonts, and created `input.tsx` and `accordion.tsx` under `src/components/ui/`.

### Files Modified
* `frontend/src/app/globals.css`
* `frontend/src/components/ui/input.tsx`
* `frontend/src/components/ui/accordion.tsx`
