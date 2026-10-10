// Headless browser playtest of a built quiz page.
// Usage: node scripts/playtest.mjs 2026-W42 [path/to/page.html]
// For every outcome, clicks through the example answer path found by simulate.py and
// checks the page shows that outcome. Also fails on any JavaScript error.
// Needs Playwright (preinstalled globally in Claude Code cloud sessions; run with
// NODE_PATH="$(npm root -g)").
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const week = process.argv[2];
if (!week) { console.error("usage: node scripts/playtest.mjs WEEK [page.html]"); process.exit(2); }
const page_path = resolve(process.argv[3] || `${root}/_site/${week}.html`);
const sim = JSON.parse(readFileSync(`${root}/.work/${week}/simulation.json`, "utf8"));
const quiz = JSON.parse(readFileSync(`${root}/quizzes/${week}/quiz.json`, "utf8"));

const launch = { headless: true };
if (process.env.PLAYWRIGHT_CHROMIUM_PATH) launch.executablePath = process.env.PLAYWRIGHT_CHROMIUM_PATH;
const browser = await chromium.launch(launch);
const failures = [];
try {
  for (const outcome of quiz.outcomes) {
    const path = sim.witnesses[outcome.id];
    if (!path) { failures.push(`${outcome.id}: no example path (unreachable)`); continue; }
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
    await page.goto(pathToFileURL(page_path).href);
    await page.click('[data-testid="start"]');
    for (const answer of path) await page.click(`[data-testid="answer-${answer}"]`);
    const shown = await page.getAttribute(".screen.result", "data-result");
    if (shown !== outcome.id) failures.push(`${outcome.id}: page showed '${shown}' for path [${path}]`);
    await page.click('[data-testid="all-outcomes"]');
    const cards = await page.locator(".all-outcomes .outcome-mini").count();
    if (cards !== quiz.outcomes.length) failures.push(`${outcome.id}: 'see all results' shows ${cards} cards`);
    for (const e of errors) failures.push(`${outcome.id}: JS error: ${e}`);
    await page.close();
  }
  // Random paths: the browser must agree with the Python scorer (catches drift between the two).
  const page = await browser.newPage();
  page.on("pageerror", (e) => failures.push(`JS error: ${e.message}`));
  await page.goto(pathToFileURL(page_path).href);
  for (const { picks, winner } of sim.samples) {
    await page.click('[data-testid="start"]');
    for (const answer of picks) await page.click(`[data-testid="answer-${answer}"]`);
    const shown = await page.getAttribute(".screen.result", "data-result");
    if (shown !== winner) failures.push(`random path [${picks}]: page showed '${shown}', scorer says '${winner}'`);
    await page.click('[data-testid="restart"]');
  }
  await page.close();
} finally {
  await browser.close();
}

if (failures.length) {
  console.log(failures.join("\n"));
  console.log(`FAIL: playtest (${failures.length} problem(s))`);
  process.exit(1);
}
console.log(`OK: playtest reached all ${quiz.outcomes.length} outcomes and matched ${sim.samples.length} random paths`);
