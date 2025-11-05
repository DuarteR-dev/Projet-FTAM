"""
Client.py

Module implémentant la classe Client pour interagir avec le serveur FTAM.
Le client permet d'établir une connexion TCP avec le serveur, d'envoyer des commandes
pour la gestion de fichiers (liste, ouverture, création, renommage, suppression, lecture, écriture)
ainsi que pour le transfert de fichiers (upload et download) avec gestion de reprise en cas d'incident.

Fonctions principales :
- connect() : Établit la connexion et reçoit le message d'association.
- send_command() : Envoie une commande textuelle au serveur et récupère la réponse.
- upload_file() : Effectue l'upload d'un fichier en gérant la reprise en cas d'erreur.
- download_file() : Télécharge un fichier en gérant la reprise en cas d'interruption.
- file_menu() : Menu interactif pour la gestion du fichier ouvert.
- main_menu() : Menu principal permettant de choisir une opération.
- close() : Ferme la connexion TCP.
"""

import os
import socket

# Taille du bloc de transfert
BLOCK_SIZE = 512

# Définition du répertoire de base (courant + "/data/")
DEFAULT_DIR = os.path.join(os.getcwd(), "data")
os.makedirs(DEFAULT_DIR, exist_ok=True)

class Client:
    """
    Classe Client pour interagir avec le serveur FTAM.
    
    Attributs:
        server_host (str): Adresse IP du serveur.
        server_port (int): Port TCP du serveur.
        sock (socket.socket): Socket de communication TCP.
    """
    def __init__(self, server_host='127.0.0.1', server_port=65432):
        """
        Initialise le client en créant une socket TCP.
        
        Args:
            server_host (str): Adresse du serveur (par défaut '127.0.0.1').
            server_port (int): Port du serveur (par défaut 65432).
        """
        self.server_host = server_host
        self.server_port = server_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    def connect(self):
        """
        Établit la connexion avec le serveur et reçoit le message d'association.
        """
        self.sock.connect((self.server_host, self.server_port))
        assoc_msg = self.sock.recv(BLOCK_SIZE).decode()
        print("Association établie :", assoc_msg)
    
    def send_command(self, command):
        """
        Envoie une commande au serveur et renvoie la réponse.
        
        Args:
            command (str): La commande à envoyer.
        
        Returns:
            str: La réponse reçue du serveur.
        """
        self.sock.sendall((command + "\n").encode())
        response = self.sock.recv(BLOCK_SIZE).decode()
        print("Réponse reçue :", response)
        return response

    def upload_file(self, local_filepath, remote_filename):
        """
        Effectue l'upload d'un fichier vers le serveur avec gestion de reprise en cas d'incident.
        
        Le fichier local est découpé en chunks de taille fixe et envoyé séquentiellement.
        En cas d'erreur, la reprise s'effectue à partir de l'offset communiqué par le serveur.
        
        Args:
            local_filepath (str): Chemin du fichier local (ou répertoire par défaut si vide).
            remote_filename (str): Nom du fichier distant.
        """
        if not local_filepath:
            local_filepath = DEFAULT_DIR
        local_full_path = os.path.join(local_filepath, os.path.basename(remote_filename))
        max_attempts = 5
        attempt = 0
        offset = 0

        while attempt < max_attempts:
            try:
                with open(local_full_path, 'rb') as f:
                    # Se positionner à l'offset connu (0 lors de la première tentative)
                    f.seek(offset)
                    response = self.send_command(f"UPLOAD {remote_filename}")
                    if response.startswith("UPLOAD_READY") or response.startswith("UPLOAD_RESUME"):
                        # Récupération de l'offset envoyé par le serveur
                        offset = int(response.split("offset=")[1])
                        f.seek(offset)
                    else:
                        print("Erreur lors de l’initiation de l'upload:", response)
                        return

                    # Envoi des chunks
                    while True:
                        chunk = f.read(BLOCK_SIZE)
                        if not chunk:
                            break
                        hex_data = chunk.hex()
                        data_response = self.send_command(f"UPLOAD_DATA {hex_data}")
                        if data_response.startswith("UPLOAD_ERROR"):
                            print("Erreur lors du transfert:", data_response)
                            if "offset=" in data_response:
                                offset = int(data_response.split("offset=")[1].split()[0])
                            raise Exception("Erreur durant le transfert d'un chunk")
                        elif data_response.startswith("UPLOAD_DATA_OK"):
                            offset = int(data_response.split("offset=")[1])
                    
                    # Fin de transfert
                    end_response = self.send_command("UPLOAD_END")
                    print("Upload terminé:", end_response)
                    return  # Succès de l'upload, sortie de la fonction

            except Exception as e:
                attempt += 1
                print(f"Tentative {attempt}/{max_attempts} échouée: {e}")
                # Possibilité d'ajouter un délai ici, par exemple: time.sleep(1)
        print("Échec de l'upload après plusieurs tentatives.")

    def begin_download(self, remote_filename, local_filepath):
        """
        Initialise le téléchargement d'un fichier depuis le serveur.
        
        Si le fichier local existe, l'offset de reprise est défini sur sa taille.
        
        Args:
            remote_filename (str): Nom du fichier distant.
            local_filepath (str): Chemin local de destination (ou répertoire par défaut si vide).
        
        Returns:
            tuple: (réponse du serveur, chemin complet du fichier local, offset de reprise)
        """
        if not local_filepath:
            local_filepath = DEFAULT_DIR
        local_full_path = os.path.join(local_filepath, remote_filename)
        offset = 0
        if os.path.exists(local_full_path):
            offset = os.path.getsize(local_full_path)  # Reprendre à la taille actuelle
        response = self.send_command(f"DOWNLOAD {remote_filename} {offset}")
        return response, local_full_path, offset

    def download_data(self, local_full_path, offset, chunk_hex):
        """
        Traite un chunk de données reçu en hexadécimal lors d'un téléchargement.
        
        Écrit les données dans le fichier local à l'offset indiqué.
        
        Args:
            local_full_path (str): Chemin complet du fichier local.
            offset (int): Offset de départ pour l'écriture.
            chunk_hex (str): Données reçues en hexadécimal.
        
        Returns:
            tuple: (message de confirmation ou d'erreur, nouveau offset)
        """
        try:
            chunk_bytes = bytes.fromhex(chunk_hex)
            with open(local_full_path, 'ab') as f:  # Mode append pour ne pas écraser
                f.seek(offset)
                f.write(chunk_bytes)
            new_offset = offset + len(chunk_bytes)
            return f"DOWNLOAD_DATA_OK offset={new_offset}", new_offset
        except Exception as e:
            return f"DOWNLOAD_ERROR {e} offset={offset}", offset

    def download_file(self, remote_filename, local_filepath):
        """
        Télécharge un fichier depuis le serveur avec gestion itérative de la reprise.
        
        Le client demande le fichier à partir de l'offset actuel (pour reprendre un téléchargement incomplet).
        Les données sont reçues sous forme de chunks en hexadécimal et écrites dans le fichier local.
        
        Args:
            remote_filename (str): Nom du fichier distant.
            local_filepath (str): Chemin de destination local (ou répertoire par défaut si vide).
        """
        if not local_filepath:
            local_filepath = DEFAULT_DIR
        local_full_path = os.path.join(local_filepath, remote_filename)
        max_attempts = 5
        attempt = 0

        while attempt < max_attempts:
            try:
                # Initialisation du téléchargement en tenant compte du fichier partiellement téléchargé
                offset = 0
                if os.path.exists(local_full_path):
                    offset = os.path.getsize(local_full_path)
                self.sock.sendall(f"DOWNLOAD {remote_filename} {offset}\n".encode())
                sock_file = self.sock.makefile('r')
                response = sock_file.readline().strip()
                if not response.startswith("DOWNLOAD_READY"):
                    print("Erreur lors de l'initiation du téléchargement:", response)
                    return

                while True:
                    line = sock_file.readline()
                    if not line:
                        raise Exception("Connexion interrompue")
                    line = line.strip()
                    if line.startswith("CHUNK"):
                        parts = line.split(maxsplit=1)
                        if len(parts) == 2:
                            chunk_hex = parts[1]
                            data_response, offset = self.download_data(local_full_path, offset, chunk_hex)
                            print(f"Chunk reçu, offset={offset}")
                            if data_response.startswith("DOWNLOAD_ERROR"):
                                raise Exception("Erreur lors du transfert d'un chunk")
                    elif line.startswith("DOWNLOAD_END"):
                        print("Téléchargement terminé, fichier sauvegardé sous", local_full_path)
                        return  # Succès du téléchargement
                    else:
                        print("Réponse inattendue:", line)
                        break

            except Exception as e:
                attempt += 1
                print(f"Erreur lors du téléchargement: {e}")
                print(f"Tentative {attempt}/{max_attempts} de reprise à partir de l'offset {offset}")
        print("Échec du téléchargement après plusieurs tentatives.")

    def file_menu(self):
        """
        Affiche un menu interactif pour la gestion du fichier actuellement ouvert.
        
        Permet d'effectuer les opérations READ, WRITE ou CLOSE sur le fichier.
        """
        while True:
            print("\n--- Sous-menu de gestion de fichier ---")
            print("1. READ")
            print("2. WRITE")
            print("3. CLOSE")
            choice = input("Votre choix : ")
            if choice == "1":
                self.send_command("READ")
            elif choice == "2":
                data = input("Entrez les données à ajouter :\n")
                self.send_command(f"WRITE {data}")
            elif choice == "3":
                self.send_command("CLOSE")
                break
            else:
                print("Option invalide, veuillez réessayer.")
    
    def main_menu(self):
        """
        Affiche le menu principal interactif pour choisir une opération sur les fichiers.
        
        Options disponibles :
        - LIST, OPEN, CREATE, RENAME, DELETE
        - UPLOAD : envoyer un fichier vers le serveur
        - DOWNLOAD : télécharger un fichier depuis le serveur
        - LEAVE : quitter l'application client
        """
        while True:
            print("\n=== Menu Principal FTAM ===")
            print("1. LIST")
            print("2. OPEN")
            print("3. CREATE")
            print("4. RENAME")
            print("5. DELETE")
            print("6. UPLOAD (envoyer un fichier vers le serveur)")
            print("7. DOWNLOAD (télécharger un fichier depuis le serveur)")
            print("8. LEAVE")
            choice = input("Votre choix : ")
            if choice == "1":
                self.send_command("LIST")
            elif choice == "2":
                filename = input("Entrez le nom du fichier à ouvrir : ")
                response = self.send_command(f"OPEN {filename}")
                if "OK" in response:
                    self.file_menu()
            elif choice == "3":
                filename = input("Entrez le nom du fichier à créer : ")
                response = self.send_command(f"CREATE {filename}")
                if "OK" in response:
                    self.file_menu()
            elif choice == "4":
                old_name = input("Entrez le nom actuel du fichier : ")
                new_name = input("Entrez le nouveau nom du fichier : ")
                self.send_command(f"RENAME {old_name} {new_name}")
            elif choice == "5":
                filename = input("Entrez le nom du fichier à supprimer : ")
                self.send_command(f"DELETE {filename}")
            elif choice == "6":
                local_file = input("Chemin du fichier local à uploader (laisser vide pour répertoire par défaut) : ")
                remote_file = input("Nom du fichier distant : ")
                self.upload_file(local_file, remote_file)
            elif choice == "7":
                remote_file = input("Nom du fichier distant à télécharger : ")
                local_file = input("Chemin de destination local (laisser vide pour répertoire par défaut) : ")
                self.download_file(remote_file, local_file)
            elif choice == "8":
                print("Fermeture du client FTAM.")
                break
            else:
                print("Option invalide, veuillez réessayer.")
    
    def close(self):
        """
        Ferme la connexion TCP avec le serveur.
        """
        self.sock.close()
