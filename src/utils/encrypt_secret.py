# Hilfsskript zum Verschlüsseln von Passwörtern für .env
# Ausführen: python encrypt_secret.py <klartext-passwort>
import sys
from cryptography.fernet import Fernet  # type: ignore[import]

from shared_modules.config import Config


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

    # FERNET_KEY aus der Config laden oder neu erzeugen
    config = Config()
    fernet_key = config.get_secret("FERNET_KEY")
    if not fernet_key:
        fernet_key = Fernet.generate_key().decode()
        print("\nKein FERNET_KEY in der Konfiguration/.env gefunden.")
        print("Ein neuer Schlüssel wurde generiert:")
        print(f"FERNET_KEY={fernet_key}")
        print("Bitte diesen Schlüssel in deiner .env oder Konfiguration eintragen und das Skript erneut ausführen.\n")
        sys.exit(1)

    f = Fernet(fernet_key.encode())
    encrypted = f.encrypt(password_bytes)
    print(f"Verschlüsseltes Passwort für .env: {encrypted.decode()}")

if __name__ == "__main__":
    main()