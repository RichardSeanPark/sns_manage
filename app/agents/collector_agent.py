from agents import Agent, AgentOutputSchema, ToolContext
from agents.llm_providers import LiteLLMProvider
from pydantic import BaseModel, Field
from typing import List
import os # API 키 환경 변수 사용 예시를 위해 추가

# 도구 임포트
from .tools.data_management_tools import get_collected_data_tool, save_collected_data_tool
from .tools.collection_tools import collect_rss_feeds_tool, crawl_webpage_tool
from .tools.scheduler_tools import schedule_collection_task_tool, check_task_status_tool, list_scheduled_tasks_tool
from .tools.monitoring_tools import log_monitoring_start_tool, log_monitoring_end_tool # 모니터링 도구 임포트

# 모델 제공자 설정 (LiteLLM 사용)
# 실제 사용 시 API 키 등 환경 변수 설정 필요
# litellm_provider = LiteLLMProvider(api_key=os.environ.get("YOUR_GEMMA_API_KEY_ENV_VAR"))
# 임시로 Provider 객체만 생성 (추후 설정 필요)
# TODO: Gemma API 키 환경 변수 설정 및 Provider 초기화 코드 활성화 필요
litellm_provider = LiteLLMProvider()

# 에이전트가 사용할 도구 목록
tools = [
    get_collected_data_tool,
    save_collected_data_tool,
    collect_rss_feeds_tool,
    crawl_webpage_tool,
    schedule_collection_task_tool,
    check_task_status_tool,
    list_scheduled_tasks_tool,
    log_monitoring_start_tool, # 모니터링 도구 추가
    log_monitoring_end_tool,   # 모니터링 도구 추가
    # TODO: evaluate_source_quality 도구 추가
]

# 에이전트의 최종 출력 스키마 (예시)
class CollectorAgentOutput(BaseModel):
    status: str = Field(description="수행된 작업의 최종 상태 (예: 'Success', 'Failed')")
    message: str = Field(description="작업 결과 또는 메시지")
    details: dict = Field(default={}, description="추가 상세 정보 (선택적)")

# Collector Agent 정의
collector_agent = Agent(
    name="CollectorAgent",
    instructions="""
당신은 AI 및 LLM 분야의 최신 뉴스를 효율적으로 수집, 관리, 평가하는 자동화된 시스템 관리 에이전트입니다. 당신의 목표는 관련성 높은 최신 정보를 놓치지 않고 시스템에 통합하는 것입니다.

사용 가능한 도구:
- `collect_rss_feeds_tool`: 지정된 RSS 피드 목록 또는 설정된 모든 RSS 피드에서 최신 기사를 수집합니다.
- `crawl_webpage_tool`: 주어진 URL의 웹 페이지에서 제목과 본문 콘텐츠를 추출합니다.
- `schedule_collection_task_tool`: 특정 작업을 스케줄러에 추가합니다.
- `check_task_status_tool`: 스케줄된 작업의 상태를 조회합니다.
- `list_scheduled_tasks_tool`: 스케줄된 모든 작업 목록을 조회합니다.
- `get_collected_data_tool`: 저장된 수집 데이터를 조회합니다 (필터링/페이징 가능).
- `save_collected_data_tool`: 수집된 데이터를 저장소에 저장합니다 (중복 확인 포함).
- `evaluate_source_quality`: 주어진 기준에 따라 데이터 소스의 품질을 평가합니다. (미구현)
- `log_monitoring_start_tool`: 특정 작업의 모니터링 로그 기록을 시작합니다.
- `log_monitoring_end_tool`: 특정 작업의 모니터링 로그 기록을 종료하고 결과를 기록합니다.

주요 임무:
1.  스케줄링된 계획(`schedule_collection_task_tool` 사용 가능)에 따라 `collect_rss_feeds_tool` 및 `crawl_webpage_tool` 도구를 사용하여 주기적으로 데이터를 수집합니다.
2.  데이터 수집 작업 시작 시 `log_monitoring_start_tool`을 호출하여 로그 ID를 얻습니다.
3.  수집된 각 데이터 항목은 `save_collected_data_tool` 도구를 사용하여 저장합니다.
4.  데이터 수집 작업 종료 시 `log_monitoring_end_tool`을 호출하여 로그 ID, 최종 상태, 통계 등을 기록합니다.
5.  정기적으로 `evaluate_source_quality` 도구를 사용하여 등록된 소스들의 품질과 관련성을 평가하고, 결과에 따라 수집 우선순위를 조정할 것을 제안합니다.
6.  수집된 콘텐츠 내에서 새로운 잠재적 정보 소스를 발견하면 보고합니다.
7.  외부 요청(`get_collected_data_tool` 사용) 또는 작업 상태 확인(`check_task_status_tool`, `list_scheduled_tasks_tool` 사용) 요청에 응답합니다.

항상 명확하고 간결하게 응답하며, 작업을 수행하기 위해 어떤 도구를 사용할 것인지 명시하십시오. 모델은 'gemma-3-27b-it'를 사용합니다.
""",
    model="gemma-3-27b-it",
    model_provider=litellm_provider,
    tools=tools,
    output_schema=AgentOutputSchema(CollectorAgentOutput)
)

# 에이전트 사용 예시 (실제 실행은 Runner 등 필요)
async def run_collector_agent(query: str):
    # from agents import Runner, RunConfig
    # config = RunConfig(model_provider=litellm_provider) # 실행 시 Provider 지정
    # result = await Runner.run(collector_agent, input=query, run_config=config)
    # return result
    print(f"Collector Agent would process query: {query}")
    # 임시 반환
    return CollectorAgentOutput(status="Simulated", message="Agent defined, tools need implementation.")
