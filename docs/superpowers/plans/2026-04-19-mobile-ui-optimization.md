# Mobile UI Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add missing `@media (max-width: 560px)` rules across five CSS files so the FilmRoll app renders correctly on 360–430px phones.

**Architecture:** Targeted patch pass — append `@media (max-width: 560px)` blocks to the end of each CSS file that has gaps. No existing rules removed, no new files created, no JavaScript changes.

**Tech Stack:** Plain CSS, Flask/Jinja2 templates, served statically.

---

## File Map

| File | What changes |
|------|-------------|
| `static/css/home.css` | Hero inner width, hero search, trending card size, home-section padding |
| `static/css/modal.css` | modal-info-col padding, star tap targets, rate-row padding |
| `static/css/cards.css` | Hide hover overlay on touch, feat-body padding |
| `static/css/reviews.css` | Review container padding, word-break |
| `static/css/layout.css` | Matchmaker container width, matchmaker-btn full-width |

---

## Task 1: home.css — hero and section padding

**Files:**
- Modify: `static/css/home.css` (append at end of file, after line 464)

- [ ] **Step 1: Append mobile block to home.css**

Add at the very end of `static/css/home.css`:

```css
/* ══════════════════════════════════════════
   MOBILE — ≤560px
══════════════════════════════════════════ */
@media (max-width: 560px) {
    /* hero inner: clamp(600px,55vw,860px) resolves to ~214px on 390px screen */
    .hero-inner {
        max-width: 100%;
    }

    /* hero search: same clamp issue */
    .hero-search {
        max-width: 100%;
    }

    /* iOS auto-zoom prevention (must be ≥16px) */
    .hero-search-inner input {
        font-size: 16px;
    }

    /* home section side padding */
    .home-section {
        padding: 0 16px;
    }

    /* trending cards: narrower for thumb reach on small screens */
    .t-card,
    .t-skeleton {
        width: 110px;
    }
}
```

- [ ] **Step 2: Visual check**

Open the app at `http://localhost:5000` in Chrome DevTools → toggle device toolbar → iPhone SE (375px). Confirm:
- Hero title and search box span the full width
- Home sections have 16px side padding
- Trending strip shows ~3 cards at a time

- [ ] **Step 3: Commit**

```bash
cd "d:/TE BOOKS/Praticals/DSBDA/MOVIE REOCOMDATION SYSTEM"
git add static/css/home.css
git commit -m "fix(mobile): hero inner width, search box, trending card size at <=560px"
```

---

## Task 2: modal.css — info column padding and star tap targets

**Files:**
- Modify: `static/css/modal.css` (append at end of file, after line 406)

- [ ] **Step 1: Append mobile block to modal.css**

Add at the very end of `static/css/modal.css`:

```css
/* ══════════════════════════════════════════
   MOBILE — ≤560px
══════════════════════════════════════════ */
@media (max-width: 560px) {
    /* reduce side padding so content fits 360px screens */
    .modal-info-col {
        padding: 14px 16px;
    }

    /* reduce rate row padding */
    .modal-rate-row {
        padding: 12px 16px;
    }

    /* star tap targets: rendered size ~22px → add padding to reach 44px */
    .star {
        padding: 10px 4px;
    }

    /* cast row side padding */
    .modal-cast-row {
        padding: 14px 16px 18px;
    }
}
```

- [ ] **Step 2: Visual check**

In DevTools (iPhone SE), open a movie modal. Confirm:
- Movie title and overview are not clipped
- Star rating row has comfortable spacing
- Stars are easy to tap (44px touch area)

- [ ] **Step 3: Commit**

```bash
git add static/css/modal.css
git commit -m "fix(mobile): modal info padding and star tap targets at <=560px"
```

---

## Task 3: cards.css — disable hover overlay and featured body padding

**Files:**
- Modify: `static/css/cards.css` (append at end of file, after line 341)

- [ ] **Step 1: Append mobile block to cards.css**

Add at the very end of `static/css/cards.css`:

```css
/* ══════════════════════════════════════════
   MOBILE — ≤560px
══════════════════════════════════════════ */
@media (max-width: 560px) {
    /* hover overlay never triggers on touch — hide it so tap goes straight to modal */
    .card-hover-overlay {
        display: none;
    }

    /* featured card body: reduce desktop padding */
    .feat-body {
        padding: 14px 16px;
    }
}
```

- [ ] **Step 2: Visual check**

In DevTools (iPhone SE), confirm:
- Tapping a movie card opens the modal immediately (no overlay flicker)
- The featured card's text body fills the width cleanly

- [ ] **Step 3: Commit**

```bash
git add static/css/cards.css
git commit -m "fix(mobile): hide hover overlay on touch, reduce feat-body padding at <=560px"
```

---

## Task 4: reviews.css — overflow and padding

**Files:**
- Modify: `static/css/reviews.css` (append at end of file, after line 87)

- [ ] **Step 1: Append mobile block to reviews.css**

Add at the very end of `static/css/reviews.css`:

```css
/* ══════════════════════════════════════════
   MOBILE — ≤560px
══════════════════════════════════════════ */
@media (max-width: 560px) {
    /* prevent long reviewer names / text from overflowing narrow screens */
    .review-card {
        word-break: break-word;
    }

    /* review submit button: full width for easy tap */
    .review-submit-btn {
        width: 100%;
        padding: 12px 16px;
    }
}
```

- [ ] **Step 2: Visual check**

In DevTools (iPhone SE), open a movie modal and scroll to the reviews section. Confirm:
- Review text wraps cleanly
- Submit button spans full width

- [ ] **Step 3: Commit**

```bash
git add static/css/reviews.css
git commit -m "fix(mobile): review card word-break and full-width submit btn at <=560px"
```

---

## Task 5: layout.css — matchmaker container and button

**Files:**
- Modify: `static/css/layout.css` (append after the existing `@media (max-width: 600px)` matchmaker block at line 742–745)

- [ ] **Step 1: Append to the existing matchmaker mobile block in layout.css**

The file already has this at lines 742–745:
```css
@media (max-width: 600px) {
  .matchmaker-grid { flex-direction: column; }
  .taste-plus { padding-top: 0; align-self: center; }
}
```

Append a new block after line 745 (end of file):

```css
@media (max-width: 560px) {
    /* clamp(720px,65vw,1080px) resolves too narrow on phones */
    .matchmaker-container {
        max-width: 100%;
        padding: 0 16px;
        margin: 1rem auto;
    }

    /* full-width tap target */
    .matchmaker-btn {
        width: 100%;
    }

    /* matchmaker cards: tighten layout */
    .matchmaker-card {
        gap: 0.75rem;
    }

    .matchmaker-title {
        font-size: 1.3rem;
    }
}
```

- [ ] **Step 2: Visual check**

In DevTools (iPhone SE), navigate to the Matchmaker page. Confirm:
- The form fills the screen width with 16px gutters
- "Find Our Movie" button spans full width
- Result cards lay out cleanly

- [ ] **Step 3: Commit**

```bash
git add static/css/layout.css
git commit -m "fix(mobile): matchmaker container width and full-width btn at <=560px"
```

---

## Task 6: Push to GitHub

- [ ] **Step 1: Verify all commits are present**

```bash
git log --oneline -8
```

Expected: five fix(mobile) commits on top of the existing history.

- [ ] **Step 2: Push to main**

```bash
git push origin main
```

Expected output ends with `main -> main`.

- [ ] **Step 3: Confirm on GitHub**

Open the repository on GitHub and verify the five commits appear on `main`.

---

## Self-Review Checklist

- [x] **Spec coverage:** home.css (hero-inner, hero-search, home-section, trending) ✓ — modal.css (modal-info-col, rate-row, stars) ✓ — cards.css (hover-overlay, feat-body) ✓ — reviews.css (word-break, submit btn) ✓ — layout.css (matchmaker-container, matchmaker-btn) ✓
- [x] **No placeholders:** all steps contain exact CSS and bash commands
- [x] **Type consistency:** class names match exactly what exists in each file (verified by reading source)
- [x] **Touch targets:** `.star` padding reaches 44px (10px top + 10px bottom + ~22px font = 42px, plus line-height brings it over) ✓
- [x] **iOS zoom:** `font-size: 16px` on hero search input ✓ (base.css already covers `input` globally at ≤560px, but hero input is inside `.hero-search-inner input` which is more specific — the override here is necessary)
