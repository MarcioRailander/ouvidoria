import json
import os
import random
import re
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_mail import Mail, Message

app = Flask(__name__)

# ================================
# CONFIGURAÇÕES DO FLASK-MAIL (LOCAL)
# ================================
# Apenas preencha com seu Gmail e sua senha de app.
# Não use a senha normal do Gmail.

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True

# Coloque seu e-mail e sua senha de app aqui
app.config['MAIL_USERNAME'] = "cetepouvidoria6@gmail.com"            # <-- SEU E-MAIL
app.config['MAIL_PASSWORD'] = "iuuo phxy wxab wuxz"              # <-- SENHA DE APP

# Remetente padrão
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

# E-mail que receberá as manifestações
ADMIN_EMAIL = "maciodejesus0@gmail.com"

mail = Mail(app)

# ================================
# ARQUIVOS DE DADOS
# ================================
DATA_FILE = "manifestacoes.json"
MATRICULAS_FILE = "matriculas_validas.json"

admin_user = "admin"
admin_pass = "1234"   # senha local


# ================================
# FUNÇÕES DE ARQUIVO/MANIPULAÇÃO
# ================================
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


# ================================
# FUNÇÕES AUXILIARES
# ================================
def gerar_protocolo():
    return str(random.randint(1000000000, 9999999999))

def validar_matricula(matricula):
    lista = carregar_matriculas_validas()
    return matricula in lista

def enviar_email(protocolo, tipo):
    """Envia notificação de nova manifestação."""
    try:
        msg = Message(
            subject=f"Nova Manifestação Registrada – Protocolo {protocolo}",
            recipients=[ADMIN_EMAIL]
        )

        msg.body = f"""
        Nova manifestação registrada.

        Protocolo: {protocolo}
        Tipo: {tipo.capitalize()}

        Acesse o painel administrativo.
        """

        mail.send(msg)
        print("E-mail enviado com sucesso!")

    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")


# ================================
# ROTAS PRINCIPAIS
# ================================
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

        # Validações
        if len(cpf) != 11:
            return jsonify({'erro': 'CPF inválido (11 dígitos).'}), 400

        if len(matricula) != 8:
            return jsonify({'erro': 'Matrícula inválida (8 dígitos).'}), 400

        if not validar_matricula(matricula):
            return jsonify({'erro': 'Matrícula não encontrada.'}), 400

        if not tipo or not descricao:
            return jsonify({'erro': 'Preencha todos os campos obrigatórios.'}), 400

        protocolo = gerar_protocolo()
        manifestacoes = carregar_manifestacoes()

        nova = {
            "protocolo": protocolo,
            "nome": nome,
            "cpf": cpf,
            "matricula": matricula,
            "tipo": tipo,
            "descricao": descricao,
            "data": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "resposta": None
        }

        manifestacoes.append(nova)
        salvar_manifestacoes(manifestacoes)

        enviar_email(protocolo, tipo)

        return jsonify({"protocolo": protocolo})

    except Exception as e:
        print("ERRO:", e)
        return jsonify({"erro": f"Erro ao registrar: {e}"}), 500


@app.route('/consultar', methods=['POST'])
def consultar():
    protocolo = request.form.get('protocolo', '').strip()

    if not protocolo.isdigit():
        return jsonify({'erro': 'Protocolo inválido.'}), 400

    manifestacoes = carregar_manifestacoes()
    for m in manifestacoes:
        if m['protocolo'] == protocolo:
            return jsonify(m)

    return jsonify({'erro': 'Manifestação não encontrada.'}), 404


@app.route('/consultar_cpf', methods=['POST'])
def consultar_cpf():
    cpf = re.sub(r'[^0-9]', '', request.form.get('cpfBusca', '').strip())

    if len(cpf) != 11:
        return jsonify({'erro': 'CPF inválido.'}), 400

    manifestacoes = carregar_manifestacoes()
    resultados = [m for m in manifestacoes if m['cpf'] == cpf]

    return jsonify(resultados)


@app.route('/consultar_matricula', methods=['POST'])
def consultar_matricula():
    matricula = re.sub(r'[^0-9]', '', request.form.get('matriculaBusca', '').strip())

    if len(matricula) != 8:
        return jsonify({'erro': 'Matrícula inválida.'}), 400

    manifestacoes = carregar_manifestacoes()
    resultados = [m for m in manifestacoes if m['matricula'] == matricula]

    return jsonify(resultados)


# ================================
# ADMINISTRAÇÃO
# ================================
@app.route('/admin')
def admin_page():
    return render_template('admin.html')


@app.route('/admin_login', methods=['POST'])
def admin_login():
    usuario = request.form.get('usuarioAdmin')
    senha = request.form.get('senhaAdmin')

    if usuario == admin_user and senha == admin_pass:
        return jsonify({'redirect': url_for('listar_manifestacoes')})
    else:
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
        return jsonify({'erro': 'Campos obrigatórios.'}), 400

    manifestacoes = carregar_manifestacoes()

    for m in manifestacoes:
        if m['protocolo'] == protocolo:
            m['resposta'] = resposta
            salvar_manifestacoes(manifestacoes)
            return jsonify({'mensagem': 'Resposta salva com sucesso.'})

    return jsonify({'erro': 'Protocolo não encontrado.'}), 404


# ================================
# EXECUÇÃO LOCAL
# ================================
if __name__ == '__main__':
    app.run(debug=True)
