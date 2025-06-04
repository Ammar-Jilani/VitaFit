import os
from typing import Optional, List, Dict, Any
import re 

from langchain_huggingface import HuggingFacePipeline, HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, PyPDFLoader


from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline # Re-import these for direct pipeline creation
from transformers.trainer_utils import set_seed
import torch


from config.settings import (
    KNOWLEDGE_BASE_DATA_DIR,
    VECTOR_DB_PERSIST_PATH,
    LLM_MODEL_NAME,
    EMBEDDING_MODEL_NAME,
    HF_TOKEN 
)

class RAGAssistant:
    def __init__(self, llm_chain: RetrievalQA, off_topic_classifier_llm: Optional[HuggingFacePipeline] = None):
        self.llm_chain = llm_chain
        self.off_topic_classifier_llm = off_topic_classifier_llm

    # Renaming user_report_text to user_data_context to reflect its new purpose
    async def get_initial_overview(self, user_data_context: str) -> str:
        if not self.llm_chain:
            raise RuntimeError("RAG LLM chain is not initialized.")

        # The prompt for the overview will now include the user's data
        overview_prompt = f"""
        Based on the following user's fitness and diet data, provide a concise and encouraging health overview.
        Highlight key aspects, progress, and general recommendations.
        
        User Data:
        {user_data_context}

        Health Overview:
        """
        response = await self.llm_chain.ainvoke({"query": overview_prompt})
        return response['result']

    async def chat_with_ai(self, user_question: str, session_id: str) -> str:
        if not self.llm_chain:
            raise RuntimeError("RAG LLM chain is not initialized.")

        # Step 1: Off-topic detection
        if self.off_topic_classifier_llm:
            is_on_topic = await self._check_if_on_topic(user_question)
            if not is_on_topic:
                print(f"Question '{user_question}' classified as OFF-TOPIC.")
                return "I'm designed to help with health, fitness, nutrition, and wellness questions. Please ask something related to those topics!"
            else:
                print(f"Question '{user_question}' classified as ON-TOPIC.")

        # Step 2: Retrieve and generate the response for the on-topic question
        response = await self.llm_chain.ainvoke({"query": user_question})
        return response['result']

    async def _check_if_on_topic(self, question: str) -> bool:
        """
        Determines if a user's question is within the allowed health and fitness domain.
        """
        # Removed all DEBUG prints
        if self.off_topic_classifier_llm is None or not callable(self.off_topic_classifier_llm):
            print("Warning: Off-topic classifier LLM is None or not callable. Skipping off-topic check.")
            return True # If it's not ready, we should skip the check and proceed

        off_topic_prompt = (
            f"Does the following question strictly fall under health, fitness, nutrition, wellness, or exercise science? "
            f"Answer with only 'YES' or 'NO'.\n"
            f"Question: '{question}'\n"
            f"Answer:"
        )

        try:
            raw_response = await self.off_topic_classifier_llm.ainvoke(off_topic_prompt)
            
            response_text = ""
            if isinstance(raw_response, list) and raw_response:
                generated_text = raw_response[0].get('generated_text', '').strip() 
                if generated_text.startswith(off_topic_prompt):
                    response_text = generated_text[len(off_topic_prompt):].strip()
                else:
                    response_text = generated_text
            elif isinstance(raw_response, str):
                response_text = raw_response.strip()
                if response_text.startswith(off_topic_prompt):
                    response_text = response_text[len(off_topic_prompt):].strip()

            response_lower = response_text.lower()

            on_topic_patterns = [
                r"\byes\b", 
                r"\bhealth\b",
                r"\bfitness\b",
                r"\bnutrition\b",
                r"\bwellness\b",
                r"\bexercise\b",
                r"\bdiet\b", 
                r"\bstress\b", 
                r"\bsleep\b" 
            ]

            is_on_topic = False
            search_scope = response_lower[:50] 

            for pattern in on_topic_patterns:
                if re.search(pattern, search_scope):
                    is_on_topic = True
                    break

            if not is_on_topic:
                if re.search(r"\bno\b", search_scope) or re.search(r"\bnot\b", search_scope):
                    is_on_topic = False 
            
            print(f"Off-topic classifier raw response (after stripping prompt): '{response_text}'")
            print(f"Off-topic classifier processed response (lower): '{response_lower}'")
            print(f"Off-topic classifier result: {'ON-TOPIC' if is_on_topic else 'OFF-TOPIC'}")
            
            return is_on_topic

        except Exception as e:
            print(f"Error during off-topic check with HuggingFacePipeline: {type(e).__name__}: {e}")
            return True # Default to True if classifier fails, to avoid blocking main chat.


async def load_rag_knowledge_base():
    print(f"Loading documents from {KNOWLEDGE_BASE_DATA_DIR}...")
    documents = []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    for root, _, files in os.walk(KNOWLEDGE_BASE_DATA_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                if file.endswith(".txt"):
                    loader = TextLoader(file_path, encoding='utf-8')
                elif file.endswith(".pdf"):
                    loader = PyPDFLoader(file_path)
                else:
                    print(f"Skipping unsupported file type: {file_path}")
                    continue

                loaded_docs = loader.load()
                documents.extend(text_splitter.split_documents(loaded_docs))
                print(f"Loaded and chunked {len(loaded_docs)} pages from {file_path}")
            except Exception as e:
                print(f"Error loading {file_path}: {e}")

    if not documents:
        print("No documents loaded into knowledge base.")
        raise RuntimeError("No documents found in knowledge base directory to load. Please add content to your 'data' folder.")

    print(f"Total chunks created: {len(documents)}")

    embeddings = HuggingFaceEmbeddings( 
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={'device': 'cuda' if torch.cuda.is_available() else 'cpu'}
    )
    print(f"Embedding model '{EMBEDDING_MODEL_NAME}' loaded using HuggingFaceEmbeddings.")

    os.makedirs(VECTOR_DB_PERSIST_PATH, exist_ok=True)

    if os.path.exists(VECTOR_DB_PERSIST_PATH) and os.listdir(VECTOR_DB_PERSIST_PATH):
        print(f"Found existing vector store at {VECTOR_DB_PERSIST_PATH}. Loading it.")
        vectorstore = Chroma(persist_directory=VECTOR_DB_PERSIST_PATH, embedding_function=embeddings)
    else:
        print(f"No existing vector store found. Creating new one at {VECTOR_DB_PERSIST_PATH}...")
        vectorstore = Chroma.from_documents(documents, embeddings, persist_directory=VECTOR_DB_PERSIST_PATH)
        print("New vector store created and persisted.")

    print("Vector store initialized.")
    return vectorstore


async def initialize_rag_components(knowledge_base: Any) -> RAGAssistant:
    print(f"Loading Hugging Face LLM '{LLM_MODEL_NAME}'...")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device for LLM: {device}")

    set_seed(42) 

    # Load tokenizer and model directly for the pipeline
    tokenizer_rag = AutoTokenizer.from_pretrained(LLM_MODEL_NAME, token=HF_TOKEN, trust_remote_code=True)
    model_rag = AutoModelForCausalLM.from_pretrained(
        LLM_MODEL_NAME,
        torch_dtype=torch.float32,
        device_map="auto" if device == "cuda" else None,
        token=HF_TOKEN,
        trust_remote_code=True
    )
    model_rag.eval()

    rag_pipeline_kwargs = {
        "max_new_tokens": 512,
        "temperature": 0.8,
        "do_sample": True,
        "repetition_penalty": 1.05,
        "pad_token_id": tokenizer_rag.eos_token_id, 
        "return_full_text": False 
    }

    llm = None 
    try:
        pipe_rag = pipeline(
            "text-generation",
            model=model_rag,
            tokenizer=tokenizer_rag,
            device=0 if device == "cuda" else -1,
            **rag_pipeline_kwargs 
        )
        llm = HuggingFacePipeline(pipeline=pipe_rag)

        print(f"Main LLM '{LLM_MODEL_NAME}' loaded successfully using HuggingFacePipeline.")
    except Exception as e:
        print(f"FATAL ERROR: Failed to load main LLM '{LLM_MODEL_NAME}'. Details: {e}")
        raise RuntimeError(f"Failed to initialize main RAG LLM: {e}") 

    rag_template = """
    You are VitaFit AI Health Assistant. Answer the following question based on the context provided.
    
    User Report or Question:
    {question}

    Retrieved Knowledge Base Context:
    {context}

    Answer:
    """
    RAG_PROMPT = PromptTemplate(
        template=rag_template, input_variables=["context", "question"]
    )

    llm_chain = RetrievalQA.from_chain_type(
        llm=llm, 
        chain_type="stuff",
        retriever=knowledge_base.as_retriever(search_kwargs={"k": 3}),
        return_source_documents=False,
        chain_type_kwargs={"prompt": RAG_PROMPT} 
    )

    # Load tokenizer and model directly for the classifier pipeline
    tokenizer_classifier = AutoTokenizer.from_pretrained(LLM_MODEL_NAME, token=HF_TOKEN, trust_remote_code=True)
    model_classifier = AutoModelForCausalLM.from_pretrained(
        LLM_MODEL_NAME,
        torch_dtype=torch.float32, 
        device_map="auto" if device == "cuda" else None, 
        token=HF_TOKEN,
        trust_remote_code=True
    )
    model_classifier.eval()

    classifier_pipeline_kwargs = {
        "max_new_tokens": 10, 
        "temperature": 0.0, 
        "do_sample": False, 
        "repetition_penalty": 1.0, 
        "pad_token_id": tokenizer_classifier.eos_token_id, 
        "return_full_text": False 
    }

    off_topic_classifier_llm = None 
    try:
        off_topic_classifier_pipe = pipeline(
            "text-generation",
            model=model_classifier,
            tokenizer=tokenizer_classifier,
            device=0 if device == "cuda" else -1,
            **classifier_pipeline_kwargs 
        )
        off_topic_classifier_llm = HuggingFacePipeline(pipeline=off_topic_classifier_pipe)

        print(f"Off-topic classifier LLM '{LLM_MODEL_NAME}' loaded successfully.")
    except Exception as e:
        print(f"FATAL ERROR: Failed to load off-topic classifier LLM '{LLM_MODEL_NAME}'. Details: {e}")
        raise RuntimeError(f"Failed to initialize off-topic classifier LLM: {e}") 

    print("RAG Assistant components loaded successfully!")
    return RAGAssistant(llm_chain=llm_chain, off_topic_classifier_llm=off_topic_classifier_llm)