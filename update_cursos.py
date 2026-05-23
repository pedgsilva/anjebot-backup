#!/usr/bin/env python3
"""
Script de recolha diaria de cursos do site anjeformacao.pt
Corre todos os dias as 02:00 via cron job
- Scrapes todas as paginas de cursos
- Atualiza anjeformacao.json (preserva equipa e orgaos sociais)
- Faz commit e push para GitHub
"""

import urllib.request
import urllib.error
import re
import json
import subprocess
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ANJEFORMACAO_JSON = os.path.join(BASE_DIR, 'anjeformacao.json')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}


def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] {msg}', flush=True)


def scrape_all_courses():
    base_url = "https://anjeformacao.pt/cursos/page/{}/"
    all_courses = []

    for page_num in range(1, 20):
        url = base_url.format(page_num)
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode('utf-8', errors='replace')
        except urllib.error.HTTPError as e:
            if e.code == 404:
                break
            continue
        except Exception:
            continue

        courses = extract_courses(html)
        log(f'Pagina {page_num}: {len(courses)} cursos')
        if not courses:
            break
        all_courses.extend(courses)

    return all_courses


def extract_courses(html):
    courses = []
    ul_match = re.search(r'<ul[^>]*class="[^"]*products[^"]*"[^>]*>(.*?)</ul>', html, re.DOTALL)
    if not ul_match:
        return courses

    for li in re.findall(r'<li[^>]*>(.*?)</li>', ul_match.group(1), re.DOTALL):
        if 'product' not in li[:200]:
            continue

        t = re.search(r'<h2[^>]*>\s*<a[^>]*>(.*?)</a>\s*</h2>', li, re.DOTALL)
        if not t:
            t = re.search(r'<h2[^>]*>(.*?)</h2>', li, re.DOTALL)
        title = re.sub(r'<[^>]+>', '', t.group(1)).strip() if t else ''

        u = re.search(r'href="(https://anjeformacao\.pt/curso/[^\"]+)"', li)
        url = u.group(1) if u else ''

        price = 'Sob consulta'
        pm = re.search(r'"price":(\d+)', li)
        if pm:
            p = int(pm.group(1))
            price = 'Gratuito' if p == 0 else f'€{p},00'
        if price == 'Sob consulta':
            full = re.sub(r'<[^>]+>', ' ', li)
            full = re.sub(r'\s+', ' ', full).strip()
            em = re.search(r'(€\s*[\d]+[.,]\d{2})', full)
            if em:
                price = em.group(1).replace(' ', '')
            elif 'Gratuito' in full:
                price = 'Gratuito'

        dm = re.search(r'(\d{2}-\d{2}-\d{4})', li)
        date = dm.group(1) if dm else 'Sob consulta'

        if title and url:
            courses.append({'titulo': title, 'preco': price, 'data': date, 'url': url})

    return courses


def update_json(new_courses):
    with open(ANJEFORMACAO_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    old_urls = set(c['url'] for c in data.get('cursos_lista', []))
    new_urls = set(c['url'] for c in new_courses)

    data['cursos_lista'] = new_courses
    data['ultima_atualizacao'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with open(ANJEFORMACAO_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    added = len(new_urls - old_urls)
    removed = len(old_urls - new_urls)
    return len(data.get('cursos_lista', [])), added, removed


def git_push():
    cred_file = os.path.expanduser('~/.git-credentials')
    username = token = ''
    if os.path.exists(cred_file):
        with open(cred_file) as f:
            m = re.match(r'https://([^:]+):([^@]+)@github\.com', f.read().strip())
        if m:
            username, token = m.group(1), m.group(2)

    if not username:
        log('ERRO: Credenciais GitHub nao encontradas')
        return False

    remote_url = f"https://{username}:{token}@github.com/{username}/anjebot.git"
    subprocess.run(['git', 'remote', 'set-url', 'origin', remote_url],
                   cwd=BASE_DIR, capture_output=True)

    st = subprocess.run(['git', 'status', '--porcelain'],
                        cwd=BASE_DIR, capture_output=True, text=True)
    if not st.stdout.strip():
        log('Sem alteracoes para commitar')
        return True

    for cmd in [
        ['git', 'add', 'anjeformacao.json'],
        ['git', 'commit', '-m', f'Update cursos anjeformacao.pt - {datetime.now().strftime("%Y-%m-%d %H:%M")}'],
        ['git', 'push', 'origin', 'main'],
    ]:
        r = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
        if r.returncode != 0:
            err = r.stderr.strip()
            if 'nothing to commit' in err:
                continue
            log(f'ERRO git: {err}')
            return False
    return True


def main():
    log('=' * 50)
    log('Inicio da recolha de cursos - anjeformacao.pt')

    courses = scrape_all_courses()
    log(f'Total: {len(courses)} cursos encontrados')

    if not courses:
        log('ERRO: Nenhum curso encontrado')
        sys.exit(1)

    old_count, added, removed = update_json(courses)
    log(f'JSON atualizado: {old_count} -> {len(courses)} cursos')
    if added:
        log(f'  + {added} novos')
    if removed:
        log(f'  - {removed} removidos')

    if git_push():
        log('GitHub atualizado com sucesso!')
    else:
        log('ERRO no push para GitHub')
        sys.exit(1)

    log('Concluido!')
    return len(courses)


if __name__ == '__main__':
    count = main()
    print(f'\nRESULTADO: {count} cursos atualizados')
