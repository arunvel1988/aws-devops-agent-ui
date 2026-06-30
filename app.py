from flask import Flask, request, jsonify, render_template
from rag import ask  # Importing the 'ask' function from rag.py

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message")
    answer = ask(user_message)  # Call the function from rag.py
    return jsonify({"response": answer})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
