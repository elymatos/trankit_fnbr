import sys
from typing import List, Dict, Any
from enum import Enum
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from trankit import Pipeline


# class App:
#     def __init__(self, scope):
#         assert scope["type"] == "http"
#         self.scope = scope
#
#     async def __call__(self, receive, send):
#         await send(
#             {
#                 "type": "http.response.start",
#                 "status": 200,
#                 "headers": [[b"content-type", b"text/plain"]],
#             }
#         )
#         version = f"{sys.version_info.major}.{sys.version_info.minor}"
#         message = f"Hello world! From Uvicorn with Gunicorn. Using Python {version}".encode(
#             "utf-8"
#         )
#         await send({"type": "http.response.body", "body": message})

class ModelName(str, Enum):
    # Enum of the available models. This allows the API to raise a more specific
    # error if an invalid model is provided.
    en = "english"
    pt = "portuguese"
    pt_gsd = "portuguese-gsd"


DEFAULT_MODEL = ModelName.pt

class Article(BaseModel):
    # Schema for a single article in a batch of articles to process
    text: str

class RequestModel(BaseModel):
    articles: List[Article]
    tokens: List[str]
    #model: ModelName = DEFAULT_MODEL
    model: str

class ResponseModel(BaseModel):
    # This is the schema of the expected response and depends on what you
    # return from get_data.
    result: Dict

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"])

#p = Pipeline(lang='portuguese', cache_dir='./cache/trankit/', gpu=True, embedding='xlm-roberta-large')
p = Pipeline(lang='portuguese', cache_dir='./cache/trankit/', gpu=False, embedding='xlm-roberta-large')
#p = Pipeline(lang='customized-mwt-ner', cache_dir='./cache/portparser')
#p = Pipeline(lang='customized-mwt-ner', cache_dir='./cache/porttinari_sud')
#en = Pipeline(lang='english', cache_dir='./cache/trankit/', gpu=True, embedding='xlm-roberta-large')
p.add('english')

@app.post("/tkparser/", summary="Process batches of text", response_model=ResponseModel)
def stanza(query: RequestModel):
    """Process a batch of articles and return the entities predicted by the
    given model. Each record in the data should have a key "text".
    """
    texts = (article.text for article in query.articles)
    all = {}
    for text in texts:
        all = p(text)
    return {"result": all}

@app.post("/tkbytoken/", summary="Process batches of text", response_model=ResponseModel)
def stanza(query: RequestModel):
    """Process a batch of articles and return the entities predicted by the
    given model. Each record in the data should have a key "text".
    """
    print(query.tokens)
#    print(query.model)
#    if (query.model == 'english'):
#        p.set_active('english')
#        all = p.posdep(query.tokens, is_sent=True)
#    else:
#        p.set_active('portuguese')
#        all = p.posdep(query.tokens, is_sent=True)
#    print(all)
    all = p.posdep(query.tokens, is_sent=True)
    return {"result": all}
