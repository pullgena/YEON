const base = require('./package.json').build;
module.exports = {
 ...base,
 appId:'com.yeon.server-terminal',
 productName:'YEON Server Terminal',
 extraMetadata:{main:'server-terminal.js'},
 files:['server-terminal.js','server-preload.js','server.js','index.html','package.json'],
 directories:{output:'dist-server'},
 win:{target:[{target:'portable',arch:['x64']}]}
};
