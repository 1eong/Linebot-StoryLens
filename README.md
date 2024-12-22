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
- ngrok-url：目前使用ngrok部署，會在.env記錄ngrok網址，for音檔獲取網址的來源參考。

## Docker 部署
XXX
需到 line Developer 裏設定 webhook 的 url。

## 使用模型会遇到的问题
- 默认模型会下载 cpu版本的pytorch，可以根据自己的运行环境下载支援 cuda gpu 版本的 pytorch。
- GPU pytorch 版本，也要对应 cuda 和 gpu driver版本。

## 開發使用套件説明
安裝子模組的套件：poetry run pip install -r MeloTTS/requirements.txt  
- aiofiles: 異步處理下載圖片（捨棄）
- bitsandbytes: 加速模型推理，優化内存，對transformer版本有要求
- oxxruntime: 尝试使用专门优化的扩散推理框架（捨棄）
- ffprobe ：音檔轉換套件
- ffmpeg :音檔轉換工具，docker需安裝（須在環境安裝此工具）
- ntkl： 英文詞性標注模型，解決生僻字報錯問題