from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import date
from typing import Optional
import os

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise Exception("DATABASE_URL nao configurada!")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class PontoDesmatamento(Base):
    __tablename__ = "pontos_desmatamento"
    id = Column(Integer, primary_key=True)
    latitude = Column(Float)
    longitude = Column(Float)
    area_ha = Column(Float)
    fonte = Column(String)
    data_deteccao = Column(Date)
    municipio = Column(String)
    status = Column(String, default="pendente")
    observacoes = Column(Text)

class AcaoCampo(Base):
    __tablename__ = "acoes_campo"
    id = Column(Integer, primary_key=True)
    ponto_id = Column(Integer)
    agente_id = Column(Integer)
    data_visita = Column(Date)
    resultado = Column(String)
    observacoes = Column(Text)

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class AcaoInput(BaseModel):
    ponto_id: int
    agente_id: int
    data_visita: date
    resultado: str
    observacoes: Optional[str] = None

@app.get("/")
def raiz():
    return {"mensagem": "Servidor funcionando!"}

@app.get("/pontos")
def listar_pontos(db: Session = Depends(get_db)):
    return db.query(PontoDesmatamento).all()

@app.post("/acoes")
def registrar_acao(acao: AcaoInput, db: Session = Depends(get_db)):
    nova = AcaoCampo(**acao.model_dump())
    db.add(nova)
    db.commit()
    return {"mensagem": "Acao registrada com sucesso!"}
