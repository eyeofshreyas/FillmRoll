# Mobile UI Optimization — Design Spec
**Date:** 2026-04-19  
**Approach:** Option A — Targeted patch pass  
**Breakpoint:** ≤560px (phones only; tablets retain desktop layout)  
**Target:** 360–430px wide phones (iPhone SE → iPhone 15 / Pixel 7)

---

## Scope

Additive `@media (max-width: 560px)` blocks added to four CSS files. No existing rules removed. No new files created.

Files touched:
- `static/css/home.css`
- `static/css/modal.css`
- `static/css/cards.css`
- `static/css/reviews.css`
- `static/css/layout.css` (matchmaker section)

Files confirmed complete, no changes needed:
- `static/css/base.css`
- `static/css/ai.css`
- `static/css/layout.css` (header, footer, bottom nav, hero already patched)

---

## Changes by File

### home.css
- `.hero-inner`: `max-width: 100%` (overrides clamp that resolves too narrow on phones)
- Hero search input: `font-size: 16px` (iOS auto-zoom prevention)
- Hero search box: `max-width: 100%`
- Mood grid / genre section: `padding: 0 16px`
- Trending card width: `130px` (down from ~160px for better thumb reach on small screens)

### modal.css
- `.modal-info-col`: padding `22px 24px` → `14px 16px`
- `.modal-rate-row`: padding `16px 24px` → `12px 16px`; star elements get `padding: 10px 4px` to reach 44px tap target (up from ~22px rendered size)

### cards.css
- `.card-hover-overlay`: `display: none` on mobile (hover overlays don't trigger on touch; tapping card opens modal directly)
- `.feat-body`: padding `28px 30px` → `14px 16px`

### reviews.css
- Review card container: `padding: 0 16px`
- Review text: `word-break: break-word` (prevents long strings overflowing narrow screens)

### layout.css — matchmaker
- `.matchmaker-container`: `max-width: 100%; padding: 0 16px` (overrides clamp that resolves too narrow)
- `.matchmaker-btn`: `width: 100%` (full-width tap target on mobile)

---

## Touch Target Rule
All interactive elements must meet 44×44px minimum. Changes above address the two violations found (stars, modal info padding).

---

## What Is NOT Changing
- Login page (already responsive)
- Header (already simplified at ≤560px)
- Bottom nav (already complete)
- AI chat panel and FAB (already complete)
- Footer (already complete)
- JS — no JavaScript changes required

---

## Delivery
Single git commit, pushed to `main` on GitHub.
