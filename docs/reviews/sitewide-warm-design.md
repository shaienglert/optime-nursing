# Sitewide warm design

Classification: B — owner-approved extension of the accepted forest/lifestyle design.
RELEVANT EXISTING PRINCIPLES: PR-001, PR-002, PR-003, PR-005, PR-009.
DOES THIS CHANGE ALTER ANY PRINCIPLE? NO.
OWNER APPROVAL REQUIRED? NO.

A shared Tailwind palette defines cream canvas, white surfaces, sand, graphite,
muted text, deep forest actions, warm borders and coral. Public, provider and
administrative screens use it, including loading/error states, comparison
dialogs and legacy results/profile renderers. Decorative panels share soft
shadows and 24px corners. Forms retain explicit labels, focus rings, keyboard
access and larger touch targets. The site retains the accepted light palette
regardless of OS color mode, avoiding mixed light/dark surfaces. Reduced motion,
high contrast focus and text scaling remain supported.

Saved conversations, profiles and guides use calm human introductions and
honest empty-state copy. Operational tools retain exact technical/status labels.
Warning/error colors and evidence/status text are preserved. Existing generated
lifestyle illustrations remain visibly labelled on the home page; no generic
photo is introduced as evidence about a community. No matching, ranking,
eligibility, provider approval, pricing or API contract changes.

Validation: Next production build/TypeScript and owned-UI guard passed; 14
existing guidance, eligibility and budget tests passed. New error/not-found and
shared home/header/guidance lint passed. All changed existing TSX files have
13 pre-existing lint errors, the same per-file/rule counts as the base, with
no new errors (hooks/refs and existing unescaped text).

Local Chromium checked 17 routes at 1440px and 390px, including A+ text scaling,
with no document overflow or page errors. It also passed home → intake and
confirmed summary → results → visit request, plus community → total-pricing
follow-up. Screens with unavailable backend data were checked as unavailable
states; provider and partner sign-in views were checked, not full authenticated
workspaces. These are local UI fixtures, not live production or AI-quality QA.
Removed logo scaling that caused mobile partner sign-in overflow. Warning and
error colors were adjusted for readable contrast on the new light canvas.
