const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  appVersion: require('../package.json').version
});
