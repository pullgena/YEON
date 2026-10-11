const fs = require("fs");
const path = require("path");

const root = __dirname;
const partsDir = path.join(root, "game_parts");
const output = path.join(root, "game.html");

const parts = fs.readdirSync(partsDir)
  .filter(name => /^part-\d+\.txt$/.test(name))
  .sort();

if (!parts.length) {
  throw new Error("game_parts 안에 게임 소스 조각이 없습니다.");
}

const html = parts.map(name =>
  fs.readFileSync(path.join(partsDir, name), "utf8")
).join("");

fs.writeFileSync(output, html, "utf8");
console.log(`game.html assembled from ${parts.length} parts`);
