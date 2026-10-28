"""Package only the built MV3 extension, with a root manifest and no secrets."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]

def main():
    source=ROOT/'extension'/'dist'
    manifest=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    required=['popup.html','popup.js','session.html','session.js','style.css','privacy.html','help.html',*manifest['icons'].values()]
    for file in required:
        if not (source/file).is_file():raise RuntimeError('Missing release file: '+file)
    destination=ROOT/'release'/f"classroom-screen-sharing-{manifest['version']}.zip"
    destination.parent.mkdir(exist_ok=True)
    entries=[]
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(source.rglob('*')):
            if not file.is_file() or file.suffix=='.map':continue
            relative=file.relative_to(source).as_posix()
            if any(part.startswith('.') for part in file.relative_to(source).parts):continue
            if file.suffix not in ('.json','.html','.css','.js','.png','.svg'):continue
            archive.write(file,relative);entries.append(relative)
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None and 'manifest.json' in archive.namelist()
        assert not any('node_modules' in x or '.env' in x or x.endswith('.map') for x in archive.namelist())
    digest=hashlib.sha256(destination.read_bytes()).hexdigest()
    (destination.with_suffix('.zip.sha256')).write_text(digest+'  '+destination.name+'\n')
    report={'version':manifest['version'],'package':destination.name,'sha256':digest,'size_bytes':destination.stat().st_size,'files':entries}
    (ROOT/'release'/'package-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))

if __name__=='__main__':main()
