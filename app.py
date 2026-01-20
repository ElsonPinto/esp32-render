from flask import Flask, request, jsonify, render_template
import os

# ===============================
# CRIA O SERVIDOR FLASK
# ===============================
app = Flask(__name__)

# ===============================
# VARIÁVEIS GLOBAIS (ESTADO)
# ===============================
estado_led = "off"                 # on / off
mensagem = "Nenhuma mensagem"      # texto para o ESP32

# ===============================
# ROTA PRINCIPAL - PÁGINA WEB
# ===============================
@app.route("/")
def index():
    return render_template(
        "index.html",
        led=estado_led,
        msg=mensagem
    )

# ===============================
# ROTA PARA CONTROLAR O LED
# ===============================
@app.route("/comando", methods=["POST"])
def comando():
    global estado_led
    dados = request.json

    # Atualiza o estado do LED
    estado_led = dados.get("led", "off")

    return jsonify({"status": "ok", "led": estado_led})

# ===============================
# ROTA PARA ENVIAR MENSAGEM
# ===============================
@app.route("/mensagem", methods=["POST"])
def set_mensagem():
    global mensagem
    dados = request.json

    # Atualiza a mensagem
    mensagem = dados.get("msg", "")

    return jsonify({"status": "mensagem recebida", "mensagem": mensagem})

# ===============================
# ROTA PARA O ESP32 CONSULTAR
# ===============================
@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "led": estado_led,
        "mensagem": mensagem
    })

# ===============================
# INICIALIZAÇÃO DO SERVIDOR
# ===============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
