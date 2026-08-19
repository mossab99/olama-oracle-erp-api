import unittest
from unittest.mock import patch

from config import Config
from repositories.families_repo import get_all_families, get_family_by_id


class FamiliesRepositoryTests(unittest.TestCase):
    @patch("repositories.families_repo.query_all")
    def test_family_directory_includes_transportation_region(self, query_all):
        query_all.return_value = []

        get_all_families()

        sql, binds = query_all.call_args.args
        self.assertIn("f.TRANS_REGION_ID AS trans_region_id", sql)
        self.assertIn("tr.REGION_DESC AS trans_region_name", sql)
        self.assertIn("LEFT JOIN SCH_TRANS_REGIONS tr", sql)
        self.assertEqual(binds, {"current_year": Config.CURRENT_YEAR})

    @patch("repositories.families_repo.query_one")
    def test_single_family_includes_transportation_region(self, query_one):
        query_one.return_value = {
            "family_id": 461,
            "trans_region_id": 89,
            "trans_region_name": "الحرشة - المستنقع المروية",
        }

        family = get_family_by_id(461)

        sql, binds = query_one.call_args.args
        self.assertIn("f.TRANS_REGION_ID AS trans_region_id", sql)
        self.assertIn("tr.REGION_DESC AS trans_region_name", sql)
        self.assertIn("LEFT JOIN SCH_TRANS_REGIONS tr", sql)
        self.assertEqual(binds, {"family_id": 461})
        self.assertEqual(family["trans_region_id"], 89)


if __name__ == "__main__":
    unittest.main()
