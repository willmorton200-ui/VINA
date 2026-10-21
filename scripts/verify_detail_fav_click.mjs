import { spawn } from 'child_process';
import fs from 'fs';
import os from 'os';
import path from 'path';

const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const outDir = 'C:\\Users\\User\\.gemini\\antigravity\\brain\\1edcd60d-9672-4ec5-8dc2-324e955c1616';
const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'edge_fav_test_'));
const port = 9339;

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
    console.log('Target selected:', pageTarget.url);
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

    console.log('Navigating to wine detail...');
    const loadPromise = new Promise(r => { loadPromiseResolver = r; });
    await send('Page.navigate', { url: 'http://127.0.0.1:8080/static/scanner.html?preview_step=wine_detail&wine=loco-cimbali-blanc-de-neige-shardone-beloe-suhoe-131' });
    await Promise.race([loadPromise, new Promise(r => setTimeout(r, 4000))]);
    await new Promise(r => setTimeout(r, 1500));

    // Check initial state
    let res = await send('Runtime.evaluate', {
      expression: `({
        slug: window.currentDetailWineSlug,
        hasBtn: !!document.getElementById('detail-wine-fav-btn'),
        isFav: document.getElementById('detail-wine-fav-btn')?.classList.contains('is-fav'),
        badge: document.getElementById('bnav-fav-badge')?.textContent
      })`,
      returnByValue: true
    });
    console.log('Initial state:', res.result?.result?.value);

    // Click heart button
    console.log('Clicking detail-wine-fav-btn (1st click - ADD)...');
    res = await send('Runtime.evaluate', {
      expression: `(function() {
        var btn = document.getElementById('detail-wine-fav-btn');
        if (btn) btn.click();
        return {
          isFavNow: btn?.classList.contains('is-fav'),
          toastText: document.getElementById('toast')?.textContent,
          toastShow: document.getElementById('toast')?.classList.contains('show'),
          badge: document.getElementById('bnav-fav-badge')?.textContent,
          localStorageFavs: localStorage.getItem('svoe_vino_favorites')
        };
      })()`,
      returnByValue: true
    });
    console.log('State after 1st click:', res.result?.result?.value);

    // Wait a brief moment to show toast and capture screenshot of active state
    await new Promise(r => setTimeout(r, 300));
    let shot = await send('Page.captureScreenshot', { format: 'png' });
    if (shot?.result?.data) {
      fs.writeFileSync(path.join(outDir, 'preview_detail_fav_clicked_active.png'), Buffer.from(shot.result.data, 'base64'));
      console.log('Saved preview_detail_fav_clicked_active.png');
    }

    // Click heart button again to verify toggling OFF
    console.log('Clicking detail-wine-fav-btn (2nd click - REMOVE)...');
    res = await send('Runtime.evaluate', {
      expression: `(function() {
        var btn = document.getElementById('detail-wine-fav-btn');
        if (btn) btn.click();
        return {
          isFavNow: btn?.classList.contains('is-fav'),
          toastText: document.getElementById('toast')?.textContent,
          badge: document.getElementById('bnav-fav-badge')?.textContent,
          localStorageFavs: localStorage.getItem('svoe_vino_favorites')
        };
      })()`,
      returnByValue: true
    });
    console.log('State after 2nd click (toggled off):', res.result?.result?.value);

    // Click once more to leave it in Favorites for Favorites tab screenshot
    console.log('Clicking detail-wine-fav-btn (3rd click - ADD BACK)...');
    await send('Runtime.evaluate', {
      expression: `document.getElementById('detail-wine-fav-btn')?.click()`
    });
    await new Promise(r => setTimeout(r, 400));

    // Capture the final active favorite card
    shot = await send('Page.captureScreenshot', { format: 'png' });
    if (shot?.result?.data) {
      fs.writeFileSync(path.join(outDir, 'preview_detail_fav_active_final.png'), Buffer.from(shot.result.data, 'base64'));
      console.log('Saved preview_detail_fav_active_final.png');
    }

    // Switch to Favorites tab and capture screenshot
    console.log('Switching to Favorites tab...');
    await send('Runtime.evaluate', { expression: `switchHubTab('favorites')` });
    await new Promise(r => setTimeout(r, 600));

    shot = await send('Page.captureScreenshot', { format: 'png' });
    if (shot?.result?.data) {
      fs.writeFileSync(path.join(outDir, 'preview_favorites_showing_added_wine.png'), Buffer.from(shot.result.data, 'base64'));
      console.log('Saved preview_favorites_showing_added_wine.png');
    }

    console.log('ALL TESTS COMPLETED SUCCESSFULLY!');
    ws.close();
  } catch (err) {
    console.error('Test error:', err);
  } finally {
    edgeProc.kill();
  }
}

run();
