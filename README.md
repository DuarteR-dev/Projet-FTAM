# FTAM — application Python de transfert et gestion de fichiers

Implémentation pédagogique d’un protocole FTAM minimaliste en Python pour lister, créer, lire, écrire, renommer, supprimer et transférer des fichiers sur TCP, avec reprise sur incident par *offset* et découpage en blocs. fileciteturn0file0

📺 **Démo vidéo** : https://youtu.be/ERZCp13Q7Zk  fileciteturn0file0

---

## Sommaire
- [Contexte et objectifs](#contexte-et-objectifs)
- [Architecture](#architecture)
- [Protocole FTAM](#protocole-ftam)
  - [Commandes générales](#commandes-générales)
  - [Transfert de fichiers](#transfert-de-fichiers)
  - [Gestion d’erreurs et reprise](#gestion-derreurs-et-reprise)
- [Choix de conception](#choix-de-conception)
- [Démarrage rapide](#démarrage-rapide)
- [Utilisation](#utilisation)
- [Configuration](#configuration)
- [Limites connues](#limites-connues)
- [Feuille de route](#feuille-de-route)
- [Crédits](#crédits)

---

## Contexte et objectifs

Ce dépôt contient un serveur et un client FTAM permettant d’échanger des messages textuels sur une connexion TCP et de transférer des données de fichiers converties en hexadécimal. L’objectif est de fournir une base simple à étudier, tester et étendre. fileciteturn0file0

---

## Architecture

Deux entités principales : fileciteturn0file0

- **Serveur FTAM** : écoute sur un port TCP dédié (par défaut `65432`), gère les commandes et implémente la reprise d’upload via un mécanisme d’*offset*. fileciteturn0file0
- **Client FTAM** : se connecte au serveur, envoie les commandes et transfère les données en *chunks* de taille fixe (`BLOCK_SIZE`). Gère la reprise de *download* via un *offset*. fileciteturn0file0

---

## Protocole FTAM

Le protocole repose sur des **messages textuels** échangés sur TCP. Les données binaires des fichiers sont **converties en hexadécimal** pour le transport puis reconverties à la réception. fileciteturn0file0

### Commandes générales

- **Association** : à la connexion, le serveur envoie `FTAM_SERVER: Association établie`. fileciteturn0file0
- **LIST** : `LIST` → renvoie la liste des fichiers du répertoire de base. fileciteturn0file0
- **OPEN / CREATE** : `OPEN <filename>` pour ouvrir un fichier existant, `CREATE <filename>` pour créer un fichier vide → réponses `OPEN_OK <filename>` / `CREATE_OK <filename>`. fileciteturn0file0
- **RENAME / DELETE** : `RENAME <oldname> <newname>` / `DELETE <filename>` → messages de succès/échec. fileciteturn0file0
- **READ / WRITE / CLOSE** : `READ` renvoie le contenu, `WRITE <data>` ajoute à la fin, `CLOSE` ferme le fichier → `READ_OK` / `WRITE_OK` / `CLOSE_OK`. fileciteturn0file0

### Transfert de fichiers

**Upload** : fileciteturn0file0

1. Init : `UPLOAD <remote_filename>` →  
   - nouveau : `UPLOAD_READY <filename> offset=0`  
   - reprise : `UPLOAD_RESUME <filename> offset=<offset>`  
2. Données : pour chaque bloc (`BLOCK_SIZE`), le client envoie `UPLOAD_DATA <hex_data>` →  
   - ok : `UPLOAD_DATA_OK offset=<new_offset>`  
   - erreur : `UPLOAD_ERROR ... offset=<offset>`  
3. Fin : `UPLOAD_END` → `UPLOAD_END_OK`

**Download** : fileciteturn0file0

1. Init : `DOWNLOAD <remote_filename> <offset>` → `DOWNLOAD_READY <filename> offset=<offset>`  
2. Données : le serveur envoie `CHUNK <hex_data>` pour chaque bloc.  
3. Fin : `DOWNLOAD_END`

### Gestion d’erreurs et reprise

En cas d’échec lors d’un bloc, le client reprend au **dernier offset validé** communiqué par le serveur. Les fonctions d’upload et de download intègrent des **boucles de reprise** pour gérer les coupures ou erreurs transitoires. fileciteturn0file0

---

## Choix de conception

- **Découpage en blocs** : taille fixe `BLOCK_SIZE = 512` octets pour maîtriser la granularité et faciliter la reprise. fileciteturn0file0
- **Reprise par offset** : reprise côté upload et download à partir de l’offset confirmé. fileciteturn0file0
- **Communication textuelle** : commandes lisibles et trafic facilement déboguable ; conversion binaire ↔ hexadécimal pour transporter les données dans des messages texte. fileciteturn0file0

---

## Démarrage rapide

> Remplacez les noms de fichiers par les **vôtres** si le dépôt utilise d’autres points d’entrée. Je ne sais pas quels sont les noms exacts des scripts dans ce projet.

```bash
# 1) Cloner le dépôt
git clone <url-du-dépôt> ftam-python
cd ftam-python

# 2) (Optionnel) Créer un environnement virtuel
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3) (Optionnel) Installer les dépendances si un requirements.txt est fourni
pip install -r requirements.txt  # si présent
```

---

## Utilisation

### Lancer le serveur
```bash
python <votre_serveur.py> --host 0.0.0.0 --port 65432
# le port par défaut est 65432 si implémenté ainsi dans le dépôt
```

### Lancer le client
```bash
python <votre_client.py> --host <ip_du_serveur> --port 65432
```

### Exemple de session (illustratif)

```text
Client -> (connexion)
Serveur -> FTAM_SERVER: Association établie

Client -> LIST
Serveur -> file1.txt file2.bin

Client -> CREATE demo.txt
Serveur -> CREATE_OK demo.txt

Client -> OPEN demo.txt
Serveur -> OPEN_OK demo.txt

Client -> WRITE Bonjour
Serveur -> WRITE_OK

Client -> CLOSE
Serveur -> CLOSE_OK

Client -> UPLOAD demo.bin
Serveur -> UPLOAD_READY demo.bin offset=0

Client -> UPLOAD_DATA <HEX_512_OCTETS>
Serveur -> UPLOAD_DATA_OK offset=512
...
Client -> UPLOAD_END
Serveur -> UPLOAD_END_OK
```

---

## Configuration

Variables et arguments usuels :

- `--host`, `--port` : interface et port d’écoute du serveur. Port par défaut : `65432`. fileciteturn0file0
- `BLOCK_SIZE` : taille des blocs de transfert, 512 octets dans le rapport. fileciteturn0file0
- Répertoires de base pour les opérations de fichiers et stockage temporaire si prévu par le dépôt. (Je ne sais pas la structure exacte ; adaptez selon votre code.)

---

## Limites connues

- Protocole texte minimaliste. Pas d’authentification ni de chiffrement décrits dans le rapport. (À compléter si présent dans le code.)
- Reprise basée sur l’offset : nécessite la cohérence des tailles locales/distantes. fileciteturn0file0

---

## Feuille de route

Pistes d’amélioration possibles :
- Authentification simple et droits par commande.
- Chiffrement de transport (ex. TLS) ou encapsulation dans un tunnel.
- Journalisation structurée et métriques.
- Tests d’intégration bout‑en‑bout et fuzzing des commandes.
- Négociation de `BLOCK_SIZE` et compression optionnelle.

---

## Crédits

- **Auteur** : Duarte Ribeiro
- **Rapport de référence** : *FTAM en Python, Bureau d’étude* (Janvier 2025). fileciteturn0file0
- **Vidéo de présentation** : https://youtu.be/ERZCp13Q7Zk  fileciteturn0file0

---

> Note : ce README synthétise le protocole et les choix décrits dans le rapport et laisse volontairement des emplacements à compléter selon l’arborescence et les noms de fichiers réels du dépôt.
