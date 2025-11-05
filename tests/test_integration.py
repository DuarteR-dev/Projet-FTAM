import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
import threading
import time
import tempfile
import Serveur  # module Serveur
from Client import Client

class IntegrationTestFTAM(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        import Serveur
        Serveur.DEFAULT_DIR = cls.temp_dir.name
        import Client
        Client.DEFAULT_DIR = cls.temp_dir.name

        cls.server = Serveur.Serveur(host='127.0.0.1', port=65434)
        cls.server_thread = threading.Thread(target=cls.server.start, daemon=True)
        cls.server_thread.start()
        time.sleep(1)  # Attendre le démarrage du serveur
    
    @classmethod
    def tearDownClass(cls):
        cls.server.stop()  # Arrête proprement le serveur
        cls.temp_dir.cleanup()
    
    def setUp(self):
        self.client = Client(server_host='127.0.0.1', server_port=65434)
        self.client.connect()
    
    def tearDown(self):
        self.client.close()
    
    def test_full_upload_and_download(self):
        # Test complet d'upload et download (voir votre code existant)
        temp_file_path = os.path.join(tempfile.gettempdir(), "integration_upload.txt")
        test_content = "Ceci est un test d'upload et download intégration."
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        self.client.upload_file(os.path.dirname(temp_file_path), "integration_upload.txt")
        server_file = os.path.join(self.temp_dir.name, "integration_upload.txt")
        self.assertTrue(os.path.exists(server_file), f"Le fichier {server_file} n'existe pas")
        with open(server_file, 'r', encoding='utf-8') as f:
            server_content = f.read().strip()
        self.assertEqual(server_content, test_content)
        
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        
        self.client.download_file("integration_upload.txt", tempfile.gettempdir())
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            downloaded_content = f.read().strip()
        self.assertEqual(downloaded_content, test_content)
        
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

if __name__ == '__main__':
    unittest.main()
