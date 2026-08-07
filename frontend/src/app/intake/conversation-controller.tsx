"use client";

import { useEffect, useRef, useState } from "react";

import { TreeOfUnderstanding } from "./tree-of-understanding";

type UnderstandingDomain = {
  id: string;
  label: string;
  hints: string[];
  understood: boolean;
};

type QuestionMode = "single" | "multi" | "input" | "compound";

const UNDERSTANDING_DOMAINS: Omit<UnderstandingDomain, "understood">[] = [
  { id: "person", label: "The person", hints: ["relationship", "age", "gender", "who are you looking"] },
  { id: "care", label: "Care needs", hints: ["assistance", "medical", "memory", "mobility", "daily living"] },
  { id: "lifestyle", label: "Daily life", hints: ["lifestyle", "happiest", "activities", "interests", "independence"] },
  { id: "family", label: "Family & support", hints: ["family", "couple", "grandchildren", "support system"] },
  { id: "culture", label: "Culture & language", hints: ["culture", "language", "faith", "religion", "dietary"] },
  { id: "location", label: "Location", hints: ["location", "distance", "address", "geography"] },
  { id: "budget", label: "Budget", hints: ["budget", "financial", "monthly"] },
];

const MULTI_QUESTION_HINTS = [
  "select all that apply",
  "choose all that apply",
  "choose every answer that applies",
  "which activities",
  "activities make",
  "languages understood",
  "languages do you understand",
  "family languages",
  "faith traditions",
  "religious support needs",
  "what feels like home",
  "dietary preferences",
  "preferred environment",
  "independence interests",
  "hobby participation",
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

function isSelectedButton(button: HTMLButtonElement): boolean {
  if (button.getAttribute("aria-pressed") === "true") return true;
  const className = button.className;
  return /bg-\[#(?:7f9f88|edf6ea|3a8c79|2f7464|1f6f5d|e6f3ee)\]|ring-2/.test(className);
}

function markSelectedButtons(article: HTMLElement): void {
  Array.from(article.querySelectorAll<HTMLButtonElement>("button[type='button']")).forEach((button) => {
    button.dataset.optimeSelected = isSelectedButton(button) ? "true" : "false";
  });
}

function articleHasAnswer(article: HTMLElement): boolean {
  const controls = Array.from(
    article.querySelectorAll<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>("input, textarea, select"),
  );
  if (controls.some(controlHasValue)) return true;

  return Array.from(article.querySelectorAll<HTMLButtonElement>("button")).some(isSelectedButton);
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

function questionMode(article: HTMLElement): QuestionMode {
  const explicitMode = article.dataset.answerMode as QuestionMode | undefined;
  if (explicitMode && ["single", "multi", "input", "compound"].includes(explicitMode)) return explicitMode;

  const text = article.innerText.toLowerCase();
  if (/follow-up questions|decision tree|based on what matters most/.test(text) || article.querySelectorAll("h4").length > 0) {
    return "compound";
  }
  if (MULTI_QUESTION_HINTS.some((hint) => text.includes(hint))) return "multi";

  const hasFreeInput = Boolean(
    article.querySelector("textarea, select, input:not([type='checkbox']):not([type='radio']):not([type='button']):not([type='submit'])"),
  );
  if (hasFreeInput) return "input";

  const optionButtons = article.querySelectorAll<HTMLButtonElement>("button[type='button']");
  if (optionButtons.length > 0) return "single";

  return "input";
}

export function ConversationController({ children }: { children: React.ReactNode }) {
  const rootRef = useRef<HTMLDivElement>(null);
  const currentKeyRef = useRef<string>("");
  const initializedRef = useRef(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [articleCount, setArticleCount] = useState(0);
  const [currentMode, setCurrentMode] = useState<QuestionMode>("input");
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
      markSelectedButtons(article);
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
    setCurrentMode(questionMode(active));
  };

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
      markSelectedButtons(article);
    });

    setCurrentMode(questionMode(articles[resolved]));
    setUnderstanding(deriveUnderstanding(articles));
    articles[resolved].scrollIntoView({ behavior: "smooth", block: "start" });
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
      articles.forEach(markSelectedButtons);
      setUnderstanding(deriveUnderstanding(articles));
    };

    const handleAnswerClick = (event: Event) => {
      const target = event.target instanceof Element ? event.target.closest<HTMLButtonElement>("button[type='button']") : null;
      if (!target) return;

      const articles = Array.from(root.querySelectorAll<HTMLElement>("main article"));
      const activeIndex = articles.findIndex((article) => !article.hidden);
      if (activeIndex < 0) return;
      const active = articles[activeIndex];
      if (!active.contains(target)) return;

      window.setTimeout(() => {
        markSelectedButtons(active);
        setUnderstanding(deriveUnderstanding(articles));
        const mode = questionMode(active);
        setCurrentMode(mode);
        if (mode === "single" && activeIndex < articles.length - 1) {
          moveTo(activeIndex + 1);
        }
      }, 120);
    };

    root.addEventListener("input", refreshUnderstanding);
    root.addEventListener("change", refreshUnderstanding);
    root.addEventListener("click", refreshUnderstanding);
    root.addEventListener("click", handleAnswerClick);

    return () => {
      observer.disconnect();
      root.removeEventListener("input", refreshUnderstanding);
      root.removeEventListener("change", refreshUnderstanding);
      root.removeEventListener("click", refreshUnderstanding);
      root.removeEventListener("click", handleAnswerClick);
    };
    // The controller intentionally owns DOM sequencing for the legacy questionnaire.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
  const showNext = currentMode !== "single" || isLastQuestion;

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

          {showNext ? (
            <button
              type="button"
              onClick={isLastQuestion ? showResults : () => moveTo(currentIndex + 1)}
              disabled={isSearching}
              className="optime-conversation-next"
            >
              {isSearching ? "Preparing results…" : isLastQuestion ? "View recommendations" : "Next"} →
            </button>
          ) : (
            <span className="optime-conversation-auto-hint">Choose an answer to continue</span>
          )}
        </div>
      ) : null}
    </div>
  );
}
