# Hilfsskript zum Verschlüsseln von Passwörtern für .env
# Ausführen: python encrypt_secret.py <klartext-passwort>
import sys

from cryptography.fernet import Fernet  # type: ignore[import]  


def main():
    if len(sys.argv) == 2:
        password = sys.argv[1]
    else:
        # Interaktive Abfrage, falls kein Argument übergeben wurde (z. B. VSCode Run/Debug)
        import getpass
        print("Kein Passwort als Argument übergeben.")
        password = getpass.getpass("Bitte Passwort eingeben (wird nicht angezeigt): ")
        if not password:
            print("Kein Passwort eingegeben. Abbruch.")
            sys.exit(1)

    password_bytes = password.encode()
    # Schlüssel generieren und anzeigen (nur einmal erzeugen und dann sicher speichern!)
    key = Fernet.generate_key()
    print(f"Dein geheimer Schlüssel (FERNET_KEY): {key.decode()}")
    f = Fernet(key)
    encrypted = f.encrypt(password_bytes)
    print(f"Verschlüsseltes Passwort für .env: {encrypted.decode()}")

if __name__ == "__main__":
    main()