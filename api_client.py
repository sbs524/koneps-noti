"""
api_client.py - 나라장터 API 통신
BidPublicInfoService API를 호출하여 입찰공고 데이터를 가져온다.
페이지네이션과 재시도 로직을 포함한다.
"""

import math
import time
import logging
import requests

import config

logger = logging.getLogger("bid_monitor")


class ApiError(Exception):
    """API 호출 관련 에러."""
    pass


def fetch_bids(start_dt, end_dt):
    """
    지정된 날짜 범위의 용역 입찰공고를 모두 가져온다.

    Args:
        start_dt: 조회 시작일시 (YYYYMMDDHHMM 형식, 예: "202602080000")
        end_dt: 조회 종료일시 (YYYYMMDDHHMM 형식, 예: "202602082359")

    Returns:
        입찰공고 딕셔너리 리스트

    Raises:
        ApiError: API 호출 실패 시
    """
    logger.info("API 조회 시작: %s ~ %s", start_dt, end_dt)
    all_items = []

    # 첫 페이지 조회하여 전체 건수 파악
    first_page_data = _fetch_page(1, start_dt, end_dt)
    body = first_page_data.get("response", {}).get("body", {})
    total_count = int(body.get("totalCount", 0))

    if total_count == 0:
        logger.info("조회 결과 없음")
        return []

    items = _extract_items(body)
    all_items.extend(items)
    logger.info("전체 %d건, 1페이지 %d건 수신", total_count, len(items))

    # 나머지 페이지 조회
    total_pages = math.ceil(total_count / config.API_ROWS_PER_PAGE)
    for page_no in range(2, total_pages + 1):
        page_data = _fetch_page(page_no, start_dt, end_dt)
        page_body = page_data.get("response", {}).get("body", {})
        page_items = _extract_items(page_body)
        all_items.extend(page_items)
        logger.info("%d/%d 페이지 수신 (%d건)", page_no, total_pages, len(page_items))

    logger.info("API 조회 완료: 총 %d건", len(all_items))
    return all_items


def _fetch_page(page_no, start_dt, end_dt):
    """
    단일 페이지를 API에서 가져온다. 실패 시 재시도한다.

    Args:
        page_no: 페이지 번호
        start_dt: 조회 시작일시
        end_dt: 조회 종료일시

    Returns:
        파싱된 JSON 응답 딕셔너리

    Raises:
        ApiError: 최대 재시도 횟수 초과 시
    """
    params = {
        "serviceKey": config.API_SERVICE_KEY,
        "pageNo": str(page_no),
        "numOfRows": str(config.API_ROWS_PER_PAGE),
        "type": config.API_RESPONSE_TYPE,
        "inqryDiv": config.API_INQUIRY_DIVISION,
        "inqryBgnDt": start_dt,
        "inqryEndDt": end_dt,
    }

    last_error = None
    for attempt in range(1, config.API_MAX_RETRIES + 1):
        try:
            response = requests.get(
                config.API_BASE_URL,
                params=params,
                timeout=config.API_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

            # 응답 코드 검증
            result_code = (
                data.get("response", {}).get("header", {}).get("resultCode", "")
            )
            if result_code != "00":
                result_msg = (
                    data.get("response", {})
                    .get("header", {})
                    .get("resultMsg", "알 수 없는 오류")
                )
                raise ApiError(
                    f"API 응답 오류: [{result_code}] {result_msg}"
                )

            return data

        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < config.API_MAX_RETRIES:
                wait_time = 2 ** attempt
                logger.warning(
                    "API 요청 실패 (시도 %d/%d): %s. %d초 후 재시도...",
                    attempt,
                    config.API_MAX_RETRIES,
                    e,
                    wait_time,
                )
                time.sleep(wait_time)
            else:
                logger.error("API 요청 최종 실패: %s", e)

        except ApiError:
            raise

        except (ValueError, KeyError) as e:
            raise ApiError(f"API 응답 파싱 실패: {e}")

    raise ApiError(f"API 호출 {config.API_MAX_RETRIES}회 실패: {last_error}")


def _extract_items(body):
    """
    API 응답 body에서 items 리스트를 추출한다.

    Args:
        body: API 응답의 body 딕셔너리

    Returns:
        입찰공고 딕셔너리 리스트
    """
    items = body.get("items", [])
    if items is None:
        return []
    if isinstance(items, dict):
        # 단일 항목인 경우 리스트로 감싸기
        return [items]
    if isinstance(items, list):
        return items
    return []
