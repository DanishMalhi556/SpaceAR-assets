// Lists each mesh node's size (world space) to spot floor planes, cables or extra objects.
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { getBounds } from '@gltf-transform/functions';
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
for (const f of process.argv.slice(2)) {
  const doc = await io.read(f);
  const scene = doc.getRoot().listScenes()[0];
  const all = getBounds(scene);
  console.log(`== ${f.split('/').pop()}  total ${all.max.map((v, i) => +(v - all.min[i]).toFixed(2)).join(' x ')}`);
  const rows = [];
  scene.traverse((n) => {
    if (!n.getMesh()) return;
    const b = getBounds(n);
    const s = b.max.map((v, i) => v - b.min[i]);
    rows.push([n.getName() || n.getMesh().getName() || '(unnamed)', s, b.min, b.max]);
  });
  rows.sort((a, b) => Math.max(...b[1]) - Math.max(...a[1]));
  for (const [name, s, mn, mx] of rows.slice(0, 8))
    console.log(`   ${name.slice(0, 36).padEnd(36)} size ${s.map((v) => v.toFixed(2)).join(' x ')}   y ${mn[1].toFixed(2)}..${mx[1].toFixed(2)}`);
  if (rows.length > 8) console.log(`   ... ${rows.length} mesh nodes`);
}
