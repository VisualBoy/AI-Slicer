import unittest
import json
from ai_slicer import analyze_printability, select_print_profile

class TestAiSlicerFunctions(unittest.TestCase):

    def test_analyze_printability(self):
        """
        Test the analyze_printability function.
        """
        dummy_file_path = "dummy_model.stl"
        expected_json_string = '{"overhangs": "excessive", "thin_walls": "detected", "non_manifold_edges": "none"}'
        
        result = analyze_printability(dummy_file_path)
        
        # Compare the dictionary objects for a more robust test
        self.assertEqual(json.loads(result), json.loads(expected_json_string))

    def test_select_print_profile(self):
        """
        Test the select_print_profile function.
        """
        dummy_file_path = "dummy_model.stl"
        dummy_material = "PLA"
        dummy_outcome = "fast_prototype"
        expected_json_string = '{"profile_name": "draft_pla_0.2mm", "reason": "Selected based on PLA material and \'fast_prototype\' outcome."}'
        
        result = select_print_profile(dummy_file_path, dummy_material, dummy_outcome)
        
        # Compare the dictionary objects for a more robust test
        self.assertEqual(json.loads(result), json.loads(expected_json_string))

if __name__ == '__main__':
    unittest.main()
