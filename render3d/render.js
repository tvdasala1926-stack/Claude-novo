// Usage: node render.js --timeline /work/x/timeline.json --out out.mp4 [--w 1080 --h 1920 --fps 30]
//        node render.js --timeline ... --preview "0.5,4,8" --outdir dir   (PNG snapshots only)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const http = require('http'), fs = require('fs'), path = require('path');

const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, arr) => (v.startsWith('--') ? [...a, [v.slice(2), arr[i + 1]]] : a), []));
const W = +args.w || 1080, H = +args.h || 1920, FPS = +args.fps || 30;
const ROOT = __dirname, TLPATH = path.resolve(args.timeline);
const tl = JSON.parse(fs.readFileSync(TLPATH, 'utf8'));
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json' };

const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0]);
  const file = u === '/__timeline.json' ? TLPATH : path.join(ROOT, u === '/' ? 'index.html' : u);
  if (!file.startsWith(ROOT) && file !== TLPATH) { res.writeHead(403); return res.end(); }
  fs.readFile(file, (e, d) => { if (e) { res.writeHead(404); return res.end(); } res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream' }); res.end(d); });
}).listen(0);

(async () => {
  const port = server.address().port;
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: W, height: H } });
  page.on('pageerror', (e) => { console.error('PAGE ERROR:', e.message); process.exitCode = 2; });
  await page.goto(`http://localhost:${port}/index.html?w=${W}&h=${H}&timeline=/__timeline.json`);
  await page.waitForFunction('window.ready===true', { timeout: 60000 });

  if (args.preview) {
    fs.mkdirSync(args.outdir, { recursive: true });
    for (const t of args.preview.split(',').map(Number)) {
      await page.evaluate((x) => window.renderAt(x), t);
      await page.screenshot({ path: path.join(args.outdir, `t_${t.toFixed(2)}.png`) });
    }
  } else {
    const n = Math.round(tl.duration * FPS);
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-preset', 'medium', '-crf', '15', '-pix_fmt', 'yuv420p', '-r', String(FPS), args.out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const t0 = Date.now();
    for (let i = 0; i < n; i++) {
      await page.evaluate((x) => window.renderAt(x), i / FPS);
      const buf = await page.screenshot({ type: 'jpeg', quality: 95 });
      if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
      if (i % 60 === 0) console.log(`frame ${i}/${n}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
    ff.stdin.end();
    await new Promise((r) => ff.on('close', r));
  }
  await browser.close(); server.close();
})().catch((e) => { console.error(e); process.exit(1); });
