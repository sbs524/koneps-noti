"""
slack_notifier.py - Slack 메시지 포맷팅 및 전송
Incoming Webhook을 통해 입찰공고 분석 결과를 Slack 채널로 전송한다.
"""

import json
import logging
import time
import requests

import config

logger = logging.getLogger("bid_monitor")


def send_results(bids, total_count, filtered_count, date_label):
    """
    필터링된 입찰공고를 Slack으로 전송한다.
    각 공고를 개별 메시지로 전송하여 사업별로 반응(이모지 등)을 남길 수 있게 한다.

    전송 순서:
    1. 헤더 메시지 (날짜, 요약 정보)
    2. 공고 각각 개별 메시지

    Args:
        bids: 입찰공고 딕셔너리 리스트
        total_count: 전체 조회 건수
        filtered_count: 필터 통과 건수
        date_label: 조회 날짜 표시 문자열 (예: "2026-02-08" 또는 "2026-02-07~09")

    Returns:
        모든 전송 성공 시 True
    """
    all_success = True

    # 1. 헤더 + 요약 메시지
    summary_text = f"전체 검색: {total_count}건 | 필터 통과: {filtered_count}건 | 상위 {len(bids)}건 표시"

    header_payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"나라장터 입찰공고 알리미 ({date_label})",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": summary_text,
                    }
                ],
            },
        ],
    }
    if not _send_to_slack(header_payload):
        all_success = False

    # 2. 공고 각각 개별 메시지
    for bid in bids:
        payload = {"blocks": [_build_bid_block(bid)]}
        if not _send_to_slack(payload):
            all_success = False

    return all_success


def send_no_results_message(date_label):
    """
    매칭되는 공고가 없을 때 알림을 전송한다.

    Args:
        date_label: 조회 날짜 표시 문자열

    Returns:
        전송 성공 시 True
    """
    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":mag: *나라장터 입찰공고 알리미 ({date_label})*\n\n조건에 맞는 입찰공고가 없습니다.",
                },
            }
        ],
    }
    return _send_to_slack(payload)


def send_error_message(error_msg):
    """
    에러 발생 시 알림을 전송한다.

    Args:
        error_msg: 에러 메시지

    Returns:
        전송 성공 시 True
    """
    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":warning: *나라장터 입찰공고 알리미 - 오류 발생*\n\n```{error_msg}```",
                },
            }
        ],
    }
    return _send_to_slack(payload)


def _build_bid_block(bid):
    """
    단일 입찰공고의 Slack 섹션 블록을 생성한다.

    Args:
        bid: 입찰공고 딕셔너리

    Returns:
        Slack Block Kit 섹션 딕셔너리
    """
    bid_name = bid.get("bidNtceNm", "제목 없음")
    institution = bid.get("dminsttNm", "") or bid.get("ntceInsttNm", "기관 미상")
    budget = _format_budget(bid)
    deadline = _format_deadline(bid)
    detail_url = bid.get("bidNtceDtlUrl", "") or bid.get("bidNtceUrl", "")

    text_parts = [
        f"  :page_facing_up: {bid_name}",
        f"  :office: 발주기관: {institution}",
        f"  :moneybag: 예산: {budget}",
        f"  :calendar: 제출마감: {deadline}",
    ]
    if detail_url:
        text_parts.append(f"  :link: <{detail_url}|공고 상세보기>")

    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "\n".join(text_parts),
        },
    }


def _send_to_slack(payload):
    """
    Slack webhook으로 메시지를 전송한다. 실패 시 1회 재시도.
    연속 전송 시 rate limit 방지를 위해 전송 후 1초 대기한다.

    Args:
        payload: Slack 메시지 페이로드 딕셔너리

    Returns:
        전송 성공 시 True
    """
    for attempt in range(2):
        try:
            response = requests.post(
                config.SLACK_WEBHOOK_URL,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            if response.status_code == 200:
                logger.info("Slack 메시지 전송 성공")
                time.sleep(1)  # rate limit 방지
                return True
            elif response.status_code == 429:
                # rate limit - 잠시 대기 후 재시도
                retry_after = int(response.headers.get("Retry-After", 2))
                logger.warning("Slack rate limit, %d초 대기...", retry_after)
                time.sleep(retry_after)
            else:
                logger.warning(
                    "Slack 전송 실패 (시도 %d): HTTP %d - %s",
                    attempt + 1,
                    response.status_code,
                    response.text,
                )
        except requests.exceptions.RequestException as e:
            logger.warning("Slack 전송 오류 (시도 %d): %s", attempt + 1, e)

    logger.error("Slack 메시지 전송 최종 실패")
    return False


def _format_deadline(bid):
    """
    제출 마감일시를 포맷한다.
    bidClseDt 필드를 사용한다. (예: "2026-02-20 10:00:00")

    Args:
        bid: 입찰공고 딕셔너리

    Returns:
        포맷된 마감일 문자열 (예: "2026-02-20 10:00")
    """
    raw = bid.get("bidClseDt", "")
    if not raw:
        return "미정"
    # "2026-02-20 10:00:00" -> "2026-02-20 10:00" (초 단위 제거)
    return raw[:16]


def _format_budget(bid):
    """
    예산 금액을 3자리 콤마 표기로 포맷한다.

    Args:
        bid: 입찰공고 딕셔너리

    Returns:
        포맷된 예산 문자열 (예: "193,600,000원")
    """
    for field_name in ("asignBdgtAmt", "presmptPrce"):
        value = bid.get(field_name, "")
        if value:
            try:
                amount = int(float(str(value).replace(",", "").strip()))
                if amount > 0:
                    return f"{amount:,}원"
            except (ValueError, TypeError):
                continue

    return "미공개"
