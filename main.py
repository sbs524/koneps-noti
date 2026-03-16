"""
main.py - 파이프라인 오케스트레이터
전체 입찰공고 분석 파이프라인을 순서대로 실행한다.
fetch -> filter -> notify
"""

import sys
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import config
import api_client
import bid_filter
import slack_notifier

logger = logging.getLogger("bid_monitor")


def run(target_date=None):
    """
    입찰공고 분석 파이프라인을 실행한다.

    Args:
        target_date: 조회할 날짜 (YYYYMMDD 형식).
                     None이면 자동으로 전일(화~금) 또는 금토일(월요일)을 조회한다.
    """
    config.setup_logging()
    logger.info("=" * 60)
    logger.info("입찰공고 분석 파이프라인 시작")

    try:
        # 1. 날짜 범위 결정
        start_dt, end_dt, date_label = _determine_date_range(target_date)
        logger.info("조회 기간: %s ~ %s (%s)", start_dt, end_dt, date_label)

        # 2. API로 전체 공고 수집
        all_bids = api_client.fetch_bids(start_dt, end_dt)
        total_count = len(all_bids)
        logger.info("전체 조회: %d건", total_count)

        # 3. 메인 키워드 필터링
        filtered_bids = bid_filter.filter_bids(all_bids)
        filtered_count = len(filtered_bids)
        logger.info("메인 필터 통과: %d건", filtered_count)

        # 결과 없으면 조기 종료
        if not filtered_bids:
            logger.info("조건에 맞는 공고 없음")
            slack_notifier.send_no_results_message(date_label)
            return

        # 5. 상위 N개 선택
        top_n = filtered_bids[: config.TOP_N_RESULTS]
        logger.info("메인 상위 %d건:", len(top_n))
        for rank, bid in enumerate(top_n, 1):
            logger.info(
                "  %d위: %s",
                rank,
                bid.get("bidNtceNm", ""),
            )

        # 6. Slack 전송
        slack_notifier.send_results(
            top_n, total_count, filtered_count, date_label,
        )

        logger.info("파이프라인 완료")

    except Exception as e:
        logger.error("파이프라인 오류: %s", e, exc_info=True)
        try:
            slack_notifier.send_error_message(str(e))
        except Exception:
            logger.error("에러 알림 전송 실패", exc_info=True)


def _determine_date_range(target_date=None):
    """
    조회할 날짜 범위를 결정한다.

    - target_date가 지정되면 해당 날짜 하루만 조회
    - 월요일: 금/토/일 3일치 조회
    - 화~금: 전일 1일치 조회

    Args:
        target_date: YYYYMMDD 형식의 날짜 문자열 또는 None

    Returns:
        (start_dt, end_dt, date_label) 튜플
        start_dt, end_dt: YYYYMMDDHHMM 형식
        date_label: 표시용 날짜 문자열
    """
    tz = ZoneInfo(config.TIMEZONE)

    if target_date:
        # 특정 날짜 지정
        start_dt = f"{target_date}0000"
        end_dt = f"{target_date}2359"
        date_label = f"{target_date[:4]}-{target_date[4:6]}-{target_date[6:8]}"
        return start_dt, end_dt, date_label

    now = datetime.now(tz)
    weekday = now.weekday()  # 0=월, 1=화, ..., 6=일

    if weekday == 0:
        # 월요일: 금(3일전), 토(2일전), 일(1일전)
        friday = now - timedelta(days=3)
        sunday = now - timedelta(days=1)
        start_dt = friday.strftime("%Y%m%d") + "0000"
        end_dt = sunday.strftime("%Y%m%d") + "2359"
        date_label = f"{friday.strftime('%Y-%m-%d')} ~ {sunday.strftime('%Y-%m-%d')}"
    else:
        # 화~금: 전일
        yesterday = now - timedelta(days=1)
        date_str = yesterday.strftime("%Y%m%d")
        start_dt = f"{date_str}0000"
        end_dt = f"{date_str}2359"
        date_label = yesterday.strftime("%Y-%m-%d")

    return start_dt, end_dt, date_label


if __name__ == "__main__":
    # 커맨드라인에서 직접 실행: python main.py [YYYYMMDD]
    target = sys.argv[1] if len(sys.argv) > 1 else None
    run(target)
