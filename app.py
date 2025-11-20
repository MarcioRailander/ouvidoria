import json 
import os 
import random 
import re 
from datetime import datetime 
from flask import Flask, render_template, request, jsonify, redirect, url_for 
from flask_mail import Mail, Message 

# Tenta carregar variáveis de ambiente locais (para desenvolvimento)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__) 

# --- CONFIGURAÇÕES DO FLASK-MAIL (SSL / PORTA 465 — FUNCIONA NO RENDER + GMAIL) ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

# Se existir variável de ambiente, usa ela. Senão, usa os padrões.
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', "cetepouvidoria6@gmail.com")
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', "iuuo phxy wxab wuxz")

ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', "cetepouvidoria6@gmail.com")

mail = Mail(app)

# ARQUIVOS E CONFIGURAÇÕES
DATA_FILE = "manifestacoes.json"
MATRICULAS_FILE = "matriculas_validas.json"

admin_user = "admin"
admin_pass = os.environ.get('ADMIN_PASSWORD', '1234')


# --- FUNÇÕES DE ARQUIVO ---
def carregar_manifestacoes():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def salvar_manifestacoes(manifestacoes):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(manifestacoes, f, indent=4, ensure_ascii=False)

def carregar_matriculas_validas():
    if os.path.exists(MATRICULAS_FILE):
        with open(MATRICULAS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


# --- FUNÇÕES AUXILIARES ---
def gerar_protocolo():
    return str(random.randint(1000000000, 9999999999))

def validar_matricula(matricula):
    matriculas_validas = carregar_matriculas_validas()
    return matricula in matriculas_validas

def enviar_email(protocolo, tipo):
    if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD') or not ADMIN_EMAIL:
        print("ERRO: Configurações de email faltando!")
        return

    try:
        msg = Message(
            f'Nova Manifestação Registrada: Protocolo {protocolo}',
            sender=app.config['MAIL_USERNAME'],
            recipients=[ADMIN_EMAIL]
        )

        msg.body = f"""
Prezado(a) Administrador(a),

Uma nova manifestação foi registrada no sistema de Ouvidoria CETEP LNAB.

Detalhes:
- Protocolo: {protocolo}
- Tipo: {tipo.capitalize()}

Acesse a área administrativa para visualizar e responder: {request.url_root}admin
"""

        mail.send(msg)
        print("E-mail enviado com sucesso!")
    except Exception as e:
        print(f"ERRO ao enviar e-mail: {e}")


# --- ROTAS ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/registrar', methods=['POST'])
def registrar():
    try:
        nome = request.form.get('nome', 'Anônimo').strip()
        cpf = re.sub(r'[^0-9]', '', request.form.get('cpf', '').strip())
        matricula = re.sub(r'[^0-9]', '', request.form.get('matricula', '').strip())
        tipo = request.form.get('tipo', '').strip()
        descricao = request.form.get('descricao', '').strip()

        if len(cpf) != 11:
            return jsonify({'erro': 'CPF inválido.'}), 400

        if len(matricula) != 8:
            return jsonify({'erro': 'Matrícula inválida.'}), 400

        if not validar_matricula(matricula):
            return jsonify({'erro': 'Matrícula não encontrada.'}), 400

        if not tipo or not descricao:
            return jsonify({'erro': 'Todos os campos obrigatórios devem ser preenchidos.'}), 400

        protocolo = gerar_protocolo()
        manifestacoes = carregar_manifestacoes()

        nova = {
            'protocolo': protocolo,
            'nome': nome,
            'cpf': cpf,
            'matricula': matricula,
            'tipo': tipo,
            'descricao': descricao,
            'data': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            'resposta': None
        }

        manifestacoes.append(nova)
        salvar_manifestacoes(manifestacoes)

        enviar_email(protocolo, tipo)

        return jsonify({'protocolo': protocolo}), 200

    except Exception as e:
        return jsonify({'erro': f'Erro interno: {e}'}), 500


@app.route('/consultar', methods=['POST'])
def consultar():
    protocolo = request.form.get('protocolo', '').strip()

    if not protocolo.isdigit():
        return jsonify({'erro': 'Protocolo inválido.'}), 400

    manifestacoes = carregar_manifestacoes()
    for m in manifestacoes:
        if m['protocolo'] == protocolo:
            return jsonify(m), 200

    return jsonify({'erro': 'Manifestação não encontrada.'}), 404


@app.route('/consultar_cpf', methods=['POST'])
def consultar_cpf():
    cpf = re.sub(r'[^0-9]', '', request.form.get('cpfBusca', '').strip())

    if len(cpf) != 11:
        return jsonify({'erro': 'CPF inválido.'}), 400

    manifestacoes = carregar_manifestacoes()
    return jsonify([m for m in manifestacoes if m['cpf'] == cpf]), 200


@app.route('/consultar_matricula', methods=['POST'])
def consultar_matricula():
    matricula = re.sub(r'[^0-9]', '', request.form.get('matriculaBusca', '').strip())

    if len(matricula) != 8:
        return jsonify({'erro': 'Matrícula inválida.'}), 400

    manifestacoes = carregar_manifestacoes()
    return jsonify([m for m in manifestacoes if m['matricula'] == matricula]), 200


@app.route('/admin')
def admin_page():
    return render_template('admin.html')

@app.route('/admin_login', methods=['POST'])
def admin_login():
    usuario = request.form.get('usuarioAdmin')
    senha = request.form.get('senhaAdmin')

    if usuario == admin_user and senha == admin_pass:
        return jsonify({'redirect': url_for('listar_manifestacoes')}), 200

    return jsonify({'erro': 'Credenciais inválidas.'}), 401


@app.route('/listar_manifestacoes')
def listar_manifestacoes():
    manifestacoes = carregar_manifestacoes()
    return render_template('admin_dashboard.html', manifestacoes=manifestacoes)


@app.route('/api/manifestacoes')
def api_manifestacoes():
    return jsonify(carregar_manifestacoes())


@app.route('/responder', methods=['POST'])
def responder_manifestacao():
    protocolo = request.form.get('protocolo')
    resposta = request.form.get('resposta')

    if not protocolo or not resposta:
        return jsonify({'erro': 'Protocolo e resposta são obrigatórios.'}), 400

    manifestacoes = carregar_manifestacoes()
    for m in manifestacoes:
        if m['protocolo'] == protocolo:
            m['resposta'] = resposta
            salvar_manifestacoes(manifestacoes)
            return jsonify({'mensagem': 'Resposta registrada com sucesso.'}), 200

    return jsonify({'erro': 'Manifestação não encontrada.'}), 404


# --- FINAL CORRIGIDO (SEM ERRO DE INDENTAÇÃO) ---
if __name__ == '__main__':
    if not os.path.exists('templates'):
        os.makedirs('templates')
    app.run(debug=True)
