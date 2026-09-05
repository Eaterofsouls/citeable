# Citeable UI Overhaul Walkthrough

All requested visual updates have been successfully implemented and tested for regression using Playwright screenshots. Here's a breakdown of the changes:

## 1. Unified Grid & Spacing (Phase 3)
- **48px Margins:** Replaced the inconsistent 32px/44px alternation across the site with a clean, unified `48px` global layout spacing.
- **Card Border Radiuses:** Increased border radius on cards (scorecards, claim rows, summary pane) to `12px` (up from 6px/8px), giving them a much more premium, modern feel.
- **Consistent Scorecards:** Removed inline styles that were forcing the scorecards to be uneven sizes. All 4 score cards now display evenly.
- **Button Sizing:** Removed the `!important` padding and size overrides on buttons, allowing them to scale properly with the new typography system.

## 2. Stepper Improvements
- **Larger Touch Targets:** The stepper at the top of the Audit Studio has been enlarged. The step dots are now `36px` tall and wide (up from 30px) with larger font sizes, making them much more legible and providing a much better touch target for mobile devices.

## 3. Help & Onboarding Overlay (Phase 6)
- **New Onboarding:** Added a clean, 4-step onboarding overlay (`help.js`) that automatically triggers for first-time visitors. It walks users through the platform (Getting Started, BYOK Vault, Running an Audit, Reviewing Results).
- **Floating Action Button:** When dismissed, the overlay gracefully minimizes to a `?` Floating Action Button fixed to the bottom right of the screen, allowing users to re-open the tutorial at any time.

## 4. Documentation Polish (Phase 5)
- **Sticky TOC:** The "On this page" right-rail table of contents is now properly sticky (`position: sticky`), keeping it accessible as users scroll down the dense documentation.
- **Image Fullscreen Viewer:** We added an overlay to all `img` tags and Mermaid `svg` diagrams in the documentation. When users hover over any image, a small `⛶ Fullscreen` button appears. Clicking it launches the image into a cinematic, full-screen modal so complex diagrams can be read easily.

## 5. Synthesis Results Rendering
- **Markdown Rendering:** The final synthesis report in the Audit Studio (which was previously dumped into a preformatted text block) is now parsed and styled beautifully into standard HTML markup using `marked.js` and our `.markdown-body` CSS component styling.

All these changes harmonize with the brand new typography system (Space Grotesk + DM Sans) you implemented, resulting in a significantly sleeker and more coherent user experience.
