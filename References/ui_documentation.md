# Take it Easy — UI 要素ドキュメント

全ページ・全 UI コンポーネントの網羅的解説。

---

## 1. アプリ全体の共通設定

| 項目 | 内容 |
|---|---|
| テーマカラー (Light) | `#00A7EB` をシードに生成された Material 3 カラースキーム |
| テーマカラー (Dark) | `#0044EB` をシードに生成されたダークカラースキーム |
| フォント | Google Fonts `M PLUS 1p` (日本語対応) |
| ロケール | `ja_JP` 固定 |
| デバッグバナー | 非表示 (`debugShowCheckedModeBanner: false`) |
| テーマモード | ユーザー設定により `system` / `light` / `dark` を切替 |

**レスポンシブ判定基準**: `(screenWidth - 80) / screenHeight < 1` でポートレート/ランドスケープを判定。画面の縦横比に基づいてレイアウトが自動的に切り替わる。

---

## 2. HomePage — メインシェル

> ソース: [main.dart](file:///Users/taira/Projects/Personal/Flutter/takeiteasy/lib/main.dart) L122–L473

### 2.1 ポートレートモード (縦向き・モバイル)

#### AppBar
| 要素 | 種類 | 説明 |
|---|---|---|
| タイトル | `Text` | 「Take it Easy」(primaryカラー、太字、20px) |
| テーマ切替ボタン | `IconButton` | ダーク時: ☀️ `light_mode` (tooltip: ライトモード) / ライト時: 🌙 `dark_mode` (tooltip: ダークモード) |
| 情報ボタン | `IconButton` | ℹ️ `info` アイコン → 情報ダイアログを表示 |
| ユーザーボタン | `IconButton` | ログイン済: プロフィール画像 `CircleAvatar` (tooltip: プロフィール) → `/profile` へ遷移 / 未ログイン: 🔑 `login` アイコン (tooltip: ログイン) → `/login` へ遷移 |

- `automaticallyImplyLeading: false` — 戻るボタンなし
- `scrolledUnderElevation: 0` — スクロール時の影なし

#### Bottom NavigationBar
| インデックス | アイコン | ラベル | 遷移先 |
|---|---|---|---|
| 0 | `Icons.list` | 科目一覧 | `ListScreen` |
| 1 | `Icons.table_view` | 時間割 | `TableScreen` |

---

### 2.2 ランドスケープモード (横向き・デスクトップ)

AppBar と Bottom NavigationBar は**非表示**。代わりに左側の `NavigationRail` が表示される。

#### NavigationRail

| 要素 | 説明 |
|---|---|
| 展開トリガー | `MouseRegion` のホバー (`onEnter` / `onExit`) で展開/折り畳み |
| 折り畳み時の幅 | 80px |
| 展開時の幅 | 256px |

##### Leading セクション (上部)
| 要素 | 折り畳み時 | 展開時 |
|---|---|---|
| ロゴ | 「TiE」テキスト (primaryカラー、太字、20px) | 「Take it Easy」テキスト (primaryカラー、太字、20px) |
| 区切り線 | 非表示 | `Divider` |

##### Destinations (中央)
| インデックス | アイコン | ラベル |
|---|---|---|
| 0 | `Icons.list` | 科目一覧 |
| 1 | `Icons.table_view` | 時間割 |

##### Trailing セクション (下部)

全要素は `NavigationRailButton` ウィジェットで、折り畳み時はアイコンのみ、展開時はラベル付きボタンに遷移する。

| 要素 | 折り畳み時 | 展開時 |
|---|---|---|
| テーマ切替 | `IconButton` (☀️/🌙) | `FilledButton.tonalIcon` (「ライトモード」/「ダークモード」) |
| ユーザー (ログイン済) | `IconButton` (プロフィール画像) | `ListTile` (アバター、表示名、メールアドレス) |
| ユーザー (未ログイン) | `IconButton` (🔑) | `OutlinedButton.icon` (「ログイン」) + 補足テキスト「ログインすると時間割を保存できます」 |
| 情報 | `IconButton` (ℹ️) | 更新日テキスト + お問い合わせリンク |

##### NavigationRailButton アニメーション
- `NavigationRail.extendedAnimation` を利用
- `animation.value == 0` (折りたたみ): アイコンのみ表示
- `animation.value > 0`: `FadeTransition` + `ClipRect` + `Align(widthFactor)` でスムーズに展開

##### NavigationRailExpanded
- 展開アニメーションに連動して幅が 80px → 256px に `lerpDouble` で変化するコンテナ
- `Divider` 等の表示に使用

---

### 2.3 メインコンテンツ領域

`IndexedStack` で 2 つの子画面を保持し、タブ切替時にも状態が維持される:
- `index: 0` → `ListScreen` (`ExcludeFocus` 付き)
- `index: 1` → `TableScreen` (`ExcludeFocus` 付き)

---

## 3. 情報ダイアログ

> ソース: [main.dart](file:///Users/taira/Projects/Personal/Flutter/takeiteasy/lib/main.dart) L173–L202, L398–L428

`AlertDialog` で表示される:

| 要素 | 内容 |
|---|---|
| タイトル | 「Take it Easy (Unofficial)」 |
| 説明テキスト | 「時間割作成をもっと簡単に」 |
| 更新日 | 「最終更新日:2024/04/3」 |
| お問い合わせリンク | 「お問い合わせ」(primaryカラー) → Google Forms へ外部リンク (`LinkTarget.blank`) |

---

## 4. ListScreen — 科目一覧画面

> ソース: [list_screen.dart](file:///Users/taira/Projects/Personal/Flutter/takeiteasy/lib/screens/list_screen.dart)

### 4.1 状態管理
- `userDataNotifierProvider` を `watch` — ローディング/エラー/データの 3 状態で分岐
- `courseListNotifierProvider` を `watch` — フィルタ済み科目リスト

### 4.2 ヘッダー (SliverAppBar)

`NestedScrollView` + `SliverAppBar(floating: true)` でスクロール時にヘッダーが隠れ、上方向スクロールで再表示される。

**ポートレート時** (`expandedHeight: 96`):
```
┌──────────────────────────────────────┐
│  [ChoiceBox]  [16px]  [フィルターBtn]  │
│              [8px gap]               │
│           [SearchBox]                │
└──────────────────────────────────────┘
```

- `フィルター` ボタン: `OutlinedButton` → `showModalBottomSheet` で `FilterColumn` を表示
  - `showDragHandle: true`, `isScrollControlled: true`

**ランドスケープ時** (`expandedHeight: 56`):
```
┌──────────────────────────────────────┐
│  [ChoiceBox]  [16px]  [SearchBox]    │
└──────────────────────────────────────┘
```
- 水平 `SingleChildScrollView` でオーバーフロー対応

### 4.3 ボディ

**ポートレート時**:
```
┌──────────────────────┐
│    CourseCard リスト    │
│    (ListView.builder) │
└──────────────────────┘
```

**ランドスケープ時**:
```
┌────────┬─┬──────────────────┐
│ Filter │ │   CourseCard リスト  │
│ Column │ │  (ListView.builder)│
│ (200px)│ │                    │
└────────┴─┴──────────────────┘
         VerticalDivider
```

**空状態メッセージ**:
- カリキュラム未選択: 「カリキュラムを選択してください」
- 該当科目なし: 「該当する科目がありません」

**ローディング**: `CircularProgressIndicator` (中央)
**エラー**: 「ユーザーデータの取得に失敗しました」

---

## 5. ChoiceBox — カリキュラム選択

> ソース: [choice_box.dart](file:///Users/taira/Projects/Personal/Flutter/takeiteasy/lib/widgets/choice_box.dart)

`DropdownMenu<String>` ウィジェット。

| 属性 | 値 |
|---|---|
| ヒントテキスト | 「カリキュラム」 |
| 最大高さ | 40px |
| ボーダー | `OutlineInputBorder` |

**選択肢 (16項目)**:

| ラベル | 値 | ラベル | 値 |
|---|---|---|---|
| 情科21(一般) | `s21310` | 知能21(一般) | `s21320` |
| 情科21(国際) | `s21311` | 知能21(国際) | `s21321` |
| 情科22(一般) | `s22210` | 知能22(一般) | `s22220` |
| 情科22(国際) | `s22211` | 知能22(国際) | `s22221` |
| 情科23(一般) | `s23310` | 知能23(一般) | `s23320` |
| 情科23(国際) | `s23311` | 知能23(国際) | `s23321` |
| 情科24(一般) | `s24310` | 知能24(一般) | `s24320` |
| 情科24(国際) | `s24311` | 知能24(国際) | `s24321` |

選択時、`userDataNotifierProvider.notifier.setCrclumcd(value)` で Firestore に保存。

---

## 6. SearchBox — 検索ボックス

> ソース: [search_box.dart](file:///Users/taira/Projects/Personal/Flutter/takeiteasy/lib/widgets/search_box.dart)

`SearchAnchor.bar` ウィジェット。

| 属性 | 値 |
|---|---|
| ヒントテキスト | 「検索」 |
| 最大幅 | 300px |
| 最小高さ | 40px |

| 要素 | 説明 |
|---|---|
| 入力フィールド | `SearchController` で管理 |
| クリアボタン | テキスト入力時に表示される ✕ `Icons.clear` アイコン → テキストとフィルタをクリア |
| サジェスト一覧 | 入力文字で科目名を部分一致検索し `ListTile` のリストを表示 |
| 確定動作 | `onSubmitted` / サジェスト選択 → `filterNotifier.search(value)` でフィルタに反映 + `closeView` + `unfocus` |

---

## 7. FilterColumn — フィルターパネル

> ソース: [filter_column.dart](file:///Users/taira/Projects/Personal/Flutter/takeiteasy/lib/widgets/filter_column.dart)

ポートレートでは `ModalBottomSheet` 内、ランドスケープではサイドバーとして表示。

### 7.1 ヘッダー

| 要素 | 説明 |
|---|---|
| タイトル | `ListTile` 「フィルター」(dense) |
| リセットボタン | `TextButton` 「リセット」(12px) — 全フィルターを初期状態に戻す |

### 7.2 チェックボックス群

| ラベル | 説明 | 表示条件 |
|---|---|---|
| 登録済み | 履修登録した科目のみ表示 | 常時 |
| 空きコマ | 空いている時間帯の科目のみ | 常時 |
| 国際コース指定科目 | 国際コース指定の英語科目のみ | 国際コース (`*1` で終わるコード) 選択時のみ |

### 7.3 FilterTile (展開式フィルターグループ)

各グループは `ExpansionTile(initiallyExpanded: true)` で初期展開状態:

#### 学年で絞り込む
| チェックボックス |
|---|
| 1年 / 2年 / 3年 / 4年 |

#### 学期で絞り込む
| チェックボックス |
|---|
| 前期前 / 前期後 / 前期 / 前集中 / 後期前 / 後期後 / 後期 / 後集中 / 通年 |

#### 分類で絞り込む
| チェックボックス |
|---|
| 教養科目 / 体育科目 / 外国語科目 / PBL科目 / 情報工学基盤 / 専門 / 教職科目 |

#### 必選で絞り込む
| チェックボックス |
|---|
| 必修 / 選択必修 / 選択 |

> [!NOTE]
> 各グループ内で**何も選択されていない場合**、そのグループのフィルターは無効化され全件表示となる（AND 条件で絞り込まない）。

---

## 8. CourseCard — 科目カード

> ソース: [course_card.dart](file:///Users/taira/Projects/Personal/Flutter/takeiteasy/lib/widgets/course_card.dart)

`InkWell` でラップされた `Card`。タップで `CourseDialog` を表示。

### 8.1 ポートレートレイアウト

```
┌──────────────────────────────────┬──────┐
│ 前期 月1 クラスA                    │  [+] │
│ 科目名 (リンク、primaryカラー)       │      │
│ (9:00開始 備考)     教養科目・必修 2.0単位 │      │
└──────────────────────────────────┴──────┘
```

| 要素 | 内容 |
|---|---|
| 1行目 | `labelMedium`: `{学期} {曜日時限} {クラス}` |
| 2行目 | `titleMedium` (primaryカラー): 科目名 → TCU シラバスへの外部リンク |
| 3行目左 | `labelMedium`: 備考 (9:00開始、注記等。該当時のみ括弧付き) |
| 3行目右 | `labelMedium`: `{分類}・{必選} {単位数}単位` / シラバス未公開時: 「シラバス未公開」 |
| 右端ボタン | 未登録: `IconButton.filled` (➕ `playlist_add_outlined`) / 登録済: `IconButton.outlined` (✓ `playlist_add_check`) |

### 8.2 ランドスケープレイアウト

```
┌──────┬───┬──────────────────────┬──────────┬──────┬───┬──────────┐
│ 前期  │   │ クラスA               │ 教養科目  │ 2.0  │   │ [登録]   │
│ 月1   │   │ 科目名 (リンク)        │ 必修     │ 単位  │   │          │
│       │   │ (9:00開始 備考)       │          │      │   │          │
└──────┴───┴──────────────────────┴──────────┴──────┴───┴──────────┘
 64px  flex1      flex8              100px    64px  flex1
```

| 要素 | 内容 |
|---|---|
| 左端 (64px) | 学期 + 曜日時限 (縦並び) |
| 中央 (flex 8) | クラス (`labelMedium`) + 科目名 (`titleLarge`, primaryカラー, リンク) + 備考 |
| 分類 (100px) | 分類名 + 必選 (縦並び) |
| 単位 (64px) | `{単位数}単位` (右寄せ) |
| 右端ボタン | 未登録: `FilledButton.icon` (「登録」) / 登録済: `OutlinedButton.icon` (「取消」) |

### 8.3 シラバスリンク URL 構造

```
https://websrv.tcu.ac.jp/tcu_web_v3/slbssbdr.do
  ?value(risyunen)=2024
  &value(semekikn)=1
  &value(kougicd)={course.code}
  &value(crclumcd)={userData.crclumcd}
```

### 8.4 代替科目名の表示ロジック

`course.altTarget` のいずれかが `userData.crclumcd` の先頭に一致する場合、`course.altName` を表示。それ以外は `course.name` を表示。

---

## 9. CourseDialog — 科目詳細ダイアログ

> ソース: [course_dialog.dart](file:///Users/taira/Projects/Personal/Flutter/takeiteasy/lib/widgets/course_dialog.dart)

`AlertDialog(scrollable: true)` で表示。

### 9.1 タイトル
科目名 (primaryカラー、`titleLarge`) — TCU シラバスへの外部リンク

### 9.2 コンテンツ (Table)

`SelectionArea` でラップされ、テキスト選択可能:

| 行 | ラベル | 値 | 表示条件 |
|---|---|---|---|
| 1 | 学期 | `course.term` | 常時 |
| 2 | 9:00開始 | 9:00 ～ 10:40 | `course.early == true` |
| 3 | 曜日・時限 | `course.period` (改行区切り) | 常時 |
| 4 | 対象学年 | `course.grade` | 常時 |
| 5 | クラス | `course.class_` | `class_ != ""` |
| 6 | 分類 | `course.category[crclumcd]` / `-` | 常時 |
| 7 | 必修/選択 | `course.compulsoriness[crclumcd]` / `-` | 常時 |
| 8 | 単位数 | `course.credits[crclumcd]` / `-` | 常時 |
| 9 | 担当者 | `course.lecturer` (改行区切り) | 常時 |
| 10 | 講義コード | `course.code` | 常時 |
| 11 | 教室 | `course.room` (改行区切り) | `room.first != ""` |
| 12 | 備考 | `course.note` | `note != ""` |

### 9.3 アクション

| 状態 | ボタン | 動作 |
|---|---|---|
| 未登録 | `TextButton` 「登録」 | `addCourse(code)` → ダイアログを閉じる |
| 登録済 | `TextButton` 「取消」 | `removeCourse(code)` → ダイアログを閉じる |

---

## 10. TableScreen — 時間割画面

> ソース: [table_screen.dart](file:///Users/taira/Projects/Personal/Flutter/takeiteasy/lib/screens/table_screen.dart)

### 10.1 タブバー (SliverAppBar)

`DefaultTabController(length: 2)` + `TabBar`:

| タブ | 内容 |
|---|---|
| 前期 | 春学期の時間割・単位数 |
| 後期 | 秋学期の時間割・単位数 |

### 10.2 各タブの構成

各タブは `SingleChildScrollView(padding: 8)` 内に以下を縦に配置:

```
┌──────────────────────────────────┐
│          TimeTable               │  ← 時限一覧表
├──────────────────────────────────┤
│   CourseTable(前半) │ CourseTable(後半)  │  ← 週間時間割 (前半/後半)
├──────────────────────────────────┤
│   CourseWrap(通年・集中) │ CreditsTable   │  ← 通年講義 + 単位集計
└──────────────────────────────────┘
```

- **ポートレート**: 全て縦並び (`Column`)
- **ランドスケープ**: 前半/後半は横並び (`Row`)、通年/単位も横並び

#### 前期タブのデータソース

| ウィジェット | 学期フィルタ |
|---|---|
| CourseTable (前半) | `['前期', '前期前']` |
| CourseTable (後半) | `['前期', '前期後']` |
| CourseWrap (通年・集中) | `['通年', '前集中']` |
| CreditsTable | `isSpring: true` |

#### 後期タブのデータソース

| ウィジェット | 学期フィルタ |
|---|---|
| CourseTable (前半) | `['後期', '後期前']` |
| CourseTable (後半) | `['後期', '後期後']` |
| CourseWrap (通年・集中) | `['通年', '後集中']` |
| CreditsTable | `isSpring: false` |

---

## 11. TimeTable — 時限一覧表

> ソース: [time_table.dart](file:///Users/taira/Projects/Personal/Flutter/takeiteasy/lib/widgets/time_table.dart) L212–L319

各時限の開始・終了時刻を表示する参照テーブル。

| 時限 | 開始 | 終了 |
|---|---|---|
| 1時限 | 9:20 | 11:00 |
| 2時限 | 11:10 | 12:50 |
| 3時限 | 13:40 | 15:20 |
| 4時限 | 15:30 | 17:10 |
| 5時限 | 17:20 | 19:00 |

- **ポートレート**: 縦並び (各行: `{N}時限 | {開始} ~ {終了}`)
- **ランドスケープ**: 横並び (1行目: 時限名、2行目: 時刻範囲)
- `TableBorder.all` + `borderRadius: 4.0`

---

## 12. CourseTable — 週間時間割グリッド

> ソース: [time_table.dart](file:///Users/taira/Projects/Personal/Flutter/takeiteasy/lib/widgets/time_table.dart) L5–L80

6列（月〜土）× 5行（1〜5時限）のグリッドテーブル。

### テーブル構造
```
┌──────┬────┬────┬────┬────┬────┬────┐
│ 前半  │ 月 │ 火 │ 水 │ 木 │ 金 │ 土 │
├──────┼────┼────┼────┼────┼────┼────┤
│ 1時限 │    │    │    │    │    │    │
│ 2時限 │    │    │    │    │    │    │
│ 3時限 │    │    │    │    │    │    │
│ 4時限 │    │    │    │    │    │    │
│ 5時限 │    │    │    │    │    │    │
└──────┴────┴────┴────┴────┴────┴────┘
```

- 第1列 (`IntrinsicColumnWidth`): 時限ラベル
- 各セルは `TableCard` ウィジェット

---

## 13. TableCard — 時間割セル

> ソース: [time_table.dart](file:///Users/taira/Projects/Personal/Flutter/takeiteasy/lib/widgets/time_table.dart) L132–L209

| 状態 | 表示 | タップ動作 |
|---|---|---|
| 科目なし | 空白 (`SizedBox(height: 58)`) | なし |
| 科目 1 件 | 科目名 (`secondaryContainer` 背景、角丸 4px、高さ 50px、最大 2 行、中央寄せ、はみ出し省略) | `CourseDialog` を表示 |
| 科目 2 件以上 (重複) | 「重複」テキスト (`errorContainer` 背景、`onErrorContainer` テキスト色) | 重複ダイアログを表示 |

### 重複ダイアログ
`AlertDialog`:
- タイトル: 「科目が重複しています」
- コンテンツ: 重複科目名の改行区切りリスト

---

## 14. CourseWrap — 通年・集中科目リスト

> ソース: [time_table.dart](file:///Users/taira/Projects/Personal/Flutter/takeiteasy/lib/widgets/time_table.dart) L82–L130

```
┌──────────────┐
│  通年・集中     │
├──────────────┤
│  [TableCard] │
│  [TableCard] │
│  ...         │
│ (最小高さ 248px)│
└──────────────┘
```

- 各科目を `TableCard` として縦に並べて表示
- `ConstrainedBox(minHeight: 248)` で最小高さを確保

---

## 15. CreditsTable — 単位数集計テーブル

> ソース: [credits_table.dart](file:///Users/taira/Projects/Personal/Flutter/takeiteasy/lib/widgets/credits_table.dart)

### 15.1 テーブル構造

#### 前期タブ (`isSpring: true`)
```
┌──────────┬──────────┬──────┬──────┐
│  単位数   │  修得済   │ 前期  │ 合計  │
├──────────┼──────────┼──────┼──────┤
│ 教養科目  │ [入力欄]  │ 2.0  │ 4.0  │
│ 体育科目  │ [入力欄]  │ 1.0  │ 1.0  │
│ ...      │ ...      │ ...  │ ...  │
├──────────┼──────────┼──────┼──────┤
│ 合計     │ 10.0     │ 8.0  │ 18.0 │
└──────────┴──────────┴──────┴──────┘
```

#### 後期タブ (`isSpring: false`)
```
┌──────────┬──────────┬──────────┬──────┐
│  単位数   │ 修得済+前期│ 後期+通年 │ 合計  │
├──────────┼──────────┼──────────┼──────┤
│ 教養科目  │  4.0     │  2.0     │ 6.0  │
│ ...      │ ...      │ ...      │ ...  │
├──────────┼──────────┼──────────┼──────┤
│ 合計     │  18.0    │  10.0    │ 28.0 │
└──────────┴──────────┴──────────┴──────┘
```

### 15.2 カテゴリ (7行)

| カテゴリ |
|---|
| 教養科目 / 体育科目 / 外国語科目 / PBL科目 / 情報工学基盤 / 専門 / 教職科目 |

### 15.3 修得済み単位の入力欄 (前期タブのみ)

`TextFormField`:
- 数値入力 (`TextInputType.numberWithOptions(decimal: true)`)
- 正規表現フィルタ: `r'^\d+(\.\d*)?'` (正の小数)
- ヒント: `(0)`
- 未入力時: `filled: true` (背景色付き)
- 入力時: `userDataNotifier.setCredits(category, value)` で Firestore に保存
- 空入力時: `setCredits(category, null)` で削除

### 15.4 合計行

`BoxDecoration(color: surface)` + **太字** スタイル:
- 前期: `修得済合計 | 前期合計 | (修得済+前期)合計`
- 後期: `(修得済+前期)合計 | 後期合計 | (修得済+前期+後期)合計`

---

## 16. ログイン画面

> ソース: [main.dart](file:///Users/taira/Projects/Personal/Flutter/takeiteasy/lib/main.dart) L26–L46
> ルート: `/login`

`Scaffold` + `AppBar(title: 'ログイン')` + Firebase UI `SignInScreen`:

| 認証プロバイダ | 設定 |
|---|---|
| メール | `EmailAuthProvider()` |
| Google | `GoogleProvider(clientId: Env.webGoogleClientId)` |

- サインイン成功時: `AuthStateChangeAction<SignedIn>` → `context.go('/')` でホーム画面へ遷移

---

## 17. プロフィール画面

> ソース: [main.dart](file:///Users/taira/Projects/Personal/Flutter/takeiteasy/lib/main.dart) L47–L67
> ルート: `/profile`

Firebase UI `ProfileScreen`:

| 属性 | 値 |
|---|---|
| AppBar タイトル | 「プロフィール」 |
| 認証プロバイダ | Email + Google (ログインと同じ) |
| サインアウト | `SignedOutAction` → `context.go('/')` |
| アカウント削除確認 | `showDeleteConfirmationDialog: true` |
| 連携解除確認 | `showUnlinkConfirmationDialog: true` |
