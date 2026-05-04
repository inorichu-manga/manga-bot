# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Nori Manga Affiliate Bot

## 目的
漫画の名言やテーマを引用の範囲内で紹介し、アフィリエイト収益を最大化する。
のりさん節（ちょい毒・ちょいユーモア・生活感）で投稿を生成する。
毎日1〜3件の投稿を自動生成し、Make経由でXに投稿する。
前日の反応を分析し、改善サイクルを回す。

## 投稿ルール
- 台詞引用は1〜2行まで
- 「気づき」「あるある」「家族(過保護な母親）・仕事ネタ（薬品開発現場）」に変換する
- 最後にアフィリンクを自然に添える
- 唐突感がない自然な文章の流れを期待します
- 【ゆらさん節の特徴】
　- ちょい毒・ちょいユーモア
　- 自虐を少し混ぜる
　- 20代のOLによる気づき
　- 学生時代ヲタサーの姫でした
　- 理系女子（薬学系）
- 100〜160字程度

## 入力データ
Googleスプレッドシートから以下を受け取る：
- title：漫画タイトル
- quote：引用（1〜2行）
- theme：テーマ
- link：アフィリエイトURL

## 出力形式
```json
{
  "analysis": "前日の投稿の分析",
  "insights": "改善ポイント",
  "posts": [
    {"text": "投稿案1"},
    {"text": "投稿案2"},
    {"text": "投稿案3"}
  ]
}
```

## タスク
1. manga_list から1件を選ぶ
2. のりさん節で投稿文を生成
3. アフィリンクを自然に添える
4. Make に JSON で返す
5. 投稿後の反応を受け取り、改善点を抽出
6. history に保存する文章を生成

## セットアップ

### 1. 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

### 2. Google サービスアカウントの作成
1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成
2. 「APIとサービス」→「Google Sheets API」を有効化
3. 「認証情報」→「サービスアカウントを作成」
4. 作成したサービスアカウントの「キー」タブ → 「鍵を追加」→ JSON → ダウンロード
5. ダウンロードした JSON を `credentials.json` としてこのディレクトリに置く

### 3. スプレッドシートの共有設定
- スプレッドシートをサービスアカウントのメールアドレス（`...@....iam.gserviceaccount.com`）と「編集者」で共有する

### 4. 環境変数の設定
`.env.example` をコピーして `.env` を作成し、値を埋める：
```bash
cp .env.example .env
```

| 変数名 | 説明 |
|---|---|
| `SPREADSHEET_ID` | スプレッドシート URL の `/d/〇〇〇/` の部分 |
| `GOOGLE_CREDENTIALS_FILE` | サービスアカウントの JSON ファイルパス（デフォルト: `credentials.json`） |

## コード構成

### `sheets.py`
Googleスプレッドシートの読み書きモジュール。

| 関数 | 説明 |
|---|---|
| `get_manga_list()` | `manga_list` シートの全行を `list[dict]` で返す |
| `pick_manga(manga_list)` | リストからランダムに1件選ぶ |
| `get_recent_history(n=7)` | `history` シートの最新n件を取得 |
| `append_history(post, manga, analysis, insights)` | `history` シートに結果を追記 |

### スプレッドシートの列構成
**manga_list シート**（2行目以降がデータ）：

| A | B | C | D |
|---|---|---|---|
| title | quote | theme | link |

**history シート**（2行目以降がデータ）：

| A | B | C | D | E |
|---|---|---|---|---|
| date | title | post | analysis | insights |
