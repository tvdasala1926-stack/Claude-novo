import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const params = new URLSearchParams(location.search);
const W = +params.get('w') || 1080;
const H = +params.get('h') || 1920;
const TL = await (await fetch(params.get('timeline'))).json();
const PORTRAIT = H >= W;

document.getElementById('stage').style.cssText = `width:${W}px;height:${H}px`;
const canvas = document.getElementById('c');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance' });
renderer.setPixelRatio(1);
renderer.setSize(W, H, false);
canvas.style.width = W + 'px';
canvas.style.height = H + 'px';
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x120a07);
scene.fog = new THREE.Fog(0x120a07, 14, 46);
const camera = new THREE.PerspectiveCamera(PORTRAIT ? 50 : 38, W / H, 0.1, 120);

const rt = new THREE.WebGLRenderTarget(W, H, { samples: 4, type: THREE.HalfFloatType });
const composer = new EffectComposer(renderer, rt);
composer.addPass(new RenderPass(scene, camera));
composer.addPass(new UnrealBloomPass(new THREE.Vector2(W / 2, H / 2), 0.75, 0.55, 0.82));
composer.addPass(new OutputPass());

// ---------- palette & helpers ----------
const ORANGE = 0xff6a2a, CREAM = 0xf3e6d8;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, t) => a + (b - a) * t;
const easeOut = (t) => 1 - Math.pow(1 - clamp(t), 3);
const easeInOut = (t) => { t = clamp(t); return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; };
const easeBack = (t) => { t = clamp(t); const c = 1.70158; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2); };
let seed = 12345;
const rnd = () => ((seed = (seed * 1664525 + 1013904223) % 4294967296) / 4294967296);

// ---------- lights ----------
scene.add(new THREE.AmbientLight(0xa08070, 0.55));
const key = new THREE.DirectionalLight(0xffc090, 2.4); key.position.set(4, 9, 6); scene.add(key);
const warm = new THREE.PointLight(ORANGE, 90, 26, 1.6); warm.position.set(-4, 3, 2); scene.add(warm);
const rim = new THREE.PointLight(0x6aa0ff, 40, 26, 1.6); rim.position.set(5, 2.5, -3); scene.add(rim);

// ---------- environment: floor + "machine" wall ----------
const floor = new THREE.Mesh(new THREE.PlaneGeometry(200, 200),
  new THREE.MeshStandardMaterial({ color: 0x1a0f0a, roughness: 0.28, metalness: 0.75 }));
floor.rotation.x = -Math.PI / 2; floor.position.y = -0.46; scene.add(floor);

function screenTexture() {
  const c = document.createElement('canvas'); c.width = 256; c.height = 160;
  const g = c.getContext('2d'); g.fillStyle = '#1a0f0a'; g.fillRect(0, 0, 256, 160);
  for (let i = 0; i < 7; i++) {
    g.fillStyle = i % 3 === 0 ? '#ff6a2a' : '#7a3a1c';
    g.fillRect(16, 14 + i * 20, 40 + rnd() * 170, 7);
  }
  return new THREE.CanvasTexture(c);
}
const wall = new THREE.Group();
for (let i = -3; i <= 3; i++) {
  const body = new THREE.Mesh(new RoundedBoxGeometry(5.2, 6, 3, 2, 0.2),
    new THREE.MeshStandardMaterial({ color: 0x9c8574, roughness: 0.6 }));
  body.position.set(i * 5.8, 2.5, 0);
  const scr = new THREE.Mesh(new THREE.PlaneGeometry(4.2, 2.6),
    new THREE.MeshBasicMaterial({ map: screenTexture(), toneMapped: false }));
  scr.position.set(i * 5.8, 3.4, 1.52);
  const strip = new THREE.Mesh(new THREE.BoxGeometry(5.2, 0.12, 0.1),
    new THREE.MeshBasicMaterial({ color: ORANGE, toneMapped: false }));
  strip.position.set(i * 5.8, 0.6, 1.52);
  wall.add(body, scr, strip);
}
wall.position.set(0, 0, -19); scene.add(wall);

// ---------- keyboard (60%, 61 keys) ----------
const L = (s) => s.split('').map((c) => [c, 1]);
const LAYOUT = [
  [...L('`1234567890-='), ['⌫', 2]],
  [['Tab', 1.5], ...L('QWERTYUIOP[]'), ['\\', 1.5]],
  [['Caps', 1.75], ...L("ASDFGHJKL;'"), ['Enter', 2.25]],
  [['Shift', 2.25], ...L('ZXCVBNM,./'), ['Shift', 2.75]],
  [['Ctrl', 1.25], ['Win', 1.25], ['Alt', 1.25], ['', 6.25], ['Alt', 1.25], ['Fn', 1.25], ['Menu', 1.25], ['Ctrl', 1.25]],
];
function legend(label, w) {
  const c = document.createElement('canvas'); c.width = Math.round(64 * w); c.height = 64;
  const g = c.getContext('2d'); g.clearRect(0, 0, c.width, 64);
  g.fillStyle = '#f3e6d8'; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.font = `bold ${label.length > 2 ? 20 : 30}px Inter, DejaVu Sans, sans-serif`;
  g.fillText(label, c.width / 2, 34);
  const t = new THREE.CanvasTexture(c); t.anisotropy = 4; return t;
}

function buildKeyboard() {
  const g = new THREE.Group();
  const inner = new THREE.Group(); g.add(inner);
  const caseMesh = new THREE.Mesh(new RoundedBoxGeometry(15.7, 0.9, 5.8, 3, 0.25),
    new THREE.MeshStandardMaterial({ color: 0x17110e, roughness: 0.35, metalness: 0.55 }));
  caseMesh.position.y = -0.45; inner.add(caseMesh);
  const keys = [];
  LAYOUT.forEach((row, r) => {
    let x = -7.5;
    row.forEach(([label, w]) => {
      const cx = x + w / 2; const cz = (r - 2) * 1.0;
      const capMat = new THREE.MeshStandardMaterial({ color: 0x1d1d24, roughness: 0.5, metalness: 0.15 });
      const cap = new THREE.Mesh(new RoundedBoxGeometry(w - 0.12, 0.5, 0.86, 2, 0.1), capMat);
      const glowMat = new THREE.MeshBasicMaterial({ color: ORANGE, toneMapped: false });
      const glow = new THREE.Mesh(new THREE.BoxGeometry(w - 0.02, 0.06, 0.96), glowMat);
      glow.position.set(cx, 0.03, cz);
      cap.position.set(cx, 0.3, cz);
      inner.add(glow, cap);
      let leg = null;
      if (label) {
        leg = new THREE.Mesh(new THREE.PlaneGeometry(Math.min(w - 0.3, 0.7 * w), 0.6),
          new THREE.MeshBasicMaterial({ map: legend(label, w), transparent: true, toneMapped: false }));
        leg.rotation.x = -Math.PI / 2; leg.position.set(cx, 0.56, cz); inner.add(leg);
      }
      keys.push({ cap, glow, glowMat, capMat, leg, cx, cz, baseY: 0.3, hue: 0 });
      x += w;
    });
  });
  return { group: g, inner, keys, caseMesh };
}

// typing pattern shared by all keyboards (deterministic)
const presses = []; { let t = 0.2; while (t < TL.duration + 1) { presses.push({ k: Math.floor(rnd() * 61), t }); t += 0.07 + rnd() * 0.16; } }
function pressAmount(k, t, attack, release) {
  let a = 0;
  for (const p of presses) {
    if (p.k !== k) continue;
    const d = t - p.t;
    if (d < 0 || d > attack + release) continue;
    a = Math.max(a, d < attack ? d / attack : 1 - (d - attack) / release);
  }
  return a;
}

function styleKeyboard(kb, t, { mode = 'rgb', amp = 0.2, attack = 0.04, release = 0.12, wave = 0.5, axis = 'x' }) {
  kb.keys.forEach((k, i) => {
    const p = pressAmount(i, t, attack, release);
    k.cap.position.y = k.baseY - amp * p;
    if (k.leg) k.leg.position.y = 0.56 - amp * p;
    if (mode === 'rgb') {
      const pos = axis === 'x' ? k.cx * 0.07 : k.cz * 0.2;
      const hue = (pos + t * wave) % 1;
      k.glowMat.color.setHSL((hue + 1) % 1, 1, 0.5 + 0.2 * p);
      k.capMat.emissive.setHSL((hue + 1) % 1, 1, 0.5).multiplyScalar(0.05 + 0.5 * p);
    } else {
      k.glowMat.color.setHex(0x2a2a2e);
      k.capMat.emissive.setHex(0x000000);
      k.capMat.color.setHex(0x55555c);
    }
  });
}

const mech = buildKeyboard();
const soft = buildKeyboard();
scene.add(mech.group, soft.group);

// ---------- devices (scene 4) ----------
const devices = new THREE.Group();
{
  const screenMat = new THREE.MeshBasicMaterial({ map: screenTexture(), toneMapped: false });
  const mon = new THREE.Group();
  mon.add(new THREE.Mesh(new RoundedBoxGeometry(5.2, 3.1, 0.2, 2, 0.08), new THREE.MeshStandardMaterial({ color: 0x0e0a08, roughness: 0.4, metalness: 0.5 })));
  const s = new THREE.Mesh(new THREE.PlaneGeometry(4.9, 2.8), screenMat); s.position.z = 0.11; mon.add(s);
  const stand = new THREE.Mesh(new THREE.BoxGeometry(0.4, 1.4, 0.3), new THREE.MeshStandardMaterial({ color: 0x1b1b21 })); stand.position.y = -2.2; mon.add(stand);
  mon.position.set(-1.9, 3.4, -3.2);
  const lap = new THREE.Group();
  lap.add(new THREE.Mesh(new RoundedBoxGeometry(3.4, 0.14, 2.3, 2, 0.05), new THREE.MeshStandardMaterial({ color: 0xcfc5ba, roughness: 0.35, metalness: 0.7 })));
  const lid = new THREE.Mesh(new RoundedBoxGeometry(3.4, 2.2, 0.1, 2, 0.05), new THREE.MeshStandardMaterial({ color: 0xcfc5ba, roughness: 0.35, metalness: 0.7 }));
  lid.position.set(0, 1.15, -1.1); lid.rotation.x = -0.18; lap.add(lid);
  const ls = new THREE.Mesh(new THREE.PlaneGeometry(3.1, 2.0), new THREE.MeshBasicMaterial({ map: screenTexture(), toneMapped: false }));
  ls.position.set(0, 1.15, -1.04); ls.rotation.x = -0.18; lap.add(ls);
  lap.position.set(2.7, 0.1, -1.6);
  devices.add(mon, lap);
}
scene.add(devices);
const beamMat = new THREE.MeshBasicMaterial({ color: ORANGE, toneMapped: false });
const beams = [new THREE.Mesh(new THREE.SphereGeometry(0.16, 12, 12), beamMat), new THREE.Mesh(new THREE.SphereGeometry(0.16, 12, 12), beamMat)];
beams.forEach((b) => scene.add(b));

// ---------- UI (DOM overlay) ----------
const ui = document.getElementById('ui');
const flash = document.getElementById('flash');
const stage = document.getElementById('stage');
function el(cls, html, style = '') { const d = document.createElement('div'); d.className = cls; d.innerHTML = html; d.style.cssText = style; ui.appendChild(d); return d; }
const sceneById = Object.fromEntries(TL.scenes.map((s) => [s.id, s]));
const UI = {};
{
  const h = sceneById.hook?.data || {};
  UI.title = el('el big', (h.lines || []).map((l, i) => `<div class="${i ? 'orange' : ''}">${l}</div>`).join(''), 'top:7%');
  const c = sceneById.compare?.data || {};
  UI.cmpA = el('pill', c.left || 'MEMBRANA', 'left:6%;top:72%;');
  UI.cmpB = el('pill', c.right || 'MECÂNICO', 'right:6%;top:72%;');
  UI.pills = TL.cues.map((cue, i) => {
    const side = i % 2 === 0 ? 'left:5%' : 'right:5%';
    return el('pill', cue.text, `${side};top:${20 + i * 11}%`);
  });
  const d = sceneById.devices?.data || {};
  UI.devA = el('pill', d.left || 'WINDOWS', 'left:5%;top:24%');
  UI.devB = el('pill', d.right || 'MAC', 'right:5%;top:42%');
  const p = sceneById.proof?.data || {};
  UI.proof = el('card', `
    <div class="stat orange" style="font-size:7vmin;letter-spacing:.3vmin">★★★★★</div>
    <div class="stat" style="font-size:19vmin;line-height:1"><span id="v-rating">0,0</span></div>
    <div class="stat" style="font-size:5.6vmin"><span id="v-reviews">0</span> mil avaliações</div>
    <div class="stat orange" style="font-size:8.6vmin;margin-top:2vmin"><span id="v-sold">0</span> mil vendidos</div>`,
    'top:10%;text-align:center');
  const c2 = sceneById.cta?.data || {};
  UI.price = el('el big', `<div style="font-size:5vmin;opacity:.8"><s>${c2.old || ''}</s> <span class="orange">${c2.off || ''}</span></div><div class="orange" style="font-size:15vmin">${c2.price || ''}</div>`, 'top:7%');
  UI.cta = el('pill', c2.cta || 'COMENTA', 'left:10%;right:10%;text-align:center;font-size:6.4vmin;top:31%');
  UI.note = el('', c2.note || '', 'position:absolute;left:0;right:0;bottom:1.6vmin;text-align:center;font-size:2.1vmin;opacity:0;color:rgba(243,230,216,.75)');
}
const ALL_UI = [UI.title, UI.cmpA, UI.cmpB, ...UI.pills, UI.devA, UI.devB, UI.proof, UI.price, UI.cta, UI.note];
function pop(e, t, y0 = 3) { const a = clamp(t / 0.28); e.style.opacity = a; e.style.transform = `translateY(${(1 - easeBack(t / 0.35)) * y0}vmin) scale(${0.85 + 0.15 * easeBack(t / 0.35)})`; }

// ---------- scenes ----------
function setKb(kb, { x = 0, y = 0, z = 0, ry = 0, s = 1, visible = true }) {
  kb.group.visible = visible; kb.group.position.set(x, y, z); kb.group.rotation.set(0, ry, 0); kb.group.scale.setScalar(s);
}
function showWall(v) { wall.visible = v; }
const SCENES = {
  hook(lt, d) {
    showWall(true);
    setKb(mech, { ry: PORTRAIT ? Math.PI / 2 : 0 }); setKb(soft, { visible: false }); devices.visible = false; beams.forEach((b) => (b.visible = false));
    const k = easeOut(lt / d);
    if (PORTRAIT) { camera.position.set(lerp(1.2, 0.2, k), lerp(3.4, 2.2, k), lerp(11.5, 7.6, k)); camera.lookAt(0, 0.2, -2.4); }
    else { camera.position.set(lerp(-3, 0, k), lerp(5, 3.6, k), lerp(11, 8.8, k)); camera.lookAt(0, 0, 0); }
    styleKeyboard(mech, TIME, { mode: 'rgb', wave: 0.7, axis: PORTRAIT ? 'z' : 'x' });
    pop(UI.title, lt - 0.15);
  },
  compare(lt, d) {
    showWall(false);
    const r = PORTRAIT ? Math.PI / 2 : 0, sc = PORTRAIT ? 0.52 : 0.55;
    const gap = PORTRAIT ? 2.2 : 0;
    setKb(soft, { x: PORTRAIT ? -gap : 0, y: 0, z: PORTRAIT ? 0 : -2.4, ry: r, s: sc });
    setKb(mech, { x: PORTRAIT ? gap : 0, y: 0, z: PORTRAIT ? 0 : 2.4, ry: r, s: sc });
    devices.visible = false; beams.forEach((b) => (b.visible = false));
    const k = easeInOut(lt / d);
    if (PORTRAIT) { camera.position.set(lerp(-1, 1, k), 11.5, 7.2); camera.lookAt(0, 0, -0.6); }
    else { camera.position.set(lerp(-2, 2, k), 8.5, 9); camera.lookAt(0, 0, 0); }
    styleKeyboard(soft, TIME * 0.8, { mode: 'dim', amp: 0.08, attack: 0.14, release: 0.3 });
    styleKeyboard(mech, TIME, { mode: 'rgb', amp: 0.22, attack: 0.035, release: 0.1, wave: 0.9, axis: PORTRAIT ? 'z' : 'x' });
    pop(UI.cmpA, lt - 0.3); pop(UI.cmpB, lt - 0.6);
  },
  features(lt, d) {
    showWall(true);
    setKb(mech, { ry: PORTRAIT ? Math.PI / 2 : 0 }); setKb(soft, { visible: false }); devices.visible = false; beams.forEach((b) => (b.visible = false));
    const a = lerp(-0.7, 0.7, easeInOut(lt / d));
    if (PORTRAIT) { camera.position.set(Math.sin(a) * 8.5, lerp(5.2, 3.0, lt / d), Math.cos(a) * 9.5 + 1); camera.lookAt(0, 0.2, -1); }
    else { camera.position.set(Math.sin(a) * 11, 5.5, Math.cos(a) * 11); camera.lookAt(0, 0, 0); }
    styleKeyboard(mech, TIME, { mode: 'rgb', wave: 0.8, axis: PORTRAIT ? 'z' : 'x' });
    TL.cues.forEach((cue, i) => { if (cue.scene === 'features') pop(UI.pills[i], TIME - cue.t); });
  },
  devices(lt, d) {
    showWall(false);
    setKb(mech, { x: 0, y: 0, z: 2.6, s: PORTRAIT ? 0.56 : 0.7 }); setKb(soft, { visible: false });
    devices.visible = true; beams.forEach((b) => (b.visible = true));
    const k = easeOut(lt / d);
    camera.position.set(lerp(-1, 0.6, k), PORTRAIT ? 5.6 : 5.5, PORTRAIT ? 11.5 : 11); camera.lookAt(0, 1.7, -0.6);
    styleKeyboard(mech, TIME, { mode: 'rgb', wave: 0.8 });
    const p = (lt * 0.9) % 1;
    beams[0].position.set(lerp(0, -1.9, p), lerp(0.5, 3.0, p), lerp(2.6, -3.1, p));
    beams[1].position.set(lerp(0, 2.7, (p + 0.5) % 1), lerp(0.5, 1.2, (p + 0.5) % 1), lerp(2.6, -1.6, (p + 0.5) % 1));
    pop(UI.devA, lt - 0.2); pop(UI.devB, lt - 1.0);
  },
  proof(lt, d) {
    showWall(false);
    const r = PORTRAIT ? Math.PI / 2 + Math.sin(lt * 1.1) * 0.3 : Math.sin(lt * 1.1) * 0.3;
    setKb(mech, { x: 0, y: 0, z: 0, ry: r, s: PORTRAIT ? 0.5 : 0.8 }); setKb(soft, { visible: false });
    devices.visible = false; beams.forEach((b) => (b.visible = false));
    camera.position.set(0, 6.0, 11); camera.lookAt(0, PORTRAIT ? 3.4 : 0, 0);
    styleKeyboard(mech, TIME, { mode: 'rgb', wave: 0.6 });
    pop(UI.proof, lt - 0.1, 4);
    const p = easeOut((lt - 0.2) / 1.4), q = easeOut((lt - 1.2) / 1.2);
    const pd = sceneById.proof.data;
    document.getElementById('v-rating').textContent = (pd.rating * p).toFixed(1).replace('.', ',');
    document.getElementById('v-reviews').textContent = (pd.reviews * p).toFixed(1).replace('.', ',');
    document.getElementById('v-sold').textContent = (pd.sold * q).toFixed(1).replace('.', ',');
  },
  cta(lt, d) {
    showWall(false);
    setKb(mech, { x: 0, y: 0, z: 0, ry: PORTRAIT ? Math.PI / 2 + Math.sin(lt * 1.2) * 0.25 : Math.sin(lt * 1.2) * 0.25, s: PORTRAIT ? 0.62 : 0.85 }); setKb(soft, { visible: false });
    devices.visible = false; beams.forEach((b) => (b.visible = false));
    camera.position.set(0, 6.4, 10.5); camera.lookAt(0, PORTRAIT ? 3.2 : 0, 0);
    styleKeyboard(mech, TIME, { mode: 'rgb', wave: 1.0 });
    pop(UI.price, lt - 0.1);
    pop(UI.cta, lt - 0.7); const pulse = 1 + 0.045 * Math.sin(lt * 7); UI.cta.style.transform += ` scale(${pulse})`;
    UI.note.style.opacity = clamp((lt - 0.4) / 0.4);
  },
};

let TIME = 0;
function renderAt(t) {
  TIME = t;
  ALL_UI.forEach((e) => { e.style.opacity = 0; });
  const sc = TL.scenes.find((s) => t >= s.start && t < s.end) || TL.scenes[TL.scenes.length - 1];
  SCENES[sc.id](t - sc.start, sc.end - sc.start);
  // whip transition at every scene boundary
  let f = 0;
  for (const s of TL.scenes.slice(1)) f = Math.max(f, clamp(1 - Math.abs(t - s.start) / 0.14));
  flash.style.opacity = (f * 0.5).toFixed(3);
  canvas.style.filter = f > 0.02 ? `blur(${(f * 14).toFixed(1)}px)` : 'none';
  warm.intensity = 90 + 25 * Math.sin(t * 2.2);
  composer.render();
}
window.renderAt = renderAt;
window.ready = true;
