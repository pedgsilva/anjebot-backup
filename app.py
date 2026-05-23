"""
ChatBot da ANJE - Formacao (anjeformacao.pt)
Backend Flask - respostas via OpenRouter
Versao melhorada com dados completos de equipa e orgaos sociais
"""

import os
import json
import re
import time
from functools import lru_cache
from flask import Flask, render_template, request, jsonify
import requests

# Load .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)

# Load site data
def load_site_data():
    data = {}
    base_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        with open(os.path.join(base_dir, 'anjeformacao.json'), 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f'Warning: {e}')
    return data

SITE_DATA = load_site_data()

# Config
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = os.getenv('OPENROUTER_MODEL', 'openrouter/owl-alpha')
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 60))
MAX_TOKENS = int(os.getenv('MAX_TOKENS', 800))

# ============================================================
# TEAM DATA - Rich structured responses
# ============================================================

def get_equipa_data():
    """Get full equipa data from JSON"""
    return SITE_DATA.get('equipa', {})

def get_orgaos_data():
    """Get full orgaos sociais data from JSON"""
    return SITE_DATA.get('orgaos_sociais', {})

def build_equipa_full_text():
    """Build complete equipa text for system prompt"""
    equipa = get_equipa_data()
    sections = []
    
    direcao = equipa.get('direcao', [])
    if direcao:
        sections.append("**Direção:**")
        for m in direcao:
            sections.append(f"• {m['nome']} - {m['cargo']}")
    
    coords = equipa.get('coordenadores_formacao', [])
    if coords:
        sections.append("\n**Coordenadores de Formação:**")
        for m in coords:
            regiao = m.get('regiao', '')
            if regiao:
                sections.append(f"• {m['nome']} - {m['cargo']} ({regiao})")
            else:
                sections.append(f"• {m['nome']} - {m['cargo']}")
    
    admin = equipa.get('administrativos', [])
    if admin:
        sections.append("\n**Administrativos:**")
        for m in admin:
            regiao = m.get('regiao', '')
            if regiao:
                sections.append(f"• {m['nome']} - {m['cargo']} ({regiao})")
            else:
                sections.append(f"• {m['nome']} - {m['cargo']}")
    
    comm = equipa.get('comunicacao_marketing', [])
    if comm:
        sections.append("\n**Comunicação e Marketing:**")
        for m in comm:
            sections.append(f"• {m['nome']} - {m['cargo']}")
    
    return '\n'.join(sections)

def build_orgaos_full_text():
    """Build complete orgaos sociais text for system prompt"""
    orgaos = get_orgaos_data()
    sections = []
    
    direcao = orgaos.get('direcao_nacional', [])
    if direcao:
        sections.append("**Direção Nacional:**")
        for m in direcao:
            sections.append(f"• {m['nome']} - {m['cargo']}")
    
    mesa = orgaos.get('mesa_assembleia_geral', [])
    if mesa:
        sections.append("\n**Mesa da Assembleia-Geral:**")
        for m in mesa:
            sections.append(f"• {m['nome']} - {m['cargo']}")
    
    cf = orgaos.get('conselho_fiscal', [])
    if cf:
        sections.append("\n**Conselho Fiscal:**")
        for m in cf:
            sections.append(f"• {m['nome']} - {m['cargo']}")
    
    return '\n'.join(sections)

def is_team_query(msg_lower):
    """Check if the query is about team/orgaos/people"""
    # Strong indicators - always team query
    strong_keywords = [
        'equipa', 'equipe', 'staff', 'funcionarios', 'funcionários',
        'direção', 'direcao', 'diretor', 'diretores', 'diretora', 'diretoras',
        'presidente', 'vice-presidente', 'vice presidente',
        'orgaos', 'órgãos', 'orgão', 'órgão',
        'conselho fiscal', 'assembleia geral', 'mesa da assembleia',
        'quem faz parte', 'quem trabalha', 'quem dirige',
        'coordenador', 'coordenadora', 'coordenadores', 'coordenadoras',
        'administrativo', 'administrativa', 'administrativos', 'administrativas',
        'comunicacao e marketing', 'comunicação e marketing',
    ]
    for kw in strong_keywords:
        if kw in msg_lower:
            return True
    
    # Person names - full names
    name_patterns = [
        'ana jogo', 'ana mendes', 'claudia almeida', 'cláudia almeida',
        'cristiana moreira', 'manuela almeida', 'vitoria pereira', 'vitória pereira',
        'ana rodrigues', 'armanda ângelo', 'catia santos', 'cátia santos',
        'patricia nobre', 'patrícia nobre', 'sara almeida', 'susana pereira',
        'fatima pinto', 'fátima pinto', 'teresa miranda',
        'carlos carvalho', 'nuno malheiro', 'filipa pinto', 'gonçalo simões',
        'gonçalo almeida', 'gonçalo abreu', 'gonçalo sá', 'filipe quinaz',
        'miguel teixeira', 'miguel moreira', 'miguel oliveira', 'sofia correia',
        'sofia xavier', 'tiago araújo', 'tiago abalroado', 'antonio fragateiro',
        'beatriz almeida', 'pedro marcelino', 'pedro cardoso', 'camilo ferreira',
        'joão pestana', 'joao pestana', 'diogo teixeira', 'diogo pinheiro',
        'ricardo santos', 'ricardo lopes', 'paula melo', 'catarina azevedo',
        'vitor almeida', 'vítor almeida', 'jose miguel', 'josé miguel',
        'manuela borges',
    ]
    for name in name_patterns:
        if name in msg_lower:
            return True
    
    # Single names only with context words
    context_words = ['quem é', 'quem e', 'fala-me', 'fala me', 'conhece', 'quem são', 'quem sao', 'membros', 'equipa', 'equipe', 'direção', 'direcao', 'orgaos', 'órgãos']
    single_names = [
        'teresa', 'claudia', 'cláudia', 'cristiana', 'manuela',
        'vitoria', 'vitória', 'sara', 'susana', 'fatima', 'fátima',
        'carlos', 'nuno', 'filipa', 'gonçalo', 'filipe', 'miguel',
        'sofia', 'tiago', 'antonio', 'beatriz', 'pedro', 'camilo',
        'joao', 'joão', 'diogo', 'ricardo', 'paula', 'catarina',
        'vitor', 'vítor', 'josé', 'jose', 'armanda', 'catia', 'cátia',
        'patricia', 'patrícia',
    ]
    has_context = any(cw in msg_lower for cw in context_words)
    if has_context:
        for name in single_names:
            if name in msg_lower:
                return True
    
    return False

def get_team_response_context(msg_lower):
    """Build rich context for team-related queries"""
    equipa = get_equipa_data()
    orgaos = get_orgaos_data()
    
    context_parts = []
    
    # Check if asking about specific person
    person_found = None
    
    all_members = []
    for section, members in equipa.items():
        for m in members:
            all_members.append((m, 'equipa', section))
    for section, members in orgaos.items():
        for m in members:
            all_members.append((m, 'orgaos', section))
    
    for m, mtype, section in all_members:
        nome_lower = m['nome'].lower()
        name_parts = nome_lower.split()
        if nome_lower in msg_lower:
            person_found = m
            break
        if len(name_parts) >= 2:
            for i in range(len(name_parts)):
                for j in range(i+1, len(name_parts)):
                    partial = ' '.join(name_parts[i:j+1])
                    if partial in msg_lower and len(partial) > 5:
                        person_found = m
                        break
                if person_found:
                    break
        if person_found:
            break
    
    if person_found:
        regiao = person_found.get('regiao', '')
        if regiao:
            return f"Pessoa: {person_found['nome']} - {person_found['cargo']} ({regiao})"
        else:
            return f"Pessoa: {person_found['nome']} - {person_found['cargo']}"
    
    # Check what type of query
    is_orgaos_query = any(kw in msg_lower for kw in ['orgaos', 'órgãos', 'orgão', 'órgão', 'conselho fiscal', 'assembleia', 'mesa', 'fiscal'])
    is_equipa_query = any(kw in msg_lower for kw in ['equipa', 'equipe', 'coordenador', 'coordenadora', 'administrativo', 'administrativa', 'comunicacao', 'comunicação'])
    
    if is_orgaos_query and not is_equipa_query:
        context_parts.append("Dados dos Órgãos Sociais da ANJE:")
        context_parts.append(build_orgaos_full_text())
    elif is_equipa_query and not is_orgaos_query:
        context_parts.append("Dados da Equipa ANJE Formação:")
        context_parts.append(build_equipa_full_text())
    else:
        context_parts.append("Dados da Equipa ANJE Formação:")
        context_parts.append(build_equipa_full_text())
        context_parts.append("\n\nDados dos Órgãos Sociais da ANJE:")
        context_parts.append(build_orgaos_full_text())
    
    return '\n'.join(context_parts)

# ============================================================
# COURSE INDEX
# ============================================================

def build_course_index():
    cursos = SITE_DATA.get('cursos_lista', [])
    area_map = {
        'ia': ['inteligencia artificial', 'claude', 'chatgpt', 'machine learning', 'ia generativa'],
        'gestao': ['gestao', 'lideran', 'equipa', 'tempo', 'projeto', 'produtividade', 'burnout'],
        'marketing': ['marketing', 'digital', 'ecommerce', 'seo', 'influenc', 'instagram', 'linkedin'],
        'vendas': ['venda', 'comercial', 'neuromarketing', 'vendedor', 'prospe', 'crm'],
        'financas': ['financ', 'tesouraria', 'poupanca', 'excel', 'powerbi', 'sql', 'python'],
        'juridico': ['juridic', 'direito', 'rgpd', 'laboral', 'sociedade'],
        'comunicacao': ['comunicar', 'storytelling', 'apresentac', 'impacto', 'pnl'],
        'certificacao': ['certifica', 'icagile', 'coach', 'pnl practitioner'],
        'hotelaria': ['hotelaria', 'turismo', 'higiene', 'alimentar'],
        'empreendedorismo': ['empreend', 'negocio', 'plano de neg'],
    }
    index = []
    for curso in cursos:
        titulo_lower = curso.get('titulo', '').lower()
        tags = set()
        for area, keywords in area_map.items():
            for kw in keywords:
                if kw in titulo_lower:
                    tags.add(area)
                    break
        index.append({'curso': curso, 'titulo_lower': titulo_lower, 'tags': tags})
    return index

COURSE_INDEX = build_course_index()

# ============================================================
# SYSTEM PROMPT
# ============================================================

def build_system_prompt():
    cursos = SITE_DATA.get('cursos_lista', [])
    contactos = SITE_DATA.get('contactos', {})
    inst = SITE_DATA.get('institucional', {})
    mods = SITE_DATA.get('modalidades', [])
    regs = SITE_DATA.get('regioes', [])

    pagos = [c for c in cursos if c['preco'] not in ('Gratuito', 'Sob consulta')]
    gratis = [c for c in cursos if c['preco'] == 'Gratuito']

    return (
        "Assistente ANJE Formacao (anjeformacao.pt).\n"
        "\n"
        "SOBRE: " + inst.get('sobre_formacao', 'Formacao Profissional Certificada.') + "\n"
        "\n"
        "CONTACTOS: " + contactos.get('email', 'infoformacao@anje.pt') + " | " + contactos.get('telefone_fixo', '(+351) 220 108 074') + "\n"
        "\n"
        "CURSOS: " + str(len(cursos)) + " (" + str(len(pagos)) + " pagos, " + str(len(gratis)) + " gratuitos)\n"
        "Modalidades: " + ', '.join(mods[:4]) + "\n"
        "Regioes: " + ', '.join(regs) + "\n"
        "\n"
        "REGRAS:\n"
        "- Portugues de Portugal\n"
        "- Cursos: usa os dados de cursos recebidos na pergunta\n"
        "- Equipa/orgaos: usa os dados recebidos na pergunta\n"
        "- **negrita** para titulos\n"
        "- Link: https://anjeformacao.pt/curso/...\n"
        "- Formato: **Titulo** - Preco: XX | Data: DD-MM\n"
        "- Nao sabe? infoformacao@anje.pt\n"
    )

STATIC_PROMPT = build_system_prompt()

# ============================================================
# COURSE SEARCH
# ============================================================

SYNONYMS = {
    'excel': ['excel', 'folha de calculo', 'folha de cálculo', 'planilha'],
    'folha': ['excel', 'folha de calculo', 'folha de cálculo', 'planilha'],
    'calculo': ['excel', 'folha de calculo', 'folha de cálculo', 'planilha'],
    'powerbi': ['powerbi', 'power bi', 'dashboard', 'dashboards'],
    'python': ['python', 'programacao', 'programação'],
    'rgpd': ['rgpd', 'protecao de dados', 'proteção de dados', 'dados pessoais'],
    'ia': ['inteligencia artificial', 'ia', 'ai', 'claude', 'chatgpt', 'machine learning'],
    'inteligencia artificial': ['inteligencia artificial', 'ia', 'ai', 'claude', 'chatgpt'],
    'marketing': ['marketing', 'digital', 'seo', 'influenc', 'instagram', 'linkedin', 'marca'],
    'vendas': ['venda', 'vendas', 'comercial', 'vendedor', 'prospe', 'crm', 'fecho'],
    'gestao': ['gestao', 'gestão', 'lideran', 'liderança', 'equipa', 'tempo', 'projeto', 'produtividade'],
    'comunicacao': ['comunicar', 'comunica', 'storytelling', 'apresentac', 'impacto', 'falar'],
    'certificacao': ['certifica', 'icagile', 'coach', 'pnl practitioner', 'certificação'],
    'hotelaria': ['hotelaria', 'turismo', 'higiene', 'alimentar', 'seguranc'],
    'empreendedorismo': ['empreend', 'negocio', 'negócio', 'plano de neg', 'startup', 'criar'],
    'juridico': ['juridic', 'direito', 'rgpd', 'laboral', 'sociedade'],
    'financas': ['financ', 'tesouraria', 'poupanca', 'controlo'],
}

def search_courses(query, max_results=15):
    if not COURSE_INDEX:
        return []
    q = query.lower().strip()
    skip = ['equipa', 'equipe', 'diretor', 'presidente', 'vice-presidente', 'orgaos', 'conselho fiscal', 'assembleia', 'mesa', 'quem e', 'quem faz parte', 'quem trabalha', 'staff', 'funcionarios', 'contacto', 'contato', 'email', 'telefone', 'morada', 'endereco', 'sobre a anje', 'sobre anje', 'historia', 'fundacao', 'missao', 'valores', 'quem somos', 'o que e']
    for kw in skip:
        if kw in q:
            return []
    stop = {'os', 'as', 'de', 'da', 'do', 'em', 'um', 'uma', 'para', 'com', 'por', 'que', 'nao', 'sim', 'mais', 'mas', 'ou', 'se', 'ao', 'aos', 'no', 'na', 'nos', 'nas', 'pelo', 'pela', 'qual', 'quais', 'como', 'onde', 'quando', 'e', 'o', 'a'}
    terms = [w for w in re.findall(r'\w+', q) if len(w) >= 2 and w not in stop]
    if not terms:
        return []
    expanded_terms = set()
    for term in terms:
        expanded_terms.add(term)
        if term in SYNONYMS:
            for syn in SYNONYMS[term]:
                expanded_terms.add(syn)
    gratuito_q = any(w in q for w in ['gratuito', 'gratis', 'sem custo', 'free'])
    scored = []
    for entry in COURSE_INDEX:
        score = 0
        titulo = entry['titulo_lower']
        tags = entry['tags']
        for term in expanded_terms:
            if term in titulo:
                score += 10
            if term in tags:
                score += 5
        if gratuito_q:
            score += 20 if entry['curso']['preco'] == 'Gratuito' else -10
        if score > 0:
            scored.append((score, entry['curso']))
    scored.sort(key=lambda x: -x[0])
    return [c[1] for c in scored[:max_results]]

def format_courses(courses):
    if not courses:
        return ""
    lines = []
    for i, c in enumerate(courses, 1):
        lines.append(str(i) + ". " + c['titulo'] + " - " + c['preco'] + " - " + c['data'])
        lines.append("   " + c['url'])
    return '\n'.join(lines)

# ============================================================
# RESPONSE CACHE
# ============================================================

response_cache = {}
CACHE_TTL = 300

def get_cache_key(msg):
    return msg.lower().strip()

# ============================================================
# ROUTES
# ============================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    msg = request.json.get('message', '').strip()
    if not msg:
        return jsonify({'error': 'Mensagem vazia'}), 400

    cache_key = get_cache_key(msg)
    if cache_key in response_cache:
        cached_time, cached_response = response_cache[cache_key]
        if time.time() - cached_time < CACHE_TTL:
            return jsonify({'response': cached_response})

    msg_lower = msg.lower().strip()
    is_team = is_team_query(msg_lower)
    
    user_content = 'Pergunta: ' + msg
    
    if is_team:
        team_context = get_team_response_context(msg_lower)
        user_content += '\n\n' + team_context
        relevant = []
    else:
        relevant = search_courses(msg, max_results=10)
        if relevant:
            user_content += '\n\nCursos:\n' + format_courses(relevant)

    if not OPENROUTER_API_KEY:
        if relevant:
            lines = ["Encontrei estes cursos:\n"]
            for c in relevant:
                lines.append('**' + c['titulo'] + '** - ' + c['preco'])
                lines.append(c['url'] + '\n')
            return jsonify({'response': '\n'.join(lines)})
        if is_team:
            equipa_text = build_equipa_full_text()
            orgaos_text = build_orgaos_full_text()
            response = "Equipa ANJE Formação:\n\n" + equipa_text
            if any(kw in msg_lower for kw in ['orgaos', 'órgãos', 'orgão', 'órgão', 'conselho', 'assembleia', 'fiscal', 'presidente', 'vice-presidente']):
                response += "\n\nÓrgãos Sociais da ANJE:\n\n" + orgaos_text
            return jsonify({'response': response})
        return jsonify({'response': 'Contacte infoformacao@anje.pt'})

    try:
        resp = requests.post(OPENROUTER_API_URL, timeout=REQUEST_TIMEOUT, headers={
            'Authorization': 'Bearer ' + OPENROUTER_API_KEY,
            'Content-Type': 'application/json',
        }, json={
            'model': MODEL,
            'messages': [
                {'role': 'system', 'content': STATIC_PROMPT},
                {'role': 'user', 'content': user_content},
            ],
            'temperature': 0.3,
            'max_tokens': MAX_TOKENS,
        })
        resp.raise_for_status()
        data = resp.json()
        reply = data['choices'][0]['message']['content']
        response_cache[cache_key] = (time.time(), reply)
        return jsonify({'response': reply})
    except requests.exceptions.Timeout:
        if relevant:
            lines = ["Encontrei estes cursos:\n"]
            for c in relevant:
                lines.append('**' + c['titulo'] + '** - ' + c['preco'])
                lines.append(c['url'] + '\n')
            return jsonify({'response': '\n'.join(lines)})
        if is_team:
            return jsonify({'response': "Equipa ANJE Formação:\n\n" + build_equipa_full_text()})
        return jsonify({'response': 'Timeout. Tente novamente.'})
    except Exception as e:
        if is_team:
            return jsonify({'response': "Equipa ANJE Formação:\n\n" + build_equipa_full_text()})
        return jsonify({'response': 'Erro. Contacte infoformacao@anje.pt'})

@app.route('/api/cursos')
def api_cursos():
    q = request.args.get('q', '')
    results = search_courses(q, 20) if q else SITE_DATA.get('cursos_lista', [])[:20]
    return jsonify({'cursos': results, 'total': len(results)})

@app.route('/health')
def health():
    equipa = get_equipa_data()
    orgaos = get_orgaos_data()
    return jsonify({
        'status': 'ok',
        'cursos': len(COURSE_INDEX),
        'api_key': bool(OPENROUTER_API_KEY),
        'equipa_members': sum(len(v) for v in equipa.values()),
        'orgaos_members': sum(len(v) for v in orgaos.values()),
    })

if __name__ == '__main__':
    equipa = get_equipa_data()
    orgaos = get_orgaos_data()
    print(f'ChatBot ANJE Formacao v2.0 | Cursos: {len(COURSE_INDEX)} | Equipa: {sum(len(v) for v in equipa.values())} | Orgaos: {sum(len(v) for v in orgaos.values())} | Modelo: {MODEL}')
    app.run(debug=False, host='0.0.0.0', port=5000)
