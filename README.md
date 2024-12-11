# Linebot StoryLens

可透過 Line 傳送圖片，並獲得一段根據該圖片編造的虛擬故事語音。

## 本地開發

虛擬環境建立：使用 `poetry env use <python版本>` 替代 `poetry shell`，可建立指定版本的 python 做開發。

啟動服務： `python run.py <env>`

#### <env> 參數

- --dev：須建立.env.dev
- --prod：須建立.env.prod
- --test：須建立.env.test

## env 環境設定

- line 的 access_token 及 secret

## Docker 部署
