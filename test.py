from flask import Flask, redirect, url_for

app= Flask(__name__)


@app.route("/")
def home():
    return "Helloooooooo ini main page <h1>WOII<h1> "


@app.route("/<name>")
def user(name):
    return f"Hellloooo {name}!"

@app.route("/admin")
def admin():
    return redirect(url_for("user"))



if __name__ == "__main__":
    app.run()