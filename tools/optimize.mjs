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
import { center, dedup, prune, textureCompress, getBounds } from '@gltf-transform/functions';
import sharp from 'sharp';

const [work, assets] = process.argv.slice(2);
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
const only = process.argv[4] ? new Set(process.argv[4].split(',')) : null;
const reportPath = path.join(work, 'models_report.json');
const report = only && fs.existsSync(reportPath) ? JSON.parse(fs.readFileSync(reportPath, 'utf8')) : {};
// Per-model corrections found by checking sizes against the source's published dimensions.
const Y90 = [0, Math.SQRT1_2, 0, Math.SQRT1_2]; // quarter turn about the vertical axis
const FIX = {
  'wardrobe-shelf-steel': { scale: 0.1 }, // source file is 10x too large
  'table-stone-oak': { rotation: Y90 }, // long side along the depth; make it the width
  'wardrobe-cube-shelf': { rotation: Y90 },
};

for (const id of fs.readdirSync(path.join(work, 'raw')).sort()) {
  if (only && !only.has(id)) continue;
  const dir = path.join(work, 'raw', id, 'model');
  const src = fs.readdirSync(dir).find((f) => /\.(gltf|glb)$/i.test(f));
  const doc = await io.read(path.join(dir, src));
  const fix = FIX[id];
  if (fix) {
    for (const scene of doc.getRoot().listScenes()) {
      const wrap = doc.createNode(`${id}-fix`);
      if (fix.scale) wrap.setScale([fix.scale, fix.scale, fix.scale]);
      if (fix.rotation) wrap.setRotation(fix.rotation);
      for (const child of scene.listChildren()) {
        scene.removeChild(child);
        wrap.addChild(child);
      }
      scene.addChild(wrap);
    }
  }
  await doc.transform(
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
