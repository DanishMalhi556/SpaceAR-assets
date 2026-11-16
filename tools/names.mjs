// Flags brand/designer names hidden in node, mesh, material and texture names.
import fs from 'node:fs';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
const brand = /ikea|nordli|malm|hemnes|kallax|pax|billy|ektorp|poang|eames|barcelona|wassily|noguchi|jacobsen|saarinen|herman ?miller|vitra|knoll|west ?elm|poltrona|cassina|ligne ?roset|kartell|muuto|flos|artemide|poulsen|panton|bertoia|corbusier|wayfair|ashley|restoration|crate|pottery ?barn|maison ?gatti|mantra|lightstar|bertosalotti|soho|chelsea/i;
for (const f of process.argv.slice(2)) {
  const root = (await io.read(f)).getRoot();
  const names = [...root.listNodes(), ...root.listMeshes(), ...root.listMaterials(), ...root.listTextures()]
    .map((p) => p.getName()).concat(root.listTextures().map((t) => t.getURI())).filter(Boolean);
  const hits = [...new Set(names.filter((n) => brand.test(n)))];
  if (hits.length) console.log(`${f.split('/').pop()}: ${hits.slice(0, 5).join(' | ')}`);
}
console.log('scan done');
