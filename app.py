import os
import json
import random
import re
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_mail import Mail, Message

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'chave_secreta_padrao_muito_insegura')

DATA_FILE = "manifestacoes.json"
MATRICULAS_FILE = "matriculas_validas.json"

ADMIN_USER = os.getenv('FLASK_ADMIN_USER', 'admin')
ADMIN_PASS = os.getenv('FLASK_ADMIN_PASS', '1234')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')

app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 465))
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mail = Mail(app)

def carregar_dados(filename):
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    if filename == DATA_FILE or filename == MATRICULAS_FILE:
        return []
    return {}

def salvar_manifestacoes(manifestacoes):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(manifestacoes, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"ERRO ao salvar manifestações: {e}")
        return False

def gerar_protocolo():
    return str(random.randint(1000000000, 9999999999))

def validar_matricula(matricula):
    matriculas_validas = carregar_dados(MATRICULAS_FILE)
    return matricula in matriculas_validas

def enviar_email(protocolo, tipo_manifestacao):
    if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD') or not ADMIN_EMAIL:
        print("ERRO CRÍTICO: Configurações de e-mail (MAIL_USERNAME/PASSWORD ou ADMIN_EMAIL) estão vazias!")
        return False

    try:
        msg = Message(
            f'Nova Manifestação Registrada (Protocolo: {protocolo})',
            sender=app.config['MAIL_USERNAME'],
            recipients=[ADMIN_EMAIL]
        )
        msg.body = (
            f"Uma nova manifestação foi registrada no sistema de ouvidoria.\n\n"
            f"Protocolo: {protocolo}\n"
            f"Tipo: {tipo_manifestacao.capitalize()}\n\n"
            f"Por favor, acesse a área administrativa para visualizá-la."
        )
        mail.send(msg)
        print(f"Email de notificação para protocolo {protocolo} enviado com sucesso!")
        return True
    except Exception as e:
        print(f"ERRO AO ENVIAR EMAIL (SMTP): {e}")
        return False

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

        if len(cpf) != 11 or not cpf.isdigit():
            flash('CPF inválido. Deve conter 11 dígitos numéricos.', 'error')
            return redirect(url_for('index'))

        if len(matricula) != 8 or not matricula.isdigit():
            flash('Matrícula inválida. Deve conter 8 dígitos numéricos.', 'error')
            return redirect(url_for('index'))

        if not validar_matricula(matricula):
            flash('Matrícula não encontrada na lista de estudantes válidos.', 'error')
            return redirect(url_for('index'))

        if not tipo or not descricao:
            flash('Todos os campos obrigatórios (Tipo, Descrição) devem ser preenchidos.', 'error')
            return redirect(url_for('index'))

        protocolo = gerar_protocolo()
        manifestacoes = carregar_dados(DATA_FILE)

        nova_manifestacao = {
            'protocolo': protocolo,
            'nome': nome,
            'cpf': cpf,
            'matricula': matricula,
            'tipo': tipo,
            'descricao': descricao,
            'data': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            'status': 'Pendente',
            'resposta': None
        }

        manifestacoes.append(nova_manifestacao)

        if salvar_manifestacoes(manifestacoes):
            flash(f'Manifestação registrada com sucesso! Seu protocolo é: {protocolo}', 'success')
            enviar_email(protocolo, tipo)
        else:
            flash(f'Manifestação registrada (Protocolo: {protocolo}), mas houve um erro ao salvar o arquivo.', 'warning')
        
        return redirect(url_for('index'))

    except Exception as e:
        print(f"Erro no registro: {e}")
        flash('Erro interno ao registrar manifestação. Tente novamente mais tarde.', 'error')
        return redirect(url_for('index'))

@app.route('/consultar', methods=['POST'])
def consultar():
    protocolo = request.form.get('protocolo', '').strip()
    if not protocolo or not protocolo.isdigit():
        return jsonify({'erro': 'Protocolo inválido.'}), 400

    manifestacoes = carregar_dados(DATA_FILE)
    
    for m in manifestacoes:
        if m['protocolo'] == protocolo:
            return jsonify({
                'protocolo': m['protocolo'], 
                'tipo': m['tipo'], 
                'descricao': m['descricao'], 
                'data': m['data'],
                'status': m['status'],
                'resposta': m['resposta']
            }), 200

    return jsonify({'erro': 'Manifestação não encontrada.'}), 404

@app.route('/admin', methods=['GET'])
def admin_page():
    return render_template('admin_login.html')

@app.route('/admin_login', methods=['POST'])
def admin_login():
    usuario = request.form.get('usuarioAdmin')
    senha = request.form.get('senhaAdmin')
    
    if usuario == ADMIN_USER and senha == ADMIN_PASS:
        return redirect(url_for('listar_manifestacoes'))
    else:
        flash('Credenciais inválidas.', 'error')
        return redirect(url_for('admin_page'))

@app.route('/listar_manifestacoes', methods=['GET'])
def listar_manifestacoes():
    manifestacoes = carregar_dados(DATA_FILE)
    manifestacoes.sort(key=lambda x: datetime.strptime(x['data'], "%d/%m/%Y %H:%M:%S"), reverse=True)
    
    return render_template('admin_dashboard.html', manifestacoes=manifestacoes)

@app.route('/responder', methods=['POST'])
def responder_manifestacao():
    protocolo = request.form.get('protocolo')
    resposta = request.form.get('resposta')

    if not protocolo or not resposta:
        flash('Protocolo e resposta são obrigatórios.', 'error')
        return redirect(url_for('listar_manifestacoes'))

    manifestacoes = carregar_dados(DATA_FILE)
    encontrada = False

    for m in manifestacoes:
        if m['protocolo'] == protocolo:
            m['resposta'] = resposta
            m['status'] = 'Respondida'
            encontrada = True
            break
    
    if encontrada:
        if salvar_manifestacoes(manifestacoes):
            flash(f'Resposta para o protocolo {protocolo} registrada com sucesso.', 'success')
        else:
            flash('Erro ao salvar a resposta no arquivo.', 'error')
    else:
        flash('Manifestação não encontrada.', 'error')

    return redirect(url_for('listar_manifestacoes'))

if __name__ == '__main__':
    for filename in [DATA_FILE, MATRICULAS_FILE]:
        if not os.path.exists(filename):
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=4)
                
    app.run(debug=True)
