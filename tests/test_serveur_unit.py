# tests/test_serveur_unit.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
import tempfile
import Serveur  # module Serveur

class TestServeurCommands(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        Serveur.DEFAULT_DIR = self.temp_dir.name
        self.server = Serveur.Serveur()
        self.session_state = {
            'open_file': None,
            'phase': 'ASSOCIATED',
            'transfer_in_progress': False,
            'transfer_offset': 0,
            'transfer_file': None,
            'error_flag': False,
            'error_message': ''
        }
    
    def tearDown(self):
        try:
            self.server.stop()
        except Exception:
            pass
        self.temp_dir.cleanup()
    
    def test_cmd_create_and_list(self):
        response, state = self.server.cmd_create(self.session_state, ["CREATE", "testfile.txt"])
        self.assertTrue(response.startswith("CREATE_OK"))
        response, state = self.server.cmd_list(self.session_state)
        self.assertIn("testfile.txt", response)
    
    def test_cmd_open_nonexistent(self):
        response, state = self.server.cmd_open(self.session_state, ["OPEN", "nonexistent.txt"])
        self.assertIn("ERREUR", response)
    
    def test_cmd_rename(self):
        self.server.cmd_create(self.session_state, ["CREATE", "oldname.txt"])
        response, state = self.server.cmd_rename(self.session_state, ["RENAME", "oldname.txt", "newname.txt"])
        self.assertTrue(response.startswith("RENAME_OK"))
        new_file_path = os.path.join(self.temp_dir.name, "newname.txt")
        self.assertTrue(os.path.exists(new_file_path))
    
    def test_cmd_delete(self):
        self.server.cmd_create(self.session_state, ["CREATE", "todelete.txt"])
        response, state = self.server.cmd_delete(self.session_state, ["DELETE", "todelete.txt"])
        self.assertTrue(response.startswith("DELETE_OK"))
        file_path = os.path.join(self.temp_dir.name, "todelete.txt")
        self.assertFalse(os.path.exists(file_path))
    
    def test_cmd_read_write_close(self):
        self.server.cmd_create(self.session_state, ["CREATE", "readwrite.txt"])
        response, state = self.server.cmd_write(self.session_state, ["WRITE", "Hello, world!"])
        self.assertTrue(response.startswith("WRITE_OK"))
        response, state = self.server.cmd_read(self.session_state)
        self.assertIn("Hello, world!", response)
        response, state = self.server.cmd_close(self.session_state)
        self.assertTrue(response.startswith("CLOSE_OK"))

if __name__ == '__main__':
    unittest.main()
