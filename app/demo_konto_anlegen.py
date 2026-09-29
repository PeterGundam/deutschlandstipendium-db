from pathlib import Path
from getpass import getpass
import base64
import hashlib
import os
import secrets

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv


PROJEKTORDNER = Path(__file__).resolve().parent.parent
load_dotenv(PROJEKTORDNER / ".env")


def passwort_hash_erstellen(passwort: str) -> str:
    salt = secrets.token_bytes(16)
    n, r, p = 2**14, 8, 1

    ergebnis = hashlib.scrypt(
        passwort.encode("utf-8"),
        salt=salt,
        n=n,
        r=r,
        p=p,
        dklen=64,
        maxmem=64 * 1024 * 1024,
    )

    salt_text = base64.b64encode(salt).decode("ascii")
    hash_text = base64.b64encode(ergebnis).decode("ascii")
    return f"scrypt${n}${r}${p}${salt_text}${hash_text}"


def main() -> None:
    passwort_db = os.getenv("DB_PASSWORD")
    if not passwort_db:
        raise RuntimeError("DB_PASSWORD fehlt in der lokalen .env-Datei.")

    with psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "stipendium_db"),
        user=os.getenv("DB_USER", "stipendium_user"),
        password=passwort_db,
    ) as verbindung:
        with verbindung.cursor(row_factory=dict_row) as cursor:
            cursor.execute("""
                SELECT
                    p.personen_id,
                    p.vorname,
                    p.nachname,
                    s.email AS studierenden_email,
                    (s.personen_id IS NOT NULL) AS ist_studierender,
                    (k.personen_id IS NOT NULL) AS ist_kommissionsmitglied
                FROM person p
                LEFT JOIN studierender s ON s.personen_id = p.personen_id
                LEFT JOIN kommissionsmitglied k ON k.personen_id = p.personen_id
                WHERE s.personen_id IS NOT NULL
                   OR k.personen_id IS NOT NULL
                ORDER BY p.personen_id
            """)
            personen = cursor.fetchall()

            print("\nVorhandene Personen:")
            for person in personen:
                rolle = (
                    "Studierende/r" if person["ist_studierender"]
                    else "Kommissionsmitglied"
                )
                print(
                    f"  ID {person['personen_id']}: "
                    f"{person['vorname']} {person['nachname']} ({rolle})"
                )

            try:
                personen_id = int(input("\nPersonen-ID für neues Konto: "))
            except ValueError:
                print("Bitte eine gültige Zahl eingeben.")
                return

            person = next(
                (p for p in personen if p["personen_id"] == personen_id),
                None,
            )
            if person is None:
                print("Diese Personen-ID steht nicht in der Liste.")
                return

            # Für dieses Projekt sollen die beiden Rollen getrennt bleiben.
            if (
                person["ist_studierender"]
                == person["ist_kommissionsmitglied"]
            ):
                print("Person hat keine eindeutige Rolle. Konto nicht angelegt.")
                return

            cursor.execute(
                "SELECT 1 FROM login_konto WHERE personen_id = %s",
                (personen_id,),
            )
            if cursor.fetchone():
                print("Für diese Person existiert bereits ein Login-Konto.")
                return

            if person["ist_studierender"]:
                email = person["studierenden_email"].strip().lower()
                print(f"Login-E-Mail: {email}")
            else:
                email = input(
                    "Login-E-Mail des Kommissionsmitglieds: "
                ).strip().lower()
                if not email or "@" not in email:
                    print("Bitte eine gültige Login-E-Mail eingeben.")
                    return

            passwort = getpass("Neues Demo-Passwort (mindestens 12 Zeichen): ")
            bestaetigung = getpass("Passwort wiederholen: ")

            if len(passwort) < 12:
                print("Passwort ist zu kurz. Konto nicht angelegt.")
                return
            if passwort != bestaetigung:
                print("Passwörter stimmen nicht überein.")
                return

            cursor.execute(
                """
                INSERT INTO login_konto (personen_id, email, passwort_hash)
                VALUES (%s, %s, %s)
                """,
                (personen_id, email, passwort_hash_erstellen(passwort)),
            )

    print("Demokonto angelegt. Gespeichert wurde nur der Passwort-Hash.")


if __name__ == "__main__":
    main()