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

type QuestionPosition = {
  articleIndex: number;
  subIndex: number;
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

function markSelectedButtons(element: HTMLElement): void {
  Array.from(element.querySelectorAll<HTMLButtonElement>("button[type='button']")).forEach((button) => {
    button.dataset.optimeSelected = isSelectedButton(button) ? "true" : "false";
  });
}

function elementHasAnswer(element: HTMLElement): boolean {
  const controls = Array.from(
    element.querySelectorAll<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>("input, textarea, select"),
  );
  if (controls.some(controlHasValue)) return true;

  return Array.from(element.querySelectorAll<HTMLButtonElement>("button")).some(isSelectedButton);
}

function deriveUnderstanding(articles: HTMLElement[]): UnderstandingDomain[] {
  return UNDERSTANDING_DOMAINS.map((domain) => {
    const matchingArticles = articles.filter((article) => {
      const text = article.innerText.toLowerCase();
      return domain.hints.some((hint) => text.includes(hint));
    });

    return {
      ...domain,
      understood: matchingArticles.some(elementHasAnswer),
    };
  });
}

function answerMode(element: HTMLElement): QuestionMode {
  const explicitMode = element.dataset.answerMode as QuestionMode | undefined;
  if (explicitMode && ["single", "multi", "input", "compound"].includes(explicitMode)) return explicitMode;

  const text = element.innerText.toLowerCase();
  if (MULTI_QUESTION_HINTS.some((hint) => text.includes(hint))) return "multi";

  const hasFreeInput = Boolean(
    element.querySelector("textarea, select, input:not([type='checkbox']):not([type='radio']):not([type='button']):not([type='submit'])"),
  );
  if (hasFreeInput) return "input";

  const optionButtons = element.querySelectorAll<HTMLButtonElement>("button[type='button']");
  if (optionButtons.length > 0) return "single";

  return "input";
}

function articleMode(article: HTMLElement): QuestionMode {
  const text = article.innerText.toLowerCase();
  if (/follow-up questions|decision tree|based on what matters most/.test(text) || article.querySelectorAll("h4").length > 0) {
    return "compound";
  }
  return answerMode(article);
}

function compoundGroups(article: HTMLElement): HTMLElement[] {
  if (articleMode(article) !== "compound") return [];

  const prompts = Array.from(article.querySelectorAll<HTMLParagraphElement>("p")).filter((prompt) => {
    const text = prompt.textContent?.trim() || "";
    if (!text || text.length > 220) return false;
    const parent = prompt.parentElement;
    if (!parent || parent === article) return false;
    const hasControls = Boolean(parent.querySelector("button[type='button'], input, select, textarea"));
    if (!hasControls) return false;
    const siblingPrompts = Array.from(parent.children).filter((child) => child.tagName === "P");
    return siblingPrompts.length <= 2;
  });

  const groups: HTMLElement[] = [];
  for (const prompt of prompts) {
    const parent = prompt.parentElement;
    if (!parent) continue;
    if (groups.includes(parent)) continue;
    if (groups.some((existing) => existing.contains(parent))) continue;
    groups.push(parent);
  }

  return groups.filter((group) => {
    const nested = groups.filter((candidate) => candidate !== group && group.contains(candidate));
    return nested.length === 0;
  });
}

function clearCompoundVisibility(article: HTMLElement): void {
  compoundGroups(article).forEach((group) => {
    group.hidden = false;
    group.removeAttribute("data-optime-compound-unit");
  });
}

function applyCompoundVisibility(article: HTMLElement, requestedSubIndex: number): { subIndex: number; subCount: number; activeUnit: HTMLElement } {
  const groups = compoundGroups(article);
  if (groups.length <= 1) {
    clearCompoundVisibility(article);
    return { subIndex: 0, subCount: 1, activeUnit: article };
  }

  const subIndex = Math.max(0, Math.min(requestedSubIndex, groups.length - 1));
  groups.forEach((group, index) => {
    const isActive = index === subIndex;
    group.hidden = !isActive;
    group.dataset.optimeCompoundUnit = isActive ? "active" : "inactive";
  });

  return { subIndex, subCount: groups.length, activeUnit: groups[subIndex] };
}

export function ConversationController({ children }: { children: React.ReactNode }) {
  const rootRef = useRef<HTMLDivElement>(null);
  const currentKeyRef = useRef<string>("");
  const currentSubIndexRef = useRef(0);
  const initializedRef = useRef(false);
  const [position, setPosition] = useState<QuestionPosition>({ articleIndex: 0, subIndex: 0 });
  const [articleCount, setArticleCount] = useState(0);
  const [currentSubCount, setCurrentSubCount] = useState(1);
  const [currentMode, setCurrentMode] = useState<QuestionMode>("input");
  const [isSearching, setIsSearching] = useState(false);
  const [understanding, setUnderstanding] = useState<UnderstandingDomain[]>(
    UNDERSTANDING_DOMAINS.map((domain) => ({ ...domain, understood: false })),
  );

  const applyPosition = (requestedArticleIndex?: number, requestedSubIndex?: number) => {
    const root = rootRef.current;
    if (!root) return;

    const articles = Array.from(root.querySelectorAll<HTMLElement>("main article"));
    if (!articles.length) return;

    articles.forEach((article) => {
      article.dataset.conversationQuestion = "true";
      article.dataset.conversationKey = questionKey(article);
      markSelectedButtons(article);
    });

    let articleIndex = typeof requestedArticleIndex === "number" ? requestedArticleIndex : position.articleIndex;
    let subIndex = typeof requestedSubIndex === "number" ? requestedSubIndex : currentSubIndexRef.current;

    if (!initializedRef.current) {
      const budgetIndex = articles.findIndex((article) => article.innerText.toLowerCase().includes("monthly budget"));
      articleIndex = budgetIndex >= 0 ? budgetIndex : 0;
      subIndex = 0;
      initializedRef.current = true;
    } else if (currentKeyRef.current && typeof requestedArticleIndex !== "number") {
      const preservedIndex = articles.findIndex((article) => article.dataset.conversationKey === currentKeyRef.current);
      if (preservedIndex >= 0) articleIndex = preservedIndex;
    }

    articleIndex = Math.max(0, Math.min(articleIndex, articles.length - 1));
    const activeArticle = articles[articleIndex];
    currentKeyRef.current = activeArticle.dataset.conversationKey || questionKey(activeArticle);

    articles.forEach((article, index) => {
      const isActive = index === articleIndex;
      article.hidden = !isActive;
      article.setAttribute("aria-hidden", isActive ? "false" : "true");
      if (!isActive) clearCompoundVisibility(article);
    });

    let activeUnit: HTMLElement = activeArticle;
    let subCount = 1;
    if (articleMode(activeArticle) === "compound") {
      const compound = applyCompoundVisibility(activeArticle, subIndex);
      subIndex = compound.subIndex;
      subCount = compound.subCount;
      activeUnit = compound.activeUnit;
    } else {
      clearCompoundVisibility(activeArticle);
      subIndex = 0;
    }

    markSelectedButtons(activeUnit);
    currentSubIndexRef.current = subIndex;

    const legacyResultsButton = findResultsButton(root);
    if (legacyResultsButton) {
      legacyResultsButton.closest<HTMLElement>("div.mt-8")?.setAttribute("data-legacy-results-action", "true");
    }

    setUnderstanding(deriveUnderstanding(articles));
    setArticleCount(articles.length);
    setCurrentSubCount(subCount);
    setCurrentMode(answerMode(activeUnit));
    setPosition({ articleIndex, subIndex });
  };

  const moveToArticle = (articleIndex: number, enterAtLastSubQuestion = false) => {
    const root = rootRef.current;
    if (!root) return;
    const articles = Array.from(root.querySelectorAll<HTMLElement>("main article"));
    if (!articles.length) return;

    const resolvedArticle = Math.max(0, Math.min(articleIndex, articles.length - 1));
    const target = articles[resolvedArticle];
    const targetGroups = compoundGroups(target);
    const targetSubIndex = enterAtLastSubQuestion && targetGroups.length > 1 ? targetGroups.length - 1 : 0;

    currentKeyRef.current = questionKey(target);
    currentSubIndexRef.current = targetSubIndex;
    applyPosition(resolvedArticle, targetSubIndex);
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const moveForward = () => {
    if (currentSubCount > 1 && position.subIndex < currentSubCount - 1) {
      currentSubIndexRef.current = position.subIndex + 1;
      applyPosition(position.articleIndex, position.subIndex + 1);
      return;
    }
    moveToArticle(position.articleIndex + 1);
  };

  const moveBack = () => {
    if (currentSubCount > 1 && position.subIndex > 0) {
      currentSubIndexRef.current = position.subIndex - 1;
      applyPosition(position.articleIndex, position.subIndex - 1);
      return;
    }
    moveToArticle(position.articleIndex - 1, true);
  };

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    applyPosition();

    const observer = new MutationObserver(() => {
      window.requestAnimationFrame(() => applyPosition());
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
      const activeArticleIndex = articles.findIndex((article) => !article.hidden);
      if (activeArticleIndex < 0) return;
      const activeArticle = articles[activeArticleIndex];
      if (!activeArticle.contains(target)) return;

      const groups = compoundGroups(activeArticle);
      const activeUnit = groups.length > 1 ? groups[currentSubIndexRef.current] || activeArticle : activeArticle;
      if (!activeUnit.contains(target)) return;

      window.setTimeout(() => {
        markSelectedButtons(activeUnit);
        setUnderstanding(deriveUnderstanding(articles));
        const mode = answerMode(activeUnit);
        setCurrentMode(mode);
        if (mode === "single") moveForward();
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

  const isFirstQuestion = position.articleIndex === 0 && position.subIndex === 0;
  const isLastQuestion = articleCount > 0 && position.articleIndex >= articleCount - 1 && position.subIndex >= currentSubCount - 1;
  const showNext = currentMode !== "single" || isLastQuestion;

  return (
    <div ref={rootRef} className="optime-conversation-controller">
      <TreeOfUnderstanding domains={understanding} />

      {children}

      {articleCount > 0 ? (
        <div className="optime-conversation-navigation" aria-label="Question navigation">
          <button type="button" onClick={moveBack} disabled={isFirstQuestion} className="optime-conversation-back">
            ← Back
          </button>

          {showNext ? (
            <button
              type="button"
              onClick={isLastQuestion ? showResults : moveForward}
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
