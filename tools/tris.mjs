// Triangle count per GLB (SRS 8.3: max 50,000 per model).
import fs from 'node:fs';
import path from 'node:path';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
const dir = process.argv[2]; const rows = [];
for (const f of fs.readdirSync(dir).filter((f) => f.endsWith('.glb'))) {
  const root = (await io.read(path.join(dir, f))).getRoot();
  let tris = 0; const variants = !!root.listExtensionsUsed().find((e) => e.extensionName === 'KHR_materials_variants');
  // Count per mesh instance (nodes), since a mesh used twice is drawn twice.
  for (const node of root.listNodes()) {
    const mesh = node.getMesh(); if (!mesh) continue;
    for (const p of mesh.listPrimitives()) {
      if (p.getMode() !== 4) continue;
      const idx = p.getIndices(); tris += (idx ? idx.getCount() : p.getAttribute('POSITION').getCount()) / 3;
    }
  }
  rows.push([f.replace('.glb', ''), Math.round(tris), variants]);
}
rows.sort((a, b) => b[1] - a[1]);
const over = rows.filter((r) => r[1] > 50000);
console.log(`${rows.length} models, ${over.length} over 50,000 triangles:`);
for (const r of over) console.log(`  ${r[0].padEnd(28)} ${r[1].toLocaleString()}`);
console.log('with colour variants (KHR_materials_variants):', rows.filter((r) => r[2]).map((r) => r[0]).join(', ') || 'none');
