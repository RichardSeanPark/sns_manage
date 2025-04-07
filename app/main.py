import argparse
import logging
import os
import sys
import threading
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes import router as api_router
from app.api.v1.collection import router as collection_router
from app.config import (
    DEBUG, STATIC_DIR, TEMPLATES_DIR, PROJECT_ROOT, 
    SERVER_HOST, SERVER_PORT, API_PREFIX, 
    MCP_ENABLED, MCP_HOST, MCP_PORT
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(PROJECT_ROOT, 'server.log'))
    ]
)

logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="AI News System API",
    description="AI 및 LLM 관련 뉴스 수집 및 요약 시스템 API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 제공
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 템플릿 엔진 설정
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# API 라우터 등록
app.include_router(api_router, prefix=API_PREFIX)
app.include_router(collection_router)

# MCP 서버 임포트 및 시작
if MCP_ENABLED:
    from app.mcp.server import start_mcp_server

@app.get("/")
async def root(request: Request):
    """
    메인 페이지 렌더링
    """
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "AI News System",
            "api_url": f"{request.base_url}api/v1",
            "mcp_enabled": MCP_ENABLED,
            "mcp_url": f"http://{MCP_HOST}:{MCP_PORT}" if MCP_ENABLED else None,
        }
    )

@app.get("/health")
async def health_check():
    """
    서버 상태 확인 엔드포인트
    """
    return {"status": "healthy"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    전역 예외 핸들러
    """
    logger.error(f"서버 오류: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "내부 서버 오류가 발생했습니다.", "message": str(exc)},
    )

def parse_args():
    """
    명령줄 인수 파싱
    """
    parser = argparse.ArgumentParser(description="AI News System 서버")
    parser.add_argument("--host", type=str, default=SERVER_HOST, help="서버 호스트")
    parser.add_argument("--port", type=int, default=SERVER_PORT, help="서버 포트")
    parser.add_argument("--reload", action="store_true", help="자동 리로드 활성화")
    parser.add_argument("--debug", action="store_true", help="디버그 모드 활성화")
    parser.add_argument("--no-mcp", action="store_true", help="MCP 서버 비활성화")
    return parser.parse_args()

def start_mcp_in_thread():
    """
    별도 스레드에서 MCP 서버 시작
    """
    if not MCP_ENABLED:
        logger.info("MCP 서버가 비활성화되어 있습니다.")
        return
    
    # MCP 서버 시작
    from app.mcp.server import start_mcp_server
    
    try:
        logger.info(f"MCP 서버 시작 중 (스레드): http://{MCP_HOST}:{MCP_PORT}")
        mcp_thread = threading.Thread(target=start_mcp_server, daemon=True)
        mcp_thread.start()
        logger.info("MCP 서버 스레드가 시작되었습니다.")
    except Exception as e:
        logger.error(f"MCP 서버 시작 실패: {str(e)}", exc_info=True)

def run_server():
    """
    서버 실행
    """
    args = parse_args()
    
    # 디버그 모드 설정
    debug_mode = args.debug or DEBUG
    
    # MCP 서버 시작 (별도 스레드)
    if MCP_ENABLED and not args.no_mcp:
        start_mcp_in_thread()
    
    # FastAPI 서버 시작
    logger.info(f"서버 시작: http://{args.host}:{args.port}")
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="debug" if debug_mode else "info",
    )

if __name__ == "__main__":
    run_server()
