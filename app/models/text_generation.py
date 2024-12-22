import torch
from transformers import pipeline, Pipeline, AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from accelerate import init_empty_weights
from app.models.translator import check
from app.utils.logger import model_logger

class MandarinLLM:
    def __init__(self):
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        self.model_name = "yentinglin/Taiwan-LLM-7B-v2.1-chat"
        self.quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,  # 使用4-bit量化
            bnb_4bit_compute_dtype=torch.bfloat16,  # 設定計算精度 (可選)
            bnb_4bit_use_double_quant=False,       # 使用double量化 (可選)
            bnb_4bit_quant_type="nf4"             # 設定量化類型，例如 'nf4' (可選)
        )
        # 使用 init_empty_weights 防止模型過早加載
        with init_empty_weights():
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                quantization_config=self.quantization_config,  # 這裡傳入量化配置
                device_map="auto",
            )
        check(self.__class__.__name__, "init")

    def __load_model(self): 
        # 加載Tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        
        # 使用 pipeline
        self.pipeline = pipeline(
            "text-generation",
            model=self.model,  # 將量化後的模型傳遞給 pipeline
            tokenizer=self.tokenizer,
            torch_dtype=torch.float16,  # 設定torch的數據類型
            device_map="auto",  # 根據設備自動設置
        )
        self.model.gradient_checkpointing_enable()
    
    def show_parameter(self):
        for name, param in self.pipeline.model.named_parameters():
            print(f"{name}: {param.device}")

    def generate_text(
            self, 
            user_input: str, 
            chat_history: list[dict] = None,
            generate_text_len: int = 600,
        ) -> str:
        """
        模型生成文字

        chat_history: List[Dict]
        - 之前的聊天記錄，範本
        - role 有 "system","user","assistant"
        [{   
            "role": "system",
            "content": "你是一位說故事家，充滿無限創意。你須要根據使用者提供的描述和故事類型延申故事劇情，内容需緊凑不拖泥帶水，且精彩有起承轉合，有結局。切忌字數介於一百至兩百字之間。"
        }]
        """
        self.__load_model()
        
        if chat_history is None:
            chat_history = [{"role": "system",
                             "content": "你是一位說故事家，充滿無限創意。你須要根據使用者提供的描述和故事類型延申故事劇情，内容需緊凑不拖泥帶水，且精彩有起承轉合，有結局。切忌字數介於一百至兩百字之間。"}]
        chat_history.append({"role": "user", "content": user_input})
        
        model_logger.info(f"[{self.__class__.__name__}] {chat_history=}")
        prompt = self.pipeline.tokenizer.apply_chat_template(chat_history, tokenize=False, add_generation_prompt=True)
        
        outputs = self.pipeline(
            prompt, 
            max_new_tokens=generate_text_len, 
            do_sample=True, 
            temperature=0.6, 
            top_k=40, 
            top_p=0.9
            )

        response = outputs[0].get("generated_text")
        new_reply = response[len(prompt):]

        model_logger.info(f"[{self.__class__.__name__}] {new_reply=}")
        self.__clear()
        return new_reply
    
    def __clear(self):
        # 刪除 pipeline 和模型
        if hasattr(self, 'pipeline'):
            del self.pipeline.model  # 刪除模型
            del self.pipeline.tokenizer  # 刪除 tokenizer
            del self.pipeline  # 刪除 pipeline 對象
            self.pipeline = None
        torch.cuda.empty_cache()
        check(self.__class__.__name__, "clear")


mandrine_llm = MandarinLLM()