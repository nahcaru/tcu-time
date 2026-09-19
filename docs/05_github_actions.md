# GitHub Actions 設計・仕様・運用ガイド

TCU-TIME における GitHub Actions ワークフローの全体設計、各ワークフローの仕様、トリガー条件、およびオンデマンド実行の設定・運用手順について解説します。

---

## 1. 概要とアーキテクチャ

TCU-TIME では、システムの品質検証（CI）、大学公式サイトからの時間割自動監視・抽出、シラバス情報のオンデマンド補完、およびスケジューラの健全性維持のために 4 つの GitHub Actions ワークフローを運用しています。

### ワークフロー役割分担マトリクス

| ワークフロー名 | ファイル | トリガー | 役割・責務 |
| :--- | :--- | :--- | :--- |
| **CI** | [`ci.yml`](../.github/workflows/ci.yml) | `pull_request` (main, dev)<br>`push` (main, dev) | **品質検証**: PR作成時およびマージ時の自動テスト（pytest, bun test）、型チェック、ビルド、リント |
| **Course Data Pipeline** | [`pipeline.yml`](../.github/workflows/pipeline.yml) | 毎日 06:00 JST (`0 21 * * *`)<br>`workflow_dispatch` | **日次監視・抽出**: 大学ASCサイトの新着PDFを検知・解析し、`extractions` テーブルに未承認データとして保存。Issue通知 |
| **Course Metadata Enricher** | [`enricher.yml`](../.github/workflows/enricher.yml) | `repository_dispatch: [enrich-courses]`<br>`workflow_dispatch` | **シラバス補完（オンデマンド）**: 管理者が時間割を承認した後に発火し、シラバスから単位数・分野系列を取得して保存 |
| **Keepalive Workflows** | [`keepalive.yml`](../.github/workflows/keepalive.yml) | 毎月1日 00:00 UTC (`0 0 1 * *`)<br>`workflow_dispatch` | **健全性維持**: GitHub Actions の「60日間非アクティブによる cron 自動停止」を防止 |

---

## 2. システムライフサイクルフロー

```mermaid
flowchart TD
    subgraph Dev [1. 開発・Pull Request 時]
        PR[PR作成 / Push] --> CI[ci.yml: 自動テスト & ビルド]
        CI -->|Pass| Merge[main / dev へマージ]
    end

    subgraph Daily [2. 日次自動監視 (毎朝 06:00 JST)]
        Cron[pipeline.yml] --> Crawl[大学ASC Webサイトを巡回]
        Crawl -->|新着/更新PDFあり| Parse[時間割データを抽出・OCR]
        Parse -->|status='extracted'| DBExt[(extractions テーブル<br/>※未承認の控え)]
        Parse --> Issue[GitHub Issue 自動起票で通知]
    end

    subgraph Admin [3. 管理者による確認・承認]
        DBExt --> UI[Web管理画面: Review & Admin]
        UI -->|ワンクリック承認 (約0.5秒)| DBCourse[(courses テーブル<br/>※本番データ反映)]
    end

    subgraph OnDemand [4. シラバス補完 (承認後オンデマンド)]
        DBCourse -->|Webhook または 手動実行| Enricher[enricher.yml: オンデマンド起動]
        Enricher --> Syllabus[都市大シラバスサーバーと通信]
        Syllabus --> DBMeta[(course_metadata テーブル<br/>単位数・分野系列)]
    end
```

---

## 3. 各ワークフローの仕様詳細

### ① CI / 品質検証 (`.github/workflows/ci.yml`)

- **目的**: バグや型エラー、リント違反を PR レビュー時やマージ前に自動検知し、コードベースの健全性を担保する。
- **トリガー**:
  - `push`: `branches: [main, dev]`
  - `pull_request`: `branches: [main, dev]`
- **ジョブ構成**:
  1. **`backend` (Python)**:
     - OS: `ubuntu-latest`
     - ツール: `astral-sh/setup-uv@v7`（`enable-cache: true`）
     - 依存解決: `uv sync --frozen --extra dev`
     - テスト実行: `uv run pytest tests/ -v`（全 196 件以上の単体テスト・モックテスト）
  2. **`frontend` (TypeScript / React)**:
     - OS: `ubuntu-latest`
     - ツール: `oven-sh/setup-bun@v2`
     - 依存解決: `bun install --frozen-lockfile`
     - テスト実行: `bun test`（全 29 件以上の単体テスト）
     - 型チェック: `bun run typecheck` (`tsc --noEmit`)
     - 本番ビルド: `bun run build` (Vite production build)
     - リント検証: `bun run lint` (ESLint)
- **並列度とキャンセル**:
  - `concurrency: group: ${{ github.workflow }}-${{ github.ref }}, cancel-in-progress: true` により、同一ブランチで新しい commit が push された場合は古い CI 実行を自動キャンセルしてリソースを節約。

---

### ② Course Data Pipeline (`.github/workflows/pipeline.yml`)

- **目的**: 毎朝大学公式サイト（ASC）を巡回し、新しい時間割PDFや変更一覧PDFを検知して自動抽出する。
- **トリガー**:
  - `schedule`: `cron: "0 21 * * *"`（日本時間 06:00 JST）
  - `workflow_dispatch`（手動実行可能）
- **処理ステップ**:
  1. `actions/checkout@v6`
  2. `astral-sh/setup-uv@v7`（`enable-cache: true`）
  3. `uv sync --frozen`
  4. `uv run python -m pipeline.main`
- **パーミッション**:
  - `contents: read`
  - `issues: write`（新着検知時に GitHub Issue を起票するため）
- **安全設計**:
  - 抽出結果は Supabase の `extractions` テーブルに `status="extracted"` として一時保存されるのみで、**本番の `courses` テーブルを勝手に書き換えることはありません**。管理者がWeb画面で確認・承認した段階で初めて本番反映されます。

---

### ③ Course Metadata Enricher (`.github/workflows/enricher.yml`)

- **目的**: 時間割PDFには記載されていない「単位数（credits）」や「分野系列（category）」を、公式シラバスからスクレイピングして補完する。
- **トリガー**:
  - `repository_dispatch: types: [enrich-courses]`（オンデマンド自動実行）
  - `workflow_dispatch`（手動ワンクリック実行）
  - ※ **日次 cron は完全廃止**（新時間割が承認されるのは年に数回のみのため、毎朝の無駄な起動を撤廃）。
- **処理ステップ**:
  1. `actions/checkout@v6`
  2. `astral-sh/setup-uv@v7`（`enable-cache: true`）
  3. `uv sync --frozen`
  4. `uv run python -m pipeline.enricher`
- **技術的特徴**:
  - 都市大シラバスサーバー（`websrv.tcu.ac.jp`）は TLS 1.0/1.1 レベルの Legacy TLS を使用しているため、専用の `LegacyTLSAdapter` を介して安全に通信します。
  - サーバー負荷軽減のため、1リクエストごとに適切なインターバル（sleep）を設けています。

---

### ④ Keepalive Workflows (`.github/workflows/keepalive.yml`)

- **目的**: GitHub の仕様により、リポジトリに 60 日間コミットなどのアクティビティがないと Scheduled ワークフロー（cron）が自動的に無効化（Disabled）されるのを防ぐ。
- **トリガー**:
  - `schedule`: `cron: "0 0 1 * *"`（毎月1日 00:00 UTC）
  - `workflow_dispatch`
- **処理ステップ**:
  - `gautamkrishnar/keepalive-workflow@v2` を実行し、ダミーコミット等の操作によって cron の自動停止を恒久的に防ぎます。

---

## 4. シークレットと環境変数設定

GitHub リポジトリの **Settings > Secrets and variables > Actions** に以下のシークレットを登録します：

| シークレット名 | 必須ワークフロー | 用途・説明 |
| :--- | :--- | :--- |
| `SUPABASE_URL` | pipeline, enricher | Supabase プロジェクトの URL (`https://{project}.supabase.co`) |
| `SUPABASE_SERVICE_KEY` | pipeline, enricher | Supabase の service_role キー（RLS バイパス権限） |
| `GEMINI_API_KEY` | pipeline | Google Gemini API キー（PDF 抽出の OCR/フォールバック用） |
| `GITHUB_TOKEN` | pipeline, keepalive | GitHub Actions 組み込みトークン（自動注入。Issue作成やcron維持に使用） |

---

## 5. オンデマンド enricher のトリガー設定ガイド

管理者が Web 管理画面で時間割を「承認」した後に `enricher` を動かす方法は 2 通りあります。

### 方法A: Supabase Database Webhook による完全自動発火（推奨）

管理者が Web 画面で「承認」ボタンを押した瞬間に、自動で GitHub Actions がキックされる仕組みです。
マイグレーション（`supabase/migrations/20260919000002_enricher_webhook.sql`）により、**完全に CLI のみでセットアップ・コード管理** できます。

#### CLI によるセットアップ手順（推奨）

1. **GitHub Personal Access Token (PAT) の取得**:
   - GitHub > Settings > Developer settings > Personal access tokens (classic または fine-grained)
   - 必要な権限: `repo`（classic の場合）または `Repository permissions > Contents: Read and write` / `Metadata: Read-only`（fine-grained の場合）

2. **マイグレーションの適用 (CLI)**:
   リポジトリ内の SQL マイグレーションを Supabase にプッシュします：
   ```bash
   supabase db push
   ```
   ※ 本マイグレーションにより、`pg_net` 拡張機能、`trigger_enricher_on_approval()` 関数、および `on_extractions_approved_enricher` トリガーが作成されます。

3. **GitHub PAT を Supabase Vault に暗号化登録 (CLI)**:
   取得した PAT を、Supabase の暗号化シークレットストア（Vault）に登録します（初回 1 回のみ）：
   ```bash
   supabase db execute "select vault.create_secret('ghp_your_personal_access_token_here', 'github_pat', 'GitHub PAT for enricher webhook');"
   ```
   > [!TIP]
   > トークンは Vault 内部で AES-256 暗号化されて保管され、SQL ファイルや Git コミット履歴には一切残りません。

#### 代替: Supabase Dashboard (GUI) で手動設定する場合

GUI で設定する場合は、**Database > Webhooks** から作成可能です：
- **Name**: `trigger-enricher-on-approval`
- **Table**: `extractions`
- **Events**: `Update` のみチェック
- **Webhook Configuration**:
  - **Method**: `POST`
  - **URL**: `https://api.github.com/repos/nahcaru/tcu-time/dispatches`
  - **HTTP Headers**:
    - `Content-Type`: `application/json`
    - `Accept`: `application/vnd.github+json`
    - `Authorization`: `Bearer <YOUR_GITHUB_PAT>`
    - `User-Agent`: `TCU-TIME-Supabase-Webhook`
  - **Payload**: `{"event_type": "enrich-courses"}`

#### 安全性の保証（レースコンディション防止）
Webhook は DB 側で全授業データ（`courses`、`schedules`、`course_targets` 等）の書き込みが 100% 完了した「AFTER UPDATE」で発火し、さらに GitHub Actions の VM 起動・依存セットアップに最低 20〜40 秒かかるため、データの競合や未反映のリスクは原理的に起こり得ません。

### 方法B: GitHub Web UI / CLI からの手動実行

1. **GitHub Web UI**:
   - リポジトリの **Actions** タブを開く。
   - 左サイドバーから **Course Metadata Enricher** を選択。
   - 右上の **Run workflow** ドロップダウンからブランチを選択し、**Run workflow** ボタンをクリック。
2. **GitHub CLI (`gh`)**:
   ```bash
   gh workflow run enricher.yml
   ```

---

## 6. 開発者向けローカル検証コマンド集

CI と同一の検証をローカルで手動実行するためのコマンド一覧です。

```bash
# -------------------------------------------------------------
# バックエンド (Pipeline)
# -------------------------------------------------------------
# 依存関係の同期
uv sync --frozen --project pipeline

# 単体テスト全件実行
uv run --project pipeline pytest pipeline/tests/ -v

# -------------------------------------------------------------
# フロントエンド (Frontend)
# -------------------------------------------------------------
cd frontend

# 依存関係のインストール
bun install --frozen-lockfile

# 単体テスト全件実行
bun test

# TypeScript 型チェック
bun run typecheck

# 本番ビルド検証
bun run build

# ESLint コードスタイル検証
bun run lint
```
