#!/usr/bin/env python3
"""TJM Store extras: builds the `catalog` release the TJM Store reads (docs/PUBLISHING.md of the Store, "Releases").

  python3 tools/build_catalog.py --repo <owner>/tjm-extras --out out [--cache <folder>] [--only <id> ...]

For each entry of mirror.json: downloads the upstream artifact (or takes it from --cache), checks its sha256 against
the pinned one, and for an app with a "tjm" section rewrites its tile name (every language) and its icon. Writes
out/<artifact>, out/icon-<id>.png where the upstream entry lists an icon, and out/catalog.json with each artifact's
new size, sha256 and its URL in this repo's `catalog` release. Python 3 standard library only."""
import argparse, copy, gzip, hashlib, io, json, os, shutil, sys, tarfile, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MTIME = 1762732800  # 2025-11-10: one time for every member, so a package is the same bytes on every run


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def fetch(url, name, want, cache, work):
    if cache and os.path.isfile(os.path.join(cache, name)):
        data = open(os.path.join(cache, name), 'rb').read()
    else:
        dst = os.path.join(work, name)
        if not os.path.isfile(dst):
            print(f'  downloading {url}')
            req = urllib.request.Request(url, headers={'User-Agent': 'tjm-extras'})
            with urllib.request.urlopen(req, timeout=600) as r, open(dst + '.part', 'wb') as f:
                shutil.copyfileobj(r, f, 1 << 20)
            os.replace(dst + '.part', dst)
        data = open(dst, 'rb').read()
    got = sha256(data)
    if got != want:
        sys.exit(f'{name}: sha256 {got}, mirror.json pins {want}: not the pinned upstream file')
    return data


def rebrand(tgz, title, icon_png):
    """The app package with its entry point's text = title in every language and its icon = icon_png."""
    src = tarfile.open(fileobj=io.BytesIO(tgz), mode='r:gz')
    members = [m for m in src.getmembers() if not os.path.basename(m.name).startswith('._')]
    names = {m.name: m for m in members}
    app_json = next(n for n in names if n.endswith('rhmiData/application.json'))
    prefix = app_json[:-len('rhmiData/application.json')]
    app = json.loads(src.extractfile(names[app_json]).read().decode('utf-8'))['application']
    ep = app['entryPoints'][0]
    text_id, icon_name = ep['textId'], ep['icon']
    texts, icons = 0, 0
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode='wb', mtime=0) as gz, tarfile.open(fileobj=gz, mode='w', format=tarfile.USTAR_FORMAT) as dst:
        for m in sorted(members, key=lambda m: m.name):
            ti = tarfile.TarInfo(m.name)
            ti.mtime, ti.uid, ti.gid, ti.uname, ti.gname = MTIME, 0, 0, 'root', 'root'
            if m.isdir():
                ti.type, ti.mode = tarfile.DIRTYPE, 0o755
                dst.addfile(ti)
                continue
            if not m.isfile():
                continue
            data = src.extractfile(m).read()
            rel = m.name[len(prefix):]
            if rel.startswith('rhmiData/variantGroups/') and '/texts/' in rel and rel.endswith('.json'):
                t = json.loads(data.decode('utf-8'))
                if text_id in t:
                    t[text_id] = title
                    data = (json.dumps(t, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
                    texts += 1
            elif rel.startswith('rhmiData/') and os.path.basename(rel) == icon_name:
                data = icon_png
                icons += 1
            ti.size, ti.mode = len(data), m.mode or 0o644
            dst.addfile(ti, io.BytesIO(data))
    if not texts or not icons:
        sys.exit(f'{title}: {texts} text files and {icons} icons changed in the package; expected both')
    print(f'  {title}: tile text in {texts} languages, icon {icon_name}')
    return out.getvalue()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo', default=os.environ.get('GITHUB_REPOSITORY'), help='<owner>/<repo> the catalog release is in')
    ap.add_argument('--out', default=os.path.join(ROOT, 'out'))
    ap.add_argument('--cache', help='a folder with upstream artifacts already downloaded')
    ap.add_argument('--only', nargs='*', help='only these component ids (a local check)')
    a = ap.parse_args()
    if not a.repo:
        sys.exit('--repo <owner>/<repo> (or GITHUB_REPOSITORY) is needed for the artifacts\' URLs')
    base = f'https://github.com/{a.repo}/releases/download/catalog/'
    mirror = json.load(open(os.path.join(ROOT, 'mirror.json'), encoding='utf-8'))
    os.makedirs(a.out, exist_ok=True)
    work = os.path.join(a.out, '..', '.upstream') if not a.cache else a.cache
    os.makedirs(work, exist_ok=True)
    catalog = []
    for item in mirror['components']:
        up = item['upstream']
        if a.only and up['id'] not in a.only:
            continue
        e = copy.deepcopy(up)
        name = up['artifact']['name']
        print(f"{up['id']}@{up['version']}")
        data = fetch(up['artifact']['url'], name, up['artifact']['sha256'], a.cache, work)
        tjm = item.get('tjm')
        if tjm:
            icon = open(os.path.join(ROOT, tjm['icon']), 'rb').read()
            data = rebrand(data, tjm['title'], icon)
            e['title'] = tjm['title']
            e['author'] = f"TJM (based on {item['source']})"
            if 'icon' in e:
                icon_name = f"icon-{up['id']}.png"
                open(os.path.join(a.out, icon_name), 'wb').write(icon)
                e['icon'], e['iconSha256'] = base + icon_name, sha256(icon)
        open(os.path.join(a.out, name), 'wb').write(data)
        e['artifact'] = {'name': name, 'size': len(data), 'sha256': sha256(data), 'url': base + urllib.parse.quote(name)}
        catalog.append(e)
    with open(os.path.join(a.out, 'catalog.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'schema': 2, 'components': catalog}, f, indent=2, ensure_ascii=False)
        f.write('\n')
    print(f'catalog.json: {len(catalog)} components -> {a.out}')


if __name__ == '__main__':
    main()
