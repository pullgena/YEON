'use strict';

/** Restrict controller connections to the manually started LAN host on port 8765. */
function isLanIPv4(host) {
  const groups = host.split('.');
  if (groups.length !== 4 || groups.some(v => !/^\d{1,3}$/.test(v) || Number(v) > 255)) return false;
  const [a, b] = groups.map(Number);
  return a === 10 || a === 127 || (a === 192 && b === 168) ||
    (a === 172 && b >= 16 && b <= 31) || (a === 169 && b === 254);
}

function parseTarget(input) {
  if (typeof input !== 'string' || input.length > 200) throw new Error('올바른 PC 주소를 입력해 주세요.');
  const trimmed = input.trim();
  if (!trimmed) throw new Error('관리받는 PC의 주소를 입력해 주세요.');
  const candidate = /^[a-zA-Z][a-zA-Z\d+.-]*:\/\//.test(trimmed) ? trimmed : `http://${trimmed}`;
  let url;
  try { url = new URL(candidate); }
  catch { throw new Error('주소 형식이 잘못되었습니다. 예: 192.168.0.10:8765'); }

  if (url.protocol !== 'http:' || url.username || url.password || url.port !== '8765' ||
      (url.pathname !== '/' && url.pathname !== '') || url.search || url.hash) {
    throw new Error('HTTP 주소와 포트 8765만 사용할 수 있습니다.');
  }
  if (!isLanIPv4(url.hostname) && url.hostname !== 'localhost') {
    throw new Error('같은 네트워크의 사설 IP 주소만 연결할 수 있습니다.');
  }
  return url.origin + '/';
}

module.exports = {isLanIPv4, parseTarget};
