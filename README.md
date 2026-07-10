# Roadmap / Spec: Minimal Hypertext Reader for Numbered Solo Adventures

## 0. Project name

Working title:

> **Solo Hypertext Reader**

Public-facing description:

> A minimalist local-first hypertext reader for numbered-entry gamebooks and solo RPG adventures.

Private-use description:

> A lightweight browser reader that lets a legally owned solo adventure PDF become a clickable hypertext experience, while keeping rules, dice, notes, maps, and combat on paper.

---

# 1. Product concept

Build a **minimalist browser-based hypertext reader** for numbered solo adventures.

The app does **not** implement GURPS, dice rolling, combat, character sheets, morale, Plot Words, or crew tracking in the MVP. Those remain paper-and-pencil.

The MVP only replaces the mechanical act of flipping between numbered entries.

The app should feel like:

> White page.
> Black serif type.
> Large centered passage.
> Click “turn to 148.”
> The current passage fades and scrolls upward.
> The next passage scrolls in from below.
> Browser Back works.

This is a **reader/navigation layer**, not a rules engine.

---

# 2. Copyright posture

## 2.1 Public repo principle

The public repository should be a **generic solo-adventure hypertext reader**.

It must **not** include:

* commercial PDFs
* OCR output from commercial works
* adventure text from commercial works
* maps from commercial works
* artwork from commercial works
* stat blocks from commercial works
* page images from commercial works
* pre-extracted JSON from commercial works
* Conan / GURPS-specific data files
* screenshots containing copyrighted adventure text

The public repo may include:

* generic reader engine
* generic extraction/validation tools
* public-domain or original demo adventure
* documentation
* tests using original dummy text
* placeholder graphics

## 2.2 Private-use principle

A user may keep their own legally obtained source PDF and generated data in a private ignored folder.

Recommended structure:

```text
solo-hypertext-reader/
  index.html
  style.css
  app.js
  README.md
  LICENSE
  tools/
  examples/
  private/              # gitignored
    source.pdf
    ocr/
    entries.json
```

Recommended `.gitignore`:

```gitignore
private/
ocr/
*.pdf
*_entries.json
conan*.json
```

## 2.3 README disclaimer

The README should include language along these lines:

> This project is a generic local-first reader for numbered-entry gamebooks and solo RPG adventures. It does not include copyrighted adventure text, PDFs, maps, artwork, stat blocks, or rules text. To use it with a commercial adventure, you must provide your own legally obtained source material and keep any generated data files private unless you have permission to redistribute them.

For any private GURPS/Conan use, the public repo should not imply affiliation or endorsement.

Suggested disclaimer:

> This project is not affiliated with, endorsed by, or sponsored by Steve Jackson Games. GURPS is a trademark of Steve Jackson Games. No GURPS rules text, adventure text, maps, artwork, or stat blocks are included.

---

# 3. Public demo

## 3.1 Purpose

The public repo should include a tiny original demo adventure to show:

* entry rendering
* clickable `turn to X` links
* browser Back
* URL hash state
* fade/scroll transition
* optional save/bookmark behavior

## 3.2 Demo file

Recommended path:

```text
examples/demo_adventure.json
```

Example:

```json
{
  "1": {
    "id": 1,
    "body": "You stand before a ruined gate. If you enter, turn to 2. If you return to camp, turn to 3."
  },
  "2": {
    "id": 2,
    "body": "The gate groans open. Inside, a stair descends into darkness. If you descend, turn to 4. If you flee, turn to 3."
  },
  "3": {
    "id": 3,
    "body": "You return to camp, wiser and poorer. Your adventure is over."
  },
  "4": {
    "id": 4,
    "body": "At the foot of the stairs you find a bronze key. Your adventure is over."
  }
}
```

This should be original text, not adapted from any commercial module.

---

# 4. MVP goal

## 4.1 MVP definition

The MVP is a static browser app that:

1. Loads a structured adventure JSON file.
2. Starts at Entry 0 if present (intro), otherwise Entry 1.
3. Displays one entry at a time.
4. Automatically turns `turn to X` references into clickable links.
5. Updates the URL when the user navigates.
6. Supports native browser Back/Forward.
7. Uses large centered serif typography.
8. Animates transitions with fade/scroll movement.
9. Runs locally without a backend.

## 4.2 MVP non-goals

The MVP should **not** include:

* automated rules
* dice roller
* combat handling
* maps
* graphics
* character sheets
* inventory
* Morale Rating tracking
* Plot Word tracking
* crew tracking
* user accounts
* cloud saves
* AI-generated summaries
* rewriting or adapting adventure prose
* copyrighted commercial adventure content in repo

---

# 5. User experience

## 5.1 Initial load

When the user opens the app, it begins at **Entry 0** if the loaded adventure has one (used for intro/framing text), otherwise **Entry 1** — unless the URL hash specifies another entry.

Example:

```text
1

The morning is still young when the ship anchors near the river mouth.

If you agree, turn to 148.

If you object, turn to 75.
```

The phrases **“turn to 148”** and **“turn to 75”** should be clickable.

## 5.2 Navigation

When the user clicks a link:

1. The clicked link briefly shows active/focus state.
2. The current entry fades slightly.
3. The current entry scrolls upward.
4. The target entry scrolls in from below.
5. The URL updates.
6. Browser history updates.

## 5.3 Back button

The browser’s native Back button must work.

Example:

```text
Entry 1 → click 148 → Entry 148
Browser Back → Entry 1
```

The app may also include a small in-page **Back** control, but native browser Back is required.

## 5.4 Direct entry navigation

Not required for MVP, but recommended soon after.

Future control:

```text
Go to entry: [___]
```

This helps recover from mistakes and resume from paper notes.

---

# 6. Visual design

## 6.1 Overall feel

The MVP should not look like:

* a fake retro terminal
* a video game HUD
* a modern app dashboard
* a faux-HyperCard clone

It should look like:

* a literary hypertext
* a newspaper/book page
* calm
* white
* black serif type
* uncluttered
* centered

## 6.2 Typography

Use a serif font stack that approximates newspaper/book typography.

Recommended MVP CSS:

```css
font-family: Georgia, "Times New Roman", Times, serif;
```

Possible future font options:

```css
font-family: "Libre Baskerville", Georgia, serif;
```

or

```css
font-family: "Crimson Text", Georgia, serif;
```

Avoid external font dependencies in MVP unless there is a clear reason.

## 6.3 Layout

Recommended CSS concept:

```css
body {
  background: #fff;
  color: #111;
  margin: 0;
}

.reader {
  max-width: 760px;
  margin: 0 auto;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8vh 24px;
}

.entry {
  font-size: clamp(24px, 3.1vw, 42px);
  line-height: 1.35;
}
```

## 6.4 Entry number

Entry number should be visible but quiet.

```css
.entry-number {
  font-size: 0.55em;
  letter-spacing: 0.08em;
  color: #777;
  margin-bottom: 1.5rem;
}
```

## 6.5 Links

Links should look like elegant text links, not buttons.

```css
a.entry-link {
  color: #111;
  text-decoration-thickness: 1px;
  text-underline-offset: 0.12em;
  cursor: pointer;
}

a.entry-link:hover {
  text-decoration-thickness: 2px;
}
```

---

# 7. Animation

## 7.1 Transition behavior

When moving from one entry to another:

* old entry fades and moves upward
* new entry enters from below
* animation is smooth but restrained
* target duration: 300–500 ms

Example CSS concept:

```css
.entry.exiting {
  opacity: 0;
  transform: translateY(-40px);
  transition: opacity 350ms ease, transform 350ms ease;
}

.entry.entering {
  opacity: 0;
  transform: translateY(40px);
}

.entry.entered {
  opacity: 1;
  transform: translateY(0);
  transition: opacity 350ms ease, transform 350ms ease;
}
```

## 7.2 Reduced motion

Respect accessibility preferences:

```css
@media (prefers-reduced-motion: reduce) {
  .entry {
    transition: none !important;
    transform: none !important;
  }
}
```

---

# 8. Data model

## 8.1 Entry format

Entries should be stored in JSON.

Example:

```json
{
  "1": {
    "id": 1,
    "body": "You stand at a ruined gate. If you enter, turn to 2. If you return to camp, turn to 3."
  }
}
```

The MVP can auto-detect links inside the body text rather than requiring manually specified links.

## 8.2 Optional richer format

Future format:

```json
{
  "1": {
    "id": 1,
    "title": "The Ruined Gate",
    "body": "You stand at a ruined gate. If you enter, turn to 2. If you return to camp, turn to 3.",
    "links": [
      { "label": "turn to 2", "target": 2 },
      { "label": "turn to 3", "target": 3 }
    ],
    "tags": []
  }
}
```

## 8.3 Text preservation

The app should preserve original text in private user-generated data.

For MVP:

* preserve paragraph breaks
* preserve punctuation
* do not rewrite prose
* do not summarize
* entry numbers stored separately
* links generated around `turn to X` references

## 8.4 Link detection

Detect patterns such as:

```text
turn to 148
Turn to 148
turn immediately to 91
If you succeed, turn to 79.
If you fail, turn to 152.
```

All detected valid entry references become clickable links.

Rendered example:

```html
If you agree, <a href="#148" class="entry-link">turn to 148</a>.
```

## 8.5 Validation

A build-time validation script should verify:

* entries 1–270 exist, or expected range for current adventure
* no duplicate entry IDs
* every detected target exists
* no broken links
* every entry has body text
* every entry containing `turn to X` has that reference linked
* endings are allowed to have no outgoing links

---

# 9. URL and history behavior

## 9.1 URL format

Use simple hash URLs:

```text
index.html#1
index.html#148
index.html#75
```

## 9.2 Browser history

On link click:

```js
history.pushState({ entryId: targetId }, "", `#${targetId}`);
```

On browser Back/Forward:

```js
window.addEventListener("popstate", () => {
  loadEntryFromHash();
});
```

## 9.3 Reload behavior

If the user reloads:

* `index.html#148` loads Entry 148
* missing hash loads Entry 0 if present, otherwise Entry 1
* invalid hash shows a graceful error and offers a link back to the start entry

---

# 10. Save behavior

## 10.1 MVP save

The MVP’s save mechanism is the URL.

The current entry is always reflected in the URL.

The user can bookmark:

```text
index.html#148
```

This is enough to resume the digital reader position.

## 10.2 Future save slots

Future version should support browser-local save slots via `localStorage`.

Example:

```json
{
  "slot1": {
    "entryId": 148,
    "path": [1, 75, 203, 148],
    "savedAt": "2026-07-10T21:14:00"
  }
}
```

## 10.3 Future export/import

Future version may allow JSON save export/import.

Example:

```json
{
  "entryId": 148,
  "path": [1, 75, 203, 148],
  "bookmarks": [1, 75],
  "notes": "Morale -2. Plot Words: CAUTIOUS, DELAYED."
}
```

## 10.4 Save scope

The app should save **reader state**, not full adventure state, unless later explicitly expanded.

Reader state:

* current entry
* path/history
* bookmarks
* optional notes

Adventure state not in MVP:

* HP
* morale
* Plot Words
* crew losses
* inventory
* combat state
* map positions

---

# 11. Controls

## 11.1 MVP controls

Keep controls minimal and visually quiet.

Required:

| Control             | Requirement |
| ------------------- | ----------- |
| Click entry link    | required    |
| Browser Back        | required    |
| Start Over          | required    |
| URL bookmark resume | required    |

Optional MVP:

| Control            | Requirement           |
| ------------------ | --------------------- |
| In-page Back       | optional              |
| Go to Entry        | optional, recommended |
| Hide/show controls | optional              |

## 11.2 Future keyboard shortcuts

| Key              | Action                        |
| ---------------- | ----------------------------- |
| `B` or Backspace | Back                          |
| `G`              | Go to entry                   |
| `1–9`            | choose visible link by number |
| `H`              | show path/history             |
| `S`              | save                          |
| `?`              | help                          |

---

# 12. Path tracking

## 12.1 MVP

Do not display path by default.

## 12.2 Future version

Optional path display:

```text
Path: 1 → 75 → 221 → 29
```

This should be hideable.

## 12.3 Path storage

Path may be stored in:

* memory
* `localStorage`
* exported JSON save
* optional URL encoding if desired

---

# 13. Loading screen and intro text

## 13.1 MVP status

Not MVP.

## 13.2 Purpose

A loading screen and intro text could add atmosphere without turning the app into a game engine.

This should be restrained and literary, not flashy.

## 13.3 Loading screen concept

Possible loading screen:

```text
Solo Hypertext Reader

Loading adventure...
```

For a private adventure build, the loading text could display the adventure title if supplied locally in metadata.

Example metadata:

```json
{
  "title": "Example Adventure",
  "subtitle": "A Numbered Solo Adventure",
  "startEntry": 1
}
```

## 13.4 Intro screen concept

Before Entry 1, the app may show an optional intro card/page:

```text
This reader handles navigation only.

Use your rulebook, dice, maps, and notes as normal.
Click numbered references to move between entries.
Bookmark the page to save your current location.
```

Buttons:

```text
[Begin at Entry 1]
[Load Saved Entry]
[About This Reader]
```

## 13.5 Copyright caution

Public intro text must not include commercial adventure text, trademarks, or copyrighted descriptions unless permission exists.

Private local builds may display user-supplied metadata from local files.

---

# 14. Graphics

## 14.1 MVP status

Not MVP.

## 14.2 Public repo graphics

The public repo may include:

* original placeholder graphics
* simple icons
* public-domain art
* CSS-only decorative elements

The public repo must not include commercial adventure artwork, maps, cover scans, page scans, or layout images.

## 14.3 Private local graphics

A private local build may optionally support user-supplied images, such as:

* cover image
* map images
* appendix scans
* decorative chapter/title images
* public-domain illustrations

These should live in ignored local folders:

```text
private/
  images/
    cover.png
    map_a.png
    map_b.png
```

## 14.4 Graphics design principle

Graphics should not overwhelm the minimalist reading experience.

Possible modes:

| Mode                   | Description                                   |
| ---------------------- | --------------------------------------------- |
| None                   | MVP default                                   |
| Intro-only             | cover/title image on loading screen           |
| Appendix viewer        | user can open map/reference images separately |
| Inline optional        | images attached to specific entries           |
| Background atmospheric | subtle and discouraged unless tasteful        |

## 14.5 Suggested future image metadata

```json
{
  "1": {
    "id": 1,
    "body": "You stand before a ruined gate. If you enter, turn to 2.",
    "image": "private/images/gate.png"
  }
}
```

The app should gracefully ignore missing images.

## 14.6 Graphics acceptance rule

If graphics are added, the text-first experience remains primary.

A good default:

* image hidden unless user opens it
* or image appears above text only on title/loading screens
* maps/reference images open in a separate overlay

---

# 15. Implementation recommendation

## 15.1 Recommended stack

Use a **static web app**.

Recommended files:

```text
solo-hypertext-reader/
  index.html
  style.css
  app.js
  README.md
  LICENSE
  examples/
    demo_adventure.json
  tools/
    validate_entries.py
    extract_entries.py
```

No backend required.

## 15.2 Why web app, not Pygame

For this minimalist version, web is better because:

* hyperlinks are native
* browser Back is native
* bookmarking is native
* typography is better
* CSS transitions are easy
* `localStorage` is built in
* static hosting is trivial
* no packaging required
* works locally

## 15.3 Local running

Development:

```bash
python3 -m http.server 8000
```

Open:

```text
http://localhost:8000/#0
```

---

# 16. Build pipeline

## 16.1 OCR pipeline

Because commercial PDFs may be image-only, use a local pipeline:

```text
PDF → page images → OCR → raw text → entry segmentation → JSON → validation
```

## 16.2 Extraction script

`extract_entries.py` should:

1. Accept a local source path.
2. OCR or ingest OCR output.
3. Detect entry numbers.
4. Extract body text for each entry.
5. Detect `turn to X` references.
6. Output local/private `entries.json`.
7. Produce a QA report.

## 16.3 Public extraction script caution

The public extraction script should be generic.

Avoid:

* hardcoded commercial PDF coordinates
* hardcoded commercial adventure corrections
* specific text snippets from commercial works
* tests using commercial text
* prebuilt commercial adventure data

## 16.4 QA report

The QA report should list:

* entries with no outgoing links
* entries with unusually many outgoing links
* suspicious OCR characters
* broken target references
* duplicate references
* possible missed references
* invalid entry IDs
* references to mechanics such as `roll`, `Plot Word`, `Morale`, `Combat Map`

The MVP does not automate those mechanics, but flagging them helps proofreading.

---

# 17. Acceptance criteria

MVP is complete when:

1. App opens to Entry 0 if present, otherwise Entry 1.
2. Demo adventure loads from `examples/demo_adventure.json`.
3. App can also load a private local adventure JSON.
4. All entries in the loaded adventure are accessible.
5. Every detected `turn to X` reference is clickable.
6. Clicking a link navigates to the correct target entry.
7. Browser Back returns to the previous entry.
8. Reloading a hash URL loads the correct entry.
9. Invalid hashes fail gracefully.
10. Text is large, centered, black serif type on white background.
11. Passage transition uses fade/up and scroll-in-from-bottom effect.
12. App runs locally with no backend.
13. Validation script reports no broken links for the demo adventure.
14. Public repo contains no commercial adventure text, maps, images, PDFs, OCR output, or generated commercial JSON.

---

# 18. Roadmap

## Version 0.1 — Public demo MVP

Scope:

* static web app
* original demo adventure
* large centered serif text
* clickable `turn to X` links
* hash URL navigation
* native browser Back
* fade/scroll transition
* Start Over
* validation script

No copyrighted adventure content.

Estimated LOE: **8–20 hours**

## Version 0.2 — Private local adventure support

Scope:

* load local/private JSON
* documented private folder workflow
* generic OCR/extraction pipeline
* QA report
* `.gitignore` protections
* README copyright guidance

Estimated LOE: **10–25 additional hours**

## Version 0.3 — Save and resume quality-of-life

Scope:

* localStorage save slots
* save/load menu
* export/import save JSON
* optional notes field
* Go to Entry
* optional in-page Back
* path stored but hidden by default

Estimated LOE: **8–20 additional hours**

## Version 0.4 — Loading screen and intro text

Scope:

* loading screen
* optional intro screen
* adventure metadata support
* Begin / Load / About controls
* user guidance: “use your own rules, dice, maps, notes”
* tasteful transition into Entry 1

Estimated LOE: **5–12 additional hours**

## Version 0.5 — Optional graphics support

Scope:

* support user-supplied private images
* intro/title image
* optional entry image metadata
* image overlay/viewer
* graceful handling of missing images
* public-domain/original placeholder demo image only

Estimated LOE: **8–25 additional hours**

## Version 0.6 — Path/history view

Scope:

* optional path drawer
* breadcrumb display
* clickable previous entries
* copy current path
* export path with save file

Estimated LOE: **5–15 additional hours**

## Version 0.7 — Paper-play support

Scope:

* optional notes field per entry or save
* bookmark entries
* printable current path
* optional dice roller
* optional reference pane

Still no rules automation.

Estimated LOE: **10–30 additional hours**

## Version 1.0 — Polished reader

Scope:

* responsive layout
* accessibility pass
* reduced-motion support
* keyboard shortcuts
* robust validation
* clean README
* public demo
* private-use documentation
* no copyrighted content in repo

Estimated total LOE from scratch: **35–90 hours**, depending on OCR/tooling ambitions.

---

# 19. Explicitly deferred / not planned

These should not be pursued unless the project’s goals change:

* full GURPS rule implementation
* tactical combat automation
* parser/Zork-style input
* AI rewrite of adventure text
* automatic character sheet management
* automatic Plot Word/Morale/Crew handling
* hosted account/cloud sync
* distributing commercial adventure data
* distributing commercial maps/art/scans

---

# 20. One-sentence product definition

**A minimalist, local-first literary hypertext reader that lets players click through numbered solo-adventure entries while preserving the original paper-and-pencil play experience and respecting copyrighted source material.**
