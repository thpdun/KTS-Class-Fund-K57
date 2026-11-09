const fs = require('fs');
const html = fs.readFileSync('web/index.html', 'utf8');

// Extract all scripts between <script> and </script>
const regex = /<script\b[^>]*>([\s\S]*?)<\/script>/gi;
let match;
let i = 0;
while ((match = regex.exec(html)) !== null) {
  i++;
  const jsCode = match[1];
  if (!jsCode.trim()) continue;
  try {
    new Function(jsCode);
    console.log(`Script block #${i}: Syntax OK`);
  } catch (err) {
    console.error(`Script block #${i} Error:`, err.message);
  }
}

