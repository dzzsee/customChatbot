import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'

const OUT = 'C:/Users/Dizi/AppData/Local/Temp/opencode/shots'
mkdirSync(OUT, { recursive: true })

const URL = 'http://localhost:4173/'

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })

await page.goto(URL, { waitUntil: 'networkidle' })
await page.waitForTimeout(1200)
await page.screenshot({ path: `${OUT}/01-desktop-empty.png` })

// Con una conversacion real, para ver las burbujas de vidrio.
await page.getByRole('textbox').fill('Hola, presentate en espanol.')
await page.getByRole('button', { name: 'Enviar' }).click()
await page.waitForTimeout(9000)
await page.screenshot({ path: `${OUT}/02-desktop-chat.png` })

// Mobil: estado vacio + drawer
const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 })
await mobile.goto(URL, { waitUntil: 'networkidle' })
await mobile.waitForTimeout(1000)
await mobile.screenshot({ path: `${OUT}/03-mobile-empty.png` })
await mobile.getByRole('button', { name: 'Abrir panel de archivos' }).click()
await mobile.waitForTimeout(700)
await mobile.screenshot({ path: `${OUT}/04-mobile-drawer.png` })

// Foco en el composer
await page.locator('textarea').focus()
await page.waitForTimeout(400)
await page.locator('textarea').fill('Probando el estado de foco del composer')
await page.waitForTimeout(300)
await page.screenshot({ path: `${OUT}/05-composer-focus.png` })

await browser.close()
console.log('capturas en', OUT)
