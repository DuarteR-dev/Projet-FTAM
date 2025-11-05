# FTAM Python — client/serveur minimal avec reprise de transfert

Projet Python fournissant un serveur et un client FTAM simplifiés. Les commandes sont textuelles sur TCP et les fichiers sont transférés en hex par blocs avec reprise via offset. Bloc par défaut: `BLOCK_SIZE = 512` octets (défini dans `src/Serveur.py` et `src/Client.py`).

## Utilisation
```bash
# Dans le dossier Projet/
python Main.py serveur        # démarre le serveur (127.0.0.1:65432, dépôt des fichiers: ./data)
python Main.py client         # lance le client interactif
```

## Structure
```text
./
├─ Main.py                # point d'entrée: python Main.py serveur|client
├─ src/
│  ├─ Serveur.py          # Serveur(host='127.0.0.1', port=65432, DEFAULT_DIR=./data)
│  └─ Client.py           # Client(server_host='127.0.0.1', server_port=65432, DEFAULT_DIR=./data)
└─ tests/
   ├─ test_client_unit.py
   ├─ test_serveur_unit.py
   └─ test_integration.py
```

## Fonctionnalités
- Gestion de fichiers: `LIST`, `OPEN`, `CREATE`, `RENAME`, `DELETE`, `READ`, `WRITE`, `CLOSE`
- Transfert: `UPLOAD` et `DOWNLOAD` par blocs hex, accusés `UPLOAD_DATA_OK offset=<n>`, fin `UPLOAD_END`
- Reprise: reprise sur incident via `offset` confirmé
- Répertoires: par défaut, le serveur et le client utilisent `./data` (créé automatiquement dans le répertoire courant)

## Lancer
Serveur avec valeurs par défaut:
```bash
python Main.py serveur
# hôte: 127.0.0.1, port: 65432, répertoire serveur: ./data
```

Client interactif:
```bash
python Main.py client
# Menu:
# 1 LIST  2 OPEN  3 CREATE  4 RENAME  5 DELETE  6 UPLOAD  7 DOWNLOAD  8 LEAVE
```

## Paramètres
Les valeurs par défaut sont dans les signatures des classes:
- `Serveur(host='127.0.0.1', port=65432)` -> modifiez l'appel dans `Main.py` si besoin
- `Client(server_host='127.0.0.1', server_port=65432)`

Taille de bloc:
- `BLOCK_SIZE = 512` dans `src/Serveur.py` et `src/Client.py`

Répertoires:
- `DEFAULT_DIR = os.path.join(os.getcwd(), "data")` côté serveur et client

## Protocole (résumé)
Messages texte sur une socket TCP. Données fichier encodées en hex.
- Commande: ex. `UPLOAD <remote_filename>` puis `UPLOAD_DATA <hex_chunk>` répété, et `UPLOAD_END`
- Accusés: `UPLOAD_DATA_OK offset=<n>` ou `UPLOAD_ERROR ... offset=<n>`
- Download: `DOWNLOAD <remote_filename> <offset>` puis réception de `CHUNK <hex_chunk>` jusqu'à `DOWNLOAD_END`

## Tests
Tests unitaires et d'intégration avec `unittest`:
```bash
# depuis Projet/
python -m unittest discover -s tests -v
```

## Dépendances
Aucun `requirements.txt` dans le projet. Fonctionne avec Python ≥ 3.10 standard.

## Notes
- Lancer le serveur depuis `Projet/` crée/alimente `Projet/data`.
- Le client place/cherche ses fichiers par défaut dans `./data` du répertoire courant.
