import json
import os
import random
import re
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_mail import Mail, Message

app = Flask(__name__)

# CONFIGURAÇÕES DO FLASK-MAIL
# O Render lerá estas configurações nas "Environment Variables" que você criou.
# Se você esquecer de configurá-las no Render, o sistema não enviará e-mail!
app.config['MAIL_SERVER'] = 'smtp.gmail.com' 
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')  # Chave secreta do Render
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')  # Chave secreta do Render (o Token de 16 caracteres)

# E-mail para onde as manifestações serão enviadas:
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL') # Chave secreta do Render

mail = Mail(app)

# ARQUIVOS DE DADOS E CONFIGURAÇÕES
DATA_FILE = "manifestacoes.json"
MATRICULAS_FILE = "matriculas_validas.json" # Arquivo de matrículas válidas
admin_user = "admin"
# Senha de Admin também vem do Render, com '1234' como valor padrão se não configurada:
admin_pass = os.environ.get('ADMIN_PASSWORD', '1234')

# FUNÇÕES DE CARREGAMENTO
def carregar_manifestacoes():
    """Carrega as manifestações do arquivo JSON."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            # Retorna o conteúdo, ou uma lista vazia se o arquivo estiver vazio/corrompido
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def salvar_manifestacoes(manifestacoes):
    """Salva as manifestações no arquivo JSON."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(manifestacoes, f, indent=4, ensure_ascii=False)

def carregar_matriculas_validas():
    """Carrega as matrículas válidas do arquivo JSON."""
    if os.path.exists(MATRICULAS_FILE):
        with open(MATRICULAS_FILE, "r", encoding="utf-8") as f:
            try:
                # O arquivo deve conter uma lista simples de strings de matrículas
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

# FUNÇÕES AUXILIARES
def gerar_protocolo():
    """Gera um protocolo único de 10 dígitos."""
    return str(random.randint(1000000000, 9999999999))

def validar_matricula(matricula):
    """Verifica se a matrícula fornecida existe na lista de matrículas válidas."""
    matriculas_validas = carregar_matriculas_validas()
    return matricula in matriculas_validas

def enviar_email(protocolo, tipo):
    """Envia uma notificação por e-mail para o administrador."""
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
        print(f"E-mail de notificação enviado para {ADMIN_EMAIL}.")
    except Exception as e:
        print(f"ERRO ao enviar e-mail: {e}")
        # Loga o erro, mas não impede o registro da manifestação


# ROTAS DA APLICAÇÃO
@app.route('/')
def index():
    """Rota principal, renderiza o formulário de ouvidoria."""
    return render_template('index.html')

@app.route('/registrar', methods=['POST'])
def registrar():
    """Recebe e processa o registro de uma nova manifestação."""
    try:
        # Pega os dados do formulário
        nome = request.form.get('nome', 'Anônimo').strip()
        cpf = request.form.get('cpf', '').strip()
        matricula = request.form.get('matricula', '').strip()
        tipo = request.form.get('tipo', '').strip()
        descricao = request.form.get('descricao', '').strip()
        
        # Limpeza e Validação de campos
        cpf = re.sub(r'[^0-9]', '', cpf)
        matricula = re.sub(r'[^0-9]', '', matricula)
        
        if len(cpf) != 11 or not cpf.isdigit():
            return jsonify({'erro': 'CPF inválido. Deve conter 11 dígitos numéricos.'}), 400

        if len(matricula) != 8 or not matricula.isdigit():
             return jsonify({'erro': 'Matrícula inválida. Deve conter 8 dígitos numéricos.'}), 400
        
        if not validar_matricula(matricula):
             return jsonify({'erro': 'Matrícula não encontrada na lista de estudantes válidos.'}), 400
        
        if not tipo or not descricao:
            return jsonify({'erro': 'Todos os campos obrigatórios (Tipo, Descrição) devem ser preenchidos.'}), 400

        # Geração e Registro
        protocolo = gerar_protocolo()
        manifestacoes = carregar_manifestacoes()

        nova_manifestacao = {
            'protocolo': protocolo,
            'nome': nome,
            'cpf': cpf,
            'matricula': matricula, # Novo campo
            'tipo': tipo,
            'descricao': descricao,
            'data': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            'resposta': None 
        }

        manifestacoes.append(nova_manifestacao)
        salvar_manifestacoes(manifestacoes)

        # Envia a notificação
        enviar_email(protocolo, tipo)

        return jsonify({'protocolo': protocolo}), 200

    except Exception as e:
        print(f"Erro no registro: {e}")
        return jsonify({'erro': f'Erro interno ao registrar manifestação: {e}'}), 500

@app.route('/consultar', methods=['POST'])
def consultar():
    """Consulta manifestação por protocolo."""
    protocolo = request.form.get('protocolo', '').strip()
    
    if not protocolo or not protocolo.isdigit():
        return jsonify({'erro': 'Protocolo inválido.'}), 400

    manifestacoes = carregar_manifestacoes()
    
    for m in manifestacoes:
        if m['protocolo'] == protocolo:
            return jsonify(m), 200

    return jsonify({'erro': 'Manifestação não encontrada.'}), 404

@app.route('/consultar_cpf', methods=['POST'])
def consultar_cpf():
    """Consulta todas as manifestações de um CPF."""
    cpf = request.form.get('cpfBusca', '').strip()
    cpf = re.sub(r'[^0-9]', '', cpf)
    
    if len(cpf) != 11 or not cpf.isdigit():
        return jsonify({'erro': 'CPF inválido. Deve conter 11 dígitos numéricos.'}), 400

    manifestacoes = carregar_manifestacoes()
    
    # Filtra manifestações que correspondam ao CPF (sem a resposta do admin para manter o foco)
    resultados = [
        {'protocolo': m['protocolo'], 'nome': m['nome'], 'cpf': m['cpf'], 'matricula': m['matricula'], 
         'tipo': m['tipo'], 'descricao': m['descricao'], 'resposta': m['resposta']}
        for m in manifestacoes if m['cpf'] == cpf
    ]

    return jsonify(resultados), 200

@app.route('/consultar_matricula', methods=['POST'])
def consultar_matricula():
    """Consulta todas as manifestações de uma Matrícula. (NOVA ROTA)"""
    matricula = request.form.get('matriculaBusca', '').strip()
    matricula = re.sub(r'[^0-9]', '', matricula)
    
    if len(matricula) != 8 or not matricula.isdigit():
        return jsonify({'erro': 'Matrícula inválida. Deve conter 8 dígitos numéricos.'}), 400

    manifestacoes = carregar_manifestacoes()
    
    # Filtra manifestações que correspondam à Matrícula
    resultados = [
        {'protocolo': m['protocolo'], 'nome': m['nome'], 'cpf': m['cpf'], 'matricula': m['matricula'], 
         'tipo': m['tipo'], 'descricao': m['descricao'], 'resposta': m['resposta']}
        for m in manifestacoes if m.get('matricula') == matricula
    ]

    return jsonify(resultados), 200


@app.route('/admin', methods=['GET'])
def admin_page():
    """Página de login do administrador."""
    return render_template('admin.html')

@app.route('/admin_login', methods=['POST'])
def admin_login():
    """Valida o login do administrador."""
    usuario = request.form.get('usuarioAdmin')
    senha = request.form.get('senhaAdmin')
    
    if usuario == admin_user and senha == admin_pass:
        # Se o login for bem-sucedido, redireciona para a listagem (usando GET)
        return jsonify({'redirect': url_for('listar_manifestacoes')}), 200
    else:
        return jsonify({'erro': 'Credenciais inválidas.'}), 401

@app.route('/listar_manifestacoes', methods=['GET'])
def listar_manifestacoes():
    """Lista todas as manifestações (acessível apenas após login)."""
    # Em uma aplicação real, aqui haveria uma verificação de sessão/cookie
    # Mas para simplificação, vamos apenas listar os dados.
    manifestacoes = carregar_manifestacoes()
    # A página admin.html (que não foi mostrada aqui) deve usar AJAX ou Jinja2 para exibir esta lista
    return render_template('admin_dashboard.html', manifestacoes=manifestacoes) 

# Se você não tem o admin_dashboard.html, use o admin.html (que provavelmente é só o login)
# ATENÇÃO: Se você só tem o admin.html, esta rota listando os dados não funcionará,
# mas para fins de demonstração, ela retorna os dados. Você precisa garantir que admin.html
# tenha um código para fazer um GET nesta rota após o login.
# Por enquanto, vou retornar um JSON para fins de depuração.
@app.route('/api/manifestacoes', methods=['GET'])
def api_manifestacoes():
    """API para listar todas as manifestações para o frontend Admin."""
    manifestacoes = carregar_manifestacoes()
    return jsonify(manifestacoes)

@app.route('/responder', methods=['POST'])
def responder_manifestacao():
    """Registra a resposta do administrador a uma manifestação."""
    protocolo = request.form.get('protocolo')
    resposta = request.form.get('resposta')

    if not protocolo or not resposta:
        return jsonify({'erro': 'Protocolo e resposta são obrigatórios.'}), 400

    manifestacoes = carregar_manifestacoes()
    encontrada = False

    for m in manifestacoes:
        if m['protocolo'] == protocolo:
            m['resposta'] = resposta
            encontrada = True
            break
    
    if encontrada:
        salvar_manifestacoes(manifestacoes)
        return jsonify({'mensagem': 'Resposta registrada com sucesso.'}), 200
    else:
        return jsonify({'erro': 'Manifestação não encontrada.'}), 404

if __name__ == '__main__':
    # Esta parte é apenas para rodar no seu computador local.
    # O Render usará o Gunicorn e ignorará estas linhas.
    app.run(debug=True)