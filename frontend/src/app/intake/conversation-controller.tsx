"use client";

import { useEffect, useRef, useState } from "react";

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

export function ConversationController({ children }: { children: React.ReactNode }) {
  const rootRef = useRef<HTMLDivElement>(null);
  const currentKeyRef = useRef<string>("");
  const initializedRef = useRef(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [articleCount, setArticleCount] = useState(0);
  const [isSearching, setIsSearching] = useState(false);

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
    observer.observe(root, { childList: true, subtree: true });

    return () => observer.disconnect();
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
  const progress = articleCount > 0 ? Math.round(((currentIndex + 1) / articleCount) * 100) : 0;

  return (
    <div ref={rootRef} className="optime-conversation-controller">
      <div className="optime-conversation-progress" aria-label={`Questionnaire progress: ${progress}%`}>
        <span style={{ width: `${progress}%` }} />
      </div>

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

          <span className="optime-conversation-count">
            {currentIndex + 1} of {articleCount}
          </span>

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
