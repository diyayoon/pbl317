from app import buat_app

app = buat_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
