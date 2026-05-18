from app import create_app


print("Starte app..")
app = create_app()
print("App gestartet.")
if __name__ == "__main__":
    app.run(debug=True, port=5002)