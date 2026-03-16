"""
config.py - 설정값 관리
모든 설정 상수를 중앙에서 관리한다.
API 키와 Slack webhook URL은 .env 파일에서 로드한다.
"""

import os
import logging

from dotenv import load_dotenv

# ──────────────────────────────────────────────
# 비즈니스 규칙
# ──────────────────────────────────────────────
# 검색 키워드 (공고명 및 첨부파일명에서 검색)
SEARCH_KEYWORDS = ["홈페이지", "포털", "플랫폼", "웹사이트"]

# 2차 필터 키워드 (이 키워드가 있으면 주요 사업 범위로 판단)
SECONDARY_KEYWORDS = ["구축", "고도화", "재구축", "개선", "개편", "개발", "전환"]

# 결과에서 제외하는 키워드
EXCLUDE_KEYWORDS = ["감리", "마케팅", "유지보수", "유지관리"]

# 예산 상한 (원)
MAX_BUDGET_WON = 500_000_000

# 상위 N개 결과
TOP_N_RESULTS = 5

# ──────────────────────────────────────────────
# .env 파일 로드
# ──────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

LOG_DIR = os.path.join(PROJECT_ROOT, "log")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "bid_monitor.log")

# ──────────────────────────────────────────────
# API 설정
# ──────────────────────────────────────────────
API_BASE_URL = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc"
API_SERVICE_KEY = os.getenv("API_SERVICE_KEY", "")
API_ROWS_PER_PAGE = 100
API_RESPONSE_TYPE = "json"
API_INQUIRY_DIVISION = "1"  # 용역 조회
API_TIMEOUT = 30  # 초
API_MAX_RETRIES = 3

# ──────────────────────────────────────────────
# Slack 설정
# ──────────────────────────────────────────────
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# ──────────────────────────────────────────────
# 타임존
# ──────────────────────────────────────────────
TIMEZONE = "Asia/Seoul"

# ──────────────────────────────────────────────
# 로깅 설정
# ──────────────────────────────────────────────
LOG_LEVEL = logging.INFO


def setup_logging():
    """로깅을 설정한다. 파일과 콘솔에 동시 출력."""
    logger = logging.getLogger("bid_monitor")
    logger.setLevel(LOG_LEVEL)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 파일 핸들러 (Permission 오류 처리)
    try:
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setLevel(LOG_LEVEL)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except (PermissionError, OSError) as e:
        # 파일 권한 오류 시 콘솔만 사용
        print(f"[WARNING] 로그 파일 생성 실패 ({LOG_FILE}): {e}")
        print("[WARNING] 콘솔에만 로그를 출력합니다.")

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
