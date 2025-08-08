from fastapi import Form,File,UploadFile,Depends
from fastapi.responses import FileResponse
from typing import Annotated
import os #실제로 저장하기위한 경로를 위해서 임포트
import shutil #실제로 저장하기위한 기능을 위해서 임포트
import mimetypes #미디어 타입스 
from uuid import uuid4 #id 생성용.

from sqlalchemy.orm import Session
from config.db import get_db
from service.models import Upload

#저장 위치 설정및 생성.
UPLOAD_DIR = "uploaded_images"
os.makedirs(UPLOAD_DIR, exist_ok=True) 

def get(txt:str):
  return{"result":txt}

#post 로 파일 정보 받아오기와 저장 로직.
def post(
    txt: Annotated[str, Form(...)],
    file: UploadFile = File(...),
    db: Session = Depends(get_db),     # ✅ DB 세션 주입
):
    # 확장자 추출
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else ""
    fileName = f"{uuid4().hex}.{ext}"
    filePath = os.path.join(UPLOAD_DIR, fileName)

    # 파일 저장
    with open(filePath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # ✅ DB 저장
    row = Upload(txt=txt, filename=fileName, path=filePath)
    db.add(row)
    db.commit()
    db.refresh(row)

    # 업로드 + DB 등록 결과 반환
    return {"id": row.id, "result": txt, "filename": fileName, "path": filePath}
  #./uploaded_images/test.png 저장될 파일의 물리적으로 위치 지정.
  

def read(fileName:str):
  filePath = os.path.join(UPLOAD_DIR, fileName)
  #./uploaded_images/test.png 저장될 파일의 물리적으로 위치 지정.
  midiaType, _ = mimetypes.guess_type(filePath)
  headers={
    "Content-Disposition":f"inline; filename='{fileName}'"
  }
  return FileResponse(path=filePath, filename=fileName, media_type=midiaType,headers=headers) #유동적인 미디어타입 지정
  #한글 이름이면 못읽음 예외처리 해줘야함
  #return{"result":"read()","filePath":filePath,"fileName":fileName}

# def post():
#   return {"test": "수정"}

# def put():
#   return {"test": "입력"}

# def delete():
#   return {"test": "삭제"}

study02 = {
  "prefix":"/s2", 
  "tags":["CRUD 2 연습"],
  "urls" : [ 
    {
      "methods":["GET"], 
      "path":"/", 
      "summary":"기본 조회", 
      "description":"CRUD 기본 정보를 조회합니다.",
      "endpoint": get,
    },
    {
      "methods":["POST"],
      "path":"/", "summary":"데이터 수정", "description":"CRUD 데이터를 수정합니다.",
      "endpoint": post,
    },
    # {
    #   "methods":["PUT"],
    #   "path":"/", "summary":"데이터 입력", "description":"CRUD 새로운 데이터를 입력합니다.",
    #   "endpoint": put,
    # },
    # {
    #   "methods":["DELETE"],
    #   "path":"/", "summary":"데이터 삭제", "description":"CRUD 데이터를 삭제합니다.",
    #   "endpoint": delete,
    # },
    {
      "methods":["GET"],
      "path":"/read",
      "summary":"파일 읽기",
      "description":"저장된 파일을 읽어옵니다.",
      "endpoint":read,
    }
  ]
}