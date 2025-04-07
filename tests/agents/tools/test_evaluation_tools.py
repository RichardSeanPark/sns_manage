import pytest
from unittest.mock import patch
from pydantic import HttpUrl

# 테스트 대상 도구 임포트
from app.agents.tools.evaluation_tools import (
    evaluate_source_quality_tool,
    EvaluateSourceInput,
    EvaluationResult
)
# random 모듈 임포트 (패치 대상)
import random

# --- Tests for evaluate_source_quality_tool (Temporary Implementation) ---

@patch('app.agents.tools.evaluation_tools.random.uniform') # random.uniform 패치
@pytest.mark.asyncio
async def test_evaluate_returns_result(mock_random_uniform: patch):
    """유효한 URL 입력 시 EvaluationResult 객체 반환 확인 (임시 구현 기준)"""
    mock_score = 0.75 # 모의 점수 설정
    mock_random_uniform.return_value = mock_score
    test_url = HttpUrl("http://test-source.com/news")
    input_data = EvaluateSourceInput(source_url=test_url)

    result = await evaluate_source_quality_tool(input_data)

    mock_random_uniform.assert_called_once_with(0.5, 0.95) # 호출 인자 확인
    assert isinstance(result, EvaluationResult)
    assert result.source_url == test_url
    # round 처리된 값 비교
    assert result.quality_score == round(mock_score, 2)
    assert isinstance(result.reasoning, str) # 임시 근거 문자열 확인
    assert str(test_url) in result.reasoning # URL이 근거에 포함되는지 확인

@patch('app.agents.tools.evaluation_tools.random.uniform')
@pytest.mark.asyncio
async def test_evaluate_score_is_rounded(mock_random_uniform: patch):
    """반환된 점수가 소수점 둘째 자리로 반올림되는지 확인"""
    mock_score = 0.833333
    mock_random_uniform.return_value = mock_score
    test_url = HttpUrl("http://another-source.org")
    input_data = EvaluateSourceInput(source_url=test_url)

    result = await evaluate_source_quality_tool(input_data)

    assert result.quality_score == 0.83 # round(0.833333, 2)

# 참고: 실제 평가 로직이 구현되면 이 테스트들은 해당 로직을 반영하도록 수정되어야 합니다.
# 예를 들어, LLM 호출을 모의 처리하거나, 규칙 기반 점수 계산 로직을 검증해야 합니다.
