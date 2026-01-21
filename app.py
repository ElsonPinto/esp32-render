from flask import Flask, request, jsonify, render_template
import sqlite3
import os

app = Flask(__name__)

# ===============================
# VARIÁVEIS GLOBAIS
# ===============================
estado_led = "off"
mensagem = "Nenhuma mensagem"

# ===============================
# BANCO DE DADOS
# ===============================
def conectar_db():
    conn = sqlite3.connect("dados.db")
    conn.row_factory = sqlite3.Row
    return conn

def criar_tabela():
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dispositivo_id TEXT,
            umidade REAL,
            temperatura REAL,
            data TEXT,
            hora TEXT
        )
    """)

    conn.commit()
    conn.close()

# ===============================
# PÁGINA PRINCIPAL
# ===============================
@app.route("/")
def index():
    return f"""
    <h1>Controle ESP32</h1>

    <h2>LED: {estado_led}</h2>

    <form action="/comando" method="post">
        <button name="led" value="on">Ligar LED</button>
        <button name="led" value="off">Desligar LED</button>
    </form>

    <form action="/mensagem" method="post">
        <input name="msg" placeholder="Mensagem para o ESP32">
        <button>Enviar Mensagem</button>
    </form>
    """

# ===============================
# COMANDO LED
# ===============================
@app.route("/comando", methods=["POST"])
def comando():
    global estado_led
    estado_led = request.form.get("led") or request.json.get("led")
    return jsonify({"status": "ok", "led": estado_led})

# ===============================
# ENVIAR MENSAGEM
# ===============================
@app.route("/mensagem", methods=["POST"])
def set_mensagem():
    global mensagem
    mensagem = request.form.get("msg") or request.json.get("msg")
    return jsonify({"mensagem": mensagem})

# ===============================
# ESP32 CONSULTA
# ===============================
@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "led": estado_led,
        "mensagem": mensagem
    })

# ===============================
# ESP32 ENVIA DADOS
# ===============================
@app.route("/api/esp32", methods=["POST"])
def receber_esp32():
    dados = request.get_json()

    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO registros (dispositivo_id, umidade, temperatura, data, hora)
        VALUES (?, ?, ?, ?, ?)
    """, (
        dados.get("dispositivo_id"),
        dados.get("umidade"),
        dados.get("temperatura"),
        dados.get("data"),
        dados.get("hora")
    ))

    conn.commit()
    conn.close()

    return jsonify({"status": "dados salvos"})

# ===============================
# VER DADOS NO NAVEGADOR
# ===============================
@app.route("/api/registros", methods=["GET"])
def listar():
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM registros ORDER BY id DESC")
    rows = cursor.fetchall()

    conn.close()
    return jsonify([dict(r) for r in rows])

# ===============================
# START
# ===============================
if __name__ == "__main__":
    criar_tabela()
    app.run(host="0.0.0.0", port=5000, debug=True)
