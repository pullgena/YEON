'use strict';
const {parseTarget} = require('./target');
const MAX_COMPUTERS = 20;

function cleanName(name, fallback) {
  if (typeof name !== 'string') return fallback;
  const value = name.replace(/[\u0000-\u001f\u007f]/g, '').trim().slice(0, 64);
  return value || fallback;
}
function cleanList(input) {
  if (!Array.isArray(input)) return [];
  const seen = new Set();
  const result = [];
  for (const row of input) {
    if (!row || typeof row.address !== 'string') continue;
    let address;
    try {address = parseTarget(row.address);} catch {continue;}
    if (seen.has(address)) continue;
    seen.add(address);
    result.push({address, name:cleanName(row.name, new URL(address).host)});
    if (result.length === MAX_COMPUTERS) break;
  }
  return result;
}
function remember(list, address, name) {
  const safe = parseTarget(address);
  const old = cleanList(list).find(item => item.address === safe);
  const fallback = old?.name || new URL(safe).host;
  const row = {address:safe, name:cleanName(name, fallback)};
  return cleanList([row, ...cleanList(list).filter(item => item.address !== safe)]);
}
function forget(list, address) {
  const safe = parseTarget(address);
  return cleanList(list).filter(item => item.address !== safe);
}
module.exports = {cleanList, cleanName, remember, forget};
