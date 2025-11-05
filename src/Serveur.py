"""
Serveur.py

Module implémentant la classe Serveur pour gérer les opérations de transfert et de gestion de fichiers via TCP.
Le serveur écoute sur un port défini (par défaut 65432) et traite des commandes textuelles envoyées par les clients.
Il gère notamment les commandes LIST, OPEN, CREATE, RENAME, DELETE, READ, WRITE, CLOSE ainsi que les transferts d'upload et de download.

Fonctions principales :
- start() : Démarre le serveur et accepte les connexions clientes.
- stop()  : Arrête le serveur en fermant le socket d'écoute.
- handle_client() : Traite les commandes d'un client connecté.
- gestionnaire_commandes() : Interprète et exécute les commandes reçues.
- Diverses fonctions cmd_* pour traiter chacune des commandes.
"""

import os
import socket
import threading

# Taille du bloc de transfert
BLOCK_SIZE = 512

# Définition du répertoire de base (courant + "/data/")
DEFAULT_DIR = os.path.join(os.getcwd(), "data")
os.makedirs(DEFAULT_DIR, exist_ok=True)

class Serveur:
    """
    Classe Serveur qui implémente le protocole FTAM.
    
    Attributs:
        host (str): Adresse IP sur laquelle le serveur écoute.
        port (int): Port TCP sur lequel le serveur écoute.
        sock (socket.socket): Socket d'écoute du serveur.
        _is_running (bool): Indique si le serveur doit continuer à accepter des connexions.
    """
    def __init__(self, host='127.0.0.1', port=65432):
        """
        Initialise le serveur en créant la socket d'écoute.
        
        Args:
            host (str): Adresse IP (par défaut '127.0.0.1').
            port (int): Port TCP (par défaut 65432).
        """
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._is_running = True

    def start(self):
        """
        Démarre le serveur :
        - Lie la socket à l'adresse et au port définis.
        - Écoute les connexions entrantes.
        - Pour chaque connexion, lance un thread pour gérer le client.
        """
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        print(f"Serveur FTAM démarré sur {self.host}:{self.port}")
        while self._is_running:
            try:
                client_sock, addr = self.sock.accept()
            except OSError:
                break  # Le socket a été fermé
            print(f"Connexion entrante de {addr}")
            threading.Thread(target=self.handle_client, args=(client_sock,), daemon=True).start()

    def stop(self):
        """
        Arrête le serveur en modifiant le flag _is_running et en fermant le socket d'écoute.
        """
        self._is_running = False
        self.sock.close()
        
    def __del__(self):
        """
        Destructeur garantissant la fermeture du socket d'écoute.
        """
        try:
            self.sock.close()
        except Exception:
            pass

    def handle_client(self, client_sock):
        """
        Gère la communication avec un client.
        
        Args:
            client_sock (socket.socket): Socket du client connecté.
        
        Le serveur :
         - Effectue l'association.
         - Lit les commandes envoyées par le client (ligne par ligne).
         - Pour les commandes DOWNLOAD, utilise un traitement en streaming.
         - Pour les autres commandes, envoie la réponse correspondante.
         - Ferme la connexion à la fin.
        """
        session_state = {
            'open_file': None,             # Nom du fichier ouvert (pour gestion interactive)
            'phase': 'ASSOCIATED',         # Phases: ASSOCIATED, FILE_OPEN, TRANSFER_IN_PROGRESS
            'transfer_in_progress': False, # Indique si un transfert est en cours
            'transfer_offset': 0,          # Offset courant dans le fichier de transfert
            'transfer_file': None,         # Fichier ouvert pour le transfert (objet file)
            'error_flag': False,           # Indique une erreur durant le transfert
            'error_message': ''
        }
        try:
            self.associer(client_sock)
            # Lecture ligne par ligne pour recevoir chaque commande
            client_file = client_sock.makefile('r')
            while True:
                line = client_file.readline()
                if not line:
                    break
                command = line.strip()
                print(f"Commande reçue: {command}")
                # Traitement en streaming pour DOWNLOAD
                if command.upper().startswith("DOWNLOAD"):
                    self.cmd_download(command, session_state, client_sock)
                else:
                    response, session_state = self.gestionnaire_commandes(command, session_state)
                    # Ajoute un saut de ligne pour séparer les réponses
                    client_sock.sendall((response + "\n").encode())
        except Exception as e:
            print("Erreur lors du traitement du client:", e)
        finally:
            client_sock.close()
            print("Connexion fermée.")

    def associer(self, client_sock):
        """
        Envoie le message d'association au client dès la connexion.
        
        Args:
            client_sock (socket.socket): Socket du client.
        """
        welcome_msg = "FTAM_SERVER: Association établie"
        client_sock.sendall(welcome_msg.encode())

    def gestionnaire_commandes(self, command, session_state):
        """
        Interprète et exécute une commande reçue.
        
        Args:
            command (str): Commande envoyée par le client.
            session_state (dict): État de la session client.
        
        Returns:
            tuple: (réponse à envoyer, état de session mis à jour)
        """
        parts = command.split()
        if not parts:
            return "ERREUR: Commande vide", session_state
        cmd = parts[0].upper()

        if cmd == "LIST":
            return self.cmd_list(session_state)

        elif cmd == "OPEN":
            return self.cmd_open(session_state, parts)

        elif cmd == "CREATE":
            return self.cmd_create(session_state, parts)

        elif cmd == "RENAME":
            return self.cmd_rename(session_state, parts)

        elif cmd == "DELETE":
            return self.cmd_delete(session_state, parts)

        elif cmd == "READ":
            return self.cmd_read(session_state)

        elif cmd == "WRITE":
            return self.cmd_write(session_state, parts)

        elif cmd == "CLOSE":
            return self.cmd_close(session_state)

        elif cmd == "UPLOAD":
            return self.cmd_begin_upload(session_state, parts)

        elif cmd == "UPLOAD_DATA":
            return self.cmd_upload_data(session_state, parts)

        elif cmd == "UPLOAD_END":
            return self.cmd_upload_end(session_state)

        elif cmd == "RESUME_UPLOAD":
            return self.cmd_resume_upload(session_state)

        else:
            return "ERREUR: Commande non reconnue", session_state
        
    def cmd_list(self, session_state):
        """
        Retourne la liste des fichiers présents dans le répertoire de base.
        
        Args:
            session_state (dict): État de la session.
        
        Returns:
            tuple: (message de réponse, état de session)
        """
        try:
            files = [f for f in os.listdir(DEFAULT_DIR) if os.path.isfile(os.path.join(DEFAULT_DIR, f))]
            if files:
                file_list = "\n".join(["  - " + f for f in files])
                display = ("=== Liste des fichiers ===\n" +
                            f"{file_list}\n" +
                            "===========================")
                return f"LIST_OK\n{display}", session_state
            else:
                return "LIST_OK\n=== Liste des fichiers ===\nAucun fichier trouvé.\n===========================", session_state
        except Exception as e:
            return f"ERREUR: Liste des fichiers impossible: {e}", session_state
        
    def cmd_open(self, session_state, parts):
        """
        Ouvre un fichier existant.
        
        Args:
            session_state (dict): État de la session.
            parts (list): Liste des paramètres de la commande.
        
        Returns:
            tuple: (message de réponse, état de session)
        """
        if session_state['open_file'] is not None:
            return "ERREUR: Un fichier est déjà ouvert", session_state
        if len(parts) < 2:
            return "ERREUR: OPEN nécessite un nom de fichier", session_state
        filename = parts[1]
        filepath = os.path.join(DEFAULT_DIR, filename)
        if not os.path.exists(filepath):
            return f"ERREUR: Le fichier '{filename}' n'existe pas", session_state
        session_state['open_file'] = filename
        session_state['phase'] = 'FILE_OPEN'
        return f"OPEN_OK {filename}", session_state
        
    def cmd_create(self, session_state, parts):
        """
        Crée un nouveau fichier vide dans le répertoire de base.
        
        Args:
            session_state (dict): État de la session.
            parts (list): Liste des paramètres de la commande.
        
        Returns:
            tuple: (message de réponse, état de session)
        """
        if session_state['open_file'] is not None:
            return "ERREUR: Un fichier est déjà ouvert", session_state
        if len(parts) < 2:
            return "ERREUR: CREATE nécessite un nom de fichier", session_state
        filename = parts[1]
        filepath = os.path.join(DEFAULT_DIR, filename)
        try:
            with open(filepath, 'w') as f:
                pass
            print(f"Fichier '{filepath}' créé.")
        except Exception as e:
            return f"ERREUR: Création du fichier échouée: {e}", session_state
        session_state['open_file'] = filename
        session_state['phase'] = 'FILE_OPEN'
        return f"CREATE_OK {filename}", session_state
        
    def cmd_rename(self, session_state, parts):
        """
        Renomme un fichier existant.
        
        Args:
            session_state (dict): État de la session.
            parts (list): [ "RENAME", old_name, new_name ]
        
        Returns:
            tuple: (message de réponse, état de session)
        """
        if len(parts) < 3:
            return "ERREUR: RENAME nécessite un ancien et un nouveau nom", session_state
        old_name = parts[1]
        new_name = parts[2]
        old_path = os.path.join(DEFAULT_DIR, old_name)
        new_path = os.path.join(DEFAULT_DIR, new_name)
        if not os.path.exists(old_path):
            return f"ERREUR: Le fichier '{old_name}' n'existe pas", session_state
        try:
            os.rename(old_path, new_path)
            return f"RENAME_OK {old_name} -> {new_name}", session_state
        except Exception as e:
            return f"ERREUR: Renommage échoué: {e}", session_state
        
    def cmd_delete(self, session_state, parts):
        """
        Supprime un fichier existant.
        
        Args:
            session_state (dict): État de la session.
            parts (list): [ "DELETE", filename ]
        
        Returns:
            tuple: (message de réponse, état de session)
        """
        if len(parts) < 2:
            return "ERREUR: DELETE nécessite un nom de fichier", session_state
        filename = parts[1]
        filepath = os.path.join(DEFAULT_DIR, filename)
        if not os.path.exists(filepath):
            return f"ERREUR: Le fichier '{filename}' n'existe pas", session_state
        try:
            os.remove(filepath)
            return f"DELETE_OK {filename}", session_state
        except Exception as e:
            return f"ERREUR: Suppression du fichier échouée: {e}", session_state
        
    def cmd_read(self, session_state):
        """
        Lit le contenu du fichier actuellement ouvert.
        
        Args:
            session_state (dict): État de la session.
        
        Returns:
            tuple: (message contenant le contenu du fichier ou une erreur, état de session)
        """
        if session_state['open_file'] is None:
            return "ERREUR: Aucun fichier ouvert. Utilise OPEN ou CREATE d'abord", session_state
        filename = session_state['open_file']
        filepath = os.path.join(DEFAULT_DIR, filename)
        try:
            with open(filepath, 'r') as f:
                content = f.read().strip()
            display = (f"=== Contenu du fichier: {filename} ===\n" +
                        f"{content}\n" +
                        "===============================")
            return f"READ_OK\n{display}", session_state
        except Exception as e:
            return f"ERREUR: Lecture du fichier échouée: {e}", session_state
        
    def cmd_write(self, session_state, parts):
        """
        Écrit (ajoute) des données dans le fichier actuellement ouvert.
        
        Args:
            session_state (dict): État de la session.
            parts (list): [ "WRITE", data... ]
        
        Returns:
            tuple: (message de confirmation ou d'erreur, état de session)
        """
        if session_state['open_file'] is None:
            return "ERREUR: Aucun fichier ouvert. Utilise OPEN ou CREATE d'abord", session_state
        if len(parts) < 2:
            return "ERREUR: WRITE nécessite des données à écrire", session_state
        filedata = " ".join(parts[1:])
        filename = session_state['open_file']
        filepath = os.path.join(DEFAULT_DIR, filename)
        try:
            with open(filepath, 'a') as f:
                f.write(filedata + "\n")
            return f"WRITE_OK {filename}", session_state
        except Exception as e:
            return f"ERREUR: Écriture dans le fichier échouée: {e}", session_state
    
    def cmd_close(self, session_state):
        """
        Ferme le fichier actuellement ouvert.
        
        Args:
            session_state (dict): État de la session.
        
        Returns:
            tuple: (message de confirmation, état de session)
        """
        if session_state['open_file'] is None:
            return "ERREUR: Aucun fichier ouvert à fermer", session_state
        filename = session_state['open_file']
        session_state['open_file'] = None
        session_state['phase'] = 'ASSOCIATED'
        return f"CLOSE_OK {filename}", session_state
          
    def cmd_begin_upload(self, session_state, parts):
        """
        Initialise un upload de fichier.
        
        Ouvre le fichier en mode 'wb' ou 'ab' (pour reprendre un upload existant) et initialise l'état de transfert.
        
        Args:
            session_state (dict): État de la session.
            parts (list): [ "UPLOAD", filename ]
        
        Returns:
            tuple: (message d'initiation de transfert, état de session)
        """
        if len(parts) < 2:
            return "ERREUR: UPLOAD nécessite un nom de fichier", session_state
        filename = parts[1]
        filepath = os.path.join(DEFAULT_DIR, filename)
        offset = 0
        mode = 'wb'
        if os.path.exists(filepath):
            offset = os.path.getsize(filepath)
            mode = 'ab'
        try:
            f = open(filepath, mode)
        except Exception as e:
            return f"ERREUR: Ouverture du fichier pour upload échouée: {e}", session_state
        session_state['transfer_in_progress'] = True
        session_state['transfer_file'] = f
        session_state['transfer_offset'] = offset
        session_state['phase'] = 'TRANSFER_IN_PROGRESS'
        if offset > 0:
            return f"UPLOAD_RESUME {filename} offset={offset}", session_state
        else:
            return f"UPLOAD_READY {filename} offset={offset}", session_state
            
    def cmd_upload_data(self, session_state, parts):
        """
        Traite l'envoi d'un chunk de données pour l'upload.
        
        Args:
            session_state (dict): État de la session.
            parts (list): [ "UPLOAD_DATA", hex_data ]
        
        Returns:
            tuple: (message de confirmation ou d'erreur, état de session)
        """
        if not session_state.get('transfer_in_progress'):
            return "ERREUR: Aucun upload en cours", session_state
        if len(parts) < 2:
            return "ERREUR: UPLOAD_DATA nécessite des données à écrire", session_state
        data_hex = " ".join(parts[1:])
        try:
            data_bytes = bytes.fromhex(data_hex)
            f = session_state['transfer_file']
            bytes_written = f.write(data_bytes)
            f.flush()
            session_state['transfer_offset'] += bytes_written
            return f"UPLOAD_DATA_OK offset={session_state['transfer_offset']}", session_state
        except Exception as e:
            session_state['error_flag'] = True
            session_state['error_message'] = str(e)
            # En cas d'erreur, ne pas fermer le fichier pour permettre la reprise
            return f"UPLOAD_ERROR {e}", session_state

    def cmd_upload_end(self, session_state):
        """
        Termine le transfert d'un fichier en upload.
        
        Ferme le fichier de transfert si aucune erreur n'est survenue.
        
        Args:
            session_state (dict): État de la session.
        
        Returns:
            tuple: (message de fin de transfert, état de session)
        """
        if not session_state.get('transfer_in_progress'):
            return "ERREUR: Aucun upload en cours", session_state
        try:
            if session_state['error_flag']:
                # En cas d'erreur, ne pas fermer le fichier pour permettre la reprise
                return "UPLOAD_INTERRUPTED", session_state
            else:
                if session_state['transfer_file']:
                    session_state['transfer_file'].close()
                    session_state['transfer_file'] = None
                session_state['transfer_in_progress'] = False
                session_state['phase'] = 'FILE_OPEN'
                session_state['error_flag'] = False
                session_state['error_message'] = ""
                return "UPLOAD_END_OK", session_state
        except Exception as e:
            return f"ERREUR: Fin de l'upload échouée: {e}", session_state

    def cmd_resume_upload(self, session_state):
        """
        Reprend un upload interrompu.
        
        Args:
            session_state (dict): État de la session.
        
        Returns:
            tuple: (message de reprise, état de session)
        """
        if not session_state.get('error_flag'):
            return "ERREUR: Aucun upload à reprendre", session_state
        if session_state['transfer_file'] is None:
            return "ERREUR: Fichier de transfert non ouvert", session_state
        session_state['transfer_in_progress'] = True
        session_state['phase'] = 'TRANSFER_IN_PROGRESS'
        session_state['error_flag'] = False
        session_state['error_message'] = ""
        return f"RESUME_UPLOAD_OK offset={session_state['transfer_offset']}", session_state

    def cmd_download(self, command, session_state, client_sock):
        """
        Gère la commande DOWNLOAD envoyée par le client.
        
        Lit le fichier à partir de l'offset donné et envoie le contenu sous forme de chunks en hexadécimal.
        
        Args:
            command (str): Commande complète (ex: "DOWNLOAD filename offset").
            session_state (dict): État de la session.
            client_sock (socket.socket): Socket du client.
        """
        parts = command.split()
        if len(parts) < 2:
            client_sock.sendall("ERREUR: DOWNLOAD nécessite un nom de fichier\n".encode())
            return
        filename = parts[1]
        offset = 0
        if len(parts) > 2:
            try:
                offset = int(parts[2])
            except ValueError:
                client_sock.sendall("ERREUR: Offset invalide\n".encode())
                return
        filepath = os.path.join(DEFAULT_DIR, filename)
        if not os.path.exists(filepath):
            client_sock.sendall(f"ERREUR: Le fichier '{filename}' n'existe pas\n".encode())
            return
        try:
            with open(filepath, 'rb') as f:
                f.seek(offset)
                header = f"DOWNLOAD_READY {filename} offset={offset}\n"
                client_sock.sendall(header.encode())
                while True:
                    chunk = f.read(BLOCK_SIZE)
                    if not chunk:
                        break
                    line = f"CHUNK {chunk.hex()}\n"
                    print(line)
                    client_sock.sendall(line.encode())
                client_sock.sendall("DOWNLOAD_END\n".encode())
        except Exception as e:
            err_msg = f"ERREUR: Téléchargement du fichier échoué: {e}\n"
            client_sock.sendall(err_msg.encode())
