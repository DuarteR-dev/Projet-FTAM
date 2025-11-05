import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
import tempfile
from Client import Client

class TestClientDownloadData(unittest.TestCase):
    def setUp(self):
        # Création d'un répertoire temporaire pour le test
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file = os.path.join(self.temp_dir.name, "download_test.txt")
        # Créer un fichier vide
        with open(self.test_file, 'wb') as f:
            f.write(b"")
        self.client = Client()
        # Si le test n'a pas besoin de connexion, vous pouvez choisir de ne pas appeler connect()
        # ou appeler connect() si nécessaire.
    
    def tearDown(self):
        # Fermer le socket client pour éviter les ResourceWarning
        try:
            self.client.close()
        except Exception:
            pass
        self.temp_dir.cleanup()
    
    def test_download_data_success(self):
        # Test avec une chaîne hexadécimale valide ("Hello" en hex)
        chunk_hex = "48656c6c6f"
        response, new_offset = self.client.download_data(self.test_file, 0, chunk_hex)
        self.assertTrue(response.startswith("DOWNLOAD_DATA_OK"))
        self.assertEqual(new_offset, 5)
        # Vérifier que le contenu du fichier est bien "Hello"
        with open(self.test_file, 'rb') as f:
            content = f.read()
        self.assertEqual(content, b"Hello")
    
    def test_download_data_invalid_hex(self):
        # Test avec une chaîne hex invalide pour provoquer une erreur
        chunk_hex = "ZZZ"
        response, offset = self.client.download_data(self.test_file, 0, chunk_hex)
        self.assertTrue(response.startswith("DOWNLOAD_ERROR"))
        self.assertEqual(offset, 0)

if __name__ == '__main__':
    unittest.main()
