"""画像ファイル名から条件を抽出し、複数フォルダー間で照合する。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from models import NUMERIC_MATCH_CONDITIONS, DataSetConfig


IMAGE_EXTENSIONS = {
    ".bmp",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
}
"""!< 検索対象とする画像拡張子。"""

MatchKey = tuple[Decimal, ...]
"""!< JSON記載順の数値条件値。固定文字列は含めない。"""


@dataclass(frozen=True)
class MatchedImages:
    """全フォルダーで条件が一致した画像群を保持する。"""

    key: MatchKey
    """!< 数値化した一致条件。"""
    title: str
    """!< スライドへ表示する一致条件文字列。"""
    paths: tuple[Path, ...]
    """!< Folder設定と同じ順序の画像パス。"""


@dataclass(frozen=True)
class MatchResult:
    """1つのDataSetに対する照合結果を保持する。"""

    images: tuple[MatchedImages, ...]
    """!< 条件値の数値昇順に並べた一致画像群。"""
    unmatched_counts: tuple[int, ...]
    """!< 各Folderで他Folderに存在しなかった画像数。"""
    ignored_counts: tuple[int, ...]
    """!< 非対応拡張子または条件不足で無視したファイル数。"""


def extract_match_key(
    file_name: str,
    conditions: tuple[str, ...],
) -> MatchKey | None:
    """! ファイル名からすべての一致条件値を抽出する。

    @param file_name 拡張子を含むファイル名。
    @param conditions JSON記載順の条件名。
    @return 数値条件のタプル。固定文字列を含む条件不足時はNone。
    """
    values: list[Decimal] = []
    for condition in conditions:
        if condition.casefold() not in NUMERIC_MATCH_CONDITIONS:
            literal = condition.replace("_", "")
            pattern = "_*".join(re.escape(char) for char in literal)
            if literal and literal[-1].isdigit():
                pattern += r"(?!\d)"
            if re.search(
                pattern, Path(file_name).stem, re.IGNORECASE,
            ) is None:
                return None
            continue
        pattern = rf"(?<![\d.])(\d+(?:\.\d+)?)\s*{re.escape(condition)}"
        match = re.search(pattern, file_name, flags=re.IGNORECASE)
        if match is None:
            return None
        try:
            values.append(Decimal(match.group(1)))
        except InvalidOperation:
            return None
    return tuple(values)


def build_title(key: MatchKey, conditions: tuple[str, ...]) -> str:
    """! 条件値と条件名からスライドタイトルを作成する。"""
    values = iter(key)
    return "".join(
        (
            f"{format(next(values), 'f')}{condition}"
            if condition.casefold() in NUMERIC_MATCH_CONDITIONS
            else condition.replace("_", "")
        )
        for condition in conditions
    )


def _index_folder(
    folder_path: Path,
    conditions: tuple[str, ...],
) -> tuple[dict[MatchKey, Path], int]:
    """! 1つのFolderを一致条件タプルで索引化する。"""
    index: dict[MatchKey, Path] = {}
    ignored_count = 0
    for path in sorted(folder_path.iterdir()):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            ignored_count += 1
            continue
        key = extract_match_key(path.name, conditions)
        if key is None:
            ignored_count += 1
            continue
        if key in index:
            raise ValueError(
                f"同じ一致条件の画像が複数あります: {index[key]} / {path}"
            )
        index[key] = path
    return index, ignored_count


def match_dataset(dataset: DataSetConfig) -> MatchResult:
    """! DataSet内の全Folderで一致する画像群を返す。

    @param dataset 照合対象のDataSet設定。
    @return 一致画像、欠落数、無視数を含む結果。
    """
    indexed_folders: list[dict[MatchKey, Path]] = []
    ignored_counts: list[int] = []
    for folder in dataset.folders:
        index, ignored_count = _index_folder(
            folder.folder_path,
            dataset.match_conditions,
        )
        indexed_folders.append(index)
        ignored_counts.append(ignored_count)

    common_keys = set(indexed_folders[0])
    for folder_index in indexed_folders[1:]:
        common_keys.intersection_update(folder_index)

    filtered_keys = set(common_keys)
    condition_indices = {
        condition: index
        for index, condition in enumerate(
            condition
            for condition in dataset.match_conditions
            if condition.casefold() in NUMERIC_MATCH_CONDITIONS
        )
    }
    for condition, values in dataset.include_values:
        if not values:
            continue
        condition_index = condition_indices[condition]
        filtered_keys = {
            key for key in filtered_keys if key[condition_index] in values
        }

    sorted_keys = sorted(filtered_keys)
    images = tuple(
        MatchedImages(
            key=key,
            title=build_title(key, dataset.match_conditions),
            paths=tuple(index[key] for index in indexed_folders),
        )
        for key in sorted_keys
    )
    unmatched_counts = tuple(
        len(index) - len(common_keys) for index in indexed_folders
    )
    return MatchResult(
        images=images,
        unmatched_counts=unmatched_counts,
        ignored_counts=tuple(ignored_counts),
    )
