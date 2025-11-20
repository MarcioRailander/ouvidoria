import os
import json
import uuid
import resend
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# ------------------------------------------------------------
# CONFIGURAÇÃO DO RESEND
# ------------------------------------------------------------
RESEND_API_KEY = "re_5mGfRMW7_FD7dFfhmgSfs6JR9srXg2jjB"
resend.api_key = RESEND_API_KEY

# E-mail que vai receber as manifestações
ADMIN_EMAIL = "cetepouvidoria6@gmail.com"


# ------------------------------------------------------------
# Função para enviar e-mail usando Resend
# ------------------------------------------------------------
def enviar_email(protocolo, tipo):
    try:
        resend.Emails.send(
            {
                "from": "Ouvidoria <ouvidoria@seuloja.com>",
                "to": ADMIN_EMAIL,
                "subject": f"Nova manifestação recebida - Protocolo {protocolo}",
                "html": f"""
                    <h2>Nova manifestação recebida</h2>
                    <p><b>Tipo:</b> {tipo}</p>
                    <p><b>Protocolo:</b> {protocolo}</p>
                    <p>Verifique o painel administrativo para mais detalhes.</p>
                """
            }
        )
        print("E-mail enviado com sucesso via Resend.")
        return True

    except Exception as e:
        print("Erro ao enviar e-mail:", e)
        return False


# ------------------------------------------------------------
# PÁGINA PRINCIPAL
# ------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')


# ------------------------------------------------------------
# CONSULTAR PROTOCOLO
# ------------------------------------------------------------
@app.route('/consultar', methods=['GET'])
def consultar():
    protocolo = request.args.get('protocolo', '').strip()

    if not os.path.exists('manifestacoes.json'):
        return jsonify({"erro": "Nenhuma manifestação registrada ainda."})

    with open('manifestacoes.json', 'r', encoding='utf-8') as arquivo:
        dados = json.load(arquivo)

    if protocolo in dados:
        return jsonify(dados[protocolo])

    return jsonify({"erro": "Protocolo não encontrado."})


# ------------------------------------------------------------
# REGISTRAR MANIFESTAÇÃO
# ------------------------------------------------------------
@app.route('/registrar', methods=['POST'])
def registrar():
    nome = request.form.get('nome')
    email = request.form.get('email')
    tipo = request.form.get('tipo')
    descricao = request.form.get('descricao')

    protocolo = str(uuid.uuid4())[:8]

    nova_manifestacao = {
        "nome": nome,
        "email": email,
        "tipo": tipo,
        "descricao": descricao,
        "protocolo": protocolo
    }

    if os.path.exists('manifestacoes.json'):
        with open('manifestacoes.json', 'r', encoding='utf-8') as arquivo:
            dados = json.load(arquivo)
    else:
        dados = {}

    dados[protocolo] = nova_manifestacao

    with open('manifestacoes.json', 'w', encoding='utf-8') as arquivo:
        json.dump(dados, arquivo, indent=4, ensure_ascii=False)

    enviar_email(protocolo, tipo)

    return jsonify({"mensagem": "Manifestação registrada com sucesso!", "protocolo": protocolo})


# ------------------------------------------------------------
# EXECUTAR APP
# ------------------------------------------------------------
if __name__ == '__main__':
    if not os.path.exists('templates'):
        os.makedirs('templates')
    app.run(debug=True)
