// Renders product shots of GLB models with a transparent background.
//   node render.mjs <models dir> <out dir> <id,id,...> [browser exe]
// Uses headless Chrome/Edge + three.js: studio environment lighting, a 3/4
// front view framed to the model's bounds, 1000 x 1000 PNG with alpha.
// Per-model view tweaks: YAW below (degrees, if a model faces another way).
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer-core';

const here = path.dirname(fileURLToPath(import.meta.url));
const [modelsDir, outDir, idList, exe = 'C:/Program Files/Google/Chrome/Application/chrome.exe'] = process.argv.slice(2);
const ids = idList.split(',');
const YAW = JSON.parse(process.env.RENDER_YAW || '{}'); // e.g. {"wardrobe-oak": 180}
fs.mkdirSync(outDir, { recursive: true });

const page = `<!doctype html><html><head><style>html,body{margin:0;background:transparent}</style>
<script type="importmap">{"imports":{"three":"/three/build/three.module.js","three/addons/":"/three/examples/jsm/"}}</script>
</head><body><script type="module">
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
const S = 1000;
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
renderer.setSize(S, S); renderer.setPixelRatio(1);
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.0;
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), 0.04).texture;
const key = new THREE.DirectionalLight(0xffffff, 1.2); key.position.set(3, 5, 4); scene.add(key);
window.renderModel = async (url, yawDeg) => {
  const gltf = await new GLTFLoader().loadAsync(url);
  const obj = gltf.scene; obj.rotation.y = THREE.MathUtils.degToRad(yawDeg); scene.add(obj);
  const box = new THREE.Box3().setFromObject(obj);
  const size = box.getSize(new THREE.Vector3()), center = box.getCenter(new THREE.Vector3());
  const camera = new THREE.PerspectiveCamera(30, 1, 0.01, 1000);
  const dir = new THREE.Vector3(0.75, 0.45, 1).normalize(); // 3/4 view from the front-right, slightly above
  const radius = size.length() / 2;
  camera.position.copy(center).addScaledVector(dir, radius / Math.sin(THREE.MathUtils.degToRad(15)) * 1.02);
  camera.lookAt(center);
  renderer.render(scene, camera);
  const png = renderer.domElement.toDataURL('image/png');
  scene.remove(obj);
  return png;
};
window.ready = true;
</script></body></html>`;

const mime = { '.js': 'text/javascript', '.glb': 'model/gltf-binary', '.html': 'text/html' };
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0]);
  let file;
  if (u === '/') { res.writeHead(200, { 'Content-Type': 'text/html' }); return res.end(page); }
  if (u.startsWith('/three/')) file = path.join(here, 'node_modules', u.slice(1));
  else if (u.startsWith('/models/')) file = path.join(modelsDir, path.basename(u));
  if (!file || !fs.existsSync(file)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': mime[path.extname(file)] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
}).listen(0, '127.0.0.1');
await new Promise((r) => server.once('listening', r));
const base = `http://127.0.0.1:${server.address().port}`;

const browser = await puppeteer.launch({
  executablePath: exe, headless: true,
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
});
try {
  const tab = await browser.newPage();
  tab.on('pageerror', (e) => console.error('page error:', e.message));
  await tab.setViewport({ width: 1000, height: 1000 });
  await tab.goto(base, { waitUntil: 'load' });
  await tab.waitForFunction('window.ready === true', { timeout: 60000 });
  const sides = process.env.RENDER_SIDES ? [0, 90, 180, 270] : [null]; // RENDER_SIDES=1: one image per side
  for (const id of ids) {
    for (const side of sides) {
      const yaw = side ?? YAW[id] ?? 0;
      const data = await tab.evaluate((u, y) => window.renderModel(u, y), `${base}/models/${id}.glb`, yaw);
      const name = side === null ? id : `${id}_${side}`;
      fs.writeFileSync(path.join(outDir, `${name}.png`), Buffer.from(data.split(',')[1], 'base64'));
    }
    console.log('rendered', id);
  }
} finally {
  await browser.close();
  server.close();
}
