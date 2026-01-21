from flask import Flask, request, jsonify, render_template
import os
import sqlite3

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
# FUNÇÃO PARA CONECTAR AO BANCO
# ===============================
def conectar_db():
    conn = sqlite3.connect("dados.db")
    conn.row_factory = sqlite3.Row
    return conn

# ===============================
# CRIAR TABELA AUTOMATICAMENTE
# ===============================
def criar_tabela():
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fazenda_id TEXT,
            dispositivo_id TEXT,
            pacote_id TEXT,
            ip TEXT,
            mac TEXT,
            umidade_1 REAL,
            umidade_2 REAL,
            umidade_3 REAL,
            umidade_4 REAL,
            umidade_5 REAL,
            temperatura REAL,
            fruto TEXT,
            data TEXT,
            hora TEXT
        )
    """)

    conn.commit()
    conn.close()

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
    estado_led = dados.get("led", "off")
    return jsonify({"status": "ok", "led": estado_led})

# ===============================
# ROTA PARA ENVIAR MENSAGEM
# ===============================
@app.route("/mensagem", methods=["POST"])
def set_mensagem():
    global mensagem
    dados = request.json
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
# ROTA PARA RECEBER DADOS DO ESP32
# ===============================
@app.route("/api/esp32", methods=["POST"])
def receber_esp32():
    recebido = request.json

    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO registros (
            fazenda_id, dispositivo_id, pacote_id, ip, mac,
            umidade_1, umidade_2, umidade_3, umidade_4, umidade_5,
            temperatura, fruto, data, hora
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        recebido.get("fazenda_id"),
        recebido.get("dispositivo_id"),
        recebido.get("pacote_id"),
        recebido.get("ip"),
        recebido.get("mac"),
        recebido.get("umidade_1"),
        recebido.get("umidade_2"),
        recebido.get("umidade_3"),
        recebido.get("umidade_4"),
        recebido.get("umidade_5"),
        recebido.get("temperatura"),
        recebido.get("fruto"),
        recebido.get("data"),
        recebido.get("hora")
    ))

    conn.commit()
    conn.close()

    return jsonify({"status": "dados salvos no banco"})

# ===============================
# ROTA PARA VER HISTÓRICO
# ===============================
@app.route("/api/registros", methods=["GET"])
def listar_registros():
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM registros ORDER BY id DESC")
    rows = cursor.fetchall()

    conn.close()

    return jsonify([dict(row) for row in rows])

# ===============================
# INICIALIZAÇÃO DO SERVIDOR
# ===============================
if __name__ == "__main__":
    criar_tabela()  # garante que o banco exista
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
