import unittest
import os
import json
from modules.rag.used_map import UsedMap

class TestUsedMap(unittest.TestCase):

    def setUp(self):
        self.test_file = "temp/test_used_map.json"
        self.used_map = UsedMap(filepath=self.test_file)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        if os.path.exists(os.path.dirname(self.test_file)):
            os.rmdir(os.path.dirname(self.test_file))

    def test_mark_and_check_usage(self):
        self.used_map.mark_used("chunk_001", context="scene_1")
        self.assertTrue(self.used_map.was_used("chunk_001", "scene_1"))
        self.assertFalse(self.used_map.was_used("chunk_001", "scene_2"))
        
        # Mark again in same context — should not duplicate
        self.used_map.mark_used("chunk_001", context="scene_1")
        self.assertEqual(len(self.used_map.used_map["chunk_001"]), 1)

        # Mark in another context
        self.used_map.mark_used("chunk_001", context="scene_2")
        self.assertTrue(self.used_map.was_used("chunk_001", "scene_2"))
        self.assertEqual(len(self.used_map.used_map["chunk_001"]), 2)

    def test_reset(self):
        self.used_map.mark_used("chunk_999")
        self.used_map.reset()
        self.assertFalse(self.used_map.was_used("chunk_999"))

    def test_save_and_load(self):
        self.used_map.mark_used("chunk_abc", context="test_context")
        self.used_map.save()

        # Load a new instance from file
        new_instance = UsedMap(filepath=self.test_file)
        self.assertTrue(new_instance.was_used("chunk_abc", "test_context"))

if __name__ == "__main__":
    unittest.main()
