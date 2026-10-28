"""JSON設定から比較用PowerPointを生成するCLI。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from config import load_config
from service import generate_presentation


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "pptx_config.json"
"""!< `--config` 省略時に使用する設定ファイル。"""


def build_parser() -> argparse.ArgumentParser:
    """! コマンドライン引数パーサーを作成する。"""
    parser = argparse.ArgumentParser(
        description="JSON設定に従って比較画像をPowerPointへ一括配置します。"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="設定JSONのパス（省略時: %(default)s）",
    )
    return parser


def main(arguments: list[str] | None = None) -> int:
    """! CLI引数を処理してPowerPoint生成を実行する。

    @param arguments コマンドライン引数。Noneの場合はsys.argvを使用する。
    @return 正常終了は0、設定または生成エラーは1。
    """
    options = build_parser().parse_args(arguments)
    try:
        config = load_config(options.config)
        generate_presentation(config)
    except (OSError, ValueError) as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
