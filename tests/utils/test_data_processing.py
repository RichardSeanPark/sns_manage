import pytest
import Levenshtein # ratio 값 확인 위해 임포트
from app.utils.data_processing import is_title_duplicate

# === Test calculate_normalized_similarity 함수 제거 ===

# === Test is_title_duplicate ===

# Levenshtein.ratio() 기준 실제 유사도 값 확인 (근사치):
# AI Reads News Fast vs AI Reads News Quick: ratio=0.757
# New Breakthrough... vs Breakthrough... New: ratio=0.882
# The Future of AI in Society vs The Future of AI Society: ratio=0.941
# Slightly Different Title vs Slightly Dif Title: ratio=0.857
# AI Development News vs AI Development Updates: ratio=0.829
# Exploring the latest AI trends vs Exploring latest AI trends: ratio=0.929

@pytest.mark.parametrize("title1, title2, threshold, expected_result", [
    # 중복으로 간주되어야 하는 경우 (ratio 기준)
    ("AI Reads News", "AI Reads News", 0.8, True),                       # 동일 (1.0)
    ("The Future of AI in Society", "The Future of AI Society", 0.8, True), # 유사 (0.941 >= 0.8)
    ("Large Language Models Explained", "large language models explained", 0.8, True), # 대소문자 (1.0)
    ("New Breakthrough in LLM Technology", "Breakthrough in LLM Technology New", 0.8, True), # 단어 순서 변경 (0.882 >= 0.8)
    ("New Breakthrough in LLM Technology", "Breakthrough in LLM Technology New", 0.85, True), # 임계값 높아도 통과 (0.882 >= 0.85)
    ("Exploring the latest AI trends", "Exploring latest AI trends", 0.8, True), # 거의 동일 (0.929 >= 0.8)
    ("Slightly Different Title", "Slightly Dif Title", 0.7, True),      # 임계값 낮으면 중복 (0.857 >= 0.7)
    ("Slightly Different Title", "Slightly Dif Title", 0.8, True),      # 임계값 0.8 이어도 중복 (0.857 >= 0.8)
    ("AI Development News", "AI Development Updates", 0.8, True),     # 유사 단어 (0.829 >= 0.8)

    # 중복으로 간주되지 않아야 하는 경우 (ratio 기준)
    ("AI Reads News Fast", "AI Reads News Quick", 0.8, False),           # 유사 단어 (0.757 < 0.8)
    ("AI Ethics Debate", "Machine Learning Applications", 0.8, False),     # 매우 다름 (ratio 낮음)
    ("Introduction to Python", "Advanced Python Programming", 0.8, False),# 다름 (ratio 낮음)
    ("Why AI is Important", "Is AI Dangerous?", 0.8, False),              # 다름 (ratio 낮음)
    ("New Breakthrough in LLM Technology", "Breakthrough in LLM Technology New", 0.9, False), # 임계값 높이면 중복 아님 (0.882 < 0.9)
    ("Slightly Different Title", "Slightly Dif Title", 0.9, False),     # 임계값 높으면 중복 아님 (0.857 < 0.9)
    ("AI Development News", "AI Development Updates", 0.85, False),    # 임계값 높으면 중복 아님 (0.829 < 0.85)
    ("News Title", "", 0.8, False), # 한쪽 제목 없음
    ("", "Another News Title", 0.8, False), # 한쪽 제목 없음
    ("", "", 0.8, False), # 양쪽 제목 없음
])
def test_is_title_duplicate(title1, title2, threshold, expected_result):
    """is_title_duplicate 함수가 다양한 제목과 임계값에 대해 올바른 결과를 반환하는지 테스트 (ratio 사용)"""
    # print(f"Testing: '{title1}' vs '{title2}' (Threshold: {threshold}) -> Ratio: {Levenshtein.ratio(title1.lower(), title2.lower()):.3f}") # 디버깅용 print 활성화 (테스트 통과 후 주석 처리)
    assert is_title_duplicate(title1, title2, threshold=threshold) == expected_result

def test_is_title_duplicate_default_threshold():
    """is_title_duplicate 함수가 기본 임계값(0.8)으로 올바르게 동작하는지 테스트 (ratio 사용)"""
    assert is_title_duplicate("AI Development News", "AI Development Updates") is True # ratio 0.829
    assert is_title_duplicate("AI Development News", "Completely Different Topic") is False
    assert is_title_duplicate("Exploring the latest AI trends", "Exploring latest AI trends") is True # ratio 0.929
    assert is_title_duplicate("New Breakthrough in LLM Technology", "Breakthrough in LLM Technology New") is True # ratio 0.882
    assert is_title_duplicate("Slightly Different Title", "Slightly Dif Title") is True # ratio 0.857
