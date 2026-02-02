from flask import Flask, request, jsonify, render_template, Response
import sqlite3
import os

app = Flask(__name__)

# =========================
# Variáveis globais
# =========================
estado_led = "off"
mensagem = ""
linha_pendente = None          # edição pendente do cartão SD
requisitar_horarios = False   # NOVO: servidor pede leitura do SD

# =========================
# Banco de dados
# =========================
DB_FILE = "dados.db"

def conectar_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def criar_tabela_registros():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_pacote INTEGER,
            fazenda TEXT,
            dispositivo_id TEXT,
            temperatura REAL,
            u1 REAL,
            u2 REAL,
            u3 REAL,
            u4 REAL,
            u5 REAL,
            fruto TEXT,
            data TEXT,
            hora TEXT,
            ip_local TEXT,
            mac TEXT
        )
    """)
    conn.commit()
    conn.close()

def criar_tabela_horarios():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS horarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            linha INTEGER,
            hora_ligar TEXT,
            hora_desligar TEXT,
            dias TEXT
        )
    """)
    conn.commit()
    conn.close()

# =========================
# Rotas principais
# =========================
@app.route("/")
def index():
    return render_template("index.html")

# =========================
# LED
# =========================
@app.route("/comando", methods=["POST"])
def comando():
    global estado_led
    data = request.get_json() or request.form
    estado_led = data.get("led", estado_led)
    return jsonify({"status": "ok", "led": estado_led})

# =========================
# Mensagem
# =========================
@app.route("/mensagem", methods=["POST"])
def set_mensagem():
    global mensagem
    data = request.get_json() or request.form
    mensagem = data.get("msg", "")
    return jsonify({"mensagem": mensagem})

@app.route("/status", methods=["GET"])
def status():
    global mensagem
    msg = mensagem
    mensagem = ""
    return jsonify({
        "led": estado_led,
        "mensagem": msg
    })

# =========================
# Receber dados do ESP32
# =========================
@app.route("/api/esp32", methods=["POST"])
def receber_esp32():
    dados = request.get_json()

    try:
        criar_tabela_registros()
        conn = conectar_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO registros (
                numero_pacote, fazenda, dispositivo_id, temperatura,
                u1, u2, u3, u4, u5, fruto, data, hora,
                ip_local, mac
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dados.get("numero_pacote"),
            dados.get("fazenda"),
            dados.get("dispositivo_id"),
            dados.get("temperatura"),
            dados.get("u1"),
            dados.get("u2"),
            dados.get("u3"),
            dados.get("u4"),
            dados.get("u5"),
            dados.get("fruto"),
            dados.get("data"),
            dados.get("hora"),
            dados.get("ip_local"),
            dados.get("mac")
        ))

        conn.commit()
        conn.close()

        return jsonify({"status": "dados salvos com sucesso"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================
# Listar registros
# =========================
@app.route("/api/registros", methods=["GET"])
def listar_registros():
    criar_tabela_registros()
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM registros ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# =========================
# Exportar TXT
# =========================
@app.route("/api/registros/txt", methods=["GET"])
def baixar_registros_txt():
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id, numero_pacote, fazenda, dispositivo_id, temperatura,
            u1, u2, u3, u4, u5, fruto, data, hora, ip_local, mac
        FROM registros
        ORDER BY id ASC
    """)

    rows = cursor.fetchall()
    conn.close()

    linhas = []
    cabecalho = [
        "id", "numero_pacote", "fazenda", "dispositivo_id", "temperatura",
        "u1", "u2", "u3", "u4", "u5", "fruto",
        "data", "hora", "ip_local", "mac"
    ]
    linhas.append("\t".join(cabecalho))

    for r in rows:
        linhas.append("\t".join([
            str(r["id"]),
            str(r["numero_pacote"]),
            r["fazenda"] or "",
            r["dispositivo_id"] or "",
            str(r["temperatura"]),
            str(r["u1"]),
            str(r["u2"]),
            str(r["u3"]),
            str(r["u4"]),
            str(r["u5"]),
            r["fruto"] or "",
            r["data"] or "",
            r["hora"] or "",
            r["ip_local"] or "",
            r["mac"] or ""
        ]))

    return Response(
        "\n".join(linhas),
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment; filename=registros_esp32.txt"}
    )

# =========================
# Cartão SD – editar horário
# =========================
@app.route("/api/horarios/editar", methods=["POST"])
def editar_horario():
    global linha_pendente
    data = request.get_json()

    linha_pendente = data
    return jsonify({"status": "ok", "mensagem": "Alteração enviada ao ESP32"})

# =========================
# NOVO — Servidor requisita leitura do SD
# =========================
@app.route("/api/horarios/requisitar", methods=["POST"])
def requisitar_horarios_sd():
    global requisitar_horarios
    requisitar_horarios = True
    return jsonify({"status": "pedido_enviado"})

# =========================
# ESP32 consulta servidor
# =========================
@app.route("/api/horarios/pull", methods=["GET"])
def pull_horarios():
    global linha_pendente, requisitar_horarios

    # prioridade: edição de horário
    if linha_pendente is not None:
        dados = linha_pendente
        linha_pendente = None
        return jsonify({"status": "editar", "dados": dados})

    # pedido de leitura do SD
    if requisitar_horarios:
        requisitar_horarios = False
        return jsonify({"status": "enviar"})

    return jsonify({"status": "nada"})

# =========================
# Receber horários do SD
# =========================
@app.route("/api/horarios/salvar", methods=["POST"])
def salvar_horarios():
    dados = request.get_json()

    criar_tabela_horarios()
    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM horarios")

    for h in dados.get("horarios", []):
        cursor.execute("""
            INSERT INTO horarios (linha, hora_ligar, hora_desligar, dias)
            VALUES (?, ?, ?, ?)
        """, (
            h["linha"],
            h["hora_ligar"],
            h["hora_desligar"],
            ",".join(map(str, h["dias"]))
        ))

    conn.commit()
    conn.close()

    return jsonify({"status": "horarios salvos no banco"})

# =========================
# Listar horários
# =========================
@app.route("/api/horarios", methods=["GET"])
def listar_horarios():
    criar_tabela_horarios()
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM horarios ORDER BY linha ASC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# =========================
# Start
# =========================
criar_tabela_registros()
criar_tabela_horarios()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
