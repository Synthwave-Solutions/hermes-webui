// Inline SVG visuals in chat (plan addendum 3.5 and 3.6, package A1).
//
// Runs against an isolated scratch WebUI (QA_BASE_URL, port 8795 for A1) with
// playwright.report.config.ts. Every chat is seeded through
// /api/session/import, so no model is involved; the page renders the stored
// reply with the production renderer. Requests to any other host are refused
// and recorded. Set SVG_VISUALS_SHOTS to also keep the screenshots there.
import { test, expect, type Page, type BrowserContext } from '@playwright/test'
import fs from 'fs'
import path from 'path'

const FIXTURES = path.join(__dirname, '..', 'fixtures', 'svg')
const read = (kind: string, name: string) => fs.readFileSync(path.join(FIXTURES, kind, name), 'utf8')
const GOOD = read('good', 'layer-stack.svg')
const PAPER = read('good', 'paper-dark-strokes.svg')
const HOSTILE = fs.readdirSync(path.join(FIXTURES, 'bad')).filter(n => n.endsWith('.svg')).sort()
const SHOTS = process.env.SVG_VISUALS_SHOTS || ''

const TAKEAWAY = 'The interface sits on automation, which sits on the data.'

async function seed(context: BrowserContext, baseURL: string, assistant: string) {
  const response = await context.request.post(new URL('api/session/import', baseURL).href, {
    data: { title: 'Visual check', messages: [
      { role: 'user', content: 'Explain the layers.' },
      { role: 'assistant', content: assistant },
    ] },
  })
  expect(response.ok()).toBeTruthy()
  return (await response.json()).session.session_id as string
}

async function isolate(context: BrowserContext, baseURL: string) {
  const origin = new URL(baseURL).origin
  const foreign: string[] = []
  await context.route('**/*', route => {
    const url = route.request().url()
    if (url.startsWith(origin) || url.startsWith('data:') || url.startsWith('blob:')) return route.continue()
    foreign.push(url)
    return route.abort()
  })
  return foreign
}

async function openChat(page: Page, sid: string) {
  await page.goto('session/' + sid)
  await page.waitForFunction(() => document.querySelector('figure.svg-visual, .svg-visual-blocked'), null,
    { timeout: 20_000 })
}

async function setTheme(page: Page, theme: 'light' | 'dark', skin = 'default') {
  await page.evaluate(([th, sk]) => {
    try { localStorage.setItem('hermes-theme', th); localStorage.setItem('hermes-skin', sk) } catch (_) { /* private mode */ }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const w = window as any
    if (typeof w._applySkin === 'function') w._applySkin(sk)
    if (typeof w._applyTheme === 'function') w._applyTheme(th)
  }, [theme, skin])
  await page.waitForTimeout(150)
}

async function shot(page: Page, name: string) {
  const file = test.info().outputPath(name + '.png')
  await page.screenshot({ path: file, fullPage: false })
  if (SHOTS) {
    fs.mkdirSync(SHOTS, { recursive: true })
    fs.copyFileSync(file, path.join(SHOTS, name + '.png'))
  }
}

async function figureState(page: Page) {
  return page.evaluate(() => {
    const fig = document.querySelector('figure.svg-visual') as HTMLElement
    const img = fig.querySelector('img.svg-visual-img') as HTMLImageElement
    const src = img.getAttribute('src') || ''
    const svg = atob(src.split(',')[1] || '')
    return {
      src,
      svg,
      alt: img.alt,
      caption: (fig.querySelector('figcaption') || { textContent: '' }).textContent,
      paper: fig.classList.contains('svg-visual--paper'),
      width: img.getBoundingClientRect().width,
      natural: img.naturalWidth,
      buttons: Array.from(fig.querySelectorAll('.svg-visual-toolbar button')).map(b => b.getAttribute('aria-label')),
      liveSvg: fig.querySelectorAll('svg').length - fig.querySelectorAll('.svg-visual-toolbar svg').length,
    }
  })
}

test.describe('inline SVG visuals', () => {
  for (const [width, height, label] of [[1440, 900, 'desktop'], [390, 844, 'phone']] as const) {
    test(`TC-SVG-001 a visual renders as a picture in light, dark and a skin (${label}, ${width} px)`, async ({ browser, baseURL }) => {
      test.setTimeout(120_000)
      const context = await browser.newContext({ viewport: { width, height } })
      const foreign = await isolate(context, baseURL!)
      const sid = await seed(context, baseURL!, 'Here is the stack.\n\n```svg\n' + GOOD + '```\n\n' + TAKEAWAY)
      const page = await context.newPage()
      const errors: string[] = []
      page.on('pageerror', e => errors.push(String(e)))
      await openChat(page, sid)
      for (const [theme, skin] of [['light', 'default'], ['dark', 'default'], ['dark', 'graphite']] as const) {
        await setTheme(page, theme, skin)
        await page.locator('figure.svg-visual').scrollIntoViewIfNeeded()
        await page.waitForFunction(() => {
          const img = document.querySelector('figure.svg-visual img') as HTMLImageElement
          return img && img.complete && img.naturalWidth > 0
        })
        const state = await figureState(page)
        expect(state.src.startsWith('data:image/svg+xml;base64,')).toBeTruthy()
        expect(state.alt).toBe('Three layers of the service')
        expect(state.caption).toBe('Three layers of the service')
        expect(state.buttons).toEqual(['View full size', 'Copy SVG', 'Download SVG', 'Show source'])
        expect(state.liveSvg).toBe(0) // the model SVG is an image, never live DOM
        expect(state.svg).toContain('<style>:root{--sp-fg:')
        const expectedFg = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--text').trim())
        expect(state.svg).toContain('--sp-fg:' + expectedFg + ';')
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
        expect(overflow).toBeLessThanOrEqual(0)
        expect(state.width).toBeLessThanOrEqual(width)
        await shot(page, `svg-${label}-${theme}-${skin}`)
      }
      await expect(page.locator('.msg-body', { hasText: TAKEAWAY }).first()).toBeVisible()
      expect(errors).toEqual([])
      expect(foreign.filter(u => /evil\.example/.test(u))).toEqual([])
      await context.close()
    })
  }

  test('TC-SVG-002 switching the theme retints an open visual within 100 ms', async ({ browser, baseURL }) => {
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } })
    await isolate(context, baseURL!)
    const sid = await seed(context, baseURL!, '```svg\n' + GOOD + '```\n\n' + TAKEAWAY)
    const page = await context.newPage()
    await openChat(page, sid)
    await setTheme(page, 'light')
    await page.waitForTimeout(1000)
    for (const next of ['dark', 'light'] as const) {
      // From the moment the theme class changes (the app's own switch work
      // before that is not the visual's) to the new image source.
      const result = await page.evaluate(theme => new Promise<{ afterSwitch: number, total: number }>(resolve => {
        const img = document.querySelector('figure.svg-visual img') as HTMLImageElement
        const before = img.getAttribute('src')
        const start = performance.now()
        let switched: number | null = null
        const onClass = new MutationObserver(() => { if (switched === null) switched = performance.now() })
        onClass.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
        const onSrc = new MutationObserver(() => {
          if (img.getAttribute('src') === before) return
          onSrc.disconnect(); onClass.disconnect()
          const now = performance.now()
          resolve({ afterSwitch: now - (switched === null ? start : switched), total: now - start })
        })
        onSrc.observe(img, { attributes: true, attributeFilter: ['src'] })
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        ;(window as any)._applyTheme(theme)
        setTimeout(() => resolve({ afterSwitch: 9999, total: 9999 }), 1000)
      }), next)
      expect(result.afterSwitch).toBeLessThan(100)
    }
    // The bare class toggle every theme path ends in, timed from the moment
    // the new theme's styles are resolved (the page restyle itself is the
    // browser's cost of any theme switch, not the visual's).
    const toggled = await page.evaluate(() => new Promise<number>(resolve => {
      const img = document.querySelector('figure.svg-visual img') as HTMLImageElement
      const before = img.getAttribute('src')
      const onSrc = new MutationObserver(() => {
        if (img.getAttribute('src') !== before) { onSrc.disconnect(); resolve(performance.now() - start) }
      })
      onSrc.observe(img, { attributes: true, attributeFilter: ['src'] })
      document.documentElement.classList.toggle('dark')
      void getComputedStyle(document.documentElement).getPropertyValue('--text')
      const start = performance.now()
      setTimeout(() => resolve(9999), 1000)
    }))
    expect(toggled).toBeLessThan(100)
    await context.close()
  })

  test('TC-SVG-003 view full size, copy, download and show source use the sanitised bytes', async ({ browser, baseURL }) => {
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, acceptDownloads: true })
    await context.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: new URL(baseURL!).origin })
    const foreign = await isolate(context, baseURL!)
    const sid = await seed(context, baseURL!, '```svg\n' + GOOD + '```\n\n' + TAKEAWAY)
    const page = await context.newPage()
    await openChat(page, sid)
    const figure = page.locator('figure.svg-visual').first()
    const expected = await page.evaluate(src => {
      const clean = sanitizeSvgSource(src)
      // _svgVisuals is the module's global lexical binding (static/svg_visuals.js).
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const internals = (_svgVisuals as any)
      return { clean: clean.svg, exported: internals.withTheme(clean.svg, internals.LIGHT_TOKENS) }
    }, GOOD)
    expect(expected.exported).toContain('--sp-fg:#1f2937;')

    await figure.getByRole('button', { name: 'View full size' }).click()
    const lightbox = page.locator('.img-lightbox.svg-visual-lightbox img')
    await expect(lightbox).toBeVisible()
    expect(await lightbox.getAttribute('src')).toBe(await figure.locator('img.svg-visual-img').getAttribute('src'))
    await shot(page, 'svg-lightbox')
    await page.keyboard.press('Escape')
    await expect(page.locator('.img-lightbox')).toHaveCount(0)

    await figure.getByRole('button', { name: 'Copy SVG' }).click()
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe(expected.exported)

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      figure.getByRole('button', { name: 'Download SVG' }).click(),
    ])
    expect(download.suggestedFilename()).toBe('three-layers-of-the-service.svg')
    expect(fs.readFileSync(await download.path(), 'utf8')).toBe(expected.exported)
    expect(page.url()).not.toContain('blob:')

    const source = figure.getByRole('button', { name: 'Show source' })
    await source.click()
    await expect(figure.locator('pre.svg-visual-source')).toBeVisible()
    expect(await figure.locator('pre.svg-visual-source code').textContent()).toBe(expected.clean)
    await expect(figure.getByRole('button', { name: 'Hide source' })).toHaveAttribute('aria-pressed', 'true')
    await shot(page, 'svg-source')
    expect(foreign.filter(u => /evil\.example/.test(u))).toEqual([])
    await context.close()
  })

  test('TC-SVG-004 a drawing without theme tokens gets the light paper card in dark mode', async ({ browser, baseURL }) => {
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } })
    await isolate(context, baseURL!)
    const sid = await seed(context, baseURL!, '```svg\n' + PAPER + '```\n\nThe trend rises twice.')
    const page = await context.newPage()
    await openChat(page, sid)
    await setTheme(page, 'dark')
    const state = await figureState(page)
    expect(state.paper).toBeTruthy()
    expect(state.svg).toContain('--sp-fg:#1f2937;') // light tokens whatever the theme
    const background = await page.locator('figure.svg-visual img').evaluate(img => getComputedStyle(img).backgroundColor)
    expect(background).toBe('rgb(255, 255, 255)')
    await shot(page, 'svg-paper-dark')
    await context.close()
  })

  test('TC-SVG-006 a streaming svg fence stays code, collapsed behind the drawing label', async ({ browser, baseURL }) => {
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } })
    await isolate(context, baseURL!)
    const sid = await seed(context, baseURL!, 'Earlier answer without a picture.')
    const page = await context.newPage()
    await page.goto('session/' + sid)
    await page.waitForFunction(() => (window as unknown as { smd?: unknown }).smd && document.querySelector('.msg-body'))
    // A reply only streams once the page has booted, locale included.
    await page.evaluate(() => (window as unknown as { i18nReady?: Promise<unknown> }).i18nReady)
    const state = await page.evaluate(() => {
      // The live bubble exactly as messages.js builds it, fed by the real
      // streaming parser: the closing fence has not arrived yet.
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const smd = (window as any).smd
      const host = document.createElement('div')
      host.className = 'assistant-segment'
      host.setAttribute('data-live-assistant', '1')
      const body = document.createElement('div')
      body.className = 'msg-body'
      host.appendChild(body)
      const bodies = document.querySelectorAll('.assistant-segment .msg-body, .msg-body')
      const anchor = bodies[bodies.length - 1] as HTMLElement
      anchor.closest('.assistant-segment, .msg-row')!.after(host)
      const parser = smd.parser(smd.default_renderer(body))
      const rows = Array.from({ length: 30 }, (_, i) => `  <rect x="${i}" y="${i}" width="10" height="10"/>`).join('\n')
      smd.parser_write(parser, 'Drawing it now.\n\n```svg\n<svg viewBox="0 0 100 100">\n' + rows + '\n')
      const code = body.querySelector('pre > code') as HTMLElement
      const pre = code.parentElement as HTMLElement
      const style = getComputedStyle(code)
      return {
        className: code.className,
        height: code.getBoundingClientRect().height,
        fullHeight: code.scrollHeight,
        maxHeight: style.maxHeight,
        label: getComputedStyle(pre, '::before').content,
        cursor: getComputedStyle(pre, '::after').content,
        property: getComputedStyle(document.documentElement).getPropertyValue('--svg-visual-drawing-label'),
        pictures: host.querySelectorAll('figure.svg-visual, img').length,
        liveSvg: host.querySelectorAll('svg').length,
      }
    })
    expect(state.maxHeight).not.toBe('none')
    expect(state.height).toBeLessThan(state.fullHeight / 2)
    expect(state.label, JSON.stringify(state)).toContain('Drawing visual')
    expect(state.cursor).toBe('""') // the streaming cursor keeps its place
    expect(state.pictures).toBe(0)
    expect(state.liveSvg).toBe(0)
    await page.locator('[data-live-assistant="1"]').scrollIntoViewIfNeeded()
    await shot(page, 'svg-streaming')
    await context.close()
  })

  test('TC-SVG-005 the hostile corpus runs nothing and loads nothing', async ({ browser, baseURL }) => {
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } })
    const foreign = await isolate(context, baseURL!)
    const fenced = HOSTILE.map(name => `${name}\n\n\`\`\`svg\n${read('bad', name)}\`\`\``).join('\n\n')
    const raw = [
      'Raw <svg onload="window.__pwned=1" viewBox="0 0 10 10"><rect width="10" height="10"/></svg> run.',
      'Raw <svg viewBox="0 0 10 10"><script>window.__pwned=1</script><image href="https://evil.example/r.png"/></svg> run.',
    ].join('\n\n')
    const sid = await seed(context, baseURL!, fenced + '\n\n' + raw)
    const page = await context.newPage()
    const dialogs: string[] = []
    page.on('dialog', d => { dialogs.push(d.message()); d.dismiss() })
    await openChat(page, sid)
    await page.waitForFunction(() => document.querySelectorAll('figure.svg-visual, .svg-visual-blocked').length >= 30)
    // Scroll every visual into view so lazy images load, then wait.
    const images = page.locator('figure.svg-visual img.svg-visual-img')
    for (let i = 0; i < await images.count(); i++) await images.nth(i).scrollIntoViewIfNeeded()
    await page.waitForTimeout(800)
    const state = await page.evaluate(() => ({
      pwned: typeof (window as unknown as { __pwned?: unknown }).__pwned !== 'undefined',
      figures: document.querySelectorAll('figure.svg-visual').length,
      blocked: document.querySelectorAll('.svg-visual-blocked').length,
      notices: Array.from(document.querySelectorAll('.svg-visual-notice')).map(n => n.textContent),
      placeholders: document.querySelectorAll('.svg-visual-block').length,
      liveModelSvg: Array.from(document.querySelectorAll('.msg-body svg')).filter(s => !s.closest('.svg-visual-toolbar, button, .code-copy-btn')).length,
      foreignObjects: document.getElementsByTagNameNS('http://www.w3.org/2000/svg', 'foreignObject').length,
    }))
    expect(state.pwned).toBe(false)
    expect(dialogs).toEqual([])
    expect(state.placeholders).toBe(0)
    expect(state.figures + state.blocked).toBe(HOSTILE.length + 2)
    expect(state.blocked).toBe(8) // the eight rejections of the corpus
    expect(new Set(state.notices)).toEqual(new Set(['This visual was not shown because it contains content that is not allowed. The source is shown below.']))
    expect(state.liveModelSvg).toBe(0)
    expect(state.foreignObjects).toBe(0)
    // Nothing from the corpus reached the network; code blocks may still ask
    // for the page's own highlighter, which the route refuses.
    expect(foreign.filter(u => !u.startsWith('https://cdn.jsdelivr.net/npm/prismjs@'))).toEqual([])
    await shot(page, 'svg-hostile')
    await context.close()
  })
})
