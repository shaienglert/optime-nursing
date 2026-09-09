export type PublicArticle = {
  slug: string;
  title: string;
  description: string;
  readingTime: string;
  publishedAt: string;
  updatedAt: string;
  sections: Array<{ heading: string; paragraphs: string[] }>;
  faqs: Array<{ question: string; answer: string }>;
  sources?: Array<{ label: string; url: string; note: string }>;
};

export const LAS_VEGAS_MARKET_FACTS = {
  updatedLabel: "September 2026",
  supply: [
    { value: "463", label: "evidence-backed senior-care locations", detail: "440 Nevada-licensed locations plus 23 independently verified independent-living properties." },
    { value: "11,331", label: "licensed beds or places", detail: "Nevada-licensed care inventory only; independent-living apartment capacity is not estimated." },
  ],
  skilledNursing: [
    { value: "66", label: "Nevada CMS-certified nursing homes" },
    { value: "7,235", label: "Nevada CMS-certified nursing-home beds" },
    { value: "2.01%", label: "falls with major injury in Nevada nursing homes" },
    { value: "23.17%", label: "short-stay rehospitalization in Nevada nursing homes" },
  ],
  national: [
    { value: "14,690", label: "U.S. CMS-certified nursing homes" },
    { value: "1,567,504", label: "U.S. CMS-certified nursing-home beds" },
    { value: "3.24%", label: "falls with major injury nationally" },
    { value: "23.75%", label: "short-stay rehospitalization nationally" },
  ],
  populationGrowth: [
    { value: "+11.95%", label: "Nevada population age 65+ projected growth, 2025–2030" },
    { value: "+17.59%", label: "Nevada population age 75+ projected growth, 2025–2030" },
    { value: "+10.69%", label: "U.S. population age 65+ projected growth, 2025–2030" },
    { value: "+20.08%", label: "U.S. population age 75+ projected growth, 2025–2030" },
  ],
} as const;

export const PUBLIC_ARTICLES: PublicArticle[] = [
  {
    slug: "what-supports-a-successful-move-into-senior-living",
    title: "What supports a successful move into senior living?",
    description: "What the research says about adjustment after a move — and the practical questions families should ask before and after move-in.",
    readingTime: "8 min read",
    publishedAt: "2026-09-09",
    updatedAt: "2026-09-09",
    sections: [
      { heading: "A move is a transition, not a transaction", paragraphs: ["Moving into residential care can be stressful for the resident and for family. That does not mean the move is wrong; it means the transition itself needs a plan.", "Research on nursing-home adjustment consistently identifies personal agency, social support, expectations, functional ability and the quality of relationships with staff and other residents as factors associated with adjustment. These are associations, not a guarantee that any one community will produce a particular outcome."] },
      { heading: "The most useful question: what must continue?", paragraphs: ["Before choosing a community, document the routines that make the person feel like themselves: wake and sleep times, favorite music, food rituals, religious practice, preferred language, family contact, bathing routine and activities they choose rather than merely attend.", "A move plan should name who will introduce the resident, who receives the first-week feedback from family and how the community will respond if the person is withdrawing, confused or unhappy."] },
      { heading: "What to measure in the first 30 days", paragraphs: ["Families should ask for a short, agreed check-in cadence. Track participation by choice, sleep, appetite, mobility, contact with family, mood concerns and any new support needs. The aim is not to judge the person for struggling; it is to see early where the plan needs to adapt."] },
    ],
    faqs: [
      { question: "Does a successful move mean the resident immediately joins activities?", answer: "No. Adjustment is individual. A better early signal is whether the person has choice, trusted contact, clear support and an opportunity to reconnect with familiar routines." },
      { question: "Can a community promise a smooth transition?", answer: "No responsible provider can promise that. It can explain its transition process, named contacts and how it monitors and responds to adjustment concerns." },
    ],
    sources: [
      { label: "Factors associated with nursing home adjustment in older adults", url: "https://pubmed.ncbi.nlm.nih.gov/33161332/", note: "2021 study identifying decision-making control, self-efficacy, social support, daily functioning and length of stay as relevant factors." },
      { label: "The adaptation of older adults' transition to residential care", url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC7818340/", note: "Open-access research on the challenges of transition to residential care." },
      { label: "Interventions to improve the transition from home to a nursing home", url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC9372886/", note: "Review of interventions for older people and informal caregivers during transition." },
    ],
  },
  {
    slug: "meaningful-hobbies-and-social-life-in-later-life",
    title: "Meaningful hobbies and social life in later life: what to look for",
    description: "A research-informed guide to activities that fit the person, rather than an activities calendar that looks good on paper.",
    readingTime: "7 min read",
    publishedAt: "2026-09-09",
    updatedAt: "2026-09-09",
    sections: [
      { heading: "The best activity is not universal", paragraphs: ["There is no single list of hobbies that makes a community a good fit. The meaningful activity is the one that connects to a person’s previous interests, identity, energy level and desire for company or quiet.", "The National Institute on Aging recommends continuing activities people enjoy and identifies options such as classes, clubs, volunteering, music, crafts, games and reconnecting with friends. The practical implication for a family is to ask not only whether an activity exists, but how often it happens, who attends and whether the resident can shape it."] },
      { heading: "Build a real preference profile", paragraphs: ["Ask about past and present interests: music, art, gardening, faith, reading, cards, learning, cooking, sport, walking, animals, volunteering, conversation and time outdoors. Also ask what the person dislikes. Avoid treating every resident as someone who wants a crowded calendar.", "For a new resident, one familiar activity or one recurring social anchor can be more useful than ten unfamiliar options listed in a brochure."] },
      { heading: "Questions to ask a community", paragraphs: ["Which activities happen weekly rather than occasionally? Can residents suggest or lead one? Are small groups available? Is transportation provided for community activities? How does the program adapt for hearing, vision, mobility or cognitive changes?"] },
    ],
    faqs: [
      { question: "Are activities only for social residents?", answer: "No. A good program offers choices: small groups, one-to-one engagement, creative work, quiet interests and opportunities to participate without pressure." },
      { question: "Can an activity calendar prove quality?", answer: "No. It shows intent. Ask for examples of actual participation, accessibility and how activities are tailored to residents." },
    ],
    sources: [
      { label: "National Institute on Aging: Participating in activities you enjoy as you age", url: "https://www.nia.nih.gov/health/healthy-aging/participating-activities-you-enjoy-you-age", note: "Public guidance on meaningful social, creative, physical and community activities." },
      { label: "National Institute on Aging: Cognitive health and older adults", url: "https://www.nia.nih.gov/health/brain-health/cognitive-health-and-older-adults", note: "Public guidance highlighting social connection and community programs as ways to address isolation." },
      { label: "The impact of activity interventions on the well-being of older adults", url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC5505561/", note: "Research examining participation in discretionary activities, life satisfaction, isolation and loneliness." },
    ],
  },
  {
    slug: "inclusive-sport-and-movement-for-older-adults-with-disabilities",
    title: "Inclusive sport and movement for older adults with disabilities",
    description: "How families can assess whether an activity is genuinely accessible, adaptable and appropriate for the person.",
    readingTime: "7 min read",
    publishedAt: "2026-09-09",
    updatedAt: "2026-09-09",
    sections: [
      { heading: "Accessibility is more than a ramp", paragraphs: ["A class can be called inclusive and still be unusable if transportation, transfers, equipment, instructions, pace or staff support are not addressed. The relevant question is whether the specific person can participate safely and meaningfully.", "CDC guidance emphasizes discussing barriers, adapting activities to the person’s abilities and avoiding inactivity. It also notes that social support, accessible programs and professionals with relevant knowledge can affect participation."] },
      { heading: "Options may be broader than families expect", paragraphs: ["Depending on ability and clinical guidance, adaptive options can include seated exercise, water-based movement, wheelchair propulsion, hand-cycling, dance, adapted yoga, seated volleyball, swimming and wheelchair sport. The correct choice depends on the person, not a diagnosis label.", "For a new or changed activity, start gradually and consult the relevant clinician or therapist where health risks, recent injury, heart symptoms or major mobility limitations are involved."] },
      { heading: "A practical accessibility check", paragraphs: ["Ask: Can the resident get to the activity? Is the path, restroom and equipment accessible? Is assistance available for transfer or positioning if needed? Can instructions be heard, seen and understood? Is there a smaller or slower option? What happens if fatigue or pain appears?", "This is a fit check, not a medical clearance. A community should be able to explain its actual setup rather than simply say that everyone is welcome."] },
    ],
    faqs: [
      { question: "Do adults with disabilities need to meet the same exercise target as everyone else?", answer: "Public guidance says activity should be consistent with a person’s abilities and that some activity is better than none. The appropriate type and amount should be individualized when needed." },
      { question: "Can a community call a class accessible without adapted equipment?", answer: "Not reliably. Accessibility depends on the individual, the environment, instruction and available support — not the name of the class." },
    ],
    sources: [
      { label: "CDC: Increasing physical activity among adults with disabilities", url: "https://www.cdc.gov/disability-and-health/conditions/physical-activity.html", note: "Public guidance on barriers, individualized activity and examples of adapted activity." },
      { label: "CDC: Resources for facilitating inclusion and overcoming barriers", url: "https://www.cdc.gov/disability-inclusion/resources/index.html", note: "Accessibility and recreation-resource guidance." },
      { label: "NCHPAD disability and inclusion science resources", url: "https://www.nchpad.org/resource-categories/disability-inclusion-science/", note: "Evidence-based disability-inclusion resource hub." },
    ],
  },
  {
    slug: "group-games-for-older-adults-connection-not-just-entertainment",
    title: "Group games for older adults: connection, choice and inclusion",
    description: "How to evaluate cards, board games, trivia, music games and digital games without overstating what they can do.",
    readingTime: "6 min read",
    publishedAt: "2026-09-09",
    updatedAt: "2026-09-09",
    sections: [
      { heading: "Games can create a reason to return", paragraphs: ["A recurring game is often more than entertainment: it can create familiar faces, a role in a group and a low-pressure reason to participate. But games are not a treatment and they are not suitable for everyone.", "Reviews of board games and game-based activities in later life report promising associations with socialization and well-being. The evidence varies by study design, setting and game, so a responsible community should not market a game as a cure for loneliness or cognitive decline."] },
      { heading: "Match the format to the person", paragraphs: ["Some people enjoy cards, dominoes, mahjong, chess or trivia. Others prefer music, storytelling, cooperative puzzles, adapted video games or one-to-one play. Match the format to vision, hearing, dexterity, language, memory, competitiveness and tolerance for noise.", "Offer opt-in participation, clear instructions, large-print or tactile materials when needed, and cooperative formats for people who dislike competition."] },
      { heading: "What to ask before relying on a program", paragraphs: ["Ask how often the group actually meets, whether newcomers are introduced, how staff adapt materials and whether residents with mobility, sensory or cognitive differences can take part. A posted activity is not the same as an inclusive recurring group."] },
    ],
    faqs: [
      { question: "Do games prevent dementia?", answer: "No. Current research does not justify promising prevention from a particular game. Games may be enjoyable and socially engaging, but they are not a substitute for clinical assessment or care." },
      { question: "Are digital games better than table games?", answer: "Not universally. The better format is the one the person can access, enjoys and chooses to return to." },
    ],
    sources: [
      { label: "Aging with board games: fostering well-being in older adults", url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC11608991/", note: "2024 review discussing socialization, quality of life and other outcomes; findings vary across studies." },
      { label: "The social effects of exergames on older adults", url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC6043731/", note: "Review of social-well-being outcomes from exergame studies." },
      { label: "Gamification for older adults: a systematic literature review", url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC8437506/", note: "Systematic review; evidence should not be treated as a clinical promise." },
    ],
  },
  {
    slug: "choosing-the-right-level-of-senior-care-las-vegas",
    title: "How to choose the right level of senior care in Las Vegas",
    description: "A practical way to distinguish independent living, assisted living, memory care and skilled nursing before comparing communities.",
    readingTime: "6 min read",
    publishedAt: "2026-09-09",
    updatedAt: "2026-09-09",
    sections: [
      { heading: "Start with support, not a building", paragraphs: ["The first decision is not which community looks nicest. It is what help is needed safely today: reminders, medication support, bathing and dressing assistance, overnight supervision, memory support, rehabilitation or 24-hour skilled care.", "A person can enjoy an active social setting and still need a higher level of care. A good search separates lifestyle preferences from non-negotiable safety and care requirements."] },
      { heading: "What the common care settings mean", paragraphs: ["Independent living is housing designed for older adults who are largely independent. It may offer meals, activities and transportation, but it is not automatically personal care or 24-hour supervision.", "Assisted living generally combines housing with help for daily activities. Memory care adds a structured, secured approach for people whose memory changes create safety or supervision needs. Skilled nursing is a clinical setting for round-the-clock nursing and rehabilitation needs."] },
      { heading: "Use a decision checklist before touring", paragraphs: ["Write down what must be true on day one: supervision at night, mobility assistance, medication handling, dietary needs, language, budget and distance from family. Then list what would improve quality of life: music, friends, outdoor space, faith community or a larger apartment.", "Ask every community the same questions. If a capability is not documented, treat it as unverified until the community confirms it in writing."] },
    ],
    faqs: [
      { question: "Can independent living provide help with bathing or medications?", answer: "Sometimes through an on-site or outside care provider, but it is not automatic. Confirm who provides the service, when it is available and what it costs." },
      { question: "When is memory care worth considering?", answer: "Consider it when memory changes create a safety, wandering, medication, overnight-supervision or judgment risk. A clinical assessment can help determine the appropriate level of support." },
    ],
  },
  {
    slug: "how-to-verify-a-senior-living-community-before-you-tour",
    title: "How to verify a senior living community before you tour",
    description: "A family checklist for verifying licensing, care claims, staffing conversations and the details that should not be assumed.",
    readingTime: "5 min read",
    publishedAt: "2026-09-09",
    updatedAt: "2026-09-09",
    sections: [
      { heading: "A listing is not proof", paragraphs: ["Directories, advertisements and reviews are useful leads. They are not proof that a community currently offers a specific service, has availability or is appropriate for one person’s needs.", "Start with the state licensing record where a licence applies. Then verify the exact location, care category and current service claim directly with the community."] },
      { heading: "Questions that prevent expensive surprises", paragraphs: ["Ask whether care is delivered by the community or an outside agency, whether help is available overnight, how medication support works, which services are included and which trigger additional charges.", "For a person with memory changes, ask about supervision, transitions between care levels, family communication and what happens if needs change after move-in."] },
      { heading: "Keep the evidence with the comparison", paragraphs: ["Record the answer, the person who gave it and the source. That makes it easier to compare communities fairly and stops a confident sales statement from becoming an assumption."] },
    ],
    faqs: [
      { question: "Does a state licence prove that every advertised service is available?", answer: "No. Licensing establishes a regulated category; service details, availability and pricing still need confirmation from the community." },
      { question: "Should a family rely on online reviews?", answer: "Use reviews as a prompt for questions, not as the sole basis for a placement decision. Verify material claims independently." },
    ],
  },
  {
    slug: "assisted-living-memory-care-and-medicaid-in-nevada",
    title: "Assisted living, memory care and Medicaid in Nevada: questions to ask",
    description: "A clear starting point for families balancing care needs, budget uncertainty and a pending Medicaid decision in Nevada.",
    readingTime: "6 min read",
    publishedAt: "2026-09-09",
    updatedAt: "2026-09-09",
    sections: [
      { heading: "Separate the care decision from the payment decision", paragraphs: ["A limited budget or a pending Medicaid decision is real, but it should not hide an urgent safety requirement. First establish the care level that is safe. Then ask which communities can support the payment path, timing and transition.", "Do not assume that a community accepts a program, has a funded bed or can hold a place while eligibility is pending. These are separate questions that require a current answer."] },
      { heading: "Ask for the full monthly picture", paragraphs: ["Request the base rate, care-level charges, medication-management fees, community fees, deposits, transportation, incontinence care, one-to-one support and any increase triggers. Compare the same assumptions across each option."] },
      { heading: "Create a contingency plan", paragraphs: ["If approval is not yet final, ask what short-term private-pay period is required, whether a payment plan exists and what happens if needs increase. For financial or benefits advice, speak with the relevant Nevada agency or a qualified local adviser."] },
    ],
    faqs: [
      { question: "Does Medicaid automatically pay for any assisted living community?", answer: "No. Coverage, eligibility, program participation, availability and the services covered must all be confirmed for the specific person and community." },
      { question: "Why compare care charges separately from rent?", answer: "The headline monthly price may not include the level of daily support the person actually needs." },
    ],
  },
];

export function articleBySlug(slug: string): PublicArticle | undefined {
  return PUBLIC_ARTICLES.find((article) => article.slug === slug);
}
