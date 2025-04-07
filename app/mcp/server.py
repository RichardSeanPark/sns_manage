import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import mcp
from mcp.server.fastmcp import FastMCP, Context
# Context import 제거 (API 변경으로 추정)
# from mcp.types import Context 

from app.collector.rss_collector import collect_feeds
from app.config import (
    DATA_DIR, MCP_ENABLED, MCP_HOST, MCP_PORT, RSS_SOURCES, 
    FILTERED_FEEDS_DIR, RAW_FEEDS_DIR, SUMMARIES_DIR,
    OPENAI_API_KEY, SUMMARY_MAX_TOKENS, SUMMARY_TEMPERATURE
)
from app.models.schemas import FeedItem

# MCP 도구 모듈 임포트
# import app.mcp.tools

logger = logging.getLogger(__name__)

# MCP 앱 생성
app = FastMCP(
    name="AI News Manager",
    description="AI 및 LLM 관련 최신 뉴스를 자동으로 수집하고 요약하는 MCP 서버",
)


# RSS 피드 수집 도구
@app.tool("collect_rss_feeds")
async def collect_rss_feeds_tool(ctx: Context, refresh: bool = False) -> Dict:
    """
    RSS 피드를 수집하는 도구
    
    Parameters:
        refresh: 강제로 피드를 새로 수집할지 여부 (기본값: False)
    
    Returns:
        Dict: 수집 결과 정보
    """
    try:
        await ctx.report_progress("RSS 피드 수집 중...")
        
        # 최신 피드 파일 확인
        feed_files = sorted(Path(RAW_FEEDS_DIR).glob("feeds_*.json"), reverse=True)
        
        # 새로 수집할지 결정
        if feed_files and not refresh:
            latest_file = feed_files[0]
            with open(latest_file, "r", encoding="utf-8") as f:
                import json
                items = json.load(f)
            
            await ctx.report_progress(f"기존 피드 사용: {latest_file.name}, {len(items)}개 피드 로드됨")
            
            return {
                "status": "success",
                "message": f"기존 피드 사용: {latest_file.name}",
                "count": len(items),
                "timestamp": datetime.now().isoformat()
            }
        
        # 피드 수집 실행
        await ctx.report_progress(f"RSS 피드 {len(RSS_SOURCES)}개 소스에서 수집 시작...")
        items = collect_feeds()
        
        await ctx.report_progress(f"RSS 피드 수집 완료: {len(items)}개 피드 수집됨")
        
        return {
            "status": "success",
            "message": "RSS 피드 수집 완료",
            "count": len(items),
            "timestamp": datetime.now().isoformat(),
            "sources_count": len(RSS_SOURCES)
        }
    except Exception as e:
        logger.error(f"RSS 피드 수집 오류: {str(e)}")
        await ctx.report_progress(f"오류 발생: {str(e)}")
        return {
            "status": "error",
            "message": f"RSS 피드 수집 실패: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


# 최신 피드 조회 도구
@app.tool("get_latest_feeds")
async def get_latest_feeds_tool(
    ctx: Context,
    limit: int = 10, 
    category: Optional[str] = None, 
    source: Optional[str] = None
) -> List[Dict]:
    """
    최신 RSS 피드를 가져오는 도구
    
    Parameters:
        limit: 반환할 피드 수 (기본값: 10, 최대: 50)
        category: 필터링할 카테고리 (선택 사항)
        source: 필터링할 소스 (선택 사항)
    
    Returns:
        List[Dict]: 최신 피드 목록
    """
    try:
        # 최대 50개로 제한
        limit = min(limit, 50)
        
        await ctx.report_progress("최신 피드 조회 중...")
        
        # 최신 피드 파일 찾기
        feed_files = sorted(Path(RAW_FEEDS_DIR).glob("feeds_*.json"), reverse=True)
        
        if not feed_files:
            # 파일이 없으면 새로 수집
            await ctx.report_progress("저장된 피드가 없어 새로 수집합니다...")
            items = collect_feeds()
            await ctx.report_progress(f"RSS 피드 수집 완료: {len(items)}개 피드 수집됨")
        else:
            # 최신 파일 사용
            latest_file = feed_files[0]
            with open(latest_file, "r", encoding="utf-8") as f:
                import json
                items_data = json.load(f)
                items = [FeedItem(**item) for item in items_data]
            
            await ctx.report_progress(f"기존 피드 로드: {latest_file.name}, {len(items)}개 피드")
        
        # 카테고리 필터링
        if category:
            items = [item for item in items if item.source_category == category]
            await ctx.report_progress(f"카테고리 '{category}'로 필터링: {len(items)}개 피드")
        
        # 소스 필터링
        if source:
            items = [item for item in items if item.source_name == source]
            await ctx.report_progress(f"소스 '{source}'로 필터링: {len(items)}개 피드")
        
        # 최신 순으로 정렬
        items.sort(key=lambda x: x.published, reverse=True)
        
        # 지정된 개수만큼 반환
        result_items = items[:limit]
        
        # 결과를 딕셔너리 목록으로 변환
        result = []
        for item in result_items:
            result.append({
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "link": str(item.link),
                "published": item.published.isoformat(),
                "source_name": item.source_name,
                "source_category": item.source_category
            })
        
        await ctx.report_progress(f"최신 피드 {len(result)}개 반환")
        return result
    except Exception as e:
        logger.error(f"최신 피드 조회 오류: {str(e)}")
        await ctx.report_progress(f"오류 발생: {str(e)}")
        return []


# 피드 검색 도구
@app.tool("search_feeds")
async def search_feeds_tool(
    ctx: Context,
    query: str, 
    limit: int = 10, 
    category: Optional[str] = None
) -> List[Dict]:
    """
    RSS 피드를 검색하는 도구
    
    Parameters:
        query: 검색할 키워드
        limit: 반환할 피드 수 (기본값: 10, 최대: 50)
        category: 필터링할 카테고리 (선택 사항)
    
    Returns:
        List[Dict]: 검색 결과 피드 목록
    """
    try:
        # 최대 50개로 제한
        limit = min(limit, 50)
        
        await ctx.report_progress(f"'{query}' 키워드로 피드 검색 중...")
        
        # 최신 피드 파일 찾기
        feed_files = sorted(Path(RAW_FEEDS_DIR).glob("feeds_*.json"), reverse=True)
        
        if not feed_files:
            await ctx.report_progress("저장된 피드가 없어 검색할 수 없습니다.")
            return []
        
        # 최신 파일 사용
        latest_file = feed_files[0]
        with open(latest_file, "r", encoding="utf-8") as f:
            import json
            items_data = json.load(f)
            items = [FeedItem(**item) for item in items_data]
        
        await ctx.report_progress(f"피드 {len(items)}개 로드됨, 검색 시작...")
        
        # 검색 쿼리로 필터링 (제목, 설명, 내용에서 검색)
        query_lower = query.lower()
        filtered_items = []
        
        for item in items:
            if (query_lower in item.title.lower() or 
                (item.description and query_lower in item.description.lower()) or 
                (item.content and query_lower in item.content.lower())):
                
                # 카테고리 필터링
                if category and item.source_category != category:
                    continue
                
                filtered_items.append(item)
        
        await ctx.report_progress(f"검색 결과: {len(filtered_items)}개 피드 발견")
        
        # 최신 순으로 정렬
        filtered_items.sort(key=lambda x: x.published, reverse=True)
        
        # 지정된 개수만큼 반환
        result_items = filtered_items[:limit]
        
        # 결과를 딕셔너리 목록으로 변환
        result = []
        for item in result_items:
            result.append({
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "link": str(item.link),
                "published": item.published.isoformat(),
                "source_name": item.source_name,
                "source_category": item.source_category
            })
        
        await ctx.report_progress(f"검색 결과 {len(result)}개 반환")
        return result
    except Exception as e:
        logger.error(f"피드 검색 오류: {str(e)}")
        await ctx.report_progress(f"오류 발생: {str(e)}")
        return []


# 카테고리 목록 리소스
@app.resource("mcp://categories")
async def get_categories_resource() -> List[str]:
    """
    사용 가능한 모든 피드 카테고리를 가져오는 리소스
    """
    try:
        # 최신 피드 파일 찾기
        feed_files = sorted(Path(RAW_FEEDS_DIR).glob("feeds_*.json"), reverse=True)
        
        if not feed_files:
            # 파일이 없으면 고정된 카테고리 목록 반환
            categories = set(source["category"] for source in RSS_SOURCES)
            return sorted(list(categories))
        
        # 최신 파일 사용
        latest_file = feed_files[0]
        with open(latest_file, "r", encoding="utf-8") as f:
            import json
            items_data = json.load(f)
            categories = set(item["source_category"] for item in items_data)
        
        return sorted(list(categories))
    except Exception as e:
        logger.error(f"카테고리 조회 오류: {str(e)}")
        return []


# 소스 목록 리소스
@app.resource("mcp://sources")
async def get_sources_resource() -> List[Dict]:
    """
    사용 가능한 모든 피드 소스를 가져오는 리소스
    """
    try:
        # 기본 소스 목록 변환
        sources = [
            {"name": source["name"], "url": source["url"], "category": source["category"]}
            for source in RSS_SOURCES
        ]
        
        return sorted(sources, key=lambda x: x["name"])
    except Exception as e:
        logger.error(f"소스 조회 오류: {str(e)}")
        return []


# 요약 목록 리소스
@app.resource("mcp://summaries?limit={limit}")
async def get_summaries_resource(limit: int = 10) -> List[Dict]:
    """
    저장된 요약 목록을 가져오는 리소스
    """
    try:
        # 최대 50개로 제한
        limit = min(limit, 50)
        
        # 요약 파일 목록 가져오기
        summary_files = sorted(Path(SUMMARIES_DIR).glob("summary_*.json"), reverse=True)
        
        # 요약 데이터 로드
        summaries = []
        
        for file_path in summary_files[:limit]:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    summary_data = json.load(f)
                    summaries.append(summary_data)
            except Exception as e:
                logger.error(f"요약 파일 '{file_path}' 로드 오류: {str(e)}")
        
        return summaries
    except Exception as e:
        logger.error(f"요약 목록 조회 오류: {str(e)}")
        return []


# 서버 상태 리소스
@app.resource("mcp://status")
async def get_status_resource() -> Dict:
    """
    서버 상태 정보를 제공하는 리소스
    """
    try:
        # 최신 피드 파일 찾기
        feed_files = sorted(Path(RAW_FEEDS_DIR).glob("feeds_*.json"), reverse=True)
        
        status_info = {
            "status": "online",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "sources_count": len(RSS_SOURCES)
        }
        
        if feed_files:
            latest_file = feed_files[0]
            # 파일 이름에서 타임스탬프 추출 (feeds_YYYYMMDD_HHMMSS.json)
            filename = latest_file.name
            timestamp_str = filename.replace("feeds_", "").replace(".json", "")
            
            with open(latest_file, "r", encoding="utf-8") as f:
                import json
                items_data = json.load(f)
            
            status_info.update({
                "latest_collection": timestamp_str,
                "feed_count": len(items_data)
            })
        else:
            status_info.update({
                "latest_collection": None,
                "feed_count": 0
            })
        
        return status_info
    except Exception as e:
        logger.error(f"상태 확인 오류: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# --- Summarizer 도구 함수들 ---
async def summarize_feed(ctx: Context, feed_item: FeedItem) -> Optional[Dict]:
    """
    하나의 피드 항목을 요약하는 함수 (헬퍼)
    """
    try:
        await ctx.report_progress(f"피드 '{feed_item.title}' 요약 중...")
        
        content_to_summarize = ""
        if feed_item.content and len(feed_item.content) > 100:
            content_to_summarize = feed_item.content
        elif feed_item.description and len(feed_item.description) > 100:
            content_to_summarize = feed_item.description
        else:
            logger.warning(f"피드 ID {feed_item.id}의 요약 가능한 내용이 부족합니다.")
            await ctx.report_progress(f"피드 '{feed_item.title}'의 요약 가능한 내용이 부족합니다.")
            return None
        
        prompt = f"""다음 뉴스 내용을 3~5개의 중요 포인트로 요약해주세요.
제목: {feed_item.title}
출처: {feed_item.source_name}
내용:
{content_to_summarize}

format:
- 핵심 포인트 1
- 핵심 포인트 2
- ...

요약:
"""
        
        # Assuming ctx has openai_completion method if using MCP's OpenAI integration
        # If not, you need to initialize OpenAI client here or pass it
        # For now, let's assume ctx has it (might need adjustment)
        if not hasattr(ctx, 'openai_completion'):
             logger.error("MCP Context does not have 'openai_completion'. OpenAI client setup needed.")
             await ctx.report_progress("오류: OpenAI 클라이언트 설정 필요.")
             # Attempt to use environment variable directly as fallback? Risky.
             # Or raise an error / return None clearly indicating setup issue.
             return None # Indicate failure due to missing capability

        response = await ctx.openai_completion(
            model="gpt-3.5-turbo", # Consider making model configurable
            messages=[
                {"role": "system", "content": "당신은 기술, AI, 머신러닝, LLM 뉴스를 요약하는 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=SUMMARY_MAX_TOKENS,
            temperature=SUMMARY_TEMPERATURE,
        )
        
        summary_text = response.choices[0].message.content.strip()
        
        summary_result = {
            "id": feed_item.id,
            "title": feed_item.title,
            "original_link": str(feed_item.link),
            "source_name": feed_item.source_name,
            "source_category": feed_item.source_category,
            "published": feed_item.published.isoformat() if isinstance(feed_item.published, datetime) else str(feed_item.published),
            "summarized_at": datetime.now().isoformat(),
            "summary": summary_text
        }
        
        os.makedirs(SUMMARIES_DIR, exist_ok=True)
        summary_file = Path(SUMMARIES_DIR) / f"summary_{feed_item.id}.json"
        
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary_result, f, ensure_ascii=False, indent=2)
        
        await ctx.report_progress(f"'{feed_item.title}' 요약 완료 및 저장됨")
        
        return summary_result
    except Exception as e:
        # Check for specific OpenAI errors if possible
        logger.error(f"피드 ID {feed_item.id} 요약 중 오류: {str(e)}")
        await ctx.report_progress(f"요약 오류 발생: {feed_item.title} - {str(e)}")
        return None

@app.tool("summarize_feed_by_id")
async def summarize_feed_by_id_tool(ctx: Context, feed_id: str) -> Dict:
    """
    ID로 특정 피드를 요약하는 도구
    """
    try:
        # Need a way to get feed by ID. Assuming a helper function or direct load.
        # For testing, let's load directly from the latest raw feed file if possible.
        feed_files = sorted(Path(RAW_FEEDS_DIR).glob("feeds_*.json"), reverse=True)
        feed_item = None
        if feed_files:
             latest_file = feed_files[0]
             try:
                 with open(latest_file, "r", encoding="utf-8") as f:
                      items_data = json.load(f)
                      for item_data in items_data:
                           if item_data.get("id") == feed_id:
                                feed_item = FeedItem(**item_data)
                                break
             except Exception as e:
                  logger.error(f"Error loading feed {feed_id} from {latest_file.name}: {e}")
                  await ctx.report_progress(f"오류: 피드 {feed_id} 로드 실패.")
                  return {"status": "error", "message": f"피드 {feed_id} 로드 중 오류 발생"}

        if not feed_item:
            await ctx.report_progress(f"ID '{feed_id}'에 해당하는 피드를 찾을 수 없습니다.")
            return {
                "status": "error",
                "message": f"ID '{feed_id}'에 해당하는 피드를 찾을 수 없습니다.",
                "feed_id": feed_id
            }
        
        summary_file = Path(SUMMARIES_DIR) / f"summary_{feed_id}.json"
        if summary_file.exists():
            try:
                with open(summary_file, "r", encoding="utf-8") as f:
                    summary_data = json.load(f)
                await ctx.report_progress(f"피드 '{feed_item.title}'는 이미 요약되어 있습니다.")
                return {
                    "status": "success",
                    "message": "이미 요약된 피드입니다.",
                    "summary": summary_data,
                    "is_new": False
                }
            except Exception as e:
                 logger.warning(f"Error reading existing summary file {summary_file}: {e}. Will re-summarize.")
                 await ctx.report_progress(f"기존 요약 파일 읽기 오류. 다시 요약합니다: {feed_item.title}")

        summary_result = await summarize_feed(ctx, feed_item)
        
        if not summary_result:
            return {
                "status": "error",
                "message": "피드 요약에 실패했습니다.",
                "feed_id": feed_id
            }
        
        return {
            "status": "success",
            "message": "피드 요약이 완료되었습니다.",
            "summary": summary_result,
            "is_new": True
        }
    except Exception as e:
        logger.error(f"피드 요약 도구 (ID: {feed_id}) 오류: {str(e)}")
        await ctx.report_progress(f"요약 도구 (ID: {feed_id}) 오류 발생: {str(e)}")
        return {
            "status": "error",
            "message": f"요약 처리 중 오류 발생: {str(e)}",
            "feed_id": feed_id
        }

@app.tool("summarize_latest_feeds")
async def summarize_latest_feeds_tool(
    ctx: Context, 
    limit: int = 5, 
    category: Optional[str] = None
) -> Dict:
    """
    최신 피드를 요약하는 도구
    """
    try:
        limit = min(limit, 10) # Keep limit reasonable
        
        # Use the get_latest_feeds_tool logic directly to get feeds
        feeds_dict = await get_latest_feeds_tool(ctx, limit=limit, category=category)
        
        # Convert dicts back to FeedItem objects for summarize_feed
        feeds_to_process = []
        for feed_data in feeds_dict:
             try:
                  # Ensure published is datetime if possible
                  if isinstance(feed_data.get('published'), str):
                       feed_data['published'] = datetime.fromisoformat(feed_data['published'])
                  feeds_to_process.append(FeedItem(**feed_data))
             except Exception as e:
                  logger.warning(f"Skipping feed for summarization due to validation error: {e} - ID: {feed_data.get('id', 'N/A')}")


        if not feeds_to_process:
            await ctx.report_progress("요약할 피드가 없습니다.")
            return {
                "status": "success", # Or error? Depends on expectation. Success = 0 feeds.
                "message": "요약할 피드가 없습니다.",
                "new_summaries": [],
                "existing_summaries": [],
                "total_count": 0
            }
        
        await ctx.report_progress(f"{len(feeds_to_process)}개의 피드 요약 시작...")
        
        already_summarized_data = []
        to_summarize_items = []
        
        for feed in feeds_to_process:
            summary_file = Path(SUMMARIES_DIR) / f"summary_{feed.id}.json"
            if summary_file.exists():
                 try:
                     with open(summary_file, "r", encoding="utf-8") as f:
                          summary_data = json.load(f)
                     already_summarized_data.append(summary_data)
                 except Exception as e:
                      logger.warning(f"Error reading existing summary file {summary_file}: {e}. Will re-summarize.")
                      to_summarize_items.append(feed)
            else:
                to_summarize_items.append(feed)
        
        new_summaries_results = []
        # Use asyncio.gather for concurrent summarization
        tasks = [summarize_feed(ctx, feed) for feed in to_summarize_items]
        results = await asyncio.gather(*tasks)
        
        for result in results:
            if result:
                new_summaries_results.append(result)
        
        return {
            "status": "success",
            "message": f"피드 요약 완료: 새로운 요약 {len(new_summaries_results)}개, 기존 요약 {len(already_summarized_data)}개",
            "new_summaries": new_summaries_results,
            "existing_summaries": already_summarized_data,
            "total_count": len(new_summaries_results) + len(already_summarized_data)
        }
    except Exception as e:
        logger.error(f"최신 피드 요약 도구 오류: {str(e)}")
        await ctx.report_progress(f"요약 도구 오류 발생: {str(e)}")
        return {
            "status": "error",
            "message": f"최신 피드 요약 중 오류 발생: {str(e)}"
        }

# --- Voice 도구 함수들 ---
@app.tool("speak_summary")
async def speak_summary_tool(ctx: Context, summary_id: str, language: str = "ko-kr") -> Dict:
    """
    요약된 내용을 음성으로 읽어주는 도구
    """
    try:
        # 요약 데이터 로드
        summary_file = Path(SUMMARIES_DIR) / f"summary_{summary_id}.json"
        
        if not summary_file.exists():
            await ctx.report_progress(f"ID '{summary_id}'에 해당하는 요약을 찾을 수 없습니다.")
            return {
                "status": "error",
                "message": f"ID '{summary_id}'에 해당하는 요약을 찾을 수 없습니다."
            }
        
        with open(summary_file, "r", encoding="utf-8") as f:
            summary_data = json.load(f)
        
        # 읽을 텍스트 준비
        title = summary_data.get("title", "제목 없음")
        source = summary_data.get("source_name", "출처 불명")
        summary_text = summary_data.get("summary", "요약 내용이 없습니다.")
        
        text_to_speak = f"{title}. {source} 기사 요약입니다. {summary_text}"
        
        # Assuming ctx has tts method
        if not hasattr(ctx, 'tts'):
             logger.error("MCP Context does not have 'tts'. TTS capability needed.")
             await ctx.report_progress("오류: TTS 기능 설정 필요.")
             return {"status": "error", "message": "TTS 기능이 활성화되지 않았습니다."}

        await ctx.tts(text=text_to_speak, language=language)
        await ctx.report_progress(f"'{title}' 요약 음성 출력 완료")
        
        return {
            "status": "success",
            "message": "요약 음성 출력 완료",
            "title": title,
            "source": source
        }
    except Exception as e:
        logger.error(f"요약 음성 출력 오류: {str(e)}")
        await ctx.report_progress(f"음성 출력 오류: {str(e)}")
        return {
            "status": "error",
            "message": f"음성 출력 중 오류 발생: {str(e)}"
        }

@app.tool("read_latest_news")
async def read_latest_news_tool(
    ctx: Context, 
    limit: int = 3, 
    category: Optional[str] = None,
    language: str = "ko-kr"
) -> Dict:
    """
    최신 뉴스를 찾아서 요약하고 음성으로 읽어주는 도구
    """
    try:
        limit = min(limit, 5)
        await ctx.report_progress("최신 뉴스 요약 및 음성 출력 준비 중...")
        
        # Call the already defined tool function
        summary_result = await summarize_latest_feeds_tool(ctx, limit=limit, category=category)
        
        if summary_result["status"] != "success" or summary_result["total_count"] == 0:
            await ctx.report_progress("읽어줄 뉴스가 없습니다.")
            return {
                "status": "error",
                "message": "읽어줄 뉴스가 없습니다."
            }
        
        all_summaries = summary_result.get("new_summaries", []) + summary_result.get("existing_summaries", [])
        # Ensure summaries are sorted by published date (descending)
        all_summaries.sort(key=lambda x: x.get("published", ""), reverse=True)
        
        await ctx.report_progress(f"{len(all_summaries)}개의 뉴스를 음성으로 출력합니다.")
        
        if not hasattr(ctx, 'tts'):
             logger.error("MCP Context does not have 'tts'. TTS capability needed for read_latest_news.")
             await ctx.report_progress("오류: TTS 기능 설정 필요.")
             return {"status": "error", "message": "TTS 기능이 활성화되지 않았습니다."}

        for idx, summary in enumerate(all_summaries[:limit], 1):
            title = summary.get("title", "제목 없음")
            source = summary.get("source_name", "출처 불명")
            summary_text = summary.get("summary", "요약 내용이 없습니다.")
            
            if idx > 1:
                await ctx.report_progress("다음 뉴스로 넘어갑니다.")
                await ctx.tts(text="다음 뉴스입니다.", language=language)
            
            news_text = f"{idx}번째 뉴스. {title}. {source} 기사 요약입니다. {summary_text}"
            await ctx.tts(text=news_text, language=language)
            await ctx.report_progress(f"{idx}번째 뉴스 '{title}' 출력 완료")
        
        await ctx.report_progress("모든 뉴스 음성 출력 완료")
        
        return {
            "status": "success",
            "message": f"{len(all_summaries[:limit])}개의 뉴스 음성 출력 완료",
            "count": len(all_summaries[:limit])
        }
    except Exception as e:
        logger.error(f"뉴스 읽기 오류: {str(e)}")
        await ctx.report_progress(f"뉴스 읽기 오류: {str(e)}")
        return {
            "status": "error",
            "message": f"뉴스 읽기 중 오류 발생: {str(e)}"
        }

# --- 리소스 함수들 ---
@app.resource("mcp://categories")
async def get_categories_resource() -> List[str]:
    """
    사용 가능한 모든 피드 카테고리를 가져오는 리소스
    """
    try:
        feed_files = sorted(Path(RAW_FEEDS_DIR).glob("feeds_*.json"), reverse=True)
        categories = set(source["category"] for source in RSS_SOURCES) # Start with config

        if feed_files:
            latest_file = feed_files[0]
            try:
                with open(latest_file, "r", encoding="utf-8") as f:
                    items_data = json.load(f)
                    # Add categories from actual feeds
                    for item in items_data:
                         if item.get("source_category"):
                              categories.add(item["source_category"])
            except Exception as e:
                 logger.warning(f"Error reading categories from {latest_file.name}: {e}")
        
        return sorted(list(categories))
    except Exception as e:
        logger.error(f"카테고리 조회 오류: {str(e)}")
        return []

@app.resource("mcp://sources")
async def get_sources_resource() -> List[Dict]:
    """
    사용 가능한 모든 피드 소스를 가져오는 리소스
    """
    try:
        sources = [
            {"name": source["name"], "url": source["url"], "category": source["category"]}
            for source in RSS_SOURCES
        ]
        return sorted(sources, key=lambda x: x["name"])
    except Exception as e:
        logger.error(f"소스 조회 오류: {str(e)}")
        return []

@app.resource("mcp://summaries?limit={limit}")
async def get_summaries_resource(limit: int = 10) -> List[Dict]:
    """
    저장된 요약 목록을 가져오는 리소스
    """
    try:
        limit = min(limit, 50)
        summary_files = sorted(Path(SUMMARIES_DIR).glob("summary_*.json"), reverse=True)
        summaries = []
        for file_path in summary_files[:limit]:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    summary_data = json.load(f)
                    summaries.append(summary_data)
            except Exception as e:
                logger.error(f"요약 파일 '{file_path}' 로드 오류: {str(e)}")
        return summaries
    except Exception as e:
        logger.error(f"요약 목록 조회 오류: {str(e)}")
        return []

@app.resource("mcp://status")
async def get_status_resource() -> Dict:
    """
    서버 상태 정보를 제공하는 리소스
    """
    try:
        feed_files = sorted(Path(RAW_FEEDS_DIR).glob("feeds_*.json"), reverse=True)
        status_info = {
            "status": "online",
            "version": "1.0.0", # Consider making version dynamic
            "timestamp": datetime.now().isoformat(),
            "sources_count": len(RSS_SOURCES)
        }
        
        if feed_files:
            latest_file = feed_files[0]
            filename = latest_file.name
            try:
                 timestamp_str = filename.split('_')[1].split('.')[0] # More robust extraction
                 status_info["latest_collection_timestamp_str"] = timestamp_str # Store raw string
                 # Optionally parse to datetime for validation/display
                 # status_info["latest_collection_dt"] = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S").isoformat()
            except IndexError:
                 logger.warning(f"Could not parse timestamp from filename: {filename}")
                 status_info["latest_collection_timestamp_str"] = None
            
            try:
                with open(latest_file, "r", encoding="utf-8") as f:
                     items_data = json.load(f)
                status_info["feed_count"] = len(items_data)
            except Exception as e:
                 logger.warning(f"Could not read feed count from {latest_file.name}: {e}")
                 status_info["feed_count"] = None # Indicate count is unavailable
        else:
            status_info["latest_collection_timestamp_str"] = None
            status_info["feed_count"] = 0
        
        # Add summary count
        try:
             summary_files = list(Path(SUMMARIES_DIR).glob("summary_*.json"))
             status_info["summary_count"] = len(summary_files)
        except Exception as e:
             logger.warning(f"Could not count summary files: {e}")
             status_info["summary_count"] = None

        return status_info
    except Exception as e:
        logger.error(f"상태 확인 오류: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# --- 서버 실행 함수들 ---
async def run_mcp_server():
    """
    MCP 서버 실행 함수
    """
    if not MCP_ENABLED:
        logger.warning("MCP 서버가 비활성화되어 있습니다.")
        return
    
    try:
        # MCP 앱 객체의 속성을 직접 확인하여 개수 로깅 (오류 발생 시 주석 처리)
        tools_count = len(app.tool) if hasattr(app, 'tool') and isinstance(app.tool, (dict, list)) else 'N/A' 
        resources_count = len(app.resource) if hasattr(app, 'resource') and isinstance(app.resource, (dict, list)) else 'N/A'
        logger.info(f"MCP 서버 시작 중: http://{MCP_HOST}:{MCP_PORT}")
        logger.info(f"등록된 도구: {tools_count}개, 리소스: {resources_count}개")
        
        # Log tool and resource names for debugging (use keys if they are dicts)
        # if isinstance(tools_count, int) and tools_count > 0:
        #     for name in app.tool.keys(): logger.info(f"- 도구: {name}") 
        # if isinstance(resources_count, int) and resources_count > 0:
        #     for name in app.resource.keys(): logger.info(f"- 리소스: {name}") 
        
        # await app.serve(host=MCP_HOST, port=MCP_PORT) # TODO: FastMCP 서버 실행 방식 확인 필요
        # 임시로 uvicorn 등을 사용하지 않고 대기만 하도록 수정 (테스트 목적)
        await asyncio.sleep(float('inf')) # 서버가 종료되지 않도록 무한 대기
    except Exception as e:
        logger.error(f"MCP 서버 실행 오류: {str(e)}")

def start_mcp_server():
    """
    MCP 서버 시작 헬퍼 함수
    """
    if not MCP_ENABLED:
        logger.warning("MCP 서버가 비활성화되어 있습니다.")
        return
    
    asyncio.run(run_mcp_server())

if __name__ == "__main__":
    start_mcp_server() 