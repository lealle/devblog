import unittest
from scripts.classify_articles import classify

class ClassificationTests(unittest.TestCase):
    def test_multiple_topics(self):
        result = classify({"title": "Spring Boot Redis 성능 최적화", "summary": ""})
        self.assertIn("Backend", result["topics"])
        self.assertIn("Database", result["topics"])
        self.assertIn("Engineering", result["topics"])

    def test_no_guess_for_unknown(self):
        result = classify({"title": "Company announcements", "summary": ""})
        self.assertEqual(result["topics"], [])
        self.assertEqual(result["content_type"], "general")

    def test_troubleshooting_type(self):
        result = classify({"title": "서비스 장애 분석", "summary": "오류 해결"})
        self.assertEqual(result["content_type"], "troubleshooting")

if __name__ == "__main__":
    unittest.main()
