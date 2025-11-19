import os
import json
import time
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mail import Mail, Message

# --- Configurações Iniciais ---
# 
# 1. Tenta carregar variáveis de ambiente (ENV) que o Render fornece.
# 2. Se não estiver no Render, carrega o .env localmente (para desenvolvimento).
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)

# --- Configuração de Segurança e Admin ---
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key_nao_usar_em_prod') 
ADMIN_USER = os.getenv('FLASK_ADMIN_USER', 'admin')
ADMIN_PASS = os.getenv('FLASK_ADMIN_PASS', '1234')

# --- Funções de Leitura e Escrita de Dados (Arquivos JSON) ---

def carregar_dados(filename):
    """Carrega dados de um arquivo JSON. Se o arquivo não existir, retorna uma lista vazia."""
    # O Render tem um sistema de arquivos efêmero.
    # Se o arquivo não estiver no repositório, ele não será encontrado no Render.
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Para evitar erros no Render se o arquivo não tiver sido enviado.
        if filename == 'manifestacoes.json':
            return [] # Lista vazia para manifestações se não houver arquivo.
        if filename == 'matriculas.json':
            return [] # Lista vazia para matrículas se não houver arquivo.
        return {} # Objeto vazio como fallback.
    except json.JSONDecodeError:
        return []

def salvar_manifestacao(manifestacoes):
    """Salva a lista de manifestações no arquivo JSON."""
    # Aviso: No Render, o conteúdo deste arquivo será perdido após o servidor "dormir"
    # ou após um novo deploy, pois não estamos usando um Banco de Dados.
    try:
        with open('manifestacoes.json', 'w', encoding='utf-8') as f:
            json.dump(manifestacoes, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Erro ao salvar manifestação: {e}")
        return False

# --- Configuração de Email (CORREÇÃO CRÍTICA PARA O RENDER/GMAIL) ---
# Usamos o SSL explícito na porta 465, que é mais estável em ambientes de nuvem.
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT')) # Deve ser '465'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_SSL'] = True    # <--- NOVO: Ativa SSL explícito para a porta 465
app.config['MAIL_USE_TLS'] = False   # <--- NOVO: Desativa o TLS (que causava o timeout)

mail = Mail(app)

# --- Funções de Suporte ---

def validar_matricula(matricula):
    """Verifica se a matrícula está na lista de matrículas válidas."""
    matriculas_validas = carregar_dados('matriculas.json')
    # O arquivo matriculas.json DEVE conter uma lista de strings. Ex: ["12345", "67890"]
    if matricula in matriculas_validas:
        return True
    return False

def enviar_email(protocolo, tipo_manifestacao):
    """Envia email de confirmação para o administrador."""
    try:
        msg = Message(
            f'Nova Manifestação Registrada (Protocolo: {protocolo})',
            sender=app.config['MAIL_USERNAME'],
            recipients=[app.config['MAIL_USERNAME']] # Envia para o próprio e-mail do sistema
        )
        msg.body = (
            f"Uma nova manifestação foi registrada no sistema de ouvidoria.\n\n"
            f"Protocolo: {protocolo}\n"
            f"Tipo: {tipo_manifestacao}\n\n"
            f"Por favor, acesse o painel de administração para visualizá-la e responder."
        )
        mail.send(msg)
        print(f"Email de protocolo {protocolo} enviado com sucesso!")
        return True
    except Exception as e:
        # CRÍTICO: Imprime o erro no log para debug (agora veremos o erro real do SMTP)
        print(f"ERRO AO ENVIAR EMAIL: {e}") 
        return False

# --- Rotas da Aplicação ---

@app.route('/')
def index():
    """Página inicial da ouvidoria com formulário de registro."""
    return render_template('index.html')

@app.route('/registrar', methods=['POST'])
def registrar():
    """Recebe e processa o formulário de manifestação."""
    
    # 1. Coleta e sanitiza os dados do formulário
    nome = request.form.get('nome').strip()
    matricula = request.form.get('matricula').strip()
    email = request.form.get('email').strip()
    tipo = request.form.get('tipo')
    descricao = request.form.get('descricao').strip()
    
    # 2. Validação de Matrícula
    if not validar_matricula(matricula):
        flash('Erro: Matrícula inválida ou não encontrada. Por favor, verifique.', 'error')
        return redirect(url_for('index'))

    # 3. Geração de Protocolo
    protocolo = f"CETEP-{int(time.time())}" # Protocolo baseado no timestamp

    # 4. Criação do Objeto Manifestação
    nova_manifestacao = {
        'protocolo': protocolo,
        'nome': nome,
        'matricula': matricula,
        'email': email,
        'tipo': tipo,
        'descricao': descricao,
        'data': time.strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'Pendente',
        'resposta': 'Aguardando análise da administração.',
    }

    # 5. Carrega, Adiciona e Salva
    manifestacoes = carregar_dados('manifestacoes.json')
    manifestacoes.append(nova_manifestacao)
    
    if salvar_manifestacao(manifestacoes):
        # 6. Envio de Email (AGORA COM SSL CORRIGIDO)
        if enviar_email(protocolo, tipo):
            flash(f'Manifestação registrada com sucesso! Seu protocolo é: {protocolo}', 'success')
        else:
            flash(f'Manifestação registrada (Protocolo: {protocolo}), mas houve um erro ao enviar a notificação por email.', 'warning')
    else:
        flash('Erro interno ao salvar a manifestação. Tente novamente mais tarde.', 'error')
        
    return redirect(url_for('index'))

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    """Página de login administrativo."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USER and password == ADMIN_PASS:
            # Em uma aplicação real, aqui você usaria sessões para manter o login.
            # Usaremos um redirecionamento simples para o propósito desta demonstração.
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Usuário ou senha inválidos.', 'error')
            
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    """Painel de administração (após login)."""
    # Em uma aplicação real, você faria a checagem de sessão aqui.
    manifestacoes = carregar_dados('manifestacoes.json')
    # Ordena as manifestações, as mais recentes primeiro (opcional)
    manifestacoes.sort(key=lambda x: x.get('data', ''), reverse=True)
    return render_template('admin_dashboard.html', manifestacoes=manifestacoes)

@app.route('/admin/responder/<protocolo>', methods=['POST'])
def admin_responder(protocolo):
    """Recebe a resposta do administrador e atualiza a manifestação."""
    nova_resposta = request.form.get('resposta').strip()
    
    manifestacoes = carregar_dados('manifestacoes.json')
    
    for man in manifestacoes:
        if man['protocolo'] == protocolo:
            man['resposta'] = nova_resposta
            man['status'] = 'Respondida'
            break
    
    if salvar_manifestacao(manifestacoes):
        flash(f'Manifestação {protocolo} respondida com sucesso!', 'success')
    else:
        flash('Erro ao salvar a resposta no arquivo.', 'error')
        
    return redirect(url_for('admin_dashboard'))

# --- Início da Aplicação ---
if __name__ == '__main__':
    # Esta parte só roda no ambiente local (não no Render/Gunicorn)
    print("Atenção: Rodando localmente. Use 'gunicorn app:app' para produção.")
    app.run(debug=True)
