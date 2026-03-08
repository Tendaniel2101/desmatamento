from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import date
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
import os

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise Exception("DATABASE_URL nao configurada!")

SECRET_KEY = os.environ.get("SECRET_KEY", "chave-secreta-desmatamento-2026")
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Agente(Base):
    __tablename__ = "agentes"
    id = Column(Integer, primary_key=True)
    nome = Column(String(100))
    email = Column(String(100), unique=True)
    senha_hash = Column(String(255))
    admin = Column(Boolean, default=False)
    ativo = Column(Boolean, default=True)

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

def verificar_senha(senha, hash):
    return pwd_context.verify(senha, hash)

def gerar_hash(senha):
    return pwd_context.hash(senha)

def criar_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def get_agente_atual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        agente = db.query(Agente).filter(Agente.email == email).first()
        if not agente:
            raise HTTPException(status_code=401, detail="Nao autorizado")
        return agente
    except:
        raise HTTPException(status_code=401, detail="Nao autorizado")

def get_admin(agente: Agente = Depends(get_agente_atual)):
    if not agente.admin:
        raise HTTPException(status_code=403, detail="Apenas admin pode fazer isso")
    return agente

class AgenteInput(BaseModel):
    nome: str
    email: str
    senha: str

class PontoInput(BaseModel):
    latitude: float
    longitude: float
    area_ha: float
    fonte: str
    data_deteccao: date
    municipio: str
    status: Optional[str] = "pendente"
    observacoes: Optional[str] = None

class AcaoInput(BaseModel):
    ponto_id: int
    agente_id: int
    data_visita: date
    resultado: str
    observacoes: Optional[str] = None

@app.get("/")
def raiz():
    return {"mensagem": "Servidor funcionando!"}

@app.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    agente = db.query(Agente).filter(Agente.email == form.username).first()
    if not agente or not verificar_senha(form.password, agente.senha_hash):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")
    token = criar_token({"sub": agente.email, "admin": agente.admin})
    return {"access_token": token, "token_type": "bearer", "nome": agente.nome, "admin": agente.admin}

@app.post("/agentes")
def criar_agente(dados: AgenteInput, admin: Agente = Depends(get_admin), db: Session = Depends(get_db)):
    if db.query(Agente).filter(Agente.email == dados.email).first():
        raise HTTPException(status_code=400, detail="Email ja cadastrado")
    novo = Agente(nome=dados.nome, email=dados.email, senha_hash=gerar_hash(dados.senha))
    db.add(novo)
    db.commit()
    return {"mensagem": f"Agente {dados.nome} criado com sucesso!"}

@app.get("/agentes")
def listar_agentes(agente: Agente = Depends(get_agente_atual), db: Session = Depends(get_db)):
    return db.query(Agente).filter(Agente.ativo == True).all()

@app.post("/admin/criar")
def criar_admin(dados: AgenteInput, db: Session = Depends(get_db)):
    if db.query(Agente).filter(Agente.admin == True).first():
        raise HTTPException(status_code=400, detail="Admin ja existe")
    novo = Agente(nome=dados.nome, email=dados.email, senha_hash=gerar_hash(dados.senha), admin=True)
    db.add(novo)
    db.commit()
    return {"mensagem": "Admin criado com sucesso!"}

@app.get("/pontos")
def listar_pontos(agente: Agente = Depends(get_agente_atual), db: Session = Depends(get_db)):
    return db.query(PontoDesmatamento).all()

@app.post("/pontos")
def criar_ponto(ponto: PontoInput, agente: Agente = Depends(get_agente_atual), db: Session = Depends(get_db)):
    novo = PontoDesmatamento(**ponto.model_dump())
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo

@app.get("/acoes")
def listar_acoes(agente: Agente = Depends(get_agente_atual), db: Session = Depends(get_db)):
    return db.query(AcaoCampo).all()

@app.post("/acoes")
def registrar_acao(acao: AcaoInput, agente: Agente = Depends(get_agente_atual), db: Session = Depends(get_db)):
    nova = AcaoCampo(**acao.model_dump())
    db.add(nova)
    db.commit()
    return {"mensagem": "Acao registrada com sucesso!"}