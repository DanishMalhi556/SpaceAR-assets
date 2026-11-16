import fs from 'node:fs';
import path from 'node:path';
import validator from 'gltf-validator';
const dir = process.argv[2];
let bad = 0;
for (const f of fs.readdirSync(dir).filter((f) => f.endsWith('.glb')).sort()) {
  const r = await validator.validateBytes(new Uint8Array(fs.readFileSync(path.join(dir, f))), { maxIssues: 50 });
  const { numErrors, numWarnings } = r.issues;
  if (numErrors || numWarnings) {
    console.log(`${f}: ${numErrors} errors, ${numWarnings} warnings`);
    for (const m of r.issues.messages.filter((m) => m.severity <= 1).slice(0, 3)) console.log(`   ${m.severity === 0 ? 'E' : 'W'} ${m.code}: ${m.message}`);
  }
  if (numErrors) bad++;
}
console.log(`${fs.readdirSync(dir).filter((f) => f.endsWith('.glb')).length} files, ${bad} with errors`);
