import os
def get_llm(temperature=0):
    provider = os.getenv("LLM_PROVIDER","ollama").lower()
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=os.getenv("OPENAI_MODEL","gpt-4o"),temperature=temperature,api_key=os.getenv("OPENAI_API_KEY"))
    from langchain_ollama import ChatOllama
    return ChatOllama(model=os.getenv("LLM_MODEL","qwen2.5:14b"),temperature=temperature,base_url=os.getenv("OLLAMA_HOST","http://localhost:11434"))
def get_embeddings():
    provider = os.getenv("LLM_PROVIDER","ollama").lower()
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))
    from langchain_ollama import OllamaEmbeddings
    return OllamaEmbeddings(model=os.getenv("EMBEDDING_MODEL","nomic-embed-text"),base_url=os.getenv("OLLAMA_HOST","http://localhost:11434"))
