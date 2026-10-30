#!/usr/bin/env node
/**
 * Default QA for review pages. Light and dark are both mandatory.
 *
 *   PLAYWRIGHT_CORE=/path/to/playwright-core/index.mjs \
 *   node qa.mjs --url file:///path/review.html \
 *     --chrome "/path/to/Google Chrome for Testing" --out /tmp/review-qa
 */
import fs from 'node:fs'
import path from 'node:path'

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, cur, i, all) => {
    if (cur.startsWith('--')) acc.push([cur.slice(2), all[i + 1]])
    return acc
  }, [])
)
const url = args.url
const chrome = args.chrome
const out = args.out || '/tmp/review-page-qa'
if (!url || !chrome) {
  console.error('usage: qa.mjs --url <file://...> --chrome <chrome binary> [--out dir]')
  process.exit(2)
}
const { chromium } = await import(process.env.PLAYWRIGHT_CORE || 'playwright-core')

const failures = []
const results = {}
const shotDir = path.resolve(out)
fs.mkdirSync(shotDir, { recursive: true })

function contrastProbe() {
  function rgb(value) {
    if (value.startsWith('color(srgb')) {
      const nums = value.match(/[\d.]+/g)
      if (!nums || nums.length < 3) throw new Error('bad color: ' + value)
      const rgb = nums.slice(0, 3).map(Number)
      if (!rgb.every(Number.isFinite)) throw new Error('bad color: ' + value)
      return rgb.map((n) => n * 255)
    }
    const nums = value.match(/\d+(\.\d+)?/g)
    if (!nums || nums.length < 3) throw new Error('bad color: ' + value)
    const rgb = nums.slice(0, 3).map(Number)
    if (!rgb.every(Number.isFinite)) throw new Error('bad color: ' + value)
    return rgb
  }
  function luminance(color) {
    const channel = color.map((v) => {
      v /= 255
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)
    })
    return 0.2126 * channel[0] + 0.7152 * channel[1] + 0.0722 * channel[2]
  }
  function background(el) {
    let node = el
    while (node) {
      const bg = getComputedStyle(node).backgroundColor
      if (bg && bg !== 'rgba(0, 0, 0, 0)') return rgb(bg)
      node = node.parentElement
    }
    return [255, 255, 255]
  }
  const failures = []
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
  let node
  while ((node = walker.nextNode())) {
    const text = node.textContent.trim()
    if (!text) continue
    const el = node.parentElement
    if (!el || el.offsetParent === null) continue
    // Decorative hints: line numbers, diff markers, dim stars, folded labels.
    if (el.classList.contains('ln') || el.classList.contains('mark') || el.classList.contains('dim')) continue
    if (el.closest('.stars') || el.closest('.dl.meta')) continue
    let ratio, bg
    try {
      const fg = rgb(getComputedStyle(el).color)
      bg = background(el)
      const l1 = luminance(fg)
      const l2 = luminance(bg)
      ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05)
    } catch (err) {
      failures.push({ text: text.slice(0, 40), selector: 'color-parse', ratio: null, error: String(err) })
      continue
    }
    if (ratio < 4.5) {
      failures.push({
        text: text.slice(0, 40),
        selector: `${el.tagName.toLowerCase()}.${String(el.className).split(' ')[0]}`,
        ratio: +ratio.toFixed(2),
        color: getComputedStyle(el).color,
        background: `rgb(${bg.map(Math.round).join(',')})`,
      })
    }
  }
  const seen = new Set()
  return failures.filter((f) => {
    const key = f.selector + f.ratio
    if (seen.has(key)) return false
    seen.add(key)
    return true
  }).slice(0, 30)
}

async function check(browser, mode, viewport, label) {
  const context = await browser.newContext({ viewport, colorScheme: mode, permissions: ['clipboard-read', 'clipboard-write'], acceptDownloads: true })
  const page = await context.newPage()
  const errors = []
  page.on('pageerror', (e) => errors.push(String(e)))
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
  await page.goto(url, { waitUntil: 'load', timeout: 120000 })
  await page.waitForTimeout(700)

  const state = await page.evaluate(() => {
    const notes = [...document.querySelectorAll('.note')].filter((n) => !n.classList.contains('filtered-out'))
    return {
      theme: document.documentElement.dataset.theme,
      pref: document.documentElement.dataset.pref,
      files: document.querySelectorAll('section.file').length,
      notes: notes.length,
      wires: document.querySelectorAll('.wires path').length,
      badges: [...document.querySelectorAll('.badge')].filter((b) => !b.classList.contains('filtered-out')).length,
      asks: document.querySelectorAll('.ask-input').length,
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      contrast: null,
    }
  })
  state.contrast = await page.evaluate(contrastProbe)
  const expected = mode === 'dark' ? 'dark' : 'light'
  if (state.theme !== expected) failures.push(`${label}: theme ${state.theme}, expected ${expected}`)
  if (errors.length) failures.push(`${label}: console/page errors: ${errors.slice(0, 3).join(' | ')}`)
  if (state.scrollWidth > state.clientWidth + 1) failures.push(`${label}: horizontal overflow ${state.scrollWidth} > ${state.clientWidth}`)
  const expectedWires = state.clientWidth > 1240 ? state.notes : 0
  if (state.wires !== expectedWires) failures.push(`${label}: ${state.notes} notes but ${state.wires} wires (expected ${expectedWires})`)
  if (state.notes !== state.badges) failures.push(`${label}: ${state.notes} notes but ${state.badges} badges`)
  if (state.asks !== state.notes) failures.push(`${label}: ${state.asks} ask inputs but ${state.notes} notes`)
  if (state.contrast.length) failures.push(`${label}: ${state.contrast.length} low-contrast text nodes (${state.contrast.map((c) => c.selector + ':' + c.ratio).join(', ')})`)
  await page.screenshot({ path: path.join(shotDir, `${label}.png`), fullPage: false })

  // Anti filter must be block-level: every visible note carries an anti chip.
  await page.evaluate(() => document.querySelector('button.flt[data-f="anti"]').click())
  await page.waitForTimeout(250)
  const anti = await page.evaluate(() => ({
    total: document.querySelectorAll('.note[data-anti="1"]').length,
    visible: document.querySelectorAll('.note:not(.filtered-out)').length,
    unrelated: [...document.querySelectorAll('.note:not(.filtered-out)')].filter((n) => !n.querySelector('.chip.anti')).length,
    files: document.querySelectorAll('section.file:not(.hidden)').length,
  }))
  if (anti.unrelated) failures.push(`${label}: anti filter shows ${anti.unrelated} unrelated notes`)
  if (anti.total !== anti.visible) failures.push(`${label}: anti filter shows ${anti.visible}/${anti.total} anti notes`)
  await page.screenshot({ path: path.join(shotDir, `${label}-anti.png`), fullPage: false })

  await page.evaluate(() => { const all = document.querySelector('button.flt[data-f="all"]'); if (all) all.click() })
  await page.waitForTimeout(150)

  // Theme toggle: auto -> light -> dark -> auto; persistence after reload.
  await page.click('#theme')
  await page.waitForTimeout(150)
  const after = await page.evaluate(() => document.documentElement.dataset.pref)
  if (after === state.pref) failures.push(`${label}: theme toggle did not change preference`)
  await page.reload({ waitUntil: 'load' })
  await page.waitForTimeout(300)
  const persisted = await page.evaluate(() => document.documentElement.dataset.pref)
  if (persisted !== after) failures.push(`${label}: theme preference did not persist`)

  results[label] = { ...state, themeToggle: after, persisted, anti }
  await context.close()
}

const browser = await chromium.launch({ executablePath: chrome, args: ['--no-sandbox'] })
await check(browser, 'light', { width: 1440, height: 1000 }, 'light-desktop')
await check(browser, 'dark', { width: 1440, height: 1000 }, 'dark-desktop')
await check(browser, 'dark', { width: 390, height: 844 }, 'dark-mobile')
await check(browser, 'light', { width: 390, height: 844 }, 'light-mobile')

// Mobile badge opens a note dialog.
const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, colorScheme: 'dark' })
const page = await mobile.newPage()
await page.goto(url, { waitUntil: 'load', timeout: 120000 })
await page.waitForTimeout(500)
const firstBadge = page.locator('.badge').first()
if ((await firstBadge.evaluate((el) => el.tagName)) !== 'BUTTON') failures.push('dark-mobile: badge is not a button')
await firstBadge.focus()
await firstBadge.press('Enter')
if (!(await page.locator('#modal').evaluate((el) => el.classList.contains('open')))) {
  failures.push('dark-mobile: badge did not open the note dialog')
}
await page.keyboard.press('Escape')
if (await page.locator('#modal').evaluate((el) => el.classList.contains('open'))) {
  failures.push('dark-mobile: Escape did not close the note dialog')
}
await page.screenshot({ path: path.join(shotDir, 'dark-mobile-modal.png') })
await mobile.close()
await browser.close()

console.log(JSON.stringify({ results, failures }, null, 2))
if (failures.length) process.exit(1)