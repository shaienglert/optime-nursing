"use client";

import { useEffect, useRef, useState } from "react";

import { TreeOfUnderstanding } from "./tree-of-understanding";

type UnderstandingDomain = {
  id: string;
  label: string;
  hints: string[];
  understood: boolean;
};

const UNDERSTANDING_DOMAINS: Omit<UnderstandingDomain, "understood">[] = [
  { id: "person", label: "The person", hints: ["relationship", "age", "gender", "who are you looking"] },
  { id: "care", label: "Care needs", hints: ["assistance", "medical", "memory", "mobility", "daily living"] },
  { id: "lifestyle", label: "Daily life", hints: ["lifestyle", "happiest", "activities", "interests", "independence"] },
  { id: "family", label: "Family & support", hints: ["family", "couple", "grandchildren", "support system"] },
  { id: "culture", label: "Culture & language", hints: ["culture", "language", "faith", "religion", "dietary"] },
  { id: "location", label: "Location", hints: ["location", "distance", "address", "geography"] },
  { id: "budget", label: "Budget", hints: ["budget", "financial", "monthly"] },
];

function questionKey(article: HTMLElement): string {
  const heading = article.querySelector("h3, h4")?.textContent?.trim();
  return heading || article.innerText.trim().slice(0, 120);
}

function findResultsButton(root: HTMLElement): HTMLButtonElement | null {
  return (
    Array.from(root.querySelectorAll<HTMLButtonElement>("button")).find((button) =>
      /view my recommendations|recommendations|find.*home/i.test(button.textContent || ""),
    ) || null
  );
}

function controlHasValue(control: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement): boolean {
  if (control instanceof HTMLInputElement && (control.type === "checkbox" || control.type === "radio")) {
    return control.checked;
  }
  return control.value.trim().length > 0;
}

function articleHasAnswer(article: HTMLElement): boolean {
  const controls = Array.from(
    article.querySelectorAll<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>("input, textarea, select"),
  );
  if (controls.some(controlHasValue)) return true;

  return Array.from(article.querySelectorAll<HTMLButtonElement>("button")).some((button) => {
    if (button.getAttribute("aria-pressed") === "true") return true;
    const className = button.className;
    return /bg-\[#(?:3a8c79|2f7464|1f6f5d|e6f3ee)\]|font-bold|ring-2/.test(className);
  });
}

function deriveUnderstanding(articles: HTMLElement[]): UnderstandingDomain[] {
  return UNDERSTANDING_DOMAINS.map((domain) => {
    const matchingArticles = articles.filter((article) => {
      const text = article.innerText.toLowerCase();
      return domain.hints.some((hint) => text.includes(hint));
    });

    return {
      ...domain,
      understood: matchingArticles.some(articleHasAnswer),
    };
  });
}

export function ConversationController({ children }: { children: React.ReactNode }) {
  const rootRef = useRef<HTMLDivElement>(null);
  const currentKeyRef = useRef<string>("");
  const initializedRef = useRef(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [articleCount, setArticleCount] = useState(0);
  const [isSearching, setIsSearching] = useState(false);
  const [understanding, setUnderstanding] = useState<UnderstandingDomain[]>(
    UNDERSTANDING_DOMAINS.map((domain) => ({ ...domain, understood: false })),
  );

  const applyCurrentQuestion = (requestedIndex?: number) => {
    const root = rootRef.current;
    if (!root) return;

    const articles = Array.from(root.querySelectorAll<HTMLElement>("main article"));
    if (!articles.length) return;

    articles.forEach((article) => {
      article.dataset.conversationQuestion = "true";
      article.dataset.conversationKey = questionKey(article);
    });

    let resolvedIndex = typeof requestedIndex === "number" ? requestedIndex : currentIndex;

    if (!initializedRef.current) {
      const budgetIndex = articles.findIndex((article) =>
        article.innerText.toLowerCase().includes("monthly budget"),
      );
      resolvedIndex = budgetIndex >= 0 ? budgetIndex : 0;
      initializedRef.current = true;
    } else if (currentKeyRef.current) {
      const preservedIndex = articles.findIndex(
        (article) => article.dataset.conversationKey === currentKeyRef.current,
      );
      if (preservedIndex >= 0) resolvedIndex = preservedIndex;
    }

    resolvedIndex = Math.max(0, Math.min(resolvedIndex, articles.length - 1));
    const active = articles[resolvedIndex];
    currentKeyRef.current = active.dataset.conversationKey || questionKey(active);

    articles.forEach((article, index) => {
      const isActive = index === resolvedIndex;
      article.hidden = !isActive;
      article.setAttribute("aria-hidden", isActive ? "false" : "true");
    });

    const legacyResultsButton = findResultsButton(root);
    if (legacyResultsButton) {
      legacyResultsButton.closest<HTMLElement>("div.mt-8")?.setAttribute("data-legacy-results-action", "true");
    }

    setUnderstanding(deriveUnderstanding(articles));
    setArticleCount(articles.length);
    setCurrentIndex(resolvedIndex);
  };

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    applyCurrentQuestion();

    const observer = new MutationObserver(() => {
      window.requestAnimationFrame(() => applyCurrentQuestion());
    });
    observer.observe(root, { childList: true, subtree: true, attributes: true, attributeFilter: ["class", "aria-pressed"] });

    const refreshUnderstanding = () => {
      const articles = Array.from(root.querySelectorAll<HTMLElement>("main article"));
      setUnderstanding(deriveUnderstanding(articles));
    };

    root.addEventListener("input", refreshUnderstanding);
    root.addEventListener("change", refreshUnderstanding);
    root.addEventListener("click", refreshUnderstanding);

    return () => {
      observer.disconnect();
      root.removeEventListener("input", refreshUnderstanding);
      root.removeEventListener("change", refreshUnderstanding);
      root.removeEventListener("click", refreshUnderstanding);
    };
    // The controller intentionally owns DOM sequencing for the legacy questionnaire.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const moveTo = (nextIndex: number) => {
    const root = rootRef.current;
    if (!root) return;
    const articles = Array.from(root.querySelectorAll<HTMLElement>("main article"));
    if (!articles.length) return;

    const resolved = Math.max(0, Math.min(nextIndex, articles.length - 1));
    currentKeyRef.current = questionKey(articles[resolved]);
    setCurrentIndex(resolved);

    articles.forEach((article, index) => {
      const isActive = index === resolved;
      article.hidden = !isActive;
      article.setAttribute("aria-hidden", isActive ? "false" : "true");
    });

    setUnderstanding(deriveUnderstanding(articles));
    articles[resolved].scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const showResults = () => {
    const root = rootRef.current;
    if (!root) return;
    const resultsButton = findResultsButton(root);
    if (!resultsButton) return;

    setIsSearching(true);
    resultsButton.disabled = false;
    resultsButton.click();
    window.setTimeout(() => setIsSearching(false), 5000);
  };

  const isLastQuestion = articleCount > 0 && currentIndex >= articleCount - 1;

  return (
    <div ref={rootRef} className="optime-conversation-controller">
      <TreeOfUnderstanding domains={understanding} />

      {children}

      {articleCount > 0 ? (
        <div className="optime-conversation-navigation" aria-label="Question navigation">
          <button
            type="button"
            onClick={() => moveTo(currentIndex - 1)}
            disabled={currentIndex === 0}
            className="optime-conversation-back"
          >
            ← Back
          </button>

          <button
            type="button"
            onClick={isLastQuestion ? showResults : () => moveTo(currentIndex + 1)}
            disabled={isSearching}
            className="optime-conversation-next"
          >
            {isSearching ? "Preparing results…" : isLastQuestion ? "View recommendations" : "Next"} →
          </button>
        </div>
      ) : null}
    </div>
  );
}
