/* Minimal Filesystem adapter using Capacitor Filesystem plugin.
   saveFile(file) -> returns an object { path, url } where path is app storage path
   On web fallback returns { url: objectUrl }
*/

const FilesystemAdapter = (function(){
  function getPlugin(){
    const Cap = window.Capacitor || {};
    return (Cap.Plugins && Cap.Plugins.Filesystem) || window.Filesystem || null;
  }

  async function readFileAsBase64(file){
    return await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result.split(',')[1];
        resolve(result);
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  async function saveFile(file){
    const plugin = getPlugin();
    if(!plugin){
      // fallback: return object URL for preview, not persistent
      const url = URL.createObjectURL(file);
      return { url };
    }

    const base64 = await readFileAsBase64(file);
    const timestamp = Date.now();
    const safeName = file.name.replace(/[^a-z0-9_.-]/gi,'_');
    const path = `uploads/${timestamp}-${safeName}`;

    try{
      await plugin.writeFile({ path, data: base64, directory: 'DATA' });
      // Create a public URL for preview (Android): use Filesystem.readFile to get data and create object URL
      const read = await plugin.readFile({ path, directory: 'DATA' });
      const blob = b64toBlob(read.data, file.type);
      const url = URL.createObjectURL(blob);
      return { path, url };
    }catch(e){
      console.error('Filesystem write failed', e);
      const url = URL.createObjectURL(file);
      return { url };
    }
  }

  async function getFileUrl(path, contentType){
    const plugin = getPlugin();
    if(!plugin){
      // Not persistent, return as-is
      return null;
    }
    try{
      const read = await plugin.readFile({ path, directory: 'DATA' });
      const blob = b64toBlob(read.data, contentType || 'image/png');
      return URL.createObjectURL(blob);
    }catch(e){
      console.warn('readFile failed', e);
      return null;
    }
  }

  async function deleteFile(path){
    const plugin = getPlugin();
    if(!plugin){
      return false;
    }
    try{
      await plugin.deleteFile({ path, directory: 'DATA' });
      return true;
    }catch(e){
      console.warn('deleteFile failed', e);
      return false;
    }
  }

  function b64toBlob(b64Data, contentType='', sliceSize=512){
    const byteCharacters = atob(b64Data);
    const byteArrays = [];

    for (let offset = 0; offset < byteCharacters.length; offset += sliceSize) {
      const slice = byteCharacters.slice(offset, offset + sliceSize);
      const byteNumbers = new Array(slice.length);
      for (let i = 0; i < slice.length; i++) {
        byteNumbers[i] = slice.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      byteArrays.push(byteArray);
    }
    return new Blob(byteArrays, {type: contentType});
  }

  return { saveFile };
})();

window.FilesystemAdapter = FilesystemAdapter;

export default FilesystemAdapter;
