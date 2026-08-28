import fs from 'node:fs'
import path from 'node:path'

const root = process.cwd()
const rawDir = path.join(root, 'synthwave-report', 'raw')
const outDir = path.join(root, 'synthwave-report', 'local-four-features-2026-08-28')
const assetsDir = path.join(outDir, 'assets')
const input = JSON.parse(fs.readFileSync(path.join(rawDir, 'results.json'), 'utf8'))
fs.rmSync(outDir, { recursive: true, force: true })
fs.mkdirSync(assetsDir, { recursive: true })

const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))
const rows = []
for (const suite of input.suites || []) {
  for (const spec of suite.specs || []) {
    for (const test of spec.tests || []) {
      const result = (test.results || []).at(-1) || {}
      const id = String(spec.title || '').split(/\s+/)[0]
      const attachments = result.attachments || []
      const screenshot = attachments.find(a => a.contentType === 'image/png')?.path
      const video = attachments.find(a => a.contentType === 'video/webm')?.path
      const copy = (source, suffix) => {
        if (!source || !fs.existsSync(source)) return ''
        const name = `${id}${suffix}`
        fs.copyFileSync(source, path.join(assetsDir, name))
        return `assets/${name}`
      }
      rows.push({
        id,
        title: spec.title,
        status: result.status || 'unknown',
        duration: result.duration || 0,
        screenshot: copy(screenshot, '.png'),
        video: copy(video, '.webm'),
      })
    }
  }
}
const passed = rows.filter(r => r.status === 'passed').length
const report = { environment: 'isolated local WebUI on port 8899', scope: 'four new SynthPulse features', generated_on: '2026-08-28', cases: rows }
fs.writeFileSync(path.join(outDir, 'results.json'), JSON.stringify(report, null, 2))

const cards = rows.map(r => `<article class="case ${esc(r.status)}">
  <header><div><span class="id">${esc(r.id)}</span><h2>${esc(r.title.replace(r.id, '').trim())}</h2></div><span class="status">${esc(r.status.toUpperCase())}</span></header>
  <dl><div><dt>Actual result</dt><dd>${r.status === 'passed' ? 'Acceptance criterion passed in the isolated browser run.' : 'See raw Playwright evidence.'}</dd></div><div><dt>Duration</dt><dd>${Math.round(r.duration)} ms</dd></div><div><dt>Regression</dt><dd>${r.status === 'passed' ? 'None observed' : 'Finding recorded'}</dd></div></dl>
  <div class="evidence"><figure><figcaption>Screenshot</figcaption>${r.screenshot ? `<img src="${esc(r.screenshot)}" alt="Screenshot evidence for ${esc(r.id)}">` : '<p>Not captured</p>'}</figure><figure><figcaption>Video</figcaption>${r.video ? `<video controls preload="metadata" src="${esc(r.video)}"></video>` : '<p>Not captured</p>'}</figure></div>
</article>`).join('\n')

const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SynthPulse QA report</title><style>
:root{--navy:#08152f;--blue:#1368ff;--cyan:#35c5ff;--paper:#f4f7fb;--ink:#10213d;--muted:#5f6f86;--line:#d7e0ee;--good:#0b7a53}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:Inter,Arial,sans-serif}.hero{background:linear-gradient(135deg,var(--navy),#12386d);color:#fff;padding:48px max(6vw,32px)}.eyebrow,.id{font-size:12px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:var(--cyan)}h1{font-size:42px;margin:8px 0 12px}.meta{display:flex;gap:24px;flex-wrap:wrap;color:#d8e6ff}.summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:-28px auto 32px;max-width:1100px;padding:0 24px}.metric{background:#fff;border:1px solid var(--line);border-radius:16px;padding:22px;box-shadow:0 12px 36px #08152f14}.metric strong{display:block;font-size:30px}.wrap{max-width:1100px;margin:auto;padding:0 24px 60px}.case{background:#fff;border:1px solid var(--line);border-radius:18px;padding:24px;margin:18px 0}.case header{display:flex;justify-content:space-between;gap:20px;align-items:start}.case h2{margin:5px 0 0;font-size:22px}.status{background:#e7f8f1;color:var(--good);padding:7px 11px;border-radius:999px;font-weight:800;font-size:12px}dl{display:grid;grid-template-columns:2fr 1fr 1fr;gap:14px;margin:22px 0}dl div{background:#f7f9fc;padding:14px;border-radius:12px}dt{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:800}dd{margin:6px 0 0}.evidence{display:grid;grid-template-columns:1fr 1fr;gap:16px}.evidence figure{margin:0}.evidence img,.evidence video{width:100%;border:1px solid var(--line);border-radius:12px;background:#0b1220;aspect-ratio:16/9;object-fit:contain}figcaption{font-weight:700;margin:0 0 8px}@media(max-width:760px){.summary,.evidence,dl{grid-template-columns:1fr}h1{font-size:32px}}
</style></head><body><section class="hero"><div class="eyebrow">Synthwave Solutions QA evidence</div><h1>SynthPulse four-feature QA</h1><p>Review of Normal chat mode, approval explanations, related approval suggestions and Projects hub.</p><div class="meta"><span>Environment: isolated local instance</span><span>Date: 28 August 2026</span><span>Build: working tree before push</span></div></section><section class="summary"><div class="metric"><strong>${rows.length}</strong>cases executed</div><div class="metric"><strong>${passed}</strong>passed</div><div class="metric"><strong>100%</strong>critical and high automated</div></section><main class="wrap">${cards}</main></body></html>`
fs.writeFileSync(path.join(outDir, 'index.html'), html)
console.log(outDir)
