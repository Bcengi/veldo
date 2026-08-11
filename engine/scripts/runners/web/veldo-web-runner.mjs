// VELDO web journey runner (reference).
//
// Drives a real browser (Playwright chromium) through a journey: a sequence
// of actions and assertions, capturing named UI states as screenshots and
// running a lightweight, dependency-free accessibility scan. This is the
// FLOW-FIRST proof the method calls for: the journey is driven end to end and
// behavior is asserted at every step, so a passing run is evidence the flow
// works, not merely that a page rendered. A journey that cannot complete its
// asserted steps fails, loudly, with the failing step named.
//
// Usage:
//   NODE_PATH="$(npm root -g)" node veldo-web-runner.mjs <journey.json> [outdir]
//
// Journey format (JSON):
//   {
//     "name": "save a search",
//     "url": "file:///abs/path/app.html",   // or http(s)://
//     "viewport": {"width": 1280, "height": 800},
//     "a11y": true,                 // run the a11y scan
//     "a11y_fail_on": true,         // violations fail the journey
//     "steps": [
//       {"action": "state", "name": "landing"},
//       {"action": "click", "selector": "#save"},
//       {"action": "expect_text", "selector": "#status", "text": "Saved"},
//       {"action": "state", "name": "after-save"}
//     ]
//   }
//
// Exit 0 = every asserted step passed and (a11y clean or not fail-on).
// Exit 1 = an assertion failed, an a11y violation failed the run, or the
//          journey errored. A machine-readable result is printed as JSON and
//          written to <outdir>/result.json; state screenshots go to <outdir>.

import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { createRequire } from 'node:module';
import { execSync } from 'node:child_process';

// ESM import does not honor NODE_PATH, so resolve Playwright (a CJS package)
// explicitly: try NODE_PATH, then the global npm root, then default. Keeps the
// runner a standalone script a consuming repo can drop in.
const require = createRequire(import.meta.url);
function loadChromium() {
  const roots = [];
  if (process.env.NODE_PATH) roots.push(process.env.NODE_PATH);
  try { roots.push(execSync('npm root -g', { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim()); } catch { /* ignore */ }
  roots.push(null);
  for (const r of roots) {
    try { return require(r ? join(r, 'playwright') : 'playwright').chromium; } catch { /* try next */ }
  }
  throw new Error('playwright not found; npm i -g playwright or set NODE_PATH to its node_modules');
}
const chromium = loadChromium();

const A11Y_SCAN = () => {
  // Runs in the page. Returns an array of {rule, count, sample} violations.
  const out = [];
  const imgs = [...document.querySelectorAll('img')].filter(
    (e) => !e.hasAttribute('alt'));
  if (imgs.length) out.push({ rule: 'img-alt', count: imgs.length,
    sample: imgs[0].outerHTML.slice(0, 120) });
  const inputs = [...document.querySelectorAll('input,select,textarea')].filter((e) => {
    if (['hidden', 'submit', 'button'].includes(e.getAttribute('type'))) return false;
    if (e.getAttribute('aria-label') || e.getAttribute('aria-labelledby')) return false;
    if (e.id && document.querySelector(`label[for="${e.id}"]`)) return false;
    if (e.closest('label')) return false;
    return true;
  });
  if (inputs.length) out.push({ rule: 'input-label', count: inputs.length,
    sample: inputs[0].outerHTML.slice(0, 120) });
  const named = (e) => (e.textContent || '').trim() || e.getAttribute('aria-label')
    || e.getAttribute('title');
  const ctrls = [...document.querySelectorAll('button,a[href]')].filter((e) => !named(e));
  if (ctrls.length) out.push({ rule: 'control-name', count: ctrls.length,
    sample: ctrls[0].outerHTML.slice(0, 120) });
  if (!document.documentElement.getAttribute('lang'))
    out.push({ rule: 'html-lang', count: 1, sample: '<html> has no lang' });
  const ids = {};
  for (const e of document.querySelectorAll('[id]'))
    ids[e.id] = (ids[e.id] || 0) + 1;
  const dupes = Object.entries(ids).filter(([, n]) => n > 1);
  if (dupes.length) out.push({ rule: 'duplicate-id', count: dupes.length,
    sample: dupes[0][0] });
  return out;
};

async function run(journeyPath, outdir) {
  const journey = JSON.parse(readFileSync(journeyPath, 'utf8'));
  // A journey may name a local fixture with `file` (resolved against the
  // journey's directory) instead of an absolute `url`, so fixtures are portable.
  if (!journey.url && journey.file)
    journey.url = 'file://' + resolve(dirname(journeyPath), journey.file);
  mkdirSync(outdir, { recursive: true });
  const result = { journey: journey.name, url: journey.url, passed: true,
    steps: [], states: [], a11y: [], error: null };

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: journey.viewport
    || { width: 1280, height: 800 } });
  try {
    await page.goto(journey.url, { waitUntil: 'load' });
    for (const [i, step] of (journey.steps || []).entries()) {
      const label = `${i}:${step.action}${step.selector ? ' ' + step.selector : ''}`;
      try {
        await applyStep(page, step, outdir, result);
        result.steps.push({ step: label, ok: true });
      } catch (e) {
        result.steps.push({ step: label, ok: false, detail: String(e.message || e) });
        result.passed = false;
        // capture the failure state for the proof
        const shot = join(outdir, `FAILURE-step-${i}.png`);
        await page.screenshot({ path: shot }).catch(() => {});
        result.states.push({ name: `FAILURE-step-${i}`, file: shot });
        break; // a broken flow is unproven from here on
      }
    }
    if (journey.a11y) {
      result.a11y = await page.evaluate(A11Y_SCAN);
      if (journey.a11y_fail_on && result.a11y.length) result.passed = false;
    }
  } catch (e) {
    result.error = String(e.message || e);
    result.passed = false;
  } finally {
    await browser.close();
  }

  writeFileSync(join(outdir, 'result.json'), JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result, null, 2));
  return result.passed ? 0 : 1;
}

async function applyStep(page, step, outdir, result) {
  const to = step.timeout || 5000;
  switch (step.action) {
    case 'goto':
      await page.goto(step.url, { waitUntil: 'load' }); break;
    case 'click':
      await page.click(step.selector, { timeout: to }); break;
    case 'fill':
      await page.fill(step.selector, step.value ?? '', { timeout: to }); break;
    case 'wait':
      await page.waitForTimeout(step.ms ?? 200); break;
    case 'expect_visible':
      await page.waitForSelector(step.selector, { state: 'visible', timeout: to }); break;
    case 'expect_hidden':
      await page.waitForSelector(step.selector, { state: 'hidden', timeout: to }); break;
    case 'expect_text': {
      await page.waitForSelector(step.selector, { timeout: to });
      const got = (await page.textContent(step.selector) || '').trim();
      if (!got.includes(step.text))
        throw new Error(`expected "${step.text}" in ${step.selector}, got "${got}"`);
      break;
    }
    case 'state': {
      const file = join(outdir, `${step.name}.png`);
      await page.screenshot({ path: file, fullPage: !!step.fullPage });
      result.states.push({ name: step.name, file });
      break;
    }
    default:
      throw new Error(`unknown action: ${step.action}`);
  }
}

const [journeyPath, outdir] = process.argv.slice(2);
if (!journeyPath) {
  console.error('usage: veldo-web-runner.mjs <journey.json> [outdir]');
  process.exit(2);
}
const out = outdir || join(dirname(resolve(journeyPath)), '_out');
run(resolve(journeyPath), resolve(out)).then((code) => process.exit(code));
