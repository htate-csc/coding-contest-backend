# algo-camp-api-tate

プログラミングコンテスト管理画面のバックエンドです。FastAPI、SQLModel、PostgreSQLで実装されています。

## 技術構成

- Python 3.10
- FastAPI
- SQLModel
- PostgreSQL
- Alembic
- uv
- Ruff
- mypy
- ty
- Pytest

## 前提

- Python 3.10 以上 (推奨: 3.10.x, `pyproject.toml` では `>=3.10,<4.0` を規定)
- uv
- PostgreSQL
- フロントエンド: [algo-camp-front-tate](https://github.com/htate-csc/algo-camp-front-tate)

## セットアップ

```bash
uv sync
```

必要に応じて仮想環境を有効化します。

```bash
source .venv/bin/activate
```

## 環境変数

設定はリポジトリ直下の `.env` から読み込まれます。主な項目は次の通りです。

- `PROJECT_NAME`
- `SECRET_KEY`
- `FRONTEND_HOST`
- `BACKEND_CORS_ORIGINS`
- `POSTGRES_SERVER`
- `POSTGRES_PORT`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `FIRST_SUPERUSER`
- `FIRST_SUPERUSER_PASSWORD`
- `SENTRY_DSN`

`FRONTEND_HOST` は未設定の場合 `http://localhost:3000` です。`POSTGRES_PORT` は未設定の場合 `6543` です。

## 開発サーバー

```bash
uv run fastapi dev app/main.py
```

APIは `/api/v1` 配下で提供されます。OpenAPI JSONは `/api/v1/openapi.json` で確認できます。

## 起動前処理

アプリケーション起動前にデータベース接続確認、マイグレーション、初期データ作成を行う場合は次を実行します。

```bash
bash scripts/prestart.sh
```

このスクリプトは次を順に実行します。

- `python app/backend_pre_start.py`
- `alembic upgrade head`
- `python app/initial_data.py`

## マイグレーション

モデル変更後はAlembicのリビジョンを作成し、データベースへ適用します。

```bash
uv run alembic revision --autogenerate -m "変更内容"
uv run alembic upgrade head
```

生成された `app/alembic/versions` 配下のファイルはコミット対象です。

## テスト

```bash
bash scripts/test.sh
```

`coverage run -m pytest tests/` を実行し、カバレッジレポートを出力します。HTMLレポートは `htmlcov/index.html` に生成されます。

## Lintと型チェック

```bash
bash scripts/lint.sh
```

このスクリプトは `mypy`、`ty`、`ruff check`、`ruff format --check` を実行します。

自動修正とフォーマットは次で実行できます。

```bash
bash scripts/format.sh
```

## OpenAPIスキーマ生成

フロントエンドのAPIクライアント更新で使うOpenAPIスキーマは次のスクリプトで生成します。

```bash
uv run python scripts/generate_openapi.py
```

生成された `openapi.json` はフロントエンド側の `npm run update-api` からも更新されます。
