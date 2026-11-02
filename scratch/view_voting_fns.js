const fs = require('fs');

const html = fs.readFileSync('web/index.html', 'utf8');

function showContext(fnName) {
  const idx = html.indexOf(fnName);
  if (idx !== -1) {
    console.log(`\n=================== ${fnName} ===================`);
    console.log(html.slice(idx, idx + 1500));
  } else {
    console.log(`Không tìm thấy ${fnName}`);
  }
}

showContext('async function voteSpend(');
showContext('async function executeSpend(');
showContext('async function voteRefund(');
showContext('async function executeRefund(');
