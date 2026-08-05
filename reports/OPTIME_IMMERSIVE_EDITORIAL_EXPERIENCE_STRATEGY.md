# OPTIME Immersive Editorial Experience Strategy

Status: OWNER REVIEW PROPOSAL - NOT IMPLEMENTED  
Date: 2026-08-02  
Scope: homepage, assessment, recommendation reveal, results, and facility profile visual experience

## Governance Check

- RELEVANT EXISTING PRINCIPLES: PR-003, PR-005, PR-007, PR-008
- DOES THIS CHANGE ALTER ANY PRINCIPLE? NO
- OWNER APPROVAL REQUIRED? NO for proposal production; explicit owner approval is required before implementation
- CLASSIFICATION: B. Implementation Completion, proposal stage only

This proposal does not modify assessment logic, APIs, ranking, evidence states, confidence, eligibility, facility facts, or recommendation order. Photography is presentation. It must not become evidence or affect ranking.

## Executive Recommendation

Adopt a **full-bleed community-life editorial environment with a high-readability glass document**.

One rights-cleared image of authentic older-adult community life fills the viewport and remains visually stable while the assessment document grows above it. The image begins cool, soft, and distant. Meaningful decision-area completion gradually restores focus, color, warmth, and depth. There is no percentage, stage label, or question count.

At readiness, the image reaches natural clarity and the advisor writes:

> I now understand enough about your family's needs to begin finding the communities most likely to fit.

The action is:

**Find My Best Matches**

Recommendations continue below without page replacement. The background crossfades in 320 ms from the generic discovery image to the rights-cleared official hero image of the highest-ranked community. The unknown place becomes a real destination.

## Experience Thesis

The image is no longer a progress widget. It is the emotional environment of the decision.

- The **background** carries atmosphere and the feeling of discovery.
- The **glass document** carries all meaning, choices, retained answers, uncertainty, and controls.
- The **advisor sentence** carries progress.
- The **official facility image** marks the transition from possibility to a real recommendation.

The interface should feel calm enough that the family notices the conversation first and the visual evolution only retrospectively.

## Final Visual Direction

Use **Community Life Editorial Photography** as the primary language. Architecture supports the scene but never becomes its subject.

The previous architecture-led proposal is rejected. Facades, apartment blocks, landscaped real-estate courtyards, and empty lobbies read as property marketing even when they are visually premium. OPTIME should show what families are actually looking for: belonging, dignity, companionship, support, and a daily life that feels human.

### Visual subject hierarchy

- 60% community life: conversation, walking together, reading, games, gardening, shared meals
- 25% purposeful support: rehabilitation, accessible movement, family presence, staff interaction without clinical staging
- 15% place: entrance, courtyard, lobby, garden, and architecture as context

No homepage or assessment hero may be a facade-only image. At least two older adults must be visible, or one older adult must be visibly engaged with another person or a shared community activity.

Required characteristics:

- Older adults visibly participating in ordinary community life
- Natural interaction rather than camera-facing performance
- A shared senior-living environment, not a detached residence
- Accessible path, seating, table, garden, lounge, or rehabilitation context
- Natural light and believable warm interior light
- Architecture remains secondary and cannot occupy more than roughly half the frame
- Editorial framing with crop-safe negative space
- Premium but not luxury-coded
- Warm but not heavily color graded
- No prominent facility branding in generic assessment media
- No posed smiles, celebratory stock gestures, staged caregiver affection, or clinical theater
- No empty facade, apartment-development, hotel, or property-brochure composition

## 1. Complete Image Strategy

### Two separate media systems

#### Discovery library

Generic, properly licensed editorial photographs of older-adult community life used only for homepage and assessment atmosphere. These images are not facilities, candidates, recommendations, or evidence.

#### Facility media library

Official, owner-authorized, public-domain, or otherwise licensed facility-specific media. Each image requires both canonical identity verification and display rights.

The systems may crossfade visually but must remain separate in data, labeling, governance, and claims.

### Session-stable selection

1. Select from `APPROVED` discovery assets only.
2. Prefer a care-context and region-profile match when market information exists.
3. Use a session seed for weighted random selection.
4. Persist the selected asset ID in the existing local assessment draft.
5. Keep the same image through refresh, edits, readiness, and recommendation preparation.
6. Avoid the last three locally viewed assets when alternatives exist.

Random means varied between assessments, not unstable within an assessment.

### Region-profile selection without state hardcoding

Selection uses metadata rather than `if state === ...` branches:

- climate: arid, subtropical, coastal, temperate, humid, cold-season
- landscape: xeriscape, palms, live oak, broadleaf, evergreen, prairie
- density: campus, suburban, mid-rise urban, dense urban
- architecture: stucco, masonry, timber, glass, shaded arcade, deep overhang
- light: bright-dry, humid-soft, coastal, seasonal
- care context: assisted living, skilled nursing, rehabilitation, mixed continuum

A market resolves to a region profile through configuration. New markets add metadata, not code branches.

### Progressive image treatment

The source composition never changes during assessment. Faces are never isolated as blur targets. Early softness applies to the whole environment; human silhouettes remain recognizable as people from the first state.

| Experience state | Blur | Brightness | Saturation | Contrast | Warm overlay | Depth treatment |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Initial | 16 px | 72% | 58% | 82% | 0% | full-frame atmospheric veil |
| Situation understood | 13 px | 76% | 64% | 86% | 1% | entrance receives broad clarity |
| Daily support understood | 10 px | 81% | 70% | 90% | 2% | facade and path separate |
| Clinical/rehabilitation understood | 7 px | 87% | 78% | 94% | 4% | garden foreground restores |
| Logistics understood | 4 px | 92% | 86% | 97% | 6% | windows and interior depth appear |
| Priorities understood | 2 px | 97% | 93% | 99% | 8% | subtle signs of life become legible |
| Ready | 0 px | 100% | 100% | 100% | 10% local only | entrance light settles |

Transitions use 700-1100 ms ease-out and never move more than 2 px. There is no bounce, zoom, pulse, or loop.

### AI status sentence

Only one sentence is visible. It maps to the current meaningful decision area and must not claim an operation that is not happening.

Approved family:

- Understanding your family's situation...
- Comparing levels of daily support...
- Reviewing rehabilitation priorities...
- Considering location and family access...
- Understanding everyday preferences...
- Considering the information that matters most...
- Preparing your personalized recommendations...

The outgoing sentence fades for 120 ms; the incoming sentence fades for 180 ms. Reduced-motion mode switches immediately.

Do not use "Checking verified evidence..." during ordinary question answering. That wording is allowed only after recommendation preparation actually begins.

## 2. Homepage Visual Redesign

The current homepage is the beginning of the assessment. Preserve that directness: do not introduce a marketing landing page before the task.

### First viewport

- Full-bleed approved community photograph
- Header floats over the image with a quiet translucent surface
- One glass introduction panel, left aligned on desktop and bottom aligned on mobile
- Brand/product name remains a first-viewport signal
- Literal offer headline: "Find the community that fits your family."
- Supporting copy explains that OPTIME asks only what meaningfully improves the recommendation
- Primary action: "Begin with what matters"
- A visible hint of the living document appears below the fold

### Tone

No trust-icon row, feature badges, marketing statistics, or illustrative decoration. The real environment and precise copy carry confidence.

## 3. Assessment Mockup Strategy

### Desktop

- Full viewport background supplied by a fixed media layer, not CSS `background-attachment: fixed`
- The image uses `position: fixed; inset: 0` with a viewport-safe cover crop
- A subtle edge vignette protects text without darkening the subject
- Living document width: `min(760px, calc(100vw - 96px))`
- Document aligned left at 7-10vw, with at least 80px top clearance
- Glass surface: `rgba(255,255,252,0.86)` to `0.92` depending on image luminance
- Backdrop blur: 10-14 px maximum
- Radius: 24 px desktop
- Shadow: broad, low-opacity, no hard border
- Inner padding: 48-64 px
- Completed answers remain in chronological order
- The active question appends beneath them
- The panel grows naturally; it is not vertically centered after the first viewport

### Mobile

- Background remains a fixed pseudo-layer, not `background-attachment`
- Stable mobile crop uses asset focal-point metadata
- Glass document occupies full width minus 12-16 px gutters
- Surface opacity increases to `0.93-0.96` for readability
- Backdrop blur decreases to 6-8 px for GPU cost
- Radius: 20 px
- Padding: 24 px
- Background receives an additional 12-18% neutral veil
- Inputs and choices remain at least 48 px high
- No sticky image or separate progress surface competes with the question

### Long document behavior

- The document grows in normal page flow
- The background remains fixed behind it
- Completed questions and answers never disappear
- Editing occurs in place
- Scrolling is native and uninterrupted
- Glass is one continuous document surface, not a stack of nested cards
- On very long sessions, the glass panel remains performant because blur is applied to one ancestor, not every answer block

## 4. Results Page Mockup Strategy

Recommendations continue below the completed assessment in the same page.

### Transition sequence

1. The assessment background reaches full clarity.
2. The exact readiness sentence and action appear.
3. After activation, advisor comparison prose appends below.
4. The top recommendation data resolves.
5. If a rights-cleared official hero is available, preload and decode it.
6. Crossfade from generic discovery image to official hero in 320 ms.
7. Keep the image fixed while the first recommendation enters the document.
8. Label it "Official community photography" with source details available.

No route replacement, image wipe, zoom, skeleton flash, or scroll jump.

### Recommendation composition

- First recommendation receives an editorial introduction, not a dense dashboard card
- Facility name and location lead
- "Why OPTIME believes this community fits" follows in prose
- Verified information and information still being verified remain visually separate
- Technical evidence stays available in a disclosure below the family-facing narrative
- Comparison controls appear after the first recommendation, not before it
- Subsequent recommendations continue as generous editorial sections

The current top-five decision table remains available, but moves after the narrative recommendations and is labeled as a detailed comparison view.

## 5. Facility Page Mockup Strategy

Every facility profile begins with a large editorial hero image.

### Hero

- Desktop: 70-82vh, full width, image first
- Mobile: 62vh minimum, 4:5 or 3:4 crop
- Facility name, city, state, and type appear in a bottom glass title surface
- Media label identifies rights/source state
- No thumbnail or split gray placeholder
- No claim that visual quality represents care quality

### Content order

1. Why OPTIME believes this community fits
2. Verified information
3. Information still being verified
4. Lifestyle
5. Rehabilitation
6. Dining
7. Activities
8. Location
9. Map
10. Official photo gallery

Evidence remains inspectable from every verified statement. Unknown information stays explicit and neutral.

### Gallery behavior

- Gallery never leads the page
- Every image has scene type, source, rights state, and verification date
- Facility-specific categories never use generic substitutes
- Low-resolution assets render at natural size in a restrained layout; they are never stretched into a hero

## 6. Recommended Photography Library

Launch with **24 approved discovery images**, organized as 12 paired stories. This exceeds the 20-image minimum. The entries below are acquisition briefs until a specific file clears licensing and quality review.

| IDs | Category | Story A | Story B | Regional profiles |
| --- | --- | --- | --- | --- |
| IE-01/02 | Welcome and Belonging | two residents greeting each other in a shared lounge | family arrival in a warm reception | universal / universal |
| IE-03/04 | Shared Conversation | small resident group in natural conversation | two friends talking by a bright window | universal / urban |
| IE-05/06 | Garden Life | residents gardening together | quiet conversation in a planted courtyard | temperate / arid |
| IE-07/08 | Walking Together | three residents on an accessible garden path | two residents resting along a shaded route | temperate / warm inland |
| IE-09/10 | Dining Together | residents sharing an ordinary lunch | small-table conversation in a daylit dining room | universal / coastal |
| IE-11/12 | Games and Interests | outdoor card or mahjong game | residents learning or creating together | subtropical / urban |
| IE-13/14 | Movement and Wellness | small chair exercise group | residents preparing for a gentle outdoor activity | universal / warm |
| IE-15/16 | Rehabilitation | therapist and resident moving through a bright non-clinical space | accessible courtyard movement | universal / coastal |
| IE-17/18 | Family Connection | adult child visiting in a shared garden | quiet multigenerational conversation | universal / universal |
| IE-19/20 | Everyday Independence | resident reading in a shared lounge | resident choosing a garden route | universal / temperate |
| IE-21/22 | Small Community | familiar group around a table | residents in an intimate boutique garden | temperate / arid |
| IE-23/24 | Place in Context | occupied community entrance | residents visible within a warm courtyard | universal / regional |

### Quality gate

Each source must pass:

- Minimum 3000 px long edge; preferred 5000 px
- Sharp focal subject at natural viewing size
- Natural daylight or believable interior light
- No obvious AI artifacts or heavy retouching
- No private-home reading
- No hospital reading
- No real-estate, apartment-development, hotel, or facade-first reading
- Human connection is legible before architectural style
- Accessible route or circulation visible where architecture is shown
- Desktop and mobile crop approval
- Sufficient dark/light range for all reveal states
- No text or logos in crop-critical regions
- No sensitive or demeaning depiction
- Model and property releases when required

## 7. Licensing Strategy

### Preferred acquisition order

1. Commissioned OPTIME photography with global digital rights
2. Facility-supplied originals under explicit OPTIME display permission
3. Premium stock with documented commercial web/app license
4. Public-domain sources with verified provenance
5. Internally commissioned photorealistic render only when photography cannot meet a regional need

### Required asset record

- immutable asset ID and checksum
- original filename and source URL
- creator, owner, licensor, and acquisition date
- rights basis and stored license snapshot
- channels, territories, term, edit rights, derivative rights, and attribution
- model/property release state
- sensitive-use approval
- discovery-generic or facility-specific classification
- facility canonical ID when specific
- identity match evidence when specific
- region-profile tags
- desktop and mobile focal coordinates
- minimum safe crop and maximum rendered dimensions
- alt text and decorative/meaningful classification
- reviewer, approval date, expiration, and takedown state

### Policy conflict to resolve before implementation

The current media acquisition policy specifies neutral/text-only fallbacks and says not to substitute a generic entrance for a facility. The new owner direction requests a premium regional lifestyle fallback.

Recommended resolution:

- Permit a regional image only as an explicitly labeled **non-facility atmospheric fallback**.
- Never label it official, place it in the official gallery, or use it as facility evidence.
- Overlay exactly: "Official community photography is currently being verified."
- Include hidden accessible text: "This regional image does not depict this community."
- Keep the facility name and evidence content outside the image.
- Update `OPTIME_MEDIA_ACQUISITION_POLICY.md` only after owner approval of this proposal.

This preserves the new visual experience without creating a misleading media claim.

## 8. Accessibility Review

### Readability

- Glass surface must maintain at least 4.5:1 text contrast under every approved image and state
- Use adaptive surface opacity based on measured image luminance, not manually guessed per page
- Body copy minimum 18 px desktop and 17 px mobile in the assessment
- Never place essential copy directly over photography without the glass surface
- Focus indicators remain visible against both glass and imagery

### Motion

- `prefers-reduced-motion: reduce` disables filter interpolation, crossfade, and parallax
- State changes remain visible through immediate blur/color/brightness differences
- Official-image replacement occurs immediately after decode in reduced-motion mode
- No continuous motion exists in either mode

### Semantics

- Generic background is decorative when the same meaning is stated in text
- If exposed to assistive technology, describe it as a representative community image
- Official facility hero alt text names the facility and scene only when identity is verified
- Regional fallback alt text states that it is regional atmosphere and not the facility
- AI status uses `aria-live="polite"` and does not announce intermediate fade states
- The fixed background is removed from keyboard and reading order

### Cognitive accessibility

- Background blur never affects the glass document itself
- One progress sentence only
- No percentages, stages, question counts, spinners, or loading dots
- Retained answers preserve orientation and reduce memory burden
- The user can pause, refresh, and resume without image or document discontinuity

### Forced colors and contrast preferences

- In forced-colors mode, remove background photography and blur; render an opaque document with system colors
- Under `prefers-contrast: more`, raise glass opacity to 0.98 and disable image warmth behind the document
- Controls retain native borders when required by the operating system

## 9. Performance Impact Analysis

### Primary risks

- Large full-viewport images can become Largest Contentful Paint
- CSS blur on a fixed full-screen image can increase GPU memory and repaint cost
- `backdrop-filter` over a long scrolling panel can be expensive
- Crossfading two high-resolution images temporarily doubles decoded image memory
- Mobile Safari handles fixed backgrounds and backdrop filters inconsistently

### Recommended implementation architecture

- Use a fixed `<picture>` layer, not CSS `background-image`
- Serve AVIF first, WebP fallback, JPEG final fallback
- Provide width variants at 640, 960, 1280, 1600, and 2200 px
- Use `sizes="100vw"` and focal-aware `object-position`
- Preload only the selected initial discovery image
- Apply blur to the image element once; do not generate seven image files
- Use one glass ancestor for the document
- On lower-powered devices, replace `backdrop-filter` with a nearly opaque translucent fill
- Decode the official result image before beginning the crossfade
- Remove the outgoing bitmap from the DOM immediately after transition

### Budgets

| Asset/metric | Mobile target | Desktop target |
| --- | ---: | ---: |
| Initial discovery image transfer | <= 220 KB | <= 480 KB |
| Official hero transfer | <= 260 KB | <= 550 KB |
| Decoded images during crossfade | <= 2 | <= 2 |
| LCP p75 on target connection | <= 2.5 s | <= 2.5 s |
| CLS | <= 0.05 | <= 0.05 |
| INP | <= 200 ms | <= 200 ms |
| Glass layers with backdrop blur | 1 | 1 |
| Concurrent filter animations | 1 | 1 |

### Loading behavior

- Reserve image dimensions before load
- Use a dominant-color wash derived from the selected asset, never gray
- Do not show a spinner or blur-up that looks like assessment progress
- The intentional initial softness begins only after the source is decoded; loading and reveal state must be distinguishable internally
- If the image fails, use an approved warm regional color field with the same readable glass surface and log the media failure; do not stretch a low-quality file

## 10. Final Recommendation Before Implementation

Approve the **Immersive Editorial Environment** with these conditions:

1. Community Life Editorial Photography is the primary discovery language.
2. The glass document uses high opacity for readability; immersion must never reduce comprehension.
3. The existing living-document behavior remains unchanged.
4. Progress is represented by one truthful advisor sentence and subtle image treatment only.
5. Generic and facility-specific media remain governed separately.
6. Regional fallback is explicitly labeled as not depicting the facility.
7. The current media policy is amended only after design approval.
8. A three-image, three-market prototype is tested before acquiring the full 24-image library.
9. Browser validation includes low-power mobile, reduced motion, high contrast, and forced colors.
10. No media metadata enters ranking, eligibility, evidence confidence, or recommendation order.

## Final Experience Audit

### Homepage

- Actual task begins immediately
- Community imagery is the first emotional signal
- No marketing detour or dashboard framing

### Assessment

- One growing glass document
- Fixed, slowly clarifying environment
- No form progress mechanics
- Questions and answers remain visible

### Recommendation reveal

- Same page and same scroll context
- Generic possibility becomes a verified real destination through crossfade
- Unknowns remain visible and neutral

### Facility profile

- Editorial hero first
- Patient fit and evidence before gallery browsing
- Official media clearly distinguished from regional fallback

### Brand result

The proposed system is emotionally closer to Apple, Airbnb, Notion, and Aesop because it uses disciplined photography, generous space, quiet transitions, and precise language. It moves away from insurance, hospital, and government-portal cues by removing progress instrumentation, gray placeholders, dense dashboard framing, and decorative illustrations.

## Approval Gate

No implementation is authorized by this document. Owner approval should explicitly cover:

- full-bleed fixed environment
- high-opacity glass document
- Community Life Editorial Photography direction
- 320 ms generic-to-official crossfade
- labeled regional fallback policy
- three-image prototype before full library acquisition