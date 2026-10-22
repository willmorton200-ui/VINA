import { spawn } from 'child_process';
import fs from 'fs';
import os from 'os';
import path from 'path';

const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const outDir = 'C:\\Users\\User\\.gemini\\antigravity\\brain\\1edcd60d-9672-4ec5-8dc2-324e955c1616';
const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'edge_cdp_pairing_qa_'));
const port = 9345;

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

    await send('Page.enable');
    await send('Runtime.enable');
    await send('DOM.enable');

    const testUrl = 'http://127.0.0.1:8080/scanner?preview_step=sommelier_stub';
    console.log(`Navigating to URL: ${testUrl}...`);

    const loadPromise = new Promise(r => { loadPromiseResolver = r; });
    await send('Page.navigate', { url: testUrl });
    await Promise.race([loadPromise, new Promise(r => setTimeout(r, 6000))]);
    await new Promise(r => setTimeout(r, 2000));

    console.log('Opening sommelier for Madera Massandra...');
    await evaluate(`
      (() => {
        if (typeof window.openSommelierEntryPoint === 'function') {
          window.openSommelierEntryPoint('massandra-madera-krymskaya', {
            name: 'Мадера Массандра Крымская Выдержанная'
          }, 'chat');
        }
      })()
    `);

    await new Promise(r => setTimeout(r, 1000));

    console.log('Sending question: "К какому блюду подходит это вино?"');
    await evaluate(`
      (async () => {
        if (typeof window.sendSommChatMessage === 'function') {
          await window.sendSommChatMessage('К какому блюду подходит это вино?');
        }
      })()
    `);

    // Wait for response to render in chat
    await new Promise(r => setTimeout(r, 3000));

    // Scroll to see both the user message and start of the assistant answer
    await evaluate(`
      (() => {
        const box = document.getElementById('somm-chat-messages');
        if (box) {
          box.scrollTop = box.scrollHeight / 3;
        }
      })()
    `);
    await new Promise(r => setTimeout(r, 500));

    const shot = await send('Page.captureScreenshot', { format: 'png' });
    if (shot && shot.result && shot.result.data) {
      const buf = Buffer.from(shot.result.data, 'base64');
      const outPath = path.join(outDir, 'preview_sommelier_food_pairing_fixed.png');
      fs.writeFileSync(outPath, buf);
      console.log(`Saved screenshot: preview_sommelier_food_pairing_fixed.png (${buf.length} bytes)`);
    }

    ws.close();
  } catch (err) {
    console.error('Error during test:', err);
  } finally {
    edgeProc.kill();
  }
}

run();
