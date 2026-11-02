const fs = require('fs');
const vm = require('vm');

const content = fs.readFileSync('web/index.html', 'utf8');

const scriptRegex = /<script\b[^>]*>([\s\S]*?)<\/script>/gi;
let match;
let count = 0;
let errors = 0;

while ((match = scriptRegex.exec(content)) !== null) {
  count++;
  const fullTag = match[0];
  const innerJs = match[1];
  const isExternal = /src=["']/.test(fullTag.split('>')[0]);

  if (isExternal) {
    const srcMatch = fullTag.match(/src=["'](.*?)["']/);
    console.log(`[Script #${count}] External: ${srcMatch ? srcMatch[1] : 'unknown'}`);
  } else if (innerJs.trim().length > 0) {
    try {
      new vm.Script(innerJs, { filename: `inline_script_${count}.js` });
      console.log(`[Script #${count}] Inline JS valid! (Lines: ${innerJs.split('\n').length}, Length: ${innerJs.length} bytes)`);
    } catch (e) {
      console.error(`[Script #${count}] Syntax Error:`, e.message);
      errors++;
    }
  }
}

if (errors === 0) {
  console.log(`\nALL ${count} SCRIPTS PASSED SYNTAX VALIDATION!`);
} else {
  console.error(`\nFAILED: ${errors} syntax errors found.`);
  process.exit(1);
}
