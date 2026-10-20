#!/usr/bin/env python3
# 5万分の1地質図幅の一覧（g50index.json）を作る
#   産総研 地質調査総合センター（GSJ）の公開データ（GSJ LD）から、図幅ごとの
#   番号・題名・図幅番号・タイルの名前・範囲を集める。アプリはこのファイルを
#   同じ場所から読むので、産総研のサーバーの制限（CORS）を受けない。
# 使い方: python scripts/make_g50index.py g50index.json
# 出典: 産業技術総合研究所 地質調査総合センター（政府標準利用規約 第2.0版）
import json, os, re, sys, time, urllib.request, urllib.error, datetime
from concurrent.futures import ThreadPoolExecutor

BASE = os.environ.get('G50_BASE', 'https://gbank.gsj.jp/ld/resource/publication/map')
UA = 'g50index/1.0 (+GitHub Actions)'
OUT = sys.argv[1] if len(sys.argv) > 1 else 'g50index.json'

def get_json(url, tries=4):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            err = e
        except Exception as e:
            err = e
        time.sleep(2 * (k + 1))
    print('  読めませんでした:', url, err, file=sys.stderr)
    return None

def num(v):
    try:
        return round(float(v), 6)
    except Exception:
        return None

def sheet_no(tms):
    m = re.match(r'G50_(\d{2})_(\d{3})', tms or '')
    return f'{m.group(1)}-{m.group(2)}' if m else ''

def one(part):
    mid = re.search(r'map(\d+)$', part.get('@id', ''))
    if not mid:
        return []
    mid = mid.group(1)
    roma = re.sub(r'^1:50K GeoMap:\s*', '', part.get('label', '')).strip()
    roma = re.sub(r'\s*\(\d{4}\)\s*$', '', roma)
    j = get_json(f'{BASE}/g050/map{mid}.json')
    time.sleep(0.2)   # 産総研のサーバーに負担をかけないよう間を空ける
    if not j:
        return []
    out = []
    pages = j.get('page') or []
    for i, pg in enumerate(pages):
        tms = pg.get('tms_dir') or ''
        if not tms:
            continue
        b = pg.get('bbox') or []
        b = [num(x) for x in b] if len(b) == 4 else None
        if b and None in b:
            b = None
        e = {'id': mid, 't': j.get('title_j') or j.get('title_e') or '', 'r': roma, 'no': sheet_no(tms), 'tms': tms, 'b': b}
        if len(pages) > 1:
            e['k'] = f"{mid}_{pg.get('page_id') or i + 1}"
            if pg.get('sub_title'):
                e['st'] = pg.get('sub_title')
        out.append(e)
    return out

def main():
    top = get_json(f'{BASE}/g050.json')
    if not top:
        sys.exit('図幅の一覧（g050.json）を読めませんでした')
    parts = (top.get('linkData') or {}).get('hasPart') or []
    print(f'図幅 {len(parts)} 件を読みます', flush=True)
    maps = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        for n, res in enumerate(ex.map(one, parts), 1):
            maps.extend(res)
            if n % 100 == 0:
                print(f'  {n} / {len(parts)}', flush=True)
    if len(maps) < len(parts) * 0.5:
        sys.exit(f'読めた図幅が少なすぎます（{len(maps)} / {len(parts)}）。前の一覧を残して終わります')
    maps.sort(key=lambda e: (e['no'] or '99-999', e['t'], int(e['id'])))
    made = datetime.date.today().isoformat()
    try:   # 中身が前と同じなら作った日も前のまま（毎月むだな更新をしない）
        old = json.load(open(OUT, encoding='utf-8'))
        if old.get('maps') == maps:
            made = old.get('made') or made
    except Exception:
        pass
    data = {'made': made, 'src': '産業技術総合研究所 地質調査総合センター 5万分の1地質図幅（GSJ LD）', 'n': len(maps), 'maps': maps}
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        f.write('\n')
    print(f'{OUT} に {len(maps)} 件を書きました')

if __name__ == '__main__':
    main()
