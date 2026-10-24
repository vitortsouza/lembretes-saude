# -*- coding: utf-8 -*-
import sys
import unittest


@unittest.skipUnless(sys.platform == "win32", "requer Windows")
class TestBandejaWindows(unittest.TestCase):
    def test_modulo_da_bandeja_pode_ser_importado(self):
        import tray

        self.assertTrue(hasattr(tray, "executar_com_bandeja"))
        self.assertTrue(hasattr(tray, "ErroBandeja"))
        self.assertTrue(hasattr(tray, "executar_acao"))
        self.assertTrue(hasattr(tray, "registrar_protocolo"))
        self.assertEqual(tray.NOME_CLASSE, "LembretesSaudeTrayWindow")


if __name__ == "__main__":
    unittest.main()
