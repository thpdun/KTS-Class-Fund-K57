const fs = require('fs');

const html = fs.readFileSync('web/index.html', 'utf8');

function findSnippet(keyword) {
  let pos = 0;
  while ((pos = html.indexOf(keyword, pos)) !== -1) {
    console.log(`\n=== Keyword: ${keyword} at pos ${pos} ===`);
    console.log(html.slice(pos - 100, pos + 800));
    pos += keyword.length;
  }
}

findSnippet('executeSpend(');
findSnippet('executeRefund(');
