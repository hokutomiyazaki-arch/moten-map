#!/usr/bin/env python3
"""index.html のガイドを ElevenLabs で voice/ に作る。--dry は一覧と字数のみ。"""
import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'voice'
MODEL = 'eleven_v3'
VOICE = '1cOJcfrlMmUCGpeJbXg9'  # リョウ
# JS の引用文字列（固定文にはエスケープがない）。
STRING = r"(['\"`])((?:\\.|(?!\1).)*?)\1"


def vkey(text):
    return re.sub(r'[\s。]', '', text)


def say_text(text):
    # 1語だと読み違えやすいものは、かなで読ませる（外＝そと・鼻側＝はながわ・覆う＝おおう）
    text = re.sub(r'外(?=[へのにが])', 'そと', text).replace('鼻側', 'はながわ').replace('覆', 'おお')
    return text.replace('止め', 'とめ').replace('cm', 'センチ').replace('8点', 'はちてん')


def texts():
    source = (ROOT / 'index.html').read_text(encoding='utf-8')
    result = {m.group(2) for m in re.finditer(r'\bsay\(\s*' + STRING, source, re.S)
              if '${' not in m.group(2)}
    scenes = re.search(r'const\s+DEMO_SCENES\s*=\s*\[(.*?)\n\];', source, re.S)
    if not scenes:
        sys.exit('DEMO_SCENES を拾えません')
    result.update(m.group(2) for m in re.finditer(r'\[\s*\d+\s*,\s*' + STRING, scenes.group(1), re.S))
    dirs = re.search(r'const\s+DIRS\s*=\s*\[(.*?)\];', source, re.S)
    eyes = re.search(r'const\s+EYE\s*=\s*\{(.*?)\};', source, re.S)
    if not dirs or not eyes:
        sys.exit('DIRS または EYE を拾えません')
    directions = re.findall(r"\bsay\s*:\s*'([^']+)'", dirs.group(1))
    pairs = re.findall(r"\b[RL]\s*:\s*\{[^}]*\bcover\s*:\s*'([^']+)'[^}]*\bside\s*:\s*'([^']+)'[^}]*\}", eyes.group(1))
    if not directions or not pairs:
        sys.exit('DIRS の say または EYE の cover・side を拾えません')
    for cover, side in pairs:
        result.add(f'{cover}を覆って、壁の目印だけを見続けます。スマホを壁に沿って{side}へずらし、点が消えたら止めて、ボタンを押し続けてください')
    for direction in directions:
        result.update(f'{n}か所め。次は{direction}' for n in range(2, 9))
        result.add(f'1つ戻しました。{direction}をやり直します')
    return sorted(result)


def tts(text, path, api_key):
    body = json.dumps({'text': text, 'model_id': MODEL,
                       'voice_settings': {'stability': 0.5, 'similarity_boost': 0.75}}).encode('utf-8')
    request = urllib.request.Request(
        f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE}?output_format=mp3_22050_32',
        data=body, headers={'xi-api-key': api_key, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=120) as response:
        path.write_bytes(response.read())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry', action='store_true', help='全文の一覧・件数・字数だけ表示')
    args = parser.parse_args()
    lines = texts()
    index = {vkey(t): hashlib.md5(say_text(t).encode('utf-8')).hexdigest()[:12] + '.mp3' for t in lines}
    todo = [(t, index[vkey(t)]) for t in lines if not (OUT / index[vkey(t)]).exists()]
    print(f'全文 {len(lines)}件・{sum(len(say_text(t)) for t in lines)}字／未生成 {len(todo)}件・{sum(len(say_text(t)) for t, _ in todo)}字', flush=True)
    if args.dry:
        for text in lines:
            print(text)
        return
    api_key = os.environ.get('ELEVENLABS_API_KEY')
    if todo and not api_key:
        sys.exit('ELEVENLABS_API_KEY がありません')
    OUT.mkdir(exist_ok=True)
    for i, (text, filename) in enumerate(todo, 1):
        tts(say_text(text), OUT / filename, api_key)
        print(f'{i}/{len(todo)} {text}', flush=True)
    (OUT / 'index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('voice/index.json を更新しました')


if __name__ == '__main__':
    main()
