
df = yf.download(
    ticker,
    period="max",             # 존재하는 전체 기간
    interval="1d",            # 일봉
    auto_adjust=False,        # 원래 가격과 수정주가를 모두 보존
    actions=True,             # 배당, 주식분할 정보 포함
    progress=False,
    multi_level_index=False,
)

output_path = output_dir / f"{ticker}_daily.csv"
df.to_csv(output_path, encoding="utf-8-sig")