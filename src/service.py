"""設定読込からPowerPoint保存までの処理を統括する。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from matching import match_dataset
from models import AppConfig
from presentation import load_presentation, render_comparison_slide


@dataclass(frozen=True)
class GenerationSummary:
    """PowerPoint生成結果の件数を保持する。"""

    matched_condition_count: int
    """!< 全DataSetで一致した条件数。"""
    added_slide_count: int
    """!< 追加したスライド数。"""


def _report_skipped_files(
    dataset_name: str,
    unmatched_counts: tuple[int, ...],
    ignored_counts: tuple[int, ...],
    logger: Callable[[str], None],
) -> None:
    """! DataSet内で使用しなかったファイル数を報告する。"""
    for index, (unmatched, ignored) in enumerate(
        zip(unmatched_counts, ignored_counts),
        start=1,
    ):
        if unmatched or ignored:
            logger(
                f"警告: {dataset_name} Folder {index}: "
                f"他Folderにない画像={unmatched}, 対象外ファイル={ignored}"
            )


def generate_presentation(
    config: AppConfig,
    logger: Callable[[str], None] = print,
) -> GenerationSummary:
    """! 設定に従ってPowerPointを生成して保存する。

    @param config 検証済みアプリケーション設定。
    @param logger 警告と進捗を受け取る関数。
    @return 一致条件数と追加スライド数。
    @raises ValueError 全DataSetで一致画像がない場合。
    """
    presentation = load_presentation(config.input_pptx)
    matched_condition_count = 0
    added_slide_count = 0
    results_by_name = {}

    for dataset in config.datasets:
        result = match_dataset(dataset)
        results_by_name[dataset.name] = result
        matched_condition_count += len(result.images)
        _report_skipped_files(
            dataset.name,
            result.unmatched_counts,
            result.ignored_counts,
            logger,
        )
        for matched in result.images:
            logger(f"照合: {dataset.name} / {matched.title}")
            for index, path in enumerate(matched.paths, start=1):
                logger(f"  Folder {index}: {path.name}")
        if not result.images:
            logger(f"警告: {dataset.name}: 全Folderで一致する画像がありません")

    if matched_condition_count == 0:
        raise ValueError("全DataSetで一致する画像がありません")

    if config.slide_order is not None:
        datasets_by_name = {
            dataset.name: dataset for dataset in config.datasets
        }
        for item in config.slide_order:
            dataset = datasets_by_name[item.dataset_name]
            result = results_by_name[dataset.name]
            for matched in result.images:
                render_comparison_slide(
                    presentation,
                    dataset,
                    matched,
                    zoom_name=item.zoom_name,
                )
                added_slide_count += 1
    else:
        for dataset in config.datasets:
            result = results_by_name[dataset.name]
            if not result.images:
                continue
        zoom_names = tuple(zoom.name for zoom in dataset.folders[0].zooms)
        for matched in result.images:
            render_comparison_slide(presentation, dataset, matched)
            added_slide_count += 1
            for zoom_name in zoom_names:
                render_comparison_slide(
                    presentation,
                    dataset,
                    matched,
                    zoom_name=zoom_name,
                )
                added_slide_count += 1

    config.output_pptx.parent.mkdir(parents=True, exist_ok=True)
    presentation.save(str(config.output_pptx))
    logger(
        f"出力完了: {config.output_pptx} "
        f"(一致条件={matched_condition_count}, 追加スライド={added_slide_count})"
    )
    return GenerationSummary(
        matched_condition_count=matched_condition_count,
        added_slide_count=added_slide_count,
    )
