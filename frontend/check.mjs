import { chromium } from 'playwright'

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

const errors = []
page.on('console', (m) => {
  if (m.type() === 'error') errors.push(m.text())
})
page.on('pageerror', (e) => errors.push(`PAGEERROR: ${e.message}`))

await page.goto('http://localhost:4173/', { waitUntil: 'networkidle' })
await page.waitForTimeout(1500)

console.log('--- console errors ---')
console.log(errors.length ? errors.join('\n') : '(ninguno)')

console.log('--- root html (300 chars) ---')
console.log((await page.locator('#root').innerHTML()).slice(0, 300))

for (const sel of ['textarea', 'header', 'h1', 'h2', 'select', '.glass', '.glass-raised']) {
  console.log(`${sel}: ${await page.locator(sel).count()}`)
}

await browser.close()
