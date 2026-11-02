const fs = require('fs');
const content = fs.readFileSync('web/index.html', 'utf8');

const scriptRegex = /<script\b[^>]*>([\s\S]*?)<\/script>/gi;
scriptRegex.exec(content); // #1
const match2 = scriptRegex.exec(content); // #2

if (match2) {
  const code = match2[1];
  // Write to a standalone js file and run node --check
  fs.writeFileSync('scratch/extracted_script_2.js', code, 'utf8');
  console.log('Wrote scratch/extracted_script_2.js, size:', code.length);
}
