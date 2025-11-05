import sys
sys.path.append('./src')
from Client import Client 
from Serveur import Serveur 

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 Main.py serveur|client")
        sys.exit(1)
    
    mode = sys.argv[1].lower()
    if mode == "serveur":
        serveur = Serveur()
        serveur.start()
    elif mode == "client":
        client = Client()
        client.connect()
        client.main_menu()
        client.close()
    else:
        print("Mode inconnu. Utilise 'serveur' ou 'client'.")