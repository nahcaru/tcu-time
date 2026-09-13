# TCU-TIME (Take It More Easily)

> **「履修登録をもっと簡単に」** — 東京都市大学 総合理工学研究科向け履修支援ツール

## プロジェクト概要

TCU-TIME は、東京都市大学の大学院生（総合理工学研究科）が授業を検索・時間割を作成・単位を管理するための Web アプリケーションです。レガシー版「Take it Easy」(Flutter Web) を、モダンな技術スタックで完全にリビルドします。

## 主な機能

| 機能 | 説明 |
|---|---|
| **科目一覧・検索** | 専攻横断で科目を閲覧、オートコンプリート検索 |
| **多次元フィルタ** | 学年・学期・分類・必選・登録済み・空きコマ |
| **時間割ビルダー** | 月〜土 × 5 時限のグリッド、対開講の可視化、重複検知 |
| **単位トラッカー** | カテゴリ別の単位数自動集計 + 修得済み手動入力 |
| **シラバスリンク** | TCU シラバスページへの直リンク |
| **クラウド同期** | Supabase Auth でログイン、登録科目・設定をクラウド保存 |
| **管理画面** | LLM 抽出結果の確認・承認・再抽出トリガー |
| **自動更新** | 教学課 Web サイトの PDF 更新を自動検知・データ更新 |

## 技術スタック

| レイヤー | 技術 |
|---|---|
| フロントエンド | Vite + React + TypeScript |
| UI コンポーネント | shadcn/ui (radix-vega) + Tailwind CSS 4 |
| データベース + 認証 | Supabase (PostgreSQL + Auth + PostgREST) |
| データパイプライン | Python (GitHub Actions, 1 日 1 回) |
| PDF 抽出 | pdfplumber + Gemini 3.1 Flash-Lite (ハイブリッド) |
| ホスティング | Cloudflare Pages |

## 月額費用

**$0** — すべて無料枠内で運用可能

| サービス | 無料枠 |
|---|---|
| GitHub Actions | 2,000 分/月 |
| Gemini 3.1 Flash-Lite | プレビュー無料枠 |
| Supabase | 500MB, 50K MAU |
| Cloudflare Pages | 帯域無制限 |

## 設計書一覧

| ファイル | 内容 |
|---|---|
| [01_data_pipeline.md](./01_data_pipeline.md) | データパイプライン設計（監視・抽出・エンリッチ・配信） |
| [02_data_model.md](./02_data_model.md) | データモデル設計（DB スキーマ・課題データ構造） |
| [03_frontend.md](./03_frontend.md) | フロントエンド設計（画面構成・コンポーネント） |
| [04_infrastructure.md](./04_infrastructure.md) | インフラ設計（ホスティング・CI/CD・環境構成） |

## レガシー版との比較

| 項目 | レガシー (Take it Easy) | 新 (TCU-TIME) |
|---|---|---|
| 対象 | 学部 情報工学部 | 大学院 総合理工学研究科 |
| フレームワーク | Flutter Web | Vite + React |
| 状態管理 | Riverpod | React hooks + Supabase |
| 認証 | Firebase Auth | Supabase Auth |
| DB | Cloud Firestore | Supabase (PostgreSQL) |
| データ配信 | 静的 JSON 埋め込み | Supabase PostgREST API |
| データ更新 | 手動 (GAS + Python) | 自動 (GitHub Actions + LLM) |
| ホスティング | Firebase Hosting | Cloudflare Pages |
