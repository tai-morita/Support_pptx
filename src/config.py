"""JSON設定を読み込み、検証済みモデルへ変換する。"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from models import (
    NUMERIC_MATCH_CONDITIONS,
    AppConfig,
    CmPoint,
    CmSize,
    DataSetConfig,
    FolderConfig,
    SlideOrderItem,
    ZoomConfig,
)


def _require(mapping: dict[str, Any], key: str, context: str) -> Any:
    """! 必須キーの値を返す。

    @param mapping 検査対象のオブジェクト。
    @param key 必須キー。
    @param context エラーへ表示する設定位置。
    @return 必須キーに対応する値。
    @raises ValueError 必須キーがない場合。
    """
    if key not in mapping:
        raise ValueError(f"{context}.{key} が必要です")
    return mapping[key]


def _require_object(value: Any, context: str) -> dict[str, Any]:
    """! 値をJSONオブジェクトとして検証する。"""
    if not isinstance(value, dict):
        raise ValueError(f"{context} はオブジェクトで指定してください")
    return value


def _resolve_path(base_dir: Path, value: Any, context: str) -> Path:
    """! 設定ファイル基準でパスを解決する。"""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} は空でない文字列で指定してください")
    path = Path(value)
    return path if path.is_absolute() else (base_dir / path).resolve()


def _parse_size(value: Any, context: str) -> CmSize:
    """! `[Height, Width]` を内部の幅と高さへ変換する。"""
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{context} は [Height, Width] で指定してください")
    try:
        height, width = (float(item) for item in value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context} は数値2個で指定してください") from exc
    if height <= 0 or width <= 0:
        raise ValueError(f"{context} の値は0より大きくしてください")
    return CmSize(width=width, height=height)


def _parse_location(value: Any, context: str) -> CmPoint:
    """! `[Horizontal, Vertical]` を内部の左上座標へ変換する。"""
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(
            f"{context} は [Horizontal, Vertical] で指定してください"
        )
    try:
        left, top = (float(item) for item in value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context} は数値2個で指定してください") from exc
    if left < 0 or top < 0:
        raise ValueError(f"{context} の値は0以上にしてください")
    return CmPoint(left=left, top=top)


def _parse_positive_float(value: Any, context: str) -> float:
    """! 0より大きい数値へ変換する。"""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context} は数値で指定してください") from exc
    if number <= 0:
        raise ValueError(f"{context} は0より大きくしてください")
    return number


def _parse_zoom(name: str, value: Any, context: str) -> ZoomConfig:
    """! 1つのZoom設定を変換する。"""
    zoom = _require_object(value, context)
    return ZoomConfig(
        name=name,
        cut_size=_parse_size(
            _require(zoom, "cut_size", context), f"{context}.cut_size"
        ),
        cut_location=_parse_location(
            _require(zoom, "cut_location", context),
            f"{context}.cut_location",
        ),
        size=_parse_size(_require(zoom, "size", context), f"{context}.size"),
        location=_parse_location(
            _require(zoom, "location", context), f"{context}.location"
        ),
    )


def _parse_folder(
    value: Any,
    base_dir: Path,
    context: str,
) -> FolderConfig:
    """! 1つのFolder設定を変換する。"""
    folder = _require_object(value, context)
    annotation = _require(folder, "annotation", context)
    if not isinstance(annotation, str):
        raise ValueError(f"{context}.annotation は文字列で指定してください")

    folder_path = _resolve_path(
        base_dir,
        _require(folder, "folder_path", context),
        f"{context}.folder_path",
    )
    if not folder_path.is_dir():
        raise ValueError(f"画像フォルダーが存在しません: {folder_path}")

    zoom_values = _require_object(
        _require(folder, "zooms", context), f"{context}.zooms"
    )
    zooms = tuple(
        _parse_zoom(name, zoom, f"{context}.zooms.{name}")
        for name, zoom in zoom_values.items()
    )
    return FolderConfig(
        annotation=annotation,
        folder_path=folder_path,
        zooms=zooms,
    )


def _parse_conditions(value: Any, context: str) -> tuple[str, ...]:
    """! 一致条件名の配列を検証する。"""
    if not isinstance(value, list) or not value:
        raise ValueError(f"{context} は1件以上の配列で指定してください")
    if any(
        not isinstance(item, str) or not item.replace("_", "").strip()
        for item in value
    ):
        raise ValueError(f"{context} は空でない文字列の配列で指定してください")
    conditions = tuple(value)
    if len(set(conditions)) != len(conditions):
        raise ValueError(f"{context} に重複した条件があります")
    return conditions


def _parse_include_values(
    value: Any,
    conditions: tuple[str, ...],
    context: str,
) -> tuple[tuple[str, tuple[Decimal, ...]], ...]:
    """! 条件ごとの任意の対象値リストを検証する。"""
    if value is None:
        return ()
    filters = _require_object(value, context)
    parsed_filters: list[tuple[str, tuple[Decimal, ...]]] = []
    for condition, raw_values in filters.items():
        filter_context = f"{context}.{condition}"
        if condition not in conditions:
            raise ValueError(
                f"{filter_context} はmatch_conditionsに含まれていません"
            )
        if condition.casefold() not in NUMERIC_MATCH_CONDITIONS:
            raise ValueError(
                f"{filter_context} は数値条件(mA, kV, sec)のみ指定できます"
            )
        if raw_values is None:
            continue
        if not isinstance(raw_values, list):
            raise ValueError(f"{filter_context} は数値の配列で指定してください")
        if not raw_values:
            continue

        values: list[Decimal] = []
        for item in raw_values:
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                raise ValueError(
                    f"{filter_context} は数値の配列で指定してください"
                )
            try:
                number = Decimal(str(item))
            except InvalidOperation as exc:
                raise ValueError(
                    f"{filter_context} に不正な数値があります"
                ) from exc
            if not number.is_finite():
                raise ValueError(f"{filter_context} は有限の数値にしてください")
            values.append(number)

        if len(set(values)) != len(values):
            raise ValueError(f"{filter_context} に重複した値があります")
        parsed_filters.append((condition, tuple(values)))
    return tuple(parsed_filters)


def _parse_dataset(value: Any, base_dir: Path, index: int) -> DataSetConfig:
    """! 1つのDataSet設定を変換する。"""
    context = f"root.datasets[{index}]"
    dataset = _require_object(value, context)
    name = _require(dataset, "name", context)
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"{context}.name は空でない文字列で指定してください")

    folder_values = _require(dataset, "folders", context)
    if not isinstance(folder_values, list) or len(folder_values) < 2:
        raise ValueError(f"{context}.folders は2件以上指定してください")
    folders = tuple(
        _parse_folder(folder, base_dir, f"{context}.folders[{folder_index}]")
        for folder_index, folder in enumerate(folder_values)
    )
    zoom_names = [
        tuple(zoom.name for zoom in folder.zooms) for folder in folders
    ]
    if any(names != zoom_names[0] for names in zoom_names[1:]):
        raise ValueError(
            f"{context} の全foldersで同じZoom名と順序を指定してください"
        )
    match_conditions = _parse_conditions(
        _require(dataset, "match_conditions", context),
        f"{context}.match_conditions",
    )

    return DataSetConfig(
        name=name,
        match_conditions=match_conditions,
        include_values=_parse_include_values(
            dataset.get("include_values"),
            match_conditions,
            f"{context}.include_values",
        ),
        slide_title_location=_parse_location(
            _require(dataset, "slide_title_location", context),
            f"{context}.slide_title_location",
        ),
        slide_title_size=_parse_size(
            _require(dataset, "slide_title_size", context),
            f"{context}.slide_title_size",
        ),
        slide_title_font_size_pt=_parse_positive_float(
            _require(dataset, "slide_title_font_size_pt", context),
            f"{context}.slide_title_font_size_pt",
        ),
        folders=folders,
    )


def _parse_slide_order(
    value: Any,
    datasets: tuple[DataSetConfig, ...],
) -> tuple[SlideOrderItem, ...]:
    """! DataSetごとの通常画像・Zoomを重複なくすべて並べた順序を読む。"""
    if not isinstance(value, list) or not value:
        raise ValueError("root.slide_order は1件以上の配列で指定してください")

    datasets_by_name = {dataset.name: dataset for dataset in datasets}
    expected: set[tuple[str, str | None]] = set()
    for dataset in datasets:
        expected.add((dataset.name, None))
        expected.update(
            (dataset.name, zoom.name)
            for zoom in dataset.folders[0].zooms
        )

    items: list[SlideOrderItem] = []
    seen: set[tuple[str, str | None]] = set()
    for index, item_value in enumerate(value):
        context = f"root.slide_order[{index}]"
        item = _require_object(item_value, context)
        dataset_name = _require(item, "dataset", context)
        if (
            not isinstance(dataset_name, str)
            or dataset_name not in datasets_by_name
        ):
            raise ValueError(
                f"{context}.dataset は存在するDataSet名で指定してください"
            )

        zoom_name = _require(item, "zoom", context)
        if zoom_name is not None:
            if not isinstance(zoom_name, str) or not zoom_name:
                raise ValueError(
                    f"{context}.zoom はZoom名またはnullで指定してください"
                )
            available_zooms = {
                zoom.name
                for zoom in datasets_by_name[dataset_name].folders[0].zooms
            }
            if zoom_name not in available_zooms:
                raise ValueError(
                    f"{context}.zoom '{zoom_name}' はDataSet "
                    f"'{dataset_name}' にありません"
                )

        key = (dataset_name, zoom_name)
        if key in seen:
            raise ValueError(
                f"{context} に重複したDataSet・Zoom指定があります"
            )
        seen.add(key)
        items.append(SlideOrderItem(dataset_name, zoom_name))

    missing = expected - seen
    if missing:
        missing_text = ", ".join(
            f"{dataset_name}/{zoom_name or '通常画像'}"
            for dataset_name, zoom_name in sorted(
                missing,
                key=lambda item: (item[0], item[1] or ""),
            )
        )
        raise ValueError(
            f"root.slide_order に未指定の出力があります: {missing_text}"
        )
    return tuple(items)


def load_config(config_path: str | Path) -> AppConfig:
    """! JSON設定を読み込み、検証済みモデルを返す。

    @param config_path 設定JSONファイルのパス。
    @return 検証済みアプリケーション設定。
    @raises ValueError 設定内容が不正な場合。
    """
    path = Path(config_path).resolve()
    try:
        raw_value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"設定JSONを読み込めません: {path}: {exc}") from exc

    root = _require_object(raw_value, "root")
    input_pptx = _resolve_path(
        path.parent,
        _require(root, "input_pptx", "root"),
        "root.input_pptx",
    )
    output_pptx = _resolve_path(
        path.parent,
        _require(root, "output_pptx", "root"),
        "root.output_pptx",
    )
    if not input_pptx.is_file():
        raise ValueError(f"入力PPTXが存在しません: {input_pptx}")
    if input_pptx == output_pptx:
        raise ValueError("input_pptx と output_pptx は別のパスにしてください")

    dataset_values = _require(root, "datasets", "root")
    if not isinstance(dataset_values, list) or not dataset_values:
        raise ValueError("root.datasets は1件以上指定してください")
    datasets = tuple(
        _parse_dataset(dataset, path.parent, index)
        for index, dataset in enumerate(dataset_values)
    )
    names = [dataset.name for dataset in datasets]
    if len(set(names)) != len(names):
        raise ValueError("root.datasets のnameに重複があります")
    slide_order = (
        _parse_slide_order(root["slide_order"], datasets)
        if "slide_order" in root
        else None
    )

    return AppConfig(
        input_pptx=input_pptx,
        output_pptx=output_pptx,
        datasets=datasets,
        slide_order=slide_order,
    )
