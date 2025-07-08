# auto-pdf-batch

---

## 目次

1. 目的・概要
2. 全体アーキテクチャ
3. 必要な環境変数・セットアップ
4. 実装詳細
    - ログイン自動化
    - 記事一覧APIの取得
    - PDF自動保存・結合
    - クラウドストレージ自動アップロード
    - チャットツールへのファイル投稿
5. チャットAPI移行の注意点
6. コード全文
7. まとめ
8. 補足・トラブルシュート

---

## 1. 目的・概要

本記事では、**Webニュース記事を自動でPDF化し、クラウドストレージおよびチャットツールに自動配信するバッチ処理**の実装手順を解説します。  
PythonのSelenium・クラウドAPI・チャットボットSDKなどを活用した業務自動化ノウハウの共有です。

---

## 2. 全体アーキテクチャ

- SeleniumでWebサービスに自動ログイン
- 記事一覧APIを通じて記事情報を取得
- 各記事を自動でPDF化
- 複数PDFを一つに結合
- クラウドストレージ（例：Google Driveなど）へアップロード
- チャットツール（例：Slackなど）にPDFファイルを投稿

---

## 3. 必要な環境変数・セットアップ

- WebサービスのユーザーID/PASS
- クラウドストレージ用の認証JSONや認証情報
- チャットボットのAPIトークン・チャンネルID
- Dockerfile例
- requirements.txt（`selenium`, `slack_sdk`, `PyPDF2`, `google-api-python-client` など）

---

## 4. 実装詳細

### 4.1 ログイン自動化

- Seleniumでログイン画面からID・パスワード入力しログイン
- モーダルウィンドウの自動操作
- Cookieの取得

### 4.2 記事一覧APIの取得

- 実際のリクエストパラメータ例
- 日付やカテゴリでの絞り込み方法
- 不要な記事（特定タイトルなど）は除外

### 4.3 PDF自動保存・結合

- ブラウザのCDPプロトコルで`Page.printToPDF`を利用
- 複数PDFを`PyPDF2.PdfMerger`で結合

### 4.4 クラウドストレージ自動アップロード

- APIを利用してPDFファイルをアップロード
- `files:write`などの権限必須
- 任意のフォルダIDを指定

### 4.5 チャットツールへのファイル投稿（新API）

- 旧APIの廃止、新APIへの移行手順
- `slack_sdk`などの導入と使い方
- Bot権限/チャンネル参加/注意点

---

## 5. チャットAPI移行の注意点

- 旧API（例：`files.upload`）の廃止・新API（例：`files_upload_v2`）への移行の背景と手順
- Bot TokenスコープやAPI廃止エラーの対策
- `pip install slack_sdk` 等が必要

---

## 6. 参考

- Selenium公式ドキュメント
- Google Drive API (Python)
- Slack SDK for Python
