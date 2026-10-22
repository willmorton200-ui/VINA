import { spawn } from 'child_process';
import fs from 'fs';
import os from 'os';
import path from 'path';

const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const outDir = 'C:\\Users\\User\\.gemini\\antigravity\\brain\\1edcd60d-9672-4ec5-8dc2-324e955c1616';
const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'edge_cdp_orig_test_'));
const port = 9355;

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

    const testUrl = 'http://127.0.0.1:8080/scanner?preview_step=catalog';
    console.log(`Navigating to URL: ${testUrl}...`);

    const loadPromise = new Promise(r => { loadPromiseResolver = r; });
    await send('Page.navigate', { url: testUrl });
    await Promise.race([loadPromise, new Promise(r => setTimeout(r, 6000))]);
    await new Promise(r => setTimeout(r, 2000));

    console.log('--- TEST 1: Original photo comparison after finding wine ---');
    // Simulate user scanning a wine:
    // Create a sample image dataUrl representing the user's bottle photo
    await evaluate(`
      (() => {
        // Create a realistic sample photo on canvas
        const canvas = document.createElement('canvas');
        canvas.width = 300;
        canvas.height = 450;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#2b2d42';
        ctx.fillRect(0, 0, 300, 450);
        ctx.fillStyle = '#722F37';
        ctx.fillRect(50, 100, 200, 260);
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 16px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('СНИМОК С КАМЕРЫ', 150, 200);
        ctx.font = '13px sans-serif';
        ctx.fillText('Мадера Массандра', 150, 230);
        ctx.fillText('Крымская 1945', 150, 255);
        const dataUrl = canvas.toDataURL('image/jpeg');

        window.currentUploadedImageURL = dataUrl;
        window.lastScannedPhotoDataUrl = dataUrl;
        sessionStorage.setItem('vina_last_scanned_photo', dataUrl);

        // Open wine detail for massandra-madera-krymskaya from scanner
        window.openWineDetail('massandra-madera-krymskaya', 'scanner');
      })()
    `);

    await new Promise(r => setTimeout(r, 1500));

    // Now trigger showScanOriginalPhoto() to open the comparison view
    await evaluate(`
      (() => {
        if (typeof window.showScanOriginalPhoto === 'function') {
          window.showScanOriginalPhoto();
        }
      })()
    `);

    await new Promise(r => setTimeout(r, 1200));

    const shot1 = await send('Page.captureScreenshot', { format: 'png' });
    if (shot1 && shot1.result && shot1.result.data) {
      const buf = Buffer.from(shot1.result.data, 'base64');
      const outPath = path.join(outDir, 'preview_original_photo_comparison.png');
      fs.writeFileSync(outPath, buf);
      console.log(`Saved screenshot: preview_original_photo_comparison.png (${buf.length} bytes)`);
    }

    console.log('--- TEST 2: Missing wine modal with photo & prompt ---');
    await evaluate(`
      (() => {
        window.showMissingWineModal('Данного вина нет в базе, отправить разработчику для добавления в базу?');
      })()
    `);

    await new Promise(r => setTimeout(r, 1000));

    const shot2 = await send('Page.captureScreenshot', { format: 'png' });
    if (shot2 && shot2.result && shot2.result.data) {
      const buf = Buffer.from(shot2.result.data, 'base64');
      const outPath = path.join(outDir, 'preview_missing_wine_modal_with_photo.png');
      fs.writeFileSync(outPath, buf);
      console.log(`Saved screenshot: preview_missing_wine_modal_with_photo.png (${buf.length} bytes)`);
    }

    console.log('--- TEST 3: Click "Отправить разработчику" ---');
    await evaluate(`
      (async () => {
        if (typeof window.submitMissingWineToDevs === 'function') {
          await window.submitMissingWineToDevs();
        }
      })()
    `);

    await new Promise(r => setTimeout(r, 1000));

    const shot3 = await send('Page.captureScreenshot', { format: 'png' });
    if (shot3 && shot3.result && shot3.result.data) {
      const buf = Buffer.from(shot3.result.data, 'base64');
      const outPath = path.join(outDir, 'preview_missing_wine_submitted_success.png');
      fs.writeFileSync(outPath, buf);
      console.log(`Saved screenshot: preview_missing_wine_submitted_success.png (${buf.length} bytes)`);
    }

    ws.close();
  } catch (err) {
    console.error('Error during test:', err);
  } finally {
    edgeProc.kill();
  }
}

run();
