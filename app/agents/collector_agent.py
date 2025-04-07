from agents import Agent, AgentOutputSchema, ToolContext
from agents.llm_providers import LiteLLMProvider
from pydantic import BaseModel, Field
from typing import List
import os # API 키 환경 변수 사용 예시를 위해 추가

# 모델 제공자 설정 (LiteLLM 사용)
# 실제 사용 시 API 키 등 환경 변수 설정 필요
# litellm_provider = LiteLLMProvider(api_key=os.environ.get("YOUR_GEMMA_API_KEY_ENV_VAR"))
# 임시로 Provider 객체만 생성 (추후 설정 필요)
# TODO: Gemma API 키 환경 변수 설정 및 Provider 초기화 코드 활성화 필요
litellm_provider = LiteLLMProvider()

# 에이전트가 사용할 도구 목록 (추후 실제 함수/클래스로 대체)
# tools = [collect_rss_tool, crawl_webpage_tool, ...]
tools = [] # 우선 빈 리스트

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
- `collect_rss_feeds`: 지정된 RSS 피드 목록에서 최신 기사를 수집합니다.
- `crawl_webpage`: 주어진 URL의 웹 페이지 콘텐츠를 수집합니다.
- `schedule_collection_task`: 특정 시간에 데이터 수집 작업을 예약합니다.
- `check_task_status`: 특정 수집 작업의 상태를 조회합니다.
- `get_collected_data`: 저장된 수집 데이터를 조회합니다 (필터링/페이징 가능).
- `save_collected_data`: 수집된 데이터를 저장소에 저장합니다 (중복 확인 포함).
- `evaluate_source_quality`: 주어진 기준에 따라 데이터 소스의 품질을 평가합니다.
- `log_monitoring_event`: 시스템 모니터링 이벤트를 기록합니다.
- (추가 도구 정의...)

주요 임무:
1.  스케줄링된 계획에 따라 `collect_rss_feeds` 및 `crawl_webpage` 도구를 사용하여 주기적으로 데이터를 수집합니다.
2.  수집된 데이터는 `save_collected_data` 도구를 사용하여 저장하기 전에 중복 여부를 확인합니다.
3.  `log_monitoring_event` 도구를 사용하여 모든 수집 작업의 시작과 종료(성공/실패 결과 포함)를 기록합니다.
4.  정기적으로 `evaluate_source_quality` 도구를 사용하여 등록된 소스들의 품질과 관련성을 평가하고, 결과에 따라 수집 우선순위를 조정할 것을 제안합니다.
5.  수집된 콘텐츠 내에서 새로운 잠재적 정보 소스를 발견하면 보고합니다.
6.  외부 요청이 있을 시 `get_collected_data` 도구를 사용하여 적절한 데이터를 조회하여 응답합니다.

항상 명확하고 간결하게 응답하며, 작업을 수행하기 위해 어떤 도구를 사용할 것인지 명시하십시오. 모델은 'gemma-3-27b-it'를 사용합니다.
""",
    model="gemma-3-27b-it", # 사용할 모델 지정
    model_provider=litellm_provider, # LiteLLM Provider 사용
    tools=tools, # 사용할 도구 목록 (현재는 비어 있음)
    output_schema=AgentOutputSchema(CollectorAgentOutput) # 출력 형식 정의
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
