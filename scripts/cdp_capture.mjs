import { spawn } from 'child_process';
import fs from 'fs';
import os from 'os';
import path from 'path';

const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const outDir = 'C:\\Users\\User\\.gemini\\antigravity\\brain\\1edcd60d-9672-4ec5-8dc2-324e955c1616';
const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'edge_cdp_'));
const port = 9333;

const edgeProc = spawn(edgePath, [
  '--headless',
  '--disable-gpu',
  '--disable-extensions',
  '--no-first-run',
  '--no-default-browser-check',
  `--user-data-dir=${tempDir}`,
  `--remote-debugging-port=${port}`,
  '--window-size=440,920',
  'about:blank'
]);

// Wait for port
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
      if (data.method === 'Runtime.consoleAPICalled') {
        console.log(`[BROWSER CONSOLE] ${data.params.type}:`, data.params.args.map(a => a.value || a.description).join(' '));
      }
      if (data.method === 'Runtime.exceptionThrown') {
        console.error(`[BROWSER ERROR]:`, data.params.exceptionDetails);
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

    await send('Page.enable');
    await send('Runtime.enable');
    await send('DOM.enable');

    const tasks = [
      {
        name: 'preview_wine_detail_card_unified.png',
        url: 'http://127.0.0.1:8080/static/scanner.html?preview_step=wine_detail&wine=loco-cimbali-blanc-de-neige-shardone-beloe-suhoe-131',
        waitMs: 1500
      },
      {
        name: 'preview_wine_detail_from_scanner.png',
        url: 'http://127.0.0.1:8080/static/scanner.html?preview_step=wine_detail_scanner',
        waitMs: 1500
      },
      {
        name: 'preview_wine_set_modal_selector.png',
        url: 'http://127.0.0.1:8080/static/scanner.html?preview_step=wine_set_modal',
        waitMs: 1500
      },
      {
        name: 'preview_wine_set_modal_generated.png',
        url: 'http://127.0.0.1:8080/static/scanner.html?preview_step=wine_set_generated',
        waitMs: 2000
      },
      {
        name: 'preview_favorites_with_sets.png',
        url: 'http://127.0.0.1:8080/static/scanner.html?preview_step=favorites_with_sets',
        waitMs: 1500
      }
    ];

    for (const t of tasks) {
      console.log(`Navigating to ${t.url}...`);
      const loadPromise = new Promise(r => { loadPromiseResolver = r; });
      await send('Page.navigate', { url: t.url });
      await Promise.race([loadPromise, new Promise(r => setTimeout(r, 4000))]);
      await new Promise(r => setTimeout(r, t.waitMs));

      const shot = await send('Page.captureScreenshot', { format: 'png' });
      if (shot && shot.result && shot.result.data) {
        const buf = Buffer.from(shot.result.data, 'base64');
        const outPath = path.join(outDir, t.name);
        fs.writeFileSync(outPath, buf);
        console.log(`Saved ${t.name} (${buf.length} bytes)`);
      } else {
        console.error(`Failed to capture ${t.name}:`, shot);
      }
    }

    ws.close();
  } catch (err) {
    console.error('Error during CDP execution:', err);
  } finally {
    edgeProc.kill();
  }
}

run();
