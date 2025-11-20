import os
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

# --- Importações para Banco de Dados (Firebase Admin SDK) ---
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    
    # Placeholder para inicialização do Firebase
    def initialize_firebase_admin():
        try:
            # Tenta carregar a configuração a partir da variável de ambiente (melhor prática no Render)
            if os.environ.get('FIREBASE_CONFIG_JSON'):
                # O JSON é carregado da variável de ambiente
                config_json = json.loads(os.environ.get('FIREBASE_CONFIG_JSON'))
                cred = credentials.Certificate(config_json)
            else:
                # Se a variável de ambiente não estiver definida, avisa e retorna None
                print("AVISO: Variável de ambiente 'FIREBASE_CONFIG_JSON' não encontrada. Usando credenciais placeholder.")
                return None 

            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)
            
            return firestore.client()
        except Exception as e:
            print(f"ERRO: Falha ao inicializar o Firebase Admin: {e}")
            return None

    db = initialize_firebase_admin()
    if db is None:
        print("Atenção: O Firestore não foi inicializado. Funções de banco de dados estarão desativadas.")

except ImportError:
    print("AVISO: A biblioteca 'firebase-admin' não foi encontrada. Funções de banco de dados estarão desativadas.")
    db = None
except Exception as e:
    print(f"ERRO INESPERADO ao inicializar o Firebase Admin: {e}")
    db = None

# ----------------- CONFIGURAÇÃO DO FLASK -----------------
app = Flask(__name__)
# Permite requisições de qualquer origem para facilitar a comunicação com o frontend
CORS(app) 

# ----------------- FUNÇÃO DE E-MAIL (AGORA É SÓ UM PRINT/PLACEHOLDER) -----------------
def enviar_email_notificacao_placeholder(protocolo: str, tipo: str, descricao: str):
    """
    Função Placeholder que simula o envio de e-mail.
    
    AVISO: ESTA FUNÇÃO NÃO ENVIA E-MAIL DE VERDADE NO RENDER.
    Ela serve apenas para mostrar onde a função de e-mail deve ser chamada.
    Você deve substituí-la pela implementação do SendGrid para que funcione.
    """
    print("--- Tentativa de Envio de E-mail ---")
    print(f"Protocolo: {protocolo}")
    print(f"Tipo: {tipo}")
    print("STATUS: FALHA (Este é um placeholder. Use SendGrid!)")
    print("-------------------------------------")
    return False # Retorna False porque o envio real falhará

# ----------------- ROTAS DO FLASK -----------------

@app.route('/api/manifestacao', methods=['POST'])
def registrar_manifestacao():
    """
    Recebe os dados do frontend, salva no Firestore e tenta enviar o e-mail (placeholder).
    """
    if not request.is_json:
        return jsonify({"message": "Requisição deve ser JSON"}), 400

    data = request.get_json()
    
    # 1. Validação simples dos dados (ajuste conforme seu formulário)
    required_fields = ['tipo', 'descricao', 'nome', 'email', 'telefone']
    for field in required_fields:
        if field not in data:
            return jsonify({"message": f"Campo obrigatório '{field}' faltando."}), 400

    # 2. Geração do Protocolo e Data
    # Formato do Protocolo: UUID + timestamp
    protocolo = f"{uuid.uuid4().hex[:8]}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    data_registro = datetime.now()

    # 3. Preparação dos dados para salvar
    manifestacao_doc = {
        'protocolo': protocolo,
        'tipo': data['tipo'],
        'descricao': data['descricao'],
        'nome': data['nome'],
        'email': data['email'],
        'telefone': data['telefone'],
        'data_registro': data_registro,
        'status': 'Aguardando Análise',
        'resposta': None # Campo para a resposta do administrador
    }

    # 4. Salvamento no Firestore
    salvamento_sucesso = False
    if db:
        try:
            # Salva na coleção 'manifestacoes' usando o protocolo como ID do documento
            doc_ref = db.collection('manifestacoes').document(protocolo)
            doc_ref.set(manifestacao_doc)
            print(f"Manifestação {protocolo} salva no Firestore com sucesso.")
            salvamento_sucesso = True
        except Exception as e:
            print(f"ERRO NO FIRESTORE: Falha ao salvar manifestação: {e}")
            
    # 5. Tentativa de Envio do E-mail (CHAMADA DO PLACEHOLDER)
    email_sucesso = enviar_email_notificacao_placeholder(
        protocolo=protocolo, 
        tipo=manifestacao_doc['tipo'], 
        descricao=manifestacao_doc['descricao']
    )

    # 6. Resposta ao Cliente
    if salvamento_sucesso:
        response_payload = {
            "message": "Manifestação registrada. E-mail de notificação não pôde ser enviado (Implementação SendGrid pendente).",
            "protocolo": protocolo,
            "email_status": "pendente"
        }
        return jsonify(response_payload), 201
    else:
        return jsonify({"message": "Erro interno ao registrar manifestação (Falha no banco de dados)."}), 500

@app.route('/', methods=['GET'])
def home():
    """ Rota de boas-vindas para verificar se o servidor está ativo. """
    return jsonify({"message": "API de Ouvidoria CETEP está rodando! (Versão sem SendGrid)", "status": "OK"}), 200

# Esta rota é um placeholder, você precisa implementar a lógica de listagem no Firestore
@app.route('/api/manifestacoes', methods=['GET'])
def get_manifestacoes():
    """ Retorna a lista de manifestações (PLACEHOLDER). """
    if db:
        try:
            # Lógica para buscar todas as manifestações
            manifestacoes_ref = db.collection('manifestacoes')
            docs = manifestacoes_ref.stream()
            lista_manifestacoes = [doc.to_dict() for doc in docs]
            
            return jsonify(lista_manifestacoes), 200
        except Exception as e:
             return jsonify({"error": f"Erro ao buscar manifestações: {e}"}), 500
    
    # Retorna dados mockados se o DB falhar
    return jsonify([
        {
            "protocolo": "MOCK-001", "tipo": "Denúncia", "descricao": "Manifestação de Teste 1.",
            "data": "2025-11-20", "nome": "Mock User", "cpf": "111.111.111-11", "matricula": "12345",
            "resposta": None, "status": "Pendente"
        }
    ]), 200

# Esta rota é um placeholder, você precisa implementar a lógica de atualização no Firestore
@app.route('/responder', methods=['POST'])
def responder_manifestacao():
    """ Atualiza a manifestação com uma resposta do administrador (PLACEHOLDER). """
    protocolo = request.form.get('protocolo')
    resposta = request.form.get('resposta')
    
    if not protocolo or not resposta:
        return jsonify({"erro": "Dados incompletos."}), 400

    if db:
        try:
            doc_ref = db.collection('manifestacoes').document(protocolo)
            doc_ref.update({
                'resposta': resposta,
                'status': 'Respondida'
            })
            return jsonify({"mensagem": f"Manifestação {protocolo} respondida com sucesso no Firestore."})
        except Exception as e:
            return jsonify({"erro": f"Erro ao atualizar Firestore: {e}"}), 500
            
    return jsonify({"mensagem": f"Manifestação {protocolo} atualizada localmente (DB desligado)."}), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
