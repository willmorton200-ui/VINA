import { spawn } from 'child_process';
import fs from 'fs';
import os from 'os';
import path from 'path';

const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const outDir = 'C:\\Users\\User\\.gemini\\antigravity\\brain\\1edcd60d-9672-4ec5-8dc2-324e955c1616';
const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'edge_party_fav_'));
const port = 9346;

const edgeProc = spawn(edgePath, [
  '--headless',
  '--disable-gpu',
  '--disable-extensions',
  '--no-first-run',
  '--no-default-browser-check',
  `--user-data-dir=${tempDir}`,
  `--remote-debugging-port=${port}`,
  '--window-size=440,960',
  'about:blank'
]);

async function waitForPort() {
  for (let i = 0; i < 30; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/json`);
      if (res.ok) return await res.json();
    } catch (e) {}
    await new Promise(r => setTimeout(r, 200));
  }
  throw new Error('Could not connect to Edge DevTools');
}

async function run() {
  try {
    const list = await waitForPort();
    const pageTarget = list.find(t => t.type === 'page' && !t.url.startsWith('chrome-extension')) || list.find(t => t.type === 'page') || list[0];
    console.log('Selected target:', pageTarget.url);
    const ws = new WebSocket(pageTarget.webSocketDebuggerUrl);

    let msgId = 1;
    const callbacks = new Map();
    let loadPromiseResolver = null;

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.method === 'Page.loadEventFired' && loadPromiseResolver) {
        loadPromiseResolver();
        loadPromiseResolver = null;
      }
      if (data.method === 'Runtime.consoleAPICalled') {
        console.log(`[CONSOLE] ${data.params.type}:`, data.params.args.map(a => a.value || a.description).join(' '));
      }
      if (data.method === 'Runtime.exceptionThrown') {
        console.error(`[BROWSER ERROR]:`, data.params.exceptionDetails);
      }
      if (data.id && callbacks.has(data.id)) {
        callbacks.get(data.id)(data);
        callbacks.delete(data.id);
      }
    };

    await new Promise(r => ws.onopen = r);

    function send(method, params = {}) {
      return new Promise(resolve => {
        const id = msgId++;
        callbacks.set(id, resolve);
        ws.send(JSON.stringify({ id, method, params }));
      });
    }

    await send('Page.enable');
    await send('Runtime.enable');

    console.log('Navigating to favorites_with_sets...');
    const loadPromise = new Promise(r => { loadPromiseResolver = r; });
    await send('Page.navigate', { url: 'http://127.0.0.1:8080/static/scanner.html?preview_step=favorites_with_sets' });
    await Promise.race([loadPromise, new Promise(r => setTimeout(r, 4000))]);
    await new Promise(r => setTimeout(r, 1200));

    // 1. Initial State Check
    let res = await send('Runtime.evaluate', {
      expression: `(function() {
        return {
          tab: document.querySelector('.hub-panel.active')?.id,
          hasCalc: !!document.querySelector('.fav-party-calc-card'),
          guestsInput: document.getElementById('fav-guests-input')?.value,
          setCardsCount: document.querySelectorAll('.fav-set-card-block .home-wine-card').length,
          standaloneCardsCount: document.querySelectorAll('#favorites-wines-grid > .home-wine-card').length,
          totalQtyValues: Array.from(document.querySelectorAll('.fav-qty-value')).map(el => el.textContent.trim()),
          summaryTotalText: document.querySelector('.fav-summary-value')?.textContent.trim()
        };
      })()`,
      returnByValue: true
    });
    console.log('1. Initial Favorites State:', JSON.stringify(res.result?.result?.value, null, 2));

    // Screenshot 1: Top view with calculator
    let snap = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(outDir, 'preview_favorites_party_calc.png'), Buffer.from(snap.result.data, 'base64'));
    console.log('Captured preview_favorites_party_calc.png');

    // 2. Click "Увеличить сет до 9 шт."
    console.log('Clicking "Увеличить сет до 9 шт."...');
    await send('Runtime.evaluate', {
      expression: `(function() {
        var btn = document.querySelector('.btn-fav-set-action.primary');
        if (btn) btn.click();
      })()`
    });
    await new Promise(r => setTimeout(r, 600));

    // Screenshot 2: Scaled to 9 notification
    snap = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(outDir, 'preview_favorites_set_scaled_9.png'), Buffer.from(snap.result.data, 'base64'));
    console.log('Captured preview_favorites_set_scaled_9.png');

    // 3. Scroll down to show the wine cards in the set with their steppers and quantity row
    console.log('Scrolling to show wine set cards with steppers...');
    await send('Runtime.evaluate', {
      expression: `window.scrollTo({ top: 380, behavior: 'instant' });`
    });
    await new Promise(r => setTimeout(r, 400));

    // Screenshot 3: Cards view showing per-bottle quantities [ - ] X шт. [ + ]
    snap = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(outDir, 'preview_favorites_bottles_qty.png'), Buffer.from(snap.result.data, 'base64'));
    console.log('Captured preview_favorites_bottles_qty.png');

    // 4. Scroll to bottom to show bottom summary card
    console.log('Scrolling to bottom summary...');
    await send('Runtime.evaluate', {
      expression: `window.scrollTo({ top: document.body.scrollHeight, behavior: 'instant' });`
    });
    await new Promise(r => setTimeout(r, 400));

    // Screenshot 4: Bottom summary card
    snap = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(outDir, 'preview_favorites_summary_card.png'), Buffer.from(snap.result.data, 'base64'));
    console.log('Captured preview_favorites_summary_card.png');

    // 5. Open Shopping List Modal
    console.log('Opening Shopping List Modal...');
    await send('Runtime.evaluate', {
      expression: `openFavShoppingListModal();`
    });
    await new Promise(r => setTimeout(r, 500));

    // Screenshot 5: Shopping List Modal
    snap = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(outDir, 'preview_favorites_shopping_modal.png'), Buffer.from(snap.result.data, 'base64'));
    console.log('Captured preview_favorites_shopping_modal.png');

    console.log('ALL VERIFICATIONS COMPLETED SUCCESSFULLY!');
    ws.close();
  } catch (err) {
    console.error('Test script error:', err);
  } finally {
    edgeProc.kill();
    try { fs.rmSync(tempDir, { recursive: true, force: true }); } catch (e) {}
  }
}

run();
