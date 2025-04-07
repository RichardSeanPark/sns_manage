import Levenshtein
import logging

logger = logging.getLogger(__name__)

def is_title_duplicate(title1: str, title2: str, threshold: float = 0.8) -> bool:
    """두 제목의 Levenshtein ratio 유사도 점수가 임계값 이상이면 True를 반환합니다."""
    if not title1 or not title2:
        # 제목 중 하나라도 없으면 중복으로 판단하지 않음
        return False
        
    # Levenshtein.ratio() 사용 (0~1 사이 유사도 반환)
    similarity = Levenshtein.ratio(title1.lower(), title2.lower())
    is_duplicate = similarity >= threshold
    
    if is_duplicate:
        logger.debug(f'Title similarity (ratio) {similarity:.3f} >= {threshold}. Considered duplicate:\n  \"{title1}\"\n  \"{title2}\"')
    else:
        logger.debug(f'Title similarity (ratio) {similarity:.3f} < {threshold}. Not considered duplicate.')
        
    return is_duplicate

# --- 향후 추가될 수 있는 데이터 처리 함수들 --- 
# def clean_html(raw_html: str) -> str:
#     pass
# 
# def extract_keywords(text: str) -> list:
#     pass
