const fs = require('fs');
const path = require('path');

const jsDir = path.join(__dirname, '..', 'js');
const files = fs.readdirSync(jsDir).filter(f => f.endsWith('.js'));
const exportsMap = {};

for (const f of files) {
  const code = fs.readFileSync(path.join(jsDir, f), 'utf8');
  const expMatches = [...code.matchAll(/export\s+(?:async\s+)?(?:function|const|let|var|class)\s+([a-zA-Z0-9_$]+)/g)].map(m => m[1]);
  exportsMap[f] = new Set(expMatches);
}

let hasErrors = false;
for (const f of files) {
  const code = fs.readFileSync(path.join(jsDir, f), 'utf8');
  const impMatches = [...code.matchAll(/import\s*\{([^}]+)\}\s*from\s*['"]\.\/([^'"]+)['"]/g)];
  for (const m of impMatches) {
    const importedNames = m[1].split(',').map(s => s.trim()).filter(Boolean);
    let targetFile = m[2];
    if (!targetFile.endsWith('.js')) targetFile += '.js';
    const available = exportsMap[targetFile];
    if (!available) {
      console.error(`ERROR: ${f} imports from non-existent ${targetFile}`);
      hasErrors = true;
      continue;
    }
    for (const name of importedNames) {
      const realName = name.split(/\s+as\s+/)[0].trim();
      if (!available.has(realName)) {
        console.error(`MISSING EXPORT: "${realName}" is imported in ${f} from ./${targetFile}, but ${targetFile} does NOT export it!`);
        hasErrors = true;
      }
    }
  }
}

if (!hasErrors) {
  console.log("SUCCESS: ALL ES MODULE CONTRACTS ARE VALID!");
} else {
  process.exit(1);
}
