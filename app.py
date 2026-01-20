from flask import Flask, request, jsonify, render_template
import os

app = Flask(__name__)

estado_led = "off"

@app.route("/")
def index():
    return render_template("index.html", led=estado_led)

@app.route("/comando", methods=["POST"])
def comando():
    global estado_led
    dados = request.json
    estado_led = dados.get("led", "off")
    return jsonify({"status": "ok"})

@app.route("/status")
def status():
    return jsonify({"led": estado_led})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
