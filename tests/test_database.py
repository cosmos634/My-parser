import tempfile
import unittest
from pathlib import Path
from lead_finder.database import add_lead, init_db, list_leads


class DatabaseTests(unittest.TestCase):
    def test_duplicate_content_is_skipped(self):
        with tempfile.TemporaryDirectory() as folder:
            db = str(Path(folder) / "test.db")
            init_db(db)
            lead = {"title": "Need a Telegram bot", "description": "Order automation", "source": "manual", "source_name": "Test"}
            self.assertTrue(add_lead(lead, db)[0])
            self.assertFalse(add_lead(lead, db)[0])
            self.assertEqual(len(list_leads(db_path=db)), 1)


if __name__ == "__main__":
    unittest.main()
