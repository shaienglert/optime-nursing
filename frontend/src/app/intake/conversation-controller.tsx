"use client";

import { useEffect, useRef, useState } from "react";

const MULTI_SELECT_HINTS = [
  "select all that apply",
  "activities",
  "languages understood",
  "family languages",
  "faith traditions",
  "religious support",
  "what feels like home",
  "dietary preferences",
  "preferred environment",
  "interests",
];

function isMultiSelect(article: HTMLElement): boolean {
  const text = article.innerText.toLowerCase();
  return MULTI_SELECT_HINTS.some((hint) => text.includes(hint));
}

function isSingleChoiceButton(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) return false;
  const button = target.closest("button");
  if (!(button instanceof HTMLButtonElement)) return false;
  if (button.type === "submit") return false;
  return true;
}

export function ConversationController({ children }: { children: React.ReactNode }) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [articleCount, setArticleCount] = useState(0);
  const [currentIsMulti, setCurrentIsMulti] = useState(false);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    let articles: HTMLElement[] = [];

    const refresh = () => {
      articles = Array.from(root.querySelectorAll<HTMLElement>("main article"));
      if (!articles.length) return;

      setArticleCount(articles.length);

      const budgetIndex = articles.findIndex((article) =>
        article.innerText.toLowerCase().includes("monthly budget"),
      );

      setCurrentIndex((previous) => {
        const resolved = previous === 0 && budgetIndex >= 0 ? budgetIndex : Math.min(previous, articles.length - 1);
        articles.forEach((article, index) => {
          article.dataset.conversationQuestion = "true";
          article.hidden = index !== resolved;
          article.setAttribute("aria-hidden", index === resolved ? "false" : "true");
        });
        setCurrentIsMulti(isMultiSelect(articles[resolved]));
        return resolved;
      });
    };

    refresh();

    const observer = new MutationObserver(refresh);
    observer.observe(root, { childList: true, subtree: true });

    const handleClick = (event: MouseEvent) => {
      const article = (event.target as Element | null)?.closest<HTMLElement>("article[data-conversation-question='true']");
      if (!article || article.hidden) return;
      if (isMultiSelect(article)) return;
      if (!isSingleChoiceButton(event.target)) return;

      window.setTimeout(() => {
        setCurrentIndex((previous) => Math.min(previous + 1, Math.max(0, articles.length - 1)));
      }, 180);
    };

    root.addEventListener("click", handleClick);

    return () => {
      observer.disconnect();
      root.removeEventListener("click", handleClick);
    };
  }, []);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const articles = Array.from(root.querySelectorAll<HTMLElement>("main article"));
    if (!articles.length) return;

    articles.forEach((article, index) => {
      article.hidden = index !== currentIndex;
      article.setAttribute("aria-hidden", index === currentIndex ? "false" : "true");
    });

    const active = articles[currentIndex];
    if (active) {
      setCurrentIsMulti(isMultiSelect(active));
      active.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [currentIndex]);

  const goNext = () => setCurrentIndex((current) => Math.min(current + 1, Math.max(0, articleCount - 1)));
  const goBack = () => setCurrentIndex((current) => Math.max(0, current - 1));

  return (
    <div ref={rootRef} className="optime-conversation-controller">
      {children}
      {articleCount > 0 ? (
        <div className="optime-conversation-navigation" aria-label="Question navigation">
          <button type="button" onClick={goBack} disabled={currentIndex === 0} className="optime-conversation-back">
            ← Back
          </button>
          <button type="button" onClick={goNext} disabled={currentIndex >= articleCount - 1} className="optime-conversation-next">
            {currentIsMulti ? "Next" : "Continue"} →
          </button>
        </div>
      ) : null}
    </div>
  );
}
