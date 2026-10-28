"""PowerPoint一括生成で使用する設定モデルを定義する。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


NUMERIC_MATCH_CONDITIONS = frozenset({"ma", "kv", "sec"})


@dataclass(frozen=True)
class CmSize:
    """cm単位の幅と高さを保持する。"""

    width: float
    """!< 幅。"""
    height: float
    """!< 高さ。"""


@dataclass(frozen=True)
class CmPoint:
    """cm単位の左上座標を保持する。"""

    left: float
    """!< スライドまたは画像左端からの距離。"""
    top: float
    """!< スライドまたは画像上端からの距離。"""


@dataclass(frozen=True)
class ZoomConfig:
    """1つの拡大表示設定を保持する。"""

    name: str
    """!< Zoomを識別する共通名。"""
    cut_size: CmSize
    """!< 元画像から切り取る大きさ。"""
    cut_location: CmPoint
    """!< スライド内の切り取り左上座標。"""
    size: CmSize
    """!< 切り取り画像を貼り付ける大きさ。"""
    location: CmPoint
    """!< 切り取り画像を貼り付ける左上座標。"""


@dataclass(frozen=True)
class FolderConfig:
    """1つの画像フォルダーとZoom設定を保持する。"""

    annotation: str
    """!< 画像下部へ表示する注釈。"""
    folder_path: Path
    """!< 画像を検索するフォルダー。"""
    zooms: tuple[ZoomConfig, ...]
    """!< JSON記載順の拡大表示設定。"""


@dataclass(frozen=True)
class DataSetConfig:
    """同一条件で比較するフォルダー群を保持する。"""

    name: str
    """!< DataSet名。"""
    match_conditions: tuple[str, ...]
    """!< 数値条件名またはファイル名に必須の固定文字列の並び。"""
    slide_title_location: CmPoint
    """!< スライドタイトルの左上座標。"""
    slide_title_size: CmSize
    """!< スライドタイトルのテキストボックスサイズ。"""
    slide_title_font_size_pt: float
    """!< スライドタイトルのフォントサイズ。"""
    folders: tuple[FolderConfig, ...]
    """!< 同一条件で比較する2個以上のフォルダー。"""
    include_values: tuple[tuple[str, tuple[Decimal, ...]], ...] = ()
    """!< 条件名ごとの出力対象値。空の場合は全値を対象にする。"""


@dataclass(frozen=True)
class SlideOrderItem:
    """出力するDataSetの通常画像またはZoomを指定する。"""

    dataset_name: str
    """!< 対象DataSet名。"""
    zoom_name: str | None
    """!< Zoom名。Noneは通常画像。"""


@dataclass(frozen=True)
class AppConfig:
    """アプリケーション全体の設定を保持する。"""

    input_pptx: Path
    """!< 入力PowerPointファイル。"""
    output_pptx: Path
    """!< 出力PowerPointファイル。"""
    datasets: tuple[DataSetConfig, ...]
    """!< PowerPointへ順番に追加するDataSet群。"""
    slide_order: tuple[SlideOrderItem, ...] | None = None
    """!< 指定時に使用するDataSet・Zoomの出力順。"""
