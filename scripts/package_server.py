"""Prepare a source-only server distribution; never include credentials/data."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
VERSION=json.loads((ROOT/'extension'/'manifest.json').read_text())['version']
DESTINATION=ROOT/'release'/f'classroom-server-source-{VERSION}.zip'
DIRECTORIES=('backend','web','extension','deploy','docs','scripts','tests')
ROOT_FILES=('README.md','VERIFICATION.md','package.json','package-lock.json','compose.yaml','playwright.config.ts','.env.example','.gitignore','.dockerignore')
SKIP={'node_modules','dist','__pycache__','.pytest_cache','.npm-cache'}
SUFFIXES={'.py','.ts','.tsx','.mjs','.ps1','.json','.css','.html','.md','.txt','.yaml','.svg','.png'}

def main():
    files=[ROOT/name for name in ROOT_FILES]
    for name in DIRECTORIES:
        for file in (ROOT/name).rglob('*'):
            if not file.is_file() or any(part in SKIP for part in file.relative_to(ROOT).parts):continue
            if file.suffix in SUFFIXES or file.name.startswith('Dockerfile'):files.append(file)
    with zipfile.ZipFile(DESTINATION,'w',zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(set(files)):archive.write(file,file.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(DESTINATION) as archive:
        assert archive.testzip() is None
        assert not any(Path(name).name=='.env' or '/data/' in name or '__pycache__' in name or 'node_modules' in name for name in archive.namelist())
    digest=hashlib.sha256(DESTINATION.read_bytes()).hexdigest()
    DESTINATION.with_suffix('.zip.sha256').write_text(digest+'  '+DESTINATION.name+'\n')
    print(json.dumps({'source_package':DESTINATION.name,'size_bytes':DESTINATION.stat().st_size,'sha256':digest,'files':len(files)},indent=2))

if __name__=='__main__':main()
