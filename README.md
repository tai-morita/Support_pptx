# Support_pptx
パワポの貼り付けを手助けしてくれる

# PowerPoint比較画像一括生成

複数フォルダーから撮影条件がすべて一致する画像だけを抽出し、通常画像とZoom画像をPowerPointへ追加します。

## セットアップ

```powershell
python -m pip install -r requirements.txt
```

このコマンドでパッケージを開発用インストールします。

`pptx_config.example.json` を `pptx_config.json` へ複製し、実際のパスとZoom配置値へ変更してください。

## 実行

```powershell
python -m cli
python -m cli --config D:\path\to\config.json
```

実行時は、照合された組ごとにDataSet名・一致条件・各Folderのファイル名をコンソールへ出力します。Folder番号は設定JSONの `folders` の順序です。Zoomが複数あっても、同じ組のファイル名は一度だけ出力します。

```text
照合: DataSet A / 80kV2mA0.8sec
  Folder 1: a_80kV2mA0.8sec.png
  Folder 2: b_80kV2mA0.8sec.png
```

## JSON設定

- `input_pptx`: テンプレートPowerPoint。
- `output_pptx`: 生成ファイル。親フォルダーは自動作成します。
- `datasets`: 処理順に並べたDataSetの配列。
- `match_conditions`: 数値を照合する条件名と、ファイル名に必須の固定文字列です。`mA`・`kV`・`sec` は直前の数値を抽出し、それ以外は固定文字列として扱います。
- `include_values`: 条件値の任意フィルターです。例: `{"mA": [2, 6, 10]}`。省略、空オブジェクト、または空配列の場合は全値を対象にします。
- `slide_title_location`: タイトル左上の位置を `[Horizontal, Vertical]` で指定します。
- `slide_title_size`: タイトルのテキストボックスを `[Height, Width]` で指定します。
- `slide_title_font_size_pt`: タイトルの文字サイズをptで指定します。
- `folders`: 2件以上指定できます。すべてのFolderに同じ条件がある画像だけを使用します。
- `annotation`: 通常画像の直下へ中央揃えで表示します。
- `folder_path`: 直下の画像を検索します。サブフォルダーは検索しません。
- `zooms`: 全Folderで同じZoom名と順序を指定します。
- `slide_order`: 省略可能です。DataSetとZoomの出力ブロック順を指定します。

相対パスは設定JSONがあるフォルダーを基準に解決します。対応画像は `.tif`、`.tiff`、`.png`、`.jpg`、`.jpeg`、`.bmp` です。

`annotation` はJSON文字列内の `\n` で改行できます。改行はテキストボックス内の改行として出力され、既存のテキストボックスサイズは変わりません。

`include_values` はDataSetごとに指定します。`{"mA": [2, 6, 10]}` の場合、全Folderで一致する画像のうちmAが2、6、10の条件だけを出力します。`{"mA": []}` や `"include_values": {}` は絞り込みなしでフォルダー内の全mA値を対象にします。

## 通常画像の自動配置

Folder直下に通常画像用の `size` と `location` は指定しません。通常画像は次の規則で自動配置します。

- 元画像の縦横比を維持します。
- タイトル下端からスライド下部の注釈領域までを画像領域として使用します。
- すべての画像を同じ高さにし、横幅に収まらない場合は縦横比を維持したまま縮小します。
- スライド左端、画像間、スライド右端の余白をすべて同じ幅にします。
- 注釈はスライド下部に固定し、対応画像と同じ横位置・幅で中央揃えします。

## 座標とサイズ

単位はすべてcmです。

- Zoomの `size`, `cut_size`: `[Height, Width]`
- Zoomの `location`, `cut_location`: `[Horizontal, Vertical]`

`cut_location` はスライド左上を原点とする絶対位置です。切り取り範囲が通常画像内に収まるように指定してください。範囲外の場合は、通常画像の配置位置と切り取り範囲を示すエラーになります。

## スライド構成

一致条件ごとに次の順で追加します。

1. 全Folderの通常画像、注釈、条件タイトル
2. 通常画像に全Folderの最初の同名Zoomを重ねたスライド
3. 以後、JSONに記載したZoom順で同様に追加

Zoom AとZoom Bがある場合は、通常、通常＋Zoom A、通常＋Zoom Bの3枚です。

トップレベルに `slide_order` を指定すると、DataSetとZoom単位でスライドをまとめる順序を変更できます。各項目は一致条件の数値順で出力されます。`zoom: null` は通常画像のスライドです。すべてのDataSetの通常画像とZoomを、それぞれ一度ずつ指定してください。

```json
"slide_order": [
	{"dataset": "DataSet A", "zoom": "head"},
	{"dataset": "DataSet A", "zoom": "ANS"},
	{"dataset": "DataSet A", "zoom": "nasion"},
	{"dataset": "DataSet B", "zoom": "head"},
	{"dataset": "DataSet A", "zoom": null},
	{"dataset": "DataSet B", "zoom": null}
]
```

`slide_order` を省略した場合は、従来どおりDataSet・条件・通常画像/Zoomの順で出力します。

## 照合規則

数値条件（`mA`・`kV`・`sec`）は整数・小数として抽出し、指定順に数値昇順で並べます。そのため、`2mA` は `10mA` より先、`0.8sec` は `2.0sec` より先になります。

それ以外の条件は、ファイル名（拡張子を除く）に含まれる必要がある固定文字列です。大文字・小文字とアンダースコアの有無を区別しません。末尾が数字の条件は、後ろに別の数字が続く場合には一致しません。

```json
"match_conditions": ["Setting_1", "mA", "kV", "PA"]
```

この場合、`PA_Setting1_80kV2mA.png` と `PA_Setting_1_80kV2mA.tif` は同じ組として扱います。`Setting2`・`Setting10` の画像や、`PA` を含まない画像は対象外です。数値条件は全Folderで一致する必要があり、固定文字列も全Folderの画像それぞれに必要です。

固定文字列はスライドタイトルにも指定順で含めます（アンダースコアは除去）。`include_values` は数値条件だけに指定できます。従来の任意の数値抽出名は、この方式では固定文字列になるため、数値条件には `mA`・`kV`・`sec` を使用してください。

片方にしかない条件の画像は使用しません。同じFolder内に同一条件の画像が複数ある場合は、曖昧な組み合わせを避けるためエラーにします。

## テスト

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -p "test_*.py" -v
python -m pycodestyle src tests
```
