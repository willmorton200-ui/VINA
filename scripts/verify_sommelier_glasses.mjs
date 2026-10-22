import { spawn } from 'child_process';
import fs from 'fs';
import os from 'os';
import path from 'path';

const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const outDir = 'C:\\Users\\User\\.gemini\\antigravity\\brain\\1edcd60d-9672-4ec5-8dc2-324e955c1616';
const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'edge_cdp_somm2_'));
const port = 9335;

const edgeProc = spawn(edgePath, [
  '--headless',
  '--disable-gpu',
  '--disable-extensions',
  '--no-first-run',
  '--no-default-browser-check',
  `--user-data-dir=${tempDir}`,
  `--remote-debugging-port=${port}`,
  '--window-size=430,932',
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
    const pageTarget = list.find(t => t.type === 'page') || list[0];
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
      if (data.id && callbacks.has(data.id)) {
        callbacks.get(data.id)(data);
        callbacks.delete(data.id);
      }
    };

    await new Promise((resolve) => { ws.onopen = resolve; });

    function send(method, params = {}) {
      return new Promise((resolve) => {
        const id = msgId++;
        callbacks.set(id, resolve);
        ws.send(JSON.stringify({ id, method, params }));
      });
    }

    async function evaluate(expression) {
      const res = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
      return res?.result?.result?.value;
    }

    async function takeScreenshot(name) {
      const shot = await send('Page.captureScreenshot', { format: 'png' });
      if (shot && shot.result && shot.result.data) {
        const buf = Buffer.from(shot.result.data, 'base64');
        const outPath = path.join(outDir, name);
        fs.writeFileSync(outPath, buf);
        console.log(`Saved screenshot: ${name} (${buf.length} bytes)`);
      } else {
        console.error(`Failed to capture screenshot: ${name}`, shot);
      }
    }

    await send('Page.enable');
    await send('Runtime.enable');
    await send('DOM.enable');

    console.log('Navigating to app with preview_step=sommelier_stub...');
    const loadPromise = new Promise(r => { loadPromiseResolver = r; });
    await send('Page.navigate', { url: 'http://127.0.0.1:8080/static/scanner.html?preview_step=sommelier_stub' });
    await Promise.race([loadPromise, new Promise(r => setTimeout(r, 4000))]);
    await new Promise(r => setTimeout(r, 1500));

    // 1. Sommelier Chat view screenshot
    await takeScreenshot('preview_sommelier_chat.png');

    // 2. Switch to Pairing mode and run a query
    console.log('Testing Sommelier Pairing tab...');
    await evaluate(`
      (async () => {
        switchSommModalTab('pairing');
        const input = document.getElementById('somm-pairing-custom-dish');
        if (input) input.value = 'Стейк Рибай';
        if (typeof runSommPairingCustom === 'function') {
          await runSommPairingCustom();
        }
      })()
    `);
    await new Promise(r => setTimeout(r, 2000));
    await takeScreenshot('preview_sommelier_pairing.png');

    // 3. Switch to Toast mode and generate a toast
    console.log('Testing Sommelier Toast tab...');
    await evaluate(`
      (async () => {
        switchSommModalTab('toast');
        if (typeof runSommModalToast === 'function') {
          await runSommModalToast();
        }
      })()
    `);
    await new Promise(r => setTimeout(r, 2000));
    await takeScreenshot('preview_sommelier_toast.png');

    // 4. Close modal and inspect Wine Detail page Sommelier sections scrolled to organoleptic profile & pairings
    console.log('Testing Wine Detail Sommelier sections...');
    await evaluate(`
      (() => {
        closeSommelierStubModal();
        const profileEl = document.getElementById('detail-somm-advice-block') || document.querySelector('.wine-food-pairing-section');
        if (profileEl) profileEl.scrollIntoView({ behavior: 'instant', block: 'center' });
      })()
    `);
    await new Promise(r => setTimeout(r, 800));
    await takeScreenshot('preview_sommelier_wine_detail_pairing.png');

    console.log('All updated screenshots completed successfully!');
    ws.close();
  } catch (err) {
    console.error('Error during CDP execution:', err);
  } finally {
    edgeProc.kill();
  }
}

run();
