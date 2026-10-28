import {build} from 'esbuild';
import {mkdir, copyFile, cp} from 'node:fs/promises';
await mkdir('dist', {recursive:true});
await build({entryPoints:['src/popup.ts','src/session.ts'],bundle:true,outdir:'dist',format:'esm',target:'chrome116',sourcemap:true});
for (const file of ['manifest.json','popup.html','session.html','style.css']) await copyFile(file, `dist/${file}`);
await cp('icons','dist/icons',{recursive:true});
for (const file of ['privacy.html','help.html']) await copyFile('../web/public/'+file,'dist/'+file);
