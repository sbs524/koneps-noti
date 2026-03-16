"""
test_runner.py - 수동 테스트 스크립트
각 모듈을 개별적으로 또는 전체 파이프라인을 테스트할 수 있다.

사용법:
    python test_runner.py api         # API 연결 테스트
    python test_runner.py filter      # 필터 로직 테스트
    python test_runner.py slack       # Slack 전송 테스트
    python test_runner.py preview [날짜]  # 필터 통과 전체 결과 미리보기 (Slack 전송 없음)
    python test_runner.py full [날짜]  # 전체 파이프라인 (기본: 전일)
"""

import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import config
import api_client
import bid_filter
import slack_notifier
import main


def test_api_connection():
    """API 연결 및 응답 구조를 테스트한다."""
    config.setup_logging()
    print("=" * 60)
    print("[테스트] API 연결 테스트")
    print("=" * 60)

    # 어제 날짜로 조회
    tz = ZoneInfo(config.TIMEZONE)
    yesterday = datetime.now(tz) - timedelta(days=1)
    date_str = yesterday.strftime("%Y%m%d")
    start_dt = f"{date_str}0000"
    end_dt = f"{date_str}2359"

    print(f"조회 기간: {start_dt} ~ {end_dt}")

    try:
        bids = api_client.fetch_bids(start_dt, end_dt)
        print(f"\n조회 결과: {len(bids)}건")

        if bids:
            print("\n--- 첫 번째 공고 샘플 ---")
            sample = bids[0]
            print(f"  공고번호: {sample.get('bidNtceNo', 'N/A')}")
            print(f"  공고명: {sample.get('bidNtceNm', 'N/A')}")
            print(f"  공고기관: {sample.get('ntceInsttNm', 'N/A')}")
            print(f"  수요기관: {sample.get('dminsttNm', 'N/A')}")
            print(f"  배정예산: {sample.get('asignBdgtAmt', 'N/A')}")
            print(f"  추정가격: {sample.get('presmptPrce', 'N/A')}")
            print(f"  용역구분: {sample.get('srvceDivNm', 'N/A')}")
            print(f"  공고일시: {sample.get('bidNtceDt', 'N/A')}")
            print(f"  상세URL: {sample.get('bidNtceDtlUrl', 'N/A')}")

            # 첨부파일명 표시
            for i in range(1, 11):
                fn = sample.get(f"ntceSpecFileNm{i}", "")
                if fn:
                    print(f"  첨부파일{i}: {fn}")

        print("\nAPI 테스트 성공!")
    except Exception as e:
        print(f"\nAPI 테스트 실패: {e}")


def test_filter():
    """필터 로직을 하드코딩된 샘플 데이터로 테스트한다."""
    print("=" * 60)
    print("[테스트] 필터 로직 테스트")
    print("=" * 60)

    test_cases = [
        {
            "bidNtceNm": "OO기관 홈페이지 구축 사업",
            "asignBdgtAmt": "300000000",
            "expected": True,
            "reason": "1차(홈페이지)+2차(구축), 3억 -> 통과",
        },
        {
            "bidNtceNm": "OO시스템 유지보수 용역",
            "asignBdgtAmt": "100000000",
            "expected": False,
            "reason": "1차/2차 미매칭 -> 제외",
        },
        {
            "bidNtceNm": "OO포털 고도화 및 유지보수",
            "asignBdgtAmt": "400000000",
            "expected": False,
            "reason": "1차+2차 매칭이지만 제외 키워드(유지보수) 포함 -> 제외",
        },
        {
            "bidNtceNm": "OO플랫폼 재구축 사업",
            "asignBdgtAmt": "600000000",
            "expected": False,
            "reason": "1차+2차 매칭이지만 6억 -> 예산 초과 제외",
        },
        {
            "bidNtceNm": "OO 건물 보수 공사",
            "asignBdgtAmt": "200000000",
            "expected": False,
            "reason": "1차 키워드 미매칭 -> 제외",
        },
        {
            "bidNtceNm": "OO기관 홈페이지 운영 사업",
            "asignBdgtAmt": "200000000",
            "expected": False,
            "reason": "1차는 매칭되지만 2차 키워드 미매칭 -> 제외",
        },
        {
            "bidNtceNm": "OO기관 웹사이트 개편 사업",
            "asignBdgtAmt": "0",
            "presmptPrce": "250000000",
            "expected": True,
            "reason": "1차(웹사이트)+2차(개편), 예산 0이지만 추정가 2.5억 -> 통과",
        },
        {
            "bidNtceNm": "OO기관 포털시스템 유지관리 사업",
            "asignBdgtAmt": "200000000",
            "expected": False,
            "reason": "1차는 매칭되지만 2차 미매칭 및 제외 키워드(유지관리) 포함 -> 제외",
        },
    ]

    pass_count = 0
    fail_count = 0

    for i, tc in enumerate(test_cases, 1):
        bid = {
            "bidNtceNm": tc["bidNtceNm"],
            "asignBdgtAmt": tc.get("asignBdgtAmt", "0"),
            "presmptPrce": tc.get("presmptPrce", "0"),
        }
        result = bid_filter.filter_bids([bid])
        passed = (len(result) > 0) == tc["expected"]

        status = "PASS" if passed else "FAIL"
        if passed:
            pass_count += 1
        else:
            fail_count += 1

        expected_str = "통과" if tc["expected"] else "제외"
        actual_str = "통과" if len(result) > 0 else "제외"

        print(f"\n  [{status}] 테스트 {i}: {tc['reason']}")
        print(f"    공고명: {tc['bidNtceNm']}")
        print(f"    예상: {expected_str}, 실제: {actual_str}")

    print(f"\n결과: {pass_count} 통과, {fail_count} 실패 / 총 {len(test_cases)}건")


def test_slack():
    """Slack 전송을 테스트한다."""
    print("=" * 60)
    print("[테스트] Slack 전송 테스트")
    print("=" * 60)

    test_bids = [
        {
            "bidNtceNm": "[테스트] OO기관 포털 고도화 사업",
            "ntceInsttNm": "테스트기관",
            "dminsttNm": "테스트기관",
            "asignBdgtAmt": "300000000",
            "bidNtceDtlUrl": "https://www.g2b.go.kr",
        },
        {
            "bidNtceNm": "[테스트] OO재단 홈페이지 재구축",
            "ntceInsttNm": "테스트재단",
            "dminsttNm": "테스트재단",
            "asignBdgtAmt": "200000000",
            "bidNtceDtlUrl": "https://www.g2b.go.kr",
        },
    ]

    print("테스트 메시지 전송 중...")
    success = slack_notifier.send_results(
        test_bids,
        total_count=100,
        filtered_count=5,
        date_label="테스트",
    )

    if success:
        print("Slack 전송 성공! 채널을 확인하세요.")
    else:
        print("Slack 전송 실패. webhook URL과 네트워크를 확인하세요.")


def test_preview(date_str=None):
    """필터 통과 전체 결과를 Slack 전송 없이 콘솔에 출력한다."""
    config.setup_logging()
    print("=" * 60)
    print("[미리보기] 필터 통과 전체 결과 (Slack 전송 없음)")
    print("=" * 60)

    try:
        # 1. 날짜 범위 결정
        start_dt, end_dt, date_label = main._determine_date_range(date_str)
        print(f"조회 기간: {date_label}")

        # 2. API 조회
        all_bids = api_client.fetch_bids(start_dt, end_dt)
        print(f"전체 조회: {len(all_bids)}건")

        # 3. 메인 필터링
        filtered_bids = bid_filter.filter_bids(all_bids)
        print(f"메인 필터 통과: {len(filtered_bids)}건")

        if not filtered_bids:
            print("\n조건에 맞는 공고가 없습니다.")
            return

        # 5. 메인 결과 전체 출력
        if filtered_bids:
            print(f"\n{'=' * 60}")
            print(f"[메인 키워드] 필터 통과 전체 {len(filtered_bids)}건")
            print("=" * 60)

            for rank, bid in enumerate(filtered_bids, 1):
                bid_name = bid.get("bidNtceNm", "제목 없음")
                institution = bid.get("dminsttNm", "") or bid.get("ntceInsttNm", "기관 미상")
                budget = slack_notifier._format_budget(bid)
                deadline = slack_notifier._format_deadline(bid)
                url = bid.get("bidNtceDtlUrl", "") or bid.get("bidNtceUrl", "")

                print(f"\n  {rank}. {bid_name}")
                print(f"    발주기관: {institution} | 예산: {budget} | 마감: {deadline}")
                if url:
                    print(f"    {url}")

        print(f"\n{'=' * 60}")
        print("미리보기 완료 (Slack 전송 없음)")

    except Exception as e:
        print(f"\n오류 발생: {e}")


def test_full_pipeline(date_str=None):
    """전체 파이프라인을 테스트한다."""
    print("=" * 60)
    print("[테스트] 전체 파이프라인 테스트")
    print("=" * 60)

    if date_str:
        print(f"지정 날짜: {date_str}")
    else:
        print("날짜: 자동 (전일 또는 금토일)")

    print()
    main.run(date_str)
    print("\n전체 파이프라인 테스트 완료")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        test_full_pipeline()
    else:
        cmd = sys.argv[1]
        if cmd == "api":
            test_api_connection()
        elif cmd == "filter":
            test_filter()
        elif cmd == "slack":
            test_slack()
        elif cmd == "preview":
            date = sys.argv[2] if len(sys.argv) > 2 else None
            test_preview(date)
        elif cmd == "full":
            date = sys.argv[2] if len(sys.argv) > 2 else None
            test_full_pipeline(date)
        else:
            print(f"알 수 없는 명령: {cmd}")
            print()
            print("사용법:")
            print("  python test_runner.py api         # API 연결 테스트")
            print("  python test_runner.py filter      # 필터 로직 테스트")
            print("  python test_runner.py slack       # Slack 전송 테스트")
            print("  python test_runner.py preview [날짜]  # 필터 통과 전체 결과 미리보기")
            print("  python test_runner.py full [날짜]  # 전체 파이프라인")
