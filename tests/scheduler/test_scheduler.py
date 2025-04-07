import pytest
from unittest.mock import MagicMock, patch
from datetime import timedelta

# 테스트 대상 모듈 임포트 시 경로 문제 해결 (프로젝트 루트 기준)
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.scheduler.scheduler import add_crawl_job, scheduler

@pytest.fixture(autouse=True)
def mock_scheduler():
    """모든 테스트 전에 APScheduler의 add_job 메소드를 모킹합니다."""
    with patch('app.scheduler.scheduler.scheduler.add_job') as mock_add_job:
        yield mock_add_job
    # 각 테스트 후 스케줄러 상태 초기화 (필요하다면)
    # scheduler.remove_all_jobs() # 실제 스케줄러 조작 대신 모킹 활용

@pytest.mark.asyncio
async def test_add_crawl_job_sets_correct_interval(mock_scheduler):
    """add_crawl_job 함수가 site_config에서 읽은 분 단위 간격으로
    interval 트리거를 올바르게 설정하는지 테스트합니다.
    """
    site_config_30_min = {
        'name': 'test_site_30',
        'url': 'http://test30.com',
        'interval_minutes': 30,
        'priority': 1
    }
    site_config_default = {
        'name': 'test_site_default',
        'url': 'http://test_default.com',
        'priority': 2
        # interval_minutes 없음 -> 기본값 60분 사용 기대
    }
    site_config_120_min = {
        'name': 'test_site_120',
        'url': 'http://test120.com',
        'interval_minutes': 120,
        'priority': 3
    }

    # 30분 간격 테스트
    add_crawl_job(site_config_30_min)
    mock_scheduler.assert_called_once()
    call_args, call_kwargs = mock_scheduler.call_args
    assert call_args[1] == 'interval'
    assert call_kwargs['minutes'] == 30
    assert call_kwargs['id'] == 'crawl_test_site_30'
    mock_scheduler.reset_mock()

    # 기본 간격 (60분) 테스트
    add_crawl_job(site_config_default)
    mock_scheduler.assert_called_once()
    call_args, call_kwargs = mock_scheduler.call_args
    assert call_args[1] == 'interval'
    assert call_kwargs['minutes'] == 60 # 기본값 확인
    assert call_kwargs['id'] == 'crawl_test_site_default'
    mock_scheduler.reset_mock()

    # 120분 간격 테스트
    add_crawl_job(site_config_120_min)
    mock_scheduler.assert_called_once()
    call_args, call_kwargs = mock_scheduler.call_args
    assert call_args[1] == 'interval'
    assert call_kwargs['minutes'] == 120
    assert call_kwargs['id'] == 'crawl_test_site_120'

# TODO: 다른 테스트 케이스 구현 (우선순위, 스케줄링 시간 정확성 등) 