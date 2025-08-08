def get():
  return {"test": "읽기"}

def post():
  return {"test": "수정"}

def put():
  return {"test": "입력"}

def delete():
  return {"test": "삭제"}

study01 = {
  "prefix":"/s1", 
  "tags":["CRUD 연습"],
  "urls" : [ 
    {
      "methods":["GET"], 
      "path":"/", "summary":"기본 조회", "description":"CRUD 기본 정보를 조회합니다.",
      "endpoint": get,
    },
    {
      "methods":["POST"],
      "path":"/", "summary":"데이터 수정", "description":"CRUD 데이터를 수정합니다.",
      "endpoint": post,
    },
    {
      "methods":["PUT"],
      "path":"/", "summary":"데이터 입력", "description":"CRUD 새로운 데이터를 입력합니다.",
      "endpoint": put,
    },
    {
      "methods":["DELETE"],
      "path":"/", "summary":"데이터 삭제", "description":"CRUD 데이터를 삭제합니다.",
      "endpoint": delete,
    }
  ]
}
