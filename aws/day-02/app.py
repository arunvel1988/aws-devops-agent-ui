
from flask import Flask, render_template, request, jsonify

from agent.core import run_agent


app = Flask(__name__)


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


# --------------------------------------------------
# CHAT API
# --------------------------------------------------

@app.route("/chat", methods=["POST"])
def chat():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Invalid request"
        }), 400

    message = data.get("message", "").strip()

    if not message:
        return jsonify({
            "error": "Message cannot be empty"
        }), 400

    try:

        # For now we use one session.
        # Later we will give every student
        # a separate session ID.

        answer = run_agent(
            message,
            session_id="default"
        )

        return jsonify({
            "answer": answer
        })

    except Exception as e:

        print("ERROR:", e)

        return jsonify({
            "error": str(e)
        }), 500


# --------------------------------------------------
# START FLASK
# --------------------------------------------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
