const fs = require('fs');
const html = fs.readFileSync('frontend/dist/index.html', 'utf-8');
const scriptMatch = html.match(/<script type="text\/babel">([\s\S]*?)<\/script>/);
if (!scriptMatch) {
  console.error('No babel script found!');
  process.exit(1);
}
console.log('Script length:', scriptMatch[1].length, 'chars');

// Check bracket balance
let openBraces = 0;
let openParens = 0;
const code = scriptMatch[1];
for (let i = 0; i < code.length; i++) {
  if (code[i] === '{') openBraces++;
  else if (code[i] === '}') openBraces--;
  else if (code[i] === '(') openParens++;
  else if (code[i] === ')') openParens--;
}
console.log('Open braces balance:', openBraces);
console.log('Open parens balance:', openParens);
if (openBraces === 0 && openParens === 0) {
  console.log('✓ All braces and parens are perfectly balanced!');
} else {
  console.error('Bracket imbalance detected!');
}
