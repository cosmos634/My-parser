import unittest
from lead_finder.scoring import classify, score_lead


class ScoringTests(unittest.TestCase):
    def test_buyer_request(self):
        result = score_lead("Нужен Telegram бот", "Нужен бот для автоматизации заказов в магазине.")
        self.assertEqual(result["category"], "telegram_bot")
        self.assertEqual(result["intent"], "buyer_request")
        self.assertGreaterEqual(result["score"], 50)

    def test_freelancer_offer_is_not_hot(self):
        result = score_lead("Предлагаю услуги Python", "Я разработчик, готов выполнить ваш заказ.")
        self.assertEqual(result["intent"], "freelancer_offer")
        self.assertLess(result["score"], 50)

    def test_unrelated_text(self):
        category, intent = classify("Сегодня хорошая погода")
        self.assertEqual(category, "other")
        self.assertEqual(intent, "unclear")


if __name__ == "__main__":
    unittest.main()
