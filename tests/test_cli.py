"""Where the commands look for the data: the folder given, $LABMAP_DATA, labmap.ini, or here."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from labmap import __main__ as cli


class DataFolder(unittest.TestCase):
    def test_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            ini = Path(tmp) / "labmap.ini"
            ini.write_text("[data]\nfolder = %USERPROFILE%\\Lab Atlas\n", encoding="utf-8")
            env = {k: v for k, v in os.environ.items() if k != "LABMAP_DATA"}
            env["USERPROFILE"] = "C:\\Users\\someone"
            with mock.patch.object(cli, "CONFIG", ini), mock.patch.dict(os.environ, env, clear=True):
                self.assertEqual(cli.data_folder("given"), Path("given"))
                self.assertEqual(cli.data_folder(None), Path("C:\\Users\\someone\\Lab Atlas"))
                ini.write_text("[data]\nfolder = shared/lab\n", encoding="utf-8")
                self.assertEqual(cli.data_folder(None), Path(tmp) / "shared" / "lab")  # relative to labmap.ini
                with mock.patch.dict(os.environ, {"LABMAP_DATA": "elsewhere"}):
                    self.assertEqual(cli.data_folder(None), Path("elsewhere"))
                ini.unlink()
                self.assertEqual(cli.data_folder(None), Path("."))


if __name__ == "__main__":
    unittest.main()
