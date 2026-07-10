"use strict";

// Kept in sync with the pattern in tools/validate_entries.py.
// Requires a trigger verb ("turn"/"return") directly followed by "to" and a
// digit run, with optional "immediately"/"paragraph" in between. This avoids
// false positives (page refs like "p. 29", "turn back" with no number, "return
// to their duties") by construction, with no denylist needed.
const LINK_REGEX_SOURCE =
  "\\b(?:turn|return)\\s+(?:immediately\\s+)?to\\s+(?:paragraph\\s+)?(\\d+)\\b";

const DEFAULT_DATA_URL = "examples/demo_adventure.json";
const TRANSITION_MS = 350;

const entryElement = document.getElementById("entry");
const startOverButton = document.getElementById("start-over");
const REDUCED_MOTION = window.matchMedia(
  "(prefers-reduced-motion: reduce)"
).matches;

let entries = null;
let entriesLoaded = false;
let startEntryId = "1";
let pendingTimeoutId = null;

function resolveDataUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("data") || DEFAULT_DATA_URL;
}

async function loadEntries(url) {
  let response;
  try {
    response = await fetch(url);
  } catch (err) {
    throw new Error(`Could not fetch "${url}": ${err.message}`);
  }
  if (!response.ok) {
    throw new Error(`Could not fetch "${url}": HTTP ${response.status}`);
  }
  try {
    return await response.json();
  } catch (err) {
    throw new Error(`"${url}" is not valid JSON: ${err.message}`);
  }
}

function determineStartEntryId(loadedEntries) {
  return Object.hasOwn(loadedEntries, "0") ? "0" : "1";
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function linkifyParagraph(escapedText) {
  const regex = new RegExp(LINK_REGEX_SOURCE, "gi");
  return escapedText.replace(
    regex,
    (match, target) => `<a href="#${target}" class="entry-link">${match}</a>`
  );
}

function renderEntryBodyHtml(bodyText) {
  const paragraphs = bodyText
    .trim()
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean);
  return paragraphs
    .map((p) => `<p>${linkifyParagraph(escapeHtml(p))}</p>`)
    .join("");
}

function buildEntryMarkup(entry) {
  return (
    `<div class="entry-number">${escapeHtml(String(entry.id))}</div>` +
    `<div class="entry-body">${renderEntryBodyHtml(entry.body)}</div>`
  );
}

function buildNotFoundMarkup(attemptedId, resolvedStartEntryId) {
  return (
    `<div class="entry-number">Not Found</div>` +
    `<div class="entry-body">` +
    `<p>There is no entry "${escapeHtml(
      attemptedId
    )}" in this adventure.</p>` +
    `<p><a href="#${resolvedStartEntryId}" class="entry-link">Return to Start</a></p>` +
    `</div>`
  );
}

function buildFatalErrorMarkup(message) {
  return (
    `<div class="entry-number">Unable to Load</div>` +
    `<div class="entry-body">` +
    `<p>${escapeHtml(message)}</p>` +
    `<p>If you are opening this file directly, try running a local server ` +
    `instead, e.g. <code>python3 -m http.server 8000</code>, then open ` +
    `<code>http://localhost:8000/</code>.</p>` +
    `</div>`
  );
}

function applyEntryContent(html) {
  entryElement.innerHTML = html;
}

function transitionToContent(html, { isInitial = false } = {}) {
  if (pendingTimeoutId !== null) {
    clearTimeout(pendingTimeoutId);
    pendingTimeoutId = null;
  }

  if (isInitial) {
    applyEntryContent(html);
    entryElement.classList.remove("exiting", "entering");
    entryElement.classList.add("entered");
    return;
  }

  const swapIn = () => {
    applyEntryContent(html);
    entryElement.classList.remove("exiting");
    entryElement.classList.add("entering");
    // Force a reflow so the "entering" starting state is committed before
    // we switch to "entered", otherwise the browser coalesces the two
    // class changes and no transition plays.
    void entryElement.offsetHeight;
    entryElement.classList.remove("entering");
    entryElement.classList.add("entered");
    entryElement.focus({ preventScroll: true });
    pendingTimeoutId = null;
  };

  entryElement.classList.remove("entered");
  entryElement.classList.add("exiting");

  if (REDUCED_MOTION) {
    swapIn();
  } else {
    pendingTimeoutId = setTimeout(swapIn, TRANSITION_MS);
  }
}

function renderEntry(targetId, { historyMode, isInitial = false } = {}) {
  const html = Object.hasOwn(entries, targetId)
    ? buildEntryMarkup(entries[targetId])
    : buildNotFoundMarkup(targetId, startEntryId);

  const hash = `#${encodeURIComponent(targetId)}`;
  if (historyMode === "push") {
    history.pushState({ entryId: targetId }, "", hash);
  } else if (historyMode === "replace") {
    history.replaceState({ entryId: targetId }, "", hash);
  }
  // historyMode === "none": the browser already updated the URL (popstate).

  transitionToContent(html, { isInitial });
}

function currentHashEntryId() {
  const raw = window.location.hash.slice(1);
  if (!raw) return "";
  try {
    return decodeURIComponent(raw).trim();
  } catch {
    return raw.trim();
  }
}

function navigateToHashOrStart({ historyMode, isInitial = false } = {}) {
  const hashId = currentHashEntryId();
  const targetId = hashId || startEntryId;
  renderEntry(targetId, { historyMode, isInitial });
}

function onEntryClick(event) {
  const link = event.target.closest("a.entry-link");
  if (!link) return;
  event.preventDefault();
  const targetId = link.getAttribute("href").slice(1);
  renderEntry(targetId, { historyMode: "push" });
}

function onPopState() {
  navigateToHashOrStart({ historyMode: "none" });
}

function onStartOverClick() {
  if (!entriesLoaded) return;
  renderEntry(startEntryId, { historyMode: "push" });
}

async function init() {
  const dataUrl = resolveDataUrl();
  try {
    entries = await loadEntries(dataUrl);
  } catch (err) {
    startOverButton.hidden = true;
    applyEntryContent(buildFatalErrorMarkup(err.message));
    entryElement.classList.add("entered");
    return;
  }

  startEntryId = determineStartEntryId(entries);
  entriesLoaded = true;

  entryElement.addEventListener("click", onEntryClick);
  window.addEventListener("popstate", onPopState);
  startOverButton.addEventListener("click", onStartOverClick);

  navigateToHashOrStart({ historyMode: "replace", isInitial: true });
}

init();
