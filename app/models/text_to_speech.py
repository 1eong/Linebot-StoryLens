import ffmpeg
import gc
import nltk
import datetime
from typing import Tuple
import torch
from MeloTTS.melo.api import TTS

from app.utils.utils import PathTool
from app.models.translator import check

class Speech:
    def __init__(self):
        self.speed = 0.8
        self.device = 'cuda' # or cuda:0
        self.model = None
        self.audio_dir = PathTool.join_path("app", "static", "audio")
        # 英文詞性標注模型安裝，套件MeloTTS未安裝，遇到特俗英文字會報錯
        nltk.download('averaged_perceptron_tagger_eng')

    def __load_model(self):
        check(self.__class__.__name__, "ready to loaded")

        if self.model is None:
            self.model = TTS(language='ZH', device=self.device)
            self.speaker_ids = self.model.hps.data.spk2id
        check(self.__class__.__name__, "model loaded")

    def generate_speech(self, input: str, user_id: str) -> Tuple[str, int]:
        self.__load_model()
        
        # audio name
        timestamp = datetime.datetime.now().strftime("%d_%H%M%S")
        wav_name = f"audio_{user_id}_{timestamp}.wav"
        m4a_name = f"audio_{user_id}_{timestamp}.m4a"
        wav_path = PathTool.join_path(self.audio_dir, wav_name)
        m4a_path = PathTool.join_path(self.audio_dir, m4a_name)

        self.model.tts_to_file(input, self.speaker_ids['ZH'], wav_path, speed=self.speed)
        
        # 轉換格式並獲取音頻時長
        self.__convert_wav_to_m4a(wav_path, m4a_path)
        duration = self.__get_audio_duration(m4a_path)
        self.__clear()

        return m4a_name, duration

    @staticmethod
    def __get_audio_duration(filepath):
        try:
            probe = ffmpeg.probe(filepath)
            duration = float(probe['format']['duration'])  # duration 為浮動型數字
            ms_duration = int(duration * 1000)  # 將秒數轉換為毫秒
            return ms_duration
        except ffmpeg.Error as e:
            print(f"Error probing file {filepath}: {e}")
            return 0  # 若發生錯誤，返回 0
    
    @staticmethod
    def __convert_wav_to_m4a(input_wav: str, output_m4a: str):
        ffmpeg.input(str(input_wav)).output(str(output_m4a), acodec='aac', ab='192k').run()

    def __clear(self):
        if hasattr(self, "model"):
            del self.model
            self.model = None
        torch.cuda.empty_cache()
        gc.collect()
        check(self.__class__.__name__, "clear")
        
speech = Speech()