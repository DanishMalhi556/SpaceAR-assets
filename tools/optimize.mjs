// Optimises raw models into AR-ready GLBs.
//   node optimize.mjs <work dir> <assets repo>
// For each <work>/raw/<id>/model/*.gltf|glb: pivot at the bottom centre (sits
// on the floor in AR), dedupe/prune, textures capped at 1024 px in their
// original format (JPEG/PNG, so no decoder extensions are needed), then
// written to <assets>/models/<id>.glb. Prints size and real dimensions.
import fs from 'node:fs';
import path from 'node:path';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { center, dedup, metalRough, prune, textureCompress, getBounds } from '@gltf-transform/functions';
import sharp from 'sharp';

const [work, assets] = process.argv.slice(2);
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
const only = process.argv[4] ? new Set(process.argv[4].split(',')) : null;
const reportPath = path.join(work, 'models_report.json');
const report = only && fs.existsSync(reportPath) ? JSON.parse(fs.readFileSync(reportPath, 'utf8')) : {};
// Per-model corrections found by checking sizes against the source's published dimensions.
// yaw: degrees about the vertical axis, so the front faces +Z (towards the viewer in AR).
const FIX = {
  'wardrobe-shelf-steel': { scale: 0.1 }, // source file is 10x too large
  'table-stone-oak': { yaw: 90 }, // long side along the depth; make it the width
  'wardrobe-cube-shelf': { yaw: 90 },
  // Sketchfab (v2): authors' units vary. Scales come from a reference part
  // (seat height, leg height, shade size, mattress size), not a guess.
  'bed-platform-dark': { scale: 0.001 }, // millimetres
  'bed-upholstered': { scale: 0.01 }, // centimetres
  'light-floor-black': { scale: 0.01 },
  'table-night-modern': { scale: 0.01 },
  'wardrobe-two-door': { scale: 0.01 },
  'sofa-mc-teal': { scale: 0.65 }, // the three Mozilla Hubs models are 1.5x too large
  'chair-mc-teal': { scale: 0.65 },
  'wardrobe-dresser-light': { scale: 0.65 },
  'wardrobe-dresser-mc': { scale: 0.375, yaw: 270 }, // legs are 21% of the height, as on the real piece
  'light-floor-drum': { scale: 0.2 }, // 155 cm tall, 55 cm shade
  'chair-arm-cushion': { scale: 0.75, yaw: 90 }, // seat height 44-52 cm
  'chair-accent-black': { scale: 0.21, yaw: 90 }, // 78 cm tall
  'sofa-wicker': { yaw: 270 }, // fronts checked from renders of all four sides
  'wardrobe-oak': { yaw: 270 },
  'bed-charcoal': { scale: 0.01, drop: ['Pillow_2.002_1_0', 'Plane.002_2_0'] }, // loose pillow and throw on the floor
  'bed-pine-single': { scale: 0.05 }, // 98 x 195 cm single
};

for (const id of fs.readdirSync(path.join(work, 'raw')).sort()) {
  if (only && !only.has(id)) continue;
  const dir = path.join(work, 'raw', id, 'model');
  const src = fs.readdirSync(dir).find((f) => /\.(gltf|glb)$/i.test(f));
  const doc = await io.read(path.join(dir, src));
  const fix = FIX[id];
  if (fix?.drop) {
    for (const n of doc.getRoot().listNodes()) {
      if (fix.drop.includes(n.getName()) || fix.drop.includes(n.getMesh()?.getName())) n.dispose();
    }
  }
  if (fix) {
    for (const scene of doc.getRoot().listScenes()) {
      const wrap = doc.createNode(`${id}-fix`);
      if (fix.scale) wrap.setScale([fix.scale, fix.scale, fix.scale]);
      if (fix.yaw) {
        const r = (fix.yaw * Math.PI) / 360; // half-angle
        wrap.setRotation([0, Math.sin(r), 0, Math.cos(r)]);
      }
      for (const child of scene.listChildren()) {
        scene.removeChild(child);
        wrap.addChild(child);
      }
      scene.addChild(wrap);
    }
  }
  await doc.transform(
    metalRough(), // old specular-glossiness materials -> metal-rough (otherwise they render white)
    center({ pivot: 'below' }),
    dedup(),
    prune({ keepAttributes: true }), // keep UV sets that texture transforms refer to
    textureCompress({ encoder: sharp, resize: [1024, 1024], quality: 85 }),
  );
  const scene = doc.getRoot().getDefaultScene() ?? doc.getRoot().listScenes()[0];
  const { min, max } = getBounds(scene);
  const dims = max.map((v, i) => +(v - min[i]).toFixed(3)); // metres: x, y(up), z
  const out = path.join(assets, 'models', `${id}.glb`);
  await io.write(out, doc);
  const size = fs.statSync(out).size;
  report[id] = { bytes: size, w_m: dims[0], h_m: dims[1], d_m: dims[2] };
  console.log(`${id.padEnd(28)} ${(size / 1e6).toFixed(2).padStart(6)} MB  ${dims.map((v) => Math.round(v * 100)).join(' x ')} cm (W x H x D)`);
}
fs.writeFileSync(path.join(work, 'models_report.json'), JSON.stringify(report, null, 1));
