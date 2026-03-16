"""
bid_filter.py - 입찰공고 필터링
1차/2차 키워드, 제외 키워드, 예산 기준으로 공고를 필터링한다.
"""

import logging

import config

logger = logging.getLogger("bid_monitor")


def filter_bids(bids):
    """
    입찰공고 리스트에 4단계 필터를 순차 적용한다.
    1. 키워드 필터
    2. 2차 키워드 필터
    3. 제외 키워드 필터
    4. 예산 상한 필터

    Args:
        bids: API에서 가져온 입찰공고 딕셔너리 리스트

    Returns:
        필터를 통과한 입찰공고 리스트
    """
    result = []
    for bid in bids:
        if not _matches_keywords(bid):
            continue
        if not _matches_secondary_keywords(bid):
            continue
        if not _is_not_excluded(bid):
            continue
        if not _within_budget(bid):
            continue
        result.append(bid)

    logger.info(
        "필터링 결과: %d건 -> %d건 (1차/2차/제외/예산)",
        len(bids),
        len(result),
    )
    return result


def _matches_keywords(bid):
    """
    공고명 또는 첨부파일명에 검색 키워드가 포함되어 있는지 확인한다.

    Args:
        bid: 입찰공고 딕셔너리

    Returns:
        키워드가 하나라도 매칭되면 True
    """
    combined = _collect_target_text(bid)
    return any(kw in combined for kw in config.SEARCH_KEYWORDS)


def _matches_secondary_keywords(bid):
    """
    공고명 또는 첨부파일명에 2차 필터 키워드가 포함되어 있는지 확인한다.

    Args:
        bid: 입찰공고 딕셔너리

    Returns:
        2차 키워드가 하나라도 매칭되면 True
    """
    combined = _collect_target_text(bid)
    return any(kw in combined for kw in config.SECONDARY_KEYWORDS)


def _is_not_excluded(bid):
    """
    제외 키워드가 있는지 판단한다.

    Args:
        bid: 입찰공고 딕셔너리

    Returns:
        제외 대상이 아니면 True, 제외 대상이면 False
    """
    name = bid.get("bidNtceNm", "")
    combined = _collect_target_text(bid)

    if any(kw in combined for kw in config.EXCLUDE_KEYWORDS):
        logger.debug("제외 키워드 포함 제외: %s", name)
        return False

    return True


def _collect_target_text(bid):
    """공고명과 첨부파일명을 결합해 필터 대상 텍스트를 만든다."""
    texts = []

    bid_name = bid.get("bidNtceNm", "")
    if bid_name:
        texts.append(bid_name)

    for i in range(1, 11):
        filename = bid.get(f"ntceSpecFileNm{i}", "")
        if filename:
            texts.append(filename)

    return " ".join(texts)


def _within_budget(bid):
    """
    예산이 상한 이하인지 확인한다.
    asignBdgtAmt가 0이거나 없으면 presmptPrce를 사용한다.
    둘 다 0이거나 없으면 포함한다 (보수적 접근).

    Args:
        bid: 입찰공고 딕셔너리

    Returns:
        예산이 상한 이하이면 True
    """
    budget = _parse_budget(bid.get("asignBdgtAmt", ""))
    if budget <= 0:
        budget = _parse_budget(bid.get("presmptPrce", ""))

    if budget <= 0:
        # 예산 정보 없음 - 포함 (놓치지 않기 위해)
        return True

    if budget > config.MAX_BUDGET_WON:
        logger.debug(
            "예산 초과 제외: %s (%s원)",
            bid.get("bidNtceNm", ""),
            f"{budget:,}",
        )
        return False

    return True


def _parse_budget(value):
    """
    예산 값을 정수로 파싱한다.

    Args:
        value: 문자열 또는 숫자 형태의 예산 값

    Returns:
        정수 예산값. 파싱 실패 시 0.
    """
    if not value:
        return 0
    try:
        cleaned = str(value).replace(",", "").strip()
        return int(float(cleaned))
    except (ValueError, TypeError):
        return 0
