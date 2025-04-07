import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.collector.rss_collector import RSSCollector, collect_feeds
from app.config import DATA_DIR, FILTERED_FEEDS_DIR, API_VERSION
from app.models.schemas import FeedItem

router = APIRouter(tags=["rss"])

logger = logging.getLogger(__name__)


@router.post("/feeds/collect", response_model=Dict)
async def collect_rss_feeds(refresh: bool = Query(False, description="강제로 피드 새로고침")):
    """
    모든 RSS 피드를 수집하는 API 엔드포인트
    
    Parameters:
        refresh: 강제로 피드를 새로 수집할지 여부
        
    Returns:
        수집된 피드 수와 상태 정보
    """
    try:
        # 최신 피드 파일 확인
        feed_files = sorted(Path(DATA_DIR / "raw_feeds").glob("feeds_*.json"), reverse=True)
        
        # 최근 파일이 있고 refresh 플래그가 False면 기존 파일 사용
        if feed_files and not refresh:
            latest_file = feed_files[0]
            with open(latest_file, "r", encoding="utf-8") as f:
                items = json.load(f)
            
            return {
                "status": "success",
                "message": f"기존 피드 사용: {latest_file.name}",
                "count": len(items),
                "timestamp": datetime.now().isoformat()
            }
        
        # 피드 수집 실행
        items = collect_feeds()
        
        return {
            "status": "success",
            "message": "RSS 피드 수집 완료",
            "count": len(items),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"RSS 피드 수집 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"RSS 피드 수집 실패: {str(e)}")


@router.get("/feeds/latest", response_model=List[FeedItem])
async def get_latest_feeds(
    limit: int = Query(20, description="반환할 피드 수", ge=1, le=100),
    category: Optional[str] = Query(None, description="필터링할 카테고리"),
    source: Optional[str] = Query(None, description="필터링할 소스")
):
    """
    최신 RSS 피드를 가져오는 API 엔드포인트
    
    Parameters:
        limit: 반환할 피드 수 (최대 100개)
        category: 특정 카테고리로 필터링 (선택 사항)
        source: 특정 소스로 필터링 (선택 사항)
        
    Returns:
        최신 피드 아이템 목록
    """
    try:
        # 최신 피드 파일 찾기
        feed_files = sorted(Path(DATA_DIR / "raw_feeds").glob("feeds_*.json"), reverse=True)
        
        if not feed_files:
            # 파일이 없으면 새로 수집
            items = collect_feeds()
        else:
            # 최신 파일 사용
            latest_file = feed_files[0]
            with open(latest_file, "r", encoding="utf-8") as f:
                items_data = json.load(f)
                items = [FeedItem(**item) for item in items_data]
        
        # 카테고리 필터링
        if category:
            items = [item for item in items if item.source_category == category]
        
        # 소스 필터링
        if source:
            items = [item for item in items if item.source_name == source]
        
        # 최신 순으로 정렬
        items.sort(key=lambda x: x.published, reverse=True)
        
        # 지정된 개수만큼 반환
        return items[:limit]
    except Exception as e:
        logger.error(f"최신 피드 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"최신 피드 조회 실패: {str(e)}")


@router.get("/feeds/categories", response_model=List[str])
async def get_feed_categories():
    """
    사용 가능한 모든 피드 카테고리를 가져오는 API 엔드포인트
    
    Returns:
        카테고리 목록
    """
    try:
        # 최신 피드 파일 찾기
        feed_files = sorted(Path(DATA_DIR / "raw_feeds").glob("feeds_*.json"), reverse=True)
        
        if not feed_files:
            # 파일이 없으면 빈 목록 반환
            return []
        
        # 최신 파일 사용
        latest_file = feed_files[0]
        with open(latest_file, "r", encoding="utf-8") as f:
            items_data = json.load(f)
            categories = set(item["source_category"] for item in items_data)
        
        return sorted(list(categories))
    except Exception as e:
        logger.error(f"카테고리 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"카테고리 조회 실패: {str(e)}")


@router.get("/feeds/sources", response_model=List[Dict])
async def get_feed_sources(category: Optional[str] = Query(None, description="필터링할 카테고리")):
    """
    사용 가능한 모든 피드 소스를 가져오는 API 엔드포인트
    
    Parameters:
        category: 특정 카테고리로 필터링 (선택 사항)
        
    Returns:
        소스 목록 (이름, URL, 카테고리 포함)
    """
    try:
        # 최신 피드 파일 찾기
        feed_files = sorted(Path(DATA_DIR / "raw_feeds").glob("feeds_*.json"), reverse=True)
        
        if not feed_files:
            # 파일이 없으면 빈 목록 반환
            return []
        
        # 최신 파일 사용
        latest_file = feed_files[0]
        with open(latest_file, "r", encoding="utf-8") as f:
            items_data = json.load(f)
            
            # 소스 정보 추출
            sources = set()
            for item in items_data:
                # 카테고리 필터링
                if category and item["source_category"] != category:
                    continue
                
                sources.add((item["source_name"], item["source_url"], item["source_category"]))
        
        # 소스 정보를 딕셔너리 리스트로 변환
        result = [
            {"name": name, "url": url, "category": category}
            for name, url, category in sources
        ]
        
        return sorted(result, key=lambda x: x["name"])
    except Exception as e:
        logger.error(f"소스 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"소스 조회 실패: {str(e)}")


@router.get("/feeds/search", response_model=List[FeedItem])
async def search_feeds(
    query: str = Query(..., description="검색 쿼리"),
    limit: int = Query(20, description="반환할 피드 수", ge=1, le=100),
    category: Optional[str] = Query(None, description="필터링할 카테고리"),
    source: Optional[str] = Query(None, description="필터링할 소스")
):
    """
    피드를 검색하는 API 엔드포인트
    
    Parameters:
        query: 검색 쿼리
        limit: 반환할 피드 수 (최대 100개)
        category: 특정 카테고리로 필터링 (선택 사항)
        source: 특정 소스로 필터링 (선택 사항)
        
    Returns:
        검색 결과 피드 아이템 목록
    """
    try:
        # 최신 피드 파일 찾기
        feed_files = sorted(Path(DATA_DIR / "raw_feeds").glob("feeds_*.json"), reverse=True)
        
        if not feed_files:
            # 파일이 없으면 빈 목록 반환
            return []
        
        # 최신 파일 사용
        latest_file = feed_files[0]
        with open(latest_file, "r", encoding="utf-8") as f:
            items_data = json.load(f)
            items = [FeedItem(**item) for item in items_data]
        
        # 검색 쿼리로 필터링 (제목, 설명, 내용에서 검색)
        query = query.lower()
        filtered_items = []
        
        for item in items:
            if (query in item.title.lower() or 
                (item.description and query in item.description.lower()) or 
                (item.content and query in item.content.lower())):
                
                # 카테고리 필터링
                if category and item.source_category != category:
                    continue
                
                # 소스 필터링
                if source and item.source_name != source:
                    continue
                
                filtered_items.append(item)
        
        # 최신 순으로 정렬
        filtered_items.sort(key=lambda x: x.published, reverse=True)
        
        # 지정된 개수만큼 반환
        return filtered_items[:limit]
    except Exception as e:
        logger.error(f"피드 검색 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"피드 검색 실패: {str(e)}")


@router.get("/feeds/{feed_id}", response_model=FeedItem)
async def get_feed_by_id(feed_id: str):
    """
    ID로 특정 피드를 가져오는 API 엔드포인트
    
    Parameters:
        feed_id: 피드 ID
        
    Returns:
        피드 아이템 상세 정보
    """
    try:
        # 모든 피드 파일 검색 (최신부터)
        feed_files = sorted(Path(DATA_DIR / "raw_feeds").glob("feeds_*.json"), reverse=True)
        
        for feed_file in feed_files:
            with open(feed_file, "r", encoding="utf-8") as f:
                items_data = json.load(f)
                
                # ID로 찾기
                for item_data in items_data:
                    if item_data["id"] == feed_id:
                        return FeedItem(**item_data)
        
        # 찾지 못한 경우
        raise HTTPException(status_code=404, detail=f"피드 ID {feed_id}를 찾을 수 없습니다")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"피드 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"피드 조회 실패: {str(e)}")


@router.get("/status", response_model=Dict)
async def get_api_status():
    """
    API 및 시스템 상태 정보를 반환하는 엔드포인트
    """
    return {
        "status": "ok", 
        "timestamp": datetime.now().isoformat(),
        "version": API_VERSION
    }
