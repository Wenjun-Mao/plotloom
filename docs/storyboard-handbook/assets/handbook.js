(function () {
  "use strict";

  const body = document.body;
  const tocToggle = document.querySelector(".toc-toggle");
  const tocScrim = document.querySelector(".toc-scrim");
  const tocPanel = document.querySelector(".toc-panel");
  const progressBar = document.querySelector(".reading-progress span");
  const progressCopy = document.querySelector(".progress-copy");
  const progressPercent = progressCopy?.querySelector("strong");
  const progressChapter = document.querySelector(".progress-chapter");
  const chapters = Array.from(document.querySelectorAll(".handbook-content > article[id]"));
  const chapterLinks = Array.from(document.querySelectorAll("[data-chapter-link]"));
  let currentChapterId = "";
  let updateScheduled = false;

  function setTocOpen(isOpen) {
    body.classList.toggle("toc-is-open", isOpen);
    tocToggle?.setAttribute("aria-expanded", String(isOpen));
    tocScrim?.setAttribute("tabindex", isOpen ? "0" : "-1");
    if (isOpen) {
      window.requestAnimationFrame(() => {
        if (body.classList.contains("toc-is-open")) {
          tocPanel?.querySelector("a")?.focus();
        }
      });
    } else {
      tocToggle?.focus({ preventScroll: true });
    }
  }

  function currentChapter() {
    const readingLine = Math.min(220, window.innerHeight * 0.28);
    let current = null;
    for (const chapter of chapters) {
      if (chapter.getBoundingClientRect().top <= readingLine) {
        current = chapter;
      } else {
        break;
      }
    }
    return current;
  }

  function setCurrentChapter(chapter) {
    const id = chapter?.id || "";
    if (id === currentChapterId) return;
    currentChapterId = id;
    const title = chapter?.dataset.title || chapter?.querySelector("h1, h2")?.textContent || "封面";
    if (progressChapter) progressChapter.textContent = title.trim();
    for (const link of chapterLinks) {
      const isCurrent = link.dataset.chapterLink === id;
      link.classList.toggle("is-current", isCurrent);
      if (isCurrent) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    }
  }

  function updateReadingState() {
    updateScheduled = false;
    const scrollRange = document.documentElement.scrollHeight - window.innerHeight;
    const percent = scrollRange > 0
      ? Math.min(100, Math.max(0, (window.scrollY / scrollRange) * 100))
      : 100;
    const roundedPercent = Math.round(percent);
    if (progressBar) progressBar.style.transform = `scaleX(${percent / 100})`;
    if (progressPercent) progressPercent.textContent = `${roundedPercent}%`;
    progressCopy?.setAttribute("aria-valuenow", String(roundedPercent));
    setCurrentChapter(currentChapter());
  }

  function scheduleReadingStateUpdate() {
    if (updateScheduled) return;
    updateScheduled = true;
    window.requestAnimationFrame(updateReadingState);
  }

  function focusChapter(index) {
    const chapter = chapters[index];
    if (!chapter) return;
    chapter.scrollIntoView({ behavior: "smooth", block: "start" });
    window.setTimeout(() => chapter.focus({ preventScroll: true }), 350);
  }

  tocToggle?.addEventListener("click", () => {
    setTocOpen(!body.classList.contains("toc-is-open"));
  });
  tocScrim?.addEventListener("click", () => setTocOpen(false));
  tocPanel?.addEventListener("click", (event) => {
    if (event.target.closest("a") && window.matchMedia("(max-width: 62rem)").matches) {
      setTocOpen(false);
    }
  });

  window.addEventListener("scroll", scheduleReadingStateUpdate, { passive: true });
  window.addEventListener("resize", scheduleReadingStateUpdate, { passive: true });
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && body.classList.contains("toc-is-open")) {
      setTocOpen(false);
      return;
    }
    if (!event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    const activeChapter = currentChapter();
    const currentIndex = chapters.indexOf(activeChapter);
    if (event.key === "ArrowLeft" && currentIndex > 0) {
      event.preventDefault();
      focusChapter(currentIndex - 1);
    }
    if (event.key === "ArrowRight" && currentIndex < chapters.length - 1) {
      event.preventDefault();
      focusChapter(currentIndex + 1);
    }
  });

  updateReadingState();
})();
